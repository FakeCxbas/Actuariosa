import { database } from '@/db/raw';
import { readInventory, privateHeaders } from '@/db/read';
export async function GET(req: Request) {
  try {
    return await readInventory(req);
  } catch {
    return Response.json(
      { error: 'No se pudo cargar el inventario. Intenta de nuevo.' },
      { status: 503, headers: privateHeaders },
    );
  }
}
const text = (x: unknown, max = 180) => {
  if (typeof x !== 'string' || !x.trim() || x.length > max)
    throw Error('Completa los campos obligatorios.');
  return x.trim();
};
const num = (x: unknown, integer = false) => {
  const n = typeof x === 'number' || typeof x === 'string' ? Number(x) : NaN;
  if (
    x === '' ||
    x === null ||
    (typeof x === 'string' && !x.trim()) ||
    !Number.isFinite(n) ||
    n < 0 ||
    n > 1e9 ||
    (integer && !Number.isInteger(n))
  )
    throw Error('Introduce una cantidad válida, sin valores negativos.');
  return n;
};
export async function POST(req: Request) {
  let replayId = '';
  let replayHash = '';
  try {
    const origin = req.headers.get('origin');
    if (origin && origin !== new URL(req.url).origin)
      return Response.json({ error: 'Origen no permitido' }, { status: 403 });
    const raw = await req.text();
    if (raw.length > 12000) throw Error('Solicitud demasiado grande.');
    const b = JSON.parse(raw) as Record<string, any>;
    if (!b || typeof b !== 'object' || Array.isArray(b))
      throw Error('Solicitud inválida.');
    const db = database();
    let id = crypto.randomUUID();
    if (b.action === 'product') {
      for (const key of ['cost', 'price']) {
        const amount = num(b[key]);
        if (Math.abs(amount * 100 - Math.round(amount * 100)) > 1e-6)
          throw Error('Los importes admiten hasta dos decimales.');
      }
      if (b.expiry && !/^\d{4}-\d{2}-\d{2}$/.test(b.expiry))
        throw Error('Fecha de vencimiento inválida.');
      const values = [
        text(b.name),
        text(b.sku, 80),
        String(b.barcode || '').slice(0, 80),
        text(b.category),
        text(b.unit),
        num(b.cost),
        num(b.price),
        num(b.minimum, true),
        b.supplier || null,
        String(b.expiry || '').slice(0, 10),
      ];
      if (b.id) {
        id = text(b.id);
        const current = await db
          .prepare('SELECT * FROM products WHERE id=?')
          .bind(id)
          .first<any>();
        if (!current) throw Error('El producto ya no existe.');
        if (
          current.unit !== b.unit &&
          (await db
            .prepare('SELECT id FROM movements WHERE product=? LIMIT 1')
            .bind(id)
            .first())
        )
          throw Error(
            'No se puede cambiar la unidad de un producto con historial. Crea otro SKU.',
          );
        const updated = await db
          .prepare(
            'UPDATE products SET name=CASE WHEN version=? AND (unit=? OR NOT EXISTS(SELECT 1 FROM movements WHERE product=products.id)) THEN ? ELSE NULL END,sku=?,barcode=?,category=?,unit=?,cost=?,price=?,minimum=?,supplier=?,expiry=?,version=version+1 WHERE id=?',
          )
          .bind(num(b.version, true), text(b.unit), ...values, id)
          .run();
        if (!updated.meta.changes)
          throw Error('El registro ya no existe. Actualiza el inventario.');
      } else
        await db
          .prepare(
            'INSERT INTO products (id,name,sku,barcode,category,unit,cost,price,minimum,supplier,expiry) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
          )
          .bind(id, ...values)
          .run();
    } else if (b.action === 'branch') {
      if (b.id) {
        id = text(b.id);
        const updated = await db
          .prepare(
            'UPDATE branches SET name=CASE WHEN version=? THEN ? ELSE NULL END,city=?,kind=?,version=version+1 WHERE id=?',
          )
          .bind(
            num(b.version, true),
            text(b.name),
            text(b.city),
            text(b.kind),
            id,
          )
          .run();
        if (!updated.meta.changes)
          throw Error('El registro ya no existe. Actualiza el inventario.');
      } else
        await db
          .prepare('INSERT INTO branches (id,name,city,kind) VALUES (?,?,?,?)')
          .bind(id, text(b.name), text(b.city), text(b.kind))
          .run();
    } else if (b.action === 'supplier') {
      if (b.id) {
        id = text(b.id);
        const updated = await db
          .prepare(
            'UPDATE suppliers SET name=CASE WHEN version=? THEN ? ELSE NULL END,email=?,phone=?,version=version+1 WHERE id=?',
          )
          .bind(
            num(b.version, true),
            text(b.name),
            String(b.email || '').slice(0, 180),
            String(b.phone || '').slice(0, 80),
            id,
          )
          .run();
        if (!updated.meta.changes)
          throw Error('El registro ya no existe. Actualiza el inventario.');
      } else
        await db
          .prepare(
            'INSERT INTO suppliers (id,name,email,phone) VALUES (?,?,?,?)',
          )
          .bind(
            id,
            text(b.name),
            String(b.email || '').slice(0, 180),
            String(b.phone || '').slice(0, 80),
          )
          .run();
    } else if (b.action === 'movement') {
      id = text(b.id, 80);
      const product = text(b.product),
        branch = text(b.branch),
        type = text(b.type);
      const q = num(b.quantity, true);
      const note = text(b.note, 500);
      const date = new Date().toISOString();
      if (!['Entrada', 'Salida', 'Transferencia', 'Conteo'].includes(type))
        throw Error('Tipo de movimiento inválido.');
      if (q === 0 && type !== 'Conteo')
        throw Error('La cantidad debe ser mayor que cero.');
      const destination = type === 'Transferencia' ? text(b.destination) : null;
      const expectedVersion =
        type === 'Conteo' ? num(b.expected_version, true) : null;
      const canonical = JSON.stringify({
        product,
        branch,
        type,
        quantity: q,
        note,
        destination,
        expectedVersion,
      });
      replayId = id;
      replayHash = Array.from(
        new Uint8Array(
          await crypto.subtle.digest(
            'SHA-256',
            new TextEncoder().encode(canonical),
          ),
        ),
      )
        .map((v) => v.toString(16).padStart(2, '0'))
        .join('');
      const existing = await db
        .prepare('SELECT request_hash FROM movements WHERE id=?')
        .bind(id)
        .first<{ request_hash: string }>();
      if (existing) {
        if (existing.request_hash !== replayHash)
          throw Error(
            'La referencia ya fue usada con otros datos. Abre un nuevo movimiento.',
          );
        return Response.json(
          { id, replayed: true },
          { headers: privateHeaders },
        );
      }
      const item = await db
        .prepare('SELECT cost FROM products WHERE id=?')
        .bind(product)
        .first<{ cost: number }>();
      if (!item) throw Error('El producto ya no existe.');
      const costCents = Math.round(item.cost * 100);
      if (destination === branch)
        throw Error('El destino debe ser otra sucursal.');
      const statements = [
        db
          .prepare(
            'INSERT INTO stock (product,branch,quantity) VALUES (?,?,0) ON CONFLICT DO NOTHING',
          )
          .bind(product, branch),
      ];
      if (type === 'Conteo') {
        statements.push(
          db
            .prepare(
              'INSERT INTO movements (id,product,branch,destination,type,quantity,note,created,request_hash,cost_cents) SELECT ?,product,branch,NULL,?,CASE WHEN version=? THEN ?-quantity ELSE NULL END,?,?,?,? FROM stock WHERE product=? AND branch=?',
            )
            .bind(
              id,
              type,
              expectedVersion,
              q,
              note,
              date,
              replayHash,
              costCents,
              product,
              branch,
            ),
        );
        statements.push(
          db
            .prepare(
              'UPDATE stock SET quantity=?,version=version+1 WHERE product=? AND branch=?',
            )
            .bind(q, product, branch),
        );
      } else {
        statements.push(
          db
            .prepare(
              'INSERT INTO movements (id,product,branch,destination,type,quantity,note,created,request_hash,cost_cents) VALUES (?,?,?,?,?,?,?,?,?,?)',
            )
            .bind(
              id,
              product,
              branch,
              destination,
              type,
              q,
              note,
              date,
              replayHash,
              costCents,
            ),
        );
        statements.push(
          db
            .prepare(
              'UPDATE stock SET quantity=quantity+?,version=version+1 WHERE product=? AND branch=?',
            )
            .bind(type === 'Entrada' ? q : -q, product, branch),
        );
        if (destination)
          statements.push(
            db
              .prepare(
                'INSERT INTO stock (product,branch,quantity) VALUES (?,?,?) ON CONFLICT(product,branch) DO UPDATE SET quantity=quantity+excluded.quantity,version=version+1',
              )
              .bind(product, destination, q),
          );
      }
      await db.batch(statements);
    } else if (b.action === 'demo') {
      if (await db.prepare('SELECT id FROM products LIMIT 1').first())
        throw Error('Los ejemplos solo se pueden cargar en un catálogo vacío.');
      const bs = [
        ['b1', 'Centro de distribución', 'Guayaquil', 'Almacén'],
        ['b2', 'Sucursal Norte', 'Quito', 'Tienda'],
        ['b3', 'Sucursal Centro', 'Guayaquil', 'Tienda'],
        ['b4', 'Sucursal Cuenca', 'Cuenca', 'Tienda'],
      ];
      const ps = [
        [
          'p1',
          'Café de origen 250 g',
          'ALI-001',
          'Alimentos',
          'Bolsa',
          4.8,
          8.5,
          30,
          's1',
          '2027-06-01',
        ],
        [
          'p2',
          'Camiseta esencial algodón',
          'MOD-001',
          'Moda',
          'Unidad',
          8.5,
          19.9,
          20,
          's2',
          '',
        ],
        [
          'p3',
          'Audífonos inalámbricos',
          'TEC-001',
          'Electrónica',
          'Unidad',
          24,
          49.9,
          15,
          's3',
          '',
        ],
        [
          'p4',
          'Jabón líquido 500 ml',
          'CUI-001',
          'Cuidado personal',
          'Unidad',
          2.1,
          4.5,
          25,
          's1',
          '2027-01-01',
        ],
        [
          'p5',
          'Taladro inalámbrico 20 V',
          'FER-001',
          'Ferretería',
          'Unidad',
          48,
          89.9,
          10,
          's3',
          '',
        ],
        [
          'p6',
          'Leche entera 1 L',
          'ALI-002',
          'Alimentos',
          'Unidad',
          0.85,
          1.35,
          40,
          's1',
          '2026-09-18',
        ],
        [
          'p7',
          'Zapatillas urbanas',
          'MOD-002',
          'Moda',
          'Par',
          22,
          45,
          12,
          's2',
          '',
        ],
        [
          'p8',
          'Lámpara de escritorio LED',
          'HOG-001',
          'Hogar',
          'Unidad',
          12.5,
          28,
          10,
          's3',
          '',
        ],
      ];
      const ss = [
        ['s1', 'Distribuidora Andina', 'ventas@andina.example', '04 200 0101'],
        [
          's2',
          'Textiles del Pacífico',
          'pedidos@pacifico.example',
          '02 200 0202',
        ],
        ['s3', 'Comercial Nova', 'ventas@nova.example', '07 200 0303'],
      ];
      const stmts = [
        ...bs.map((v) =>
          db
            .prepare(
              'INSERT INTO branches (id,name,city,kind) VALUES (?,?,?,?) ON CONFLICT DO NOTHING',
            )
            .bind(...v),
        ),
        ...ss.map((v) =>
          db
            .prepare(
              'INSERT INTO suppliers (id,name,email,phone) VALUES (?,?,?,?) ON CONFLICT DO NOTHING',
            )
            .bind(...v),
        ),
        ...ps.map((v) =>
          db
            .prepare(
              'INSERT INTO products (id,name,sku,category,unit,cost,price,minimum,supplier,expiry) VALUES (?,?,?,?,?,?,?,?,?,?)',
            )
            .bind(...v),
        ),
      ];
      ps.forEach((p, i) =>
        bs.forEach((b, j) => {
          const q = [
            [240, 86, 120, 64],
            [180, 52, 38, 28],
            [65, 8, 22, 16],
            [320, 72, 110, 48],
            [28, 6, 12, 9],
            [480, 24, 180, 96],
            [95, 32, 28, 0],
            [120, 36, 42, 24],
          ][i][j];
          stmts.push(
            db
              .prepare(
                'INSERT INTO stock (product,branch,quantity) VALUES (?,?,?)',
              )
              .bind(p[0], b[0], q),
          );
          stmts.push(
            db
              .prepare(
                'INSERT INTO movements (id,product,branch,destination,type,quantity,note,created) VALUES (?,?,?,NULL,?,?,?,?)',
              )
              .bind(
                crypto.randomUUID(),
                p[0],
                b[0],
                'Entrada',
                q,
                'Inventario inicial · ejemplo',
                new Date(Date.now() - (i * 4 + j) * 21600000).toISOString(),
              ),
          );
        }),
      );
      await db.batch(stmts);
    } else throw Error('Acción no válida.');
    return Response.json({ id }, { headers: privateHeaders });
  } catch (e) {
    if (replayId && replayHash) {
      try {
        const existing = await database()
          .prepare('SELECT request_hash FROM movements WHERE id=?')
          .bind(replayId)
          .first<{ request_hash: string }>();
        if (existing?.request_hash === replayHash)
          return Response.json(
            { id: replayId, replayed: true },
            { headers: privateHeaders },
          );
      } catch {}
    }
    const message = String(e);
    const conflict =
      message.includes('NOT NULL') || message.includes('otros datos');
    const error = conflict
      ? 'Los datos cambiaron desde que abriste el formulario. Ciérralo, actualiza y vuelve a intentarlo.'
      : message.includes('nonnegative_stock')
        ? 'Stock insuficiente. Revisa las existencias de la sucursal de origen.'
        : message.includes('UNIQUE')
          ? 'Ya existe un producto con ese SKU.'
          : message.includes('FOREIGN KEY')
            ? 'El producto, proveedor o sucursal no existe.'
            : message.includes('D1_')
              ? 'No se pudo guardar la operación. Vuelve a intentarlo.'
              : e instanceof Error
                ? e.message
                : 'No se pudo guardar.';
    return Response.json(
      { error },
      { status: conflict ? 409 : 400, headers: privateHeaders },
    );
  }
}
