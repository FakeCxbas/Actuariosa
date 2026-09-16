import { database } from './raw';
export const privateHeaders = {
  'Cache-Control': 'no-store, private',
  Vary: 'Cookie',
};
export async function readInventory(req: Request) {
  const db = database();
  const url = new URL(req.url);
  const mode = url.searchParams.get('mode');
  if (mode === 'history' || mode === 'history_export') {
    const page = Math.max(
      1,
      Math.min(100000, Math.floor(Number(url.searchParams.get('page')) || 1)),
    );
    const search = (url.searchParams.get('search') || '').slice(0, 180);
    const branch = url.searchParams.get('branch') || 'all';
    const where =
      "WHERE (?='all' OR m.branch=? OR m.destination=?) AND (instr(lower(p.name||' '||m.note||' '||m.type),lower(?))>0)";
    const args = [branch, branch, branch, search];
    const r = await db.batch<Record<string, any>>([
      db
        .prepare(
          `SELECT m.*,p.name AS product_name FROM movements m JOIN products p ON p.id=m.product ${where} ORDER BY m.created DESC,m.id DESC LIMIT ${mode === 'history_export' ? 10001 : 25} OFFSET ?`,
        )
        .bind(...args, mode === 'history_export' ? 0 : (page - 1) * 25),
      db
        .prepare(
          `SELECT COUNT(*) AS total FROM movements m JOIN products p ON p.id=m.product ${where}`,
        )
        .bind(...args),
    ]);
    if (mode === 'history_export' && r[0].results.length > 10000)
      return Response.json(
        {
          error:
            'La exportación supera 10.000 movimientos. Descarga el respaldo completo desde Control.',
        },
        { status: 413, headers: privateHeaders },
      );
    return Response.json(
      { rows: r[0].results, total: r[1].results[0].total, page },
      { headers: privateHeaders },
    );
  }
  if (mode === 'control') {
    const r = await db.batch<Record<string, any>>([
      db.prepare(
        `WITH ledger AS (SELECT product,branch,CASE WHEN type IN ('Entrada','Conteo') THEN quantity ELSE -quantity END AS delta FROM movements UNION ALL SELECT product,destination AS branch,quantity AS delta FROM movements WHERE type='Transferencia'), expected AS (SELECT product,branch,SUM(delta) AS quantity FROM ledger GROUP BY product,branch), keys AS (SELECT product,branch FROM stock UNION SELECT product,branch FROM expected) SELECT k.product,k.branch,COALESCE(s.quantity,0) AS actual,COALESCE(e.quantity,0) AS expected FROM keys k LEFT JOIN stock s ON s.product=k.product AND s.branch=k.branch LEFT JOIN expected e ON e.product=k.product AND e.branch=k.branch WHERE COALESCE(s.quantity,0)<>COALESCE(e.quantity,0) LIMIT 101`,
      ),
      db.prepare('SELECT * FROM audit ORDER BY id DESC LIMIT 50'),
      db.prepare('SELECT COUNT(*) AS total FROM movements'),
      db.prepare('SELECT COUNT(*) AS total FROM stock'),
    ]);
    return Response.json(
      {
        discrepancies: r[0].results,
        logs: r[1].results,
        movements: r[2].results[0].total,
        positions: r[3].results[0].total,
        checkedAt: new Date().toISOString(),
      },
      { headers: privateHeaders },
    );
  }
  if (mode === 'backup') {
    // Bounded export: never attempt an unbounded response in the 128 MB Worker.
    const counts = await db.batch<Record<string, any>>(
      ['products', 'branches', 'suppliers', 'stock', 'movements', 'audit'].map(
        (t) => db.prepare(`SELECT COUNT(*) AS n FROM ${t}`),
      ),
    );
    if (counts.reduce((sum, r) => sum + Number(r.results[0].n), 0) > 50000)
      return Response.json(
        {
          error:
            'La copia supera 50.000 registros. Solicita una exportación administrada de la base para conservar todo el historial.',
        },
        { status: 413, headers: privateHeaders },
      );
    const names = [
      'products',
      'branches',
      'suppliers',
      'stock',
      'movements',
      'audit',
      'app_state',
    ];
    const results = await db.batch<Record<string, any>>(
      names.map((t) => db.prepare(`SELECT * FROM ${t}`)),
    );
    const payload = JSON.stringify(
      Object.fromEntries(names.map((t, i) => [t, results[i].results])),
    );
    const bytes = new TextEncoder().encode(payload);
    if (bytes.length > 16000000)
      return Response.json(
        {
          error:
            'La copia supera el tamaño permitido. Solicita una exportación administrada.',
        },
        { status: 413, headers: privateHeaders },
      );
    const sha256 = Array.from(
      new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
    )
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
    return Response.json(
      {
        format: 'nexo-backup-v1',
        schemaVersion: 2,
        exportedAt: new Date().toISOString(),
        payload,
        sha256,
      },
      {
        headers: {
          ...privateHeaders,
          'Content-Disposition': 'attachment; filename="nexo-backup.json"',
        },
      },
    );
  }
  const version = await db
    .prepare("SELECT revision FROM app_state WHERE id='inventory'")
    .first<{ revision: number }>();
  const revision = version?.revision || 0;
  if (url.searchParams.get('since') === String(revision))
    return Response.json(
      { unchanged: true, revision },
      { headers: privateHeaders },
    );
  const names = ['products', 'branches', 'suppliers', 'stock', 'movements'];
  const r = await db.batch<Record<string, any>>([
    ...names.map((t) =>
      db.prepare(
        `SELECT * FROM ${t}${t === 'movements' ? ' ORDER BY created DESC LIMIT 50' : ''}`,
      ),
    ),
    db
      .prepare(
        'SELECT substr(created,1,10) AS day,type,branch,destination,SUM(quantity) AS quantity FROM movements WHERE created>=? GROUP BY day,type,branch,destination',
      )
      .bind(new Date(Date.now() - 31 * 86400000).toISOString()),
    db.prepare("SELECT revision FROM app_state WHERE id='inventory'"),
  ]);
  return Response.json(
    {
      ...Object.fromEntries(names.map((t, i) => [t, r[i].results])),
      daily: r[5].results,
      revision: r[6].results[0]?.revision || 0,
    },
    { headers: privateHeaders },
  );
}
