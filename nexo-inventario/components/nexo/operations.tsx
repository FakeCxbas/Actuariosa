'use client';
import { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Download,
  RefreshCw,
  Smartphone,
  WifiOff,
  Check,
  AlertTriangle,
  ArrowLeftRight,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
export function InstallButton() {
  const [prompt, setPrompt] = useState<any>(null),
    [help, setHelp] = useState(false),
    [installed, setInstalled] = useState(false);
  useEffect(() => {
    setInstalled(window.matchMedia('(display-mode: standalone)').matches);
    const install = (e: Event) => {
      e.preventDefault();
      setPrompt(e);
    };
    const done = () => {
      setInstalled(true);
      setPrompt(null);
    };
    window.addEventListener('beforeinstallprompt', install);
    window.addEventListener('appinstalled', done);
    if ('serviceWorker' in navigator)
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    return () => {
      window.removeEventListener('beforeinstallprompt', install);
      window.removeEventListener('appinstalled', done);
    };
  }, []);
  return (
    <div>
      <button
        className="secondary"
        onClick={async () => {
          if (prompt) {
            await prompt.prompt();
            await prompt.userChoice;
            setPrompt(null);
          } else setHelp(!help);
        }}
      >
        <Smartphone size={16} />
        {installed
          ? 'Instalada en este dispositivo'
          : 'Instalar en mi dispositivo'}
      </button>
      {help && (
        <p className="form-hint">
          En iPhone o iPad: Safari → Compartir → Añadir a pantalla de inicio. En
          Chrome o Edge: menú → Instalar aplicación, si está disponible. Inicia
          sesión en este mismo espacio desde cada dispositivo. Los movimientos
          requieren conexión.
        </p>
      )}
    </div>
  );
}
export function ControlCenter({
  products,
  branches,
  revision,
}: {
  products: { id: string; name: string }[];
  branches: { id: string; name: string }[];
  revision: number;
}) {
  const [result, setResult] = useState<any>(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [backupBusy, setBackupBusy] = useState(false),
    [saved, setSaved] = useState(false);
  async function check() {
    setBusy(true);
    setError('');
    try {
      const r = await fetch('/api/inventory?mode=control', {
        cache: 'no-store',
      });
      const j = (await r.json()) as any;
      if (!r.ok) throw Error(j.error);
      setResult(j);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo verificar');
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void check();
  }, [revision]);
  async function backup() {
    setBackupBusy(true);
    setError('');
    try {
      const r = await fetch('/api/inventory?mode=backup', {
        cache: 'no-store',
      });
      if (!r.ok) {
        const j = (await r.json()) as any;
        throw Error(j.error);
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nexo-respaldo-${new Date().toISOString().replaceAll(':', '-')}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo exportar');
    } finally {
      setBackupBusy(false);
    }
  }
  const names: any = {
    products: 'Producto',
    branches: 'Sucursal',
    suppliers: 'Proveedor',
  };
  const labels: any = {
    name: 'Nombre',
    sku: 'SKU',
    barcode: 'Código de barras',
    category: 'Categoría',
    unit: 'Unidad',
    cost: 'Costo',
    price: 'Precio',
    minimum: 'Stock mínimo',
    expiry: 'Vencimiento',
    supplier: 'Proveedor',
    city: 'Ciudad',
    kind: 'Tipo',
    email: 'Correo',
    phone: 'Teléfono',
  };
  return (
    <div className="control-center">
      <p className="analysis-link">
        <a href="/viabilidad.html">
          Ver análisis de costos y calculadora de rentabilidad ↗
        </a>
      </p>
      <div className="control-grid">
        <section className="panel control-card">
          <div className="control-icon">
            <ShieldCheck />
          </div>
          <h2>Integridad de las existencias</h2>
          <p>
            Compara el saldo actual con todas las entradas, salidas,
            transferencias y ajustes registrados.
          </p>
          <div
            className={
              'integrity-status ' +
              (result?.discrepancies.length ? 'amber-text' : 'green-text')
            }
          >
            {result ? (
              result.discrepancies.length ? (
                <>
                  <AlertTriangle size={19} /> Hay diferencias para revisar
                </>
              ) : (
                <>
                  <Check size={19} /> Saldos e historial coinciden
                </>
              )
            ) : (
              'Verificando…'
            )}
          </div>
          {result && (
            <p>
              {result.positions} posiciones · {result.movements} movimientos
              <br />
              Comprobado: {new Date(result.checkedAt).toLocaleString('es-EC')}
            </p>
          )}
          <button className="secondary" disabled={busy} onClick={check}>
            <RefreshCw size={15} />
            {busy ? 'Verificando…' : 'Verificar nuevamente'}
          </button>
          <small>
            La conciliación comprueba los registros. Confirma el inventario real
            mediante conteos físicos.
          </small>
        </section>
        <section className="panel control-card">
          <div className="control-icon">
            <Download />
          </div>
          <h2>Tus datos pueden acompañarte</h2>
          <p>
            Descarga una copia con productos, ubicaciones, proveedores,
            existencias, movimientos y bitácora. Incluye una huella para
            detectar archivos dañados.
          </p>
          <button className="primary" disabled={backupBusy} onClick={backup}>
            <Download size={16} />
            {backupBusy ? 'Preparando copia…' : 'Descargar respaldo completo'}
          </button>
          {saved && (
            <p className="green-text" role="status">
              Copia descargada. Guárdala en un lugar seguro.
            </p>
          )}
          <small>
            Hasta 50.000 registros y 16 MB de contenido. Para más volumen se
            necesita una exportación administrada. La restauración se realiza en
            una base nueva, sin sobrescribir tu operación.
          </small>
        </section>
        <section className="panel control-card">
          <div className="control-icon">
            <Smartphone />
          </div>
          <h2>La misma app, donde estés</h2>
          <p>
            Accede desde teléfono, tablet o PC y añádela a tu pantalla de inicio
            cuando el navegador lo permita.
          </p>
          <InstallButton />
          <div className="form-hint">
            <WifiOff size={16} /> Sin conexión, los movimientos no se envían ni
            se confirman. Al regresar, actualizamos los saldos.
          </div>
        </section>
      </div>
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}
      {result?.discrepancies.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <h2>Diferencias entre saldo e historial</h2>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                {['Producto', 'Sucursal', 'Saldo', 'Según historial'].map(
                  (h) => (
                    <TableHead key={h}>{h}</TableHead>
                  ),
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.discrepancies.map((d: any) => (
                <TableRow key={d.product + d.branch}>
                  <TableCell>
                    {products.find((p) => p.id === d.product)?.name ||
                      d.product}
                  </TableCell>
                  <TableCell>
                    {branches.find((b) => b.id === d.branch)?.name || d.branch}
                  </TableCell>
                  <TableCell>{d.actual}</TableCell>
                  <TableCell>{d.expected}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="form-hint">
            Investiga la diferencia antes de ajustar. La app no corrige saldos
            automáticamente.
          </p>
        </section>
      )}
      <section className="panel audit-panel">
        <div className="panel-heading">
          <div>
            <h2>Bitácora de cambios</h2>
            <p>
              Últimos 50 cambios de catálogo y ubicaciones desde esta
              actualización.
            </p>
          </div>
          <ShieldCheck size={19} />
        </div>
        {result?.logs.length ? (
          result.logs.map((log: any) => {
            const before = JSON.parse(log.before || 'null'),
              after = JSON.parse(log.after || 'null');
            return (
              <details className="audit-entry" key={log.id}>
                <summary>
                  <span className="audit-dot" />
                  <div>
                    <b>
                      {names[log.entity] || log.entity} ·{' '}
                      {after?.name || before?.name}
                    </b>
                    <small>
                      {log.action === 'INSERT'
                        ? 'Creado'
                        : log.action === 'UPDATE'
                          ? 'Actualizado'
                          : 'Eliminado'}{' '}
                      · {new Date(log.created).toLocaleString('es-EC')}
                    </small>
                  </div>
                  <span>Ver cambios</span>
                </summary>
                <div className="audit-changes">
                  {Object.keys(after || before || {})
                    .filter(
                      (k) =>
                        !['id', 'version'].includes(k) &&
                        before?.[k] !== after?.[k],
                    )
                    .map((k) => (
                      <p key={k}>
                        <b>{labels[k] || k}</b>
                        <span>
                          {String(before?.[k] ?? '—')} →{' '}
                          {String(after?.[k] ?? '—')}
                        </span>
                      </p>
                    ))}
                </div>
              </details>
            );
          })
        ) : (
          <div className="empty-state">
            <p>Aquí aparecerán los próximos cambios.</p>
          </div>
        )}
        <p className="audit-note">
          Espacio privado del propietario. Esta bitácora registra valores y
          fechas; la identificación y los permisos individuales de empleados
          requieren una fase de multiusuario.
        </p>
      </section>
    </div>
  );
}
export function MovementHistory({
  branch,
  search,
  branches,
  revision,
}: {
  branch: string;
  search: string;
  branches: { id: string; name: string }[];
  revision: number;
}) {
  const [page, setPage] = useState(1),
    [data, setData] = useState<any>({ rows: [], total: 0 }),
    [error, setError] = useState(''),
    [loading, setLoading] = useState(true);
  useEffect(() => setPage(1), [branch, search]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const t = setTimeout(() => {
      fetch(
        '/api/inventory?' +
          new URLSearchParams({
            mode: 'history',
            branch,
            search,
            page: String(page),
          }),
        { signal: controller.signal, cache: 'no-store' },
      )
        .then(async (r) => {
          const j = (await r.json()) as any;
          if (!r.ok) throw Error(j.error);
          setData(j);
          setError('');
        })
        .catch((e) => {
          if (e.name !== 'AbortError')
            setError('No se pudo cargar el historial.');
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 180);
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [branch, search, page, revision]);
  const name = (id: string) => branches.find((b) => b.id === id)?.name || id;
  return (
    <>
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            {[
              'Movimiento',
              'Producto',
              'Sucursal / destino',
              'Cantidad',
              'Referencia',
              'Fecha',
            ].map((h) => (
              <TableHead key={h}>{h}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.rows.map((m: any) => (
            <TableRow key={m.id}>
              <TableCell>
                <span className="movement-type">
                  <ArrowLeftRight size={16} />
                  {m.type}
                </span>
              </TableCell>
              <TableCell>{m.product_name}</TableCell>
              <TableCell>
                {name(m.branch)}
                {m.destination && (
                  <small className="unit-label">→ {name(m.destination)}</small>
                )}
              </TableCell>
              <TableCell>
                {m.type === 'Salida' ? '-' : m.type === 'Entrada' ? '+' : ''}
                {m.quantity}
              </TableCell>
              <TableCell className="note-cell">{m.note}</TableCell>
              <TableCell>
                <span className="date-cell">
                  {new Date(m.created).toLocaleString('es-EC')}
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!data.rows.length && (
        <div className="empty-state">
          {loading ? 'Cargando…' : 'No hay movimientos con estos filtros.'}
        </div>
      )}
      <div className="table-footer">
        <span>
          {data.total} movimientos ·{' '}
          {loading ? 'Actualizando…' : 'Historial completo'}
        </span>
        <div className="pagination">
          <button
            disabled={page === 1 || loading}
            onClick={() => setPage(page - 1)}
          >
            Anterior
          </button>
          <span>
            {page} / {Math.max(1, Math.ceil(data.total / 25))}
          </span>
          <button
            disabled={page * 25 >= data.total || loading}
            onClick={() => setPage(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
    </>
  );
}
