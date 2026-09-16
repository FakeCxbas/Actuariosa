'use client';
import { useEffect, useMemo, useState, useRef, type FormEvent } from 'react';
import {
  ShieldCheck,
  Package,
  LayoutDashboard,
  ArrowLeftRight,
  Warehouse,
  Truck,
  ChartNoAxesCombined,
  Bell,
  Plus,
  Search,
  ChevronRight,
  Boxes,
  ArrowUpRight,
  CircleHelp,
  Check,
  Download,
  AlertTriangle,
  MapPin,
  Pencil,
  X,
  RefreshCw,
  Coffee,
  Shirt,
  Headphones,
  Droplets,
  Wrench,
  Milk,
  Footprints,
  LampDesk,
} from 'lucide-react';
import {
  SidebarProvider,
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarTrigger,
  useSidebar,
} from '@/components/ui/sidebar';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ControlCenter, MovementHistory } from '@/components/nexo/operations';
import { Progress } from '@/components/ui/progress';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
type Product = {
  id: string;
  name: string;
  sku: string;
  barcode: string;
  category: string;
  unit: string;
  cost: number;
  price: number;
  minimum: number;
  supplier: string | null;
  expiry: string;
};
type Branch = { id: string; name: string; city: string; kind: string };
type Supplier = { id: string; name: string; email: string; phone: string };
type Movement = {
  id: string;
  product: string;
  branch: string;
  destination: string | null;
  type: string;
  quantity: number;
  note: string;
  created: string;
};
type Data = {
  products: Product[];
  branches: Branch[];
  suppliers: Supplier[];
  stock: {
    product: string;
    branch: string;
    quantity: number;
    version: number;
  }[];
  movements: Movement[];
  revision: number;
  daily: {
    day: string;
    type: string;
    branch: string;
    destination: string | null;
    quantity: number;
  }[];
};
const empty: Data = {
  products: [],
  branches: [],
  suppliers: [],
  stock: [],
  movements: [],
  revision: 0,
  daily: [],
};
const nav = [
  [LayoutDashboard, 'Resumen'],
  [Package, 'Inventario'],
  [ArrowLeftRight, 'Movimientos'],
  [Warehouse, 'Sucursales'],
  [Truck, 'Proveedores'],
  [ChartNoAxesCombined, 'Reportes'],
  [ShieldCheck, 'Control'],
] as const;
const categories = [
  'Alimentos',
  'Moda',
  'Electrónica',
  'Cuidado personal',
  'Ferretería',
  'Hogar',
  'Otros',
];
const money = (n: number) =>
  new Intl.NumberFormat('es-EC', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(n);
const integer = (n: number) => new Intl.NumberFormat('es-EC').format(n);
function Picker({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (s: string) => void;
  options: { value: string; label: string }[];
  label: string;
}) {
  return (
    <Select
      value={value}
      onValueChange={(v) => v !== null && onChange(v)}
      items={options}
    >
      <SelectTrigger aria-label={label} className="picker">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
function Nav({
  view,
  onChange,
}: {
  view: string;
  onChange: (x: string) => void;
}) {
  const { setOpenMobile } = useSidebar();
  return (
    <nav>
      {nav.map(([Icon, label]) => (
        <button
          className={label === view ? 'nav-item active' : 'nav-item'}
          onClick={() => {
            onChange(label);
            setOpenMobile(false);
          }}
          key={label}
        >
          <Icon size={19} />
          {label}
        </button>
      ))}
    </nav>
  );
}
const productIcons = [
  Coffee,
  Shirt,
  Headphones,
  Droplets,
  Wrench,
  Milk,
  Footprints,
  LampDesk,
];
function ProductIcon({ p }: { p: Product }) {
  const i = [
    'ALI-001',
    'MOD-001',
    'TEC-001',
    'CUI-001',
    'FER-001',
    'ALI-002',
    'MOD-002',
    'HOG-001',
  ].indexOf(p.sku);
  const Icon = productIcons[i] || Package;
  return (
    <span className={'product-icon color-' + (Math.max(i, 0) % 5)}>
      <Icon size={20} />
    </span>
  );
}
export default function Home() {
  const [data, setData] = useState<Data>(empty),
    [view, setView] = useState('Resumen'),
    [branch, setBranch] = useState('all'),
    [search, setSearch] = useState(''),
    [category, setCategory] = useState('all'),
    [status, setStatus] = useState('all'),
    [period, setPeriod] = useState('7'),
    [page, setPage] = useState(1),
    [modal, setModal] = useState<string | null>(null),
    [form, setForm] = useState<Record<string, string>>({}),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [notice, setNotice] = useState(''),
    [connection, setConnection] = useState(false),
    [syncError, setSyncError] = useState(''),
    [lastSync, setLastSync] = useState('');
  const revisionRef = useRef<number | null>(null),
    requestRef = useRef<Promise<boolean> | null>(null);
  async function refresh(force = false): Promise<boolean> {
    if (requestRef.current) {
      await requestRef.current;
      if (force) return refresh(true);
      return true;
    }
    const task = (async () => {
      try {
        const r = await fetch(
          '/api/inventory' +
            (!force && revisionRef.current !== null
              ? '?since=' + revisionRef.current
              : ''),
          { cache: 'no-store' },
        );
        const j = (await r.json()) as Data & {
          error?: string;
          unchanged?: boolean;
        };
        if (!r.ok) throw Error(j.error || 'No se pudo actualizar');
        if (!j.unchanged) {
          setData(j);
          revisionRef.current = j.revision;
        }
        setConnection(true);
        setSyncError('');
        setLastSync(
          new Date().toLocaleTimeString('es-EC', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          }),
        );
        return true;
      } catch (e) {
        setSyncError(e instanceof Error ? e.message : 'No se pudo conectar');
        setConnection(false);
        return false;
      } finally {
        setLoading(false);
      }
    })();
    requestRef.current = task;
    try {
      return await task;
    } finally {
      requestRef.current = null;
    }
  }
  useEffect(() => {
    void refresh();
    const update = () => {
      if (document.visibilityState === 'visible' && navigator.onLine)
        void refresh();
    };
    const offline = () => {
      setConnection(false);
      setSyncError(
        'Sin conexión. Los saldos pueden estar desactualizados; los movimientos no se enviarán.',
      );
    };
    const timer = setInterval(update, 60000);
    document.addEventListener('visibilitychange', update);
    window.addEventListener('online', update);
    window.addEventListener('offline', offline);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', update);
      window.removeEventListener('online', update);
      window.removeEventListener('offline', offline);
    };
  }, []);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(''), 4500);
    return () => clearTimeout(t);
  }, [notice]);
  useEffect(() => {
    setPage(1);
  }, [search, category, status, branch, view]);
  useEffect(() => {
    const context = (document as any).modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    Promise.resolve(
      context.registerTool(
        {
          name: 'search_inventory',
          title: 'Buscar inventario',
          description:
            'Busca productos por nombre, SKU o código y muestra el inventario filtrado.',
          inputSchema: {
            type: 'object',
            properties: { query: { type: 'string', maxLength: 180 } },
            required: ['query'],
            additionalProperties: false,
          },
          annotations: { readOnlyHint: true },
          execute(input: unknown) {
            const q = (input as any)?.query;
            if (typeof q !== 'string' || q.length > 180)
              throw Error('Consulta inválida');
            setView('Inventario');
            setSearch(q);
            return {
              products: data.products
                .filter((p) =>
                  (p.name + ' ' + p.sku + ' ' + p.barcode)
                    .toLowerCase()
                    .includes(q.toLowerCase()),
                )
                .map((p) => ({ id: p.id, name: p.name, sku: p.sku })),
            };
          },
        },
        { signal: lifecycle.signal },
      ),
    ).catch(() => {});
    return () => lifecycle.abort();
  }, [data.products]);
  const qty = (id: string, b = branch) =>
    data.stock
      .filter((s) => s.product === id && (b === 'all' || s.branch === b))
      .reduce((n, s) => n + s.quantity, 0);
  const low = (p: Product) =>
    branch === 'all'
      ? data.branches.some((b) => qty(p.id, b.id) <= p.minimum)
      : qty(p.id) <= p.minimum;
  const rows = data.products.filter(
    (p) =>
      (p.name + ' ' + p.sku + ' ' + p.barcode)
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (category === 'all' || p.category === category) &&
      (status === 'all' || (status === 'low' ? low(p) : !low(p))),
  );
  const stocks = data.stock.filter(
    (s) => branch === 'all' || s.branch === branch,
  );
  const total = stocks.reduce((n, s) => n + s.quantity, 0),
    value = stocks.reduce(
      (n, s) =>
        n +
        (s.quantity *
          Math.round(
            (data.products.find((p) => p.id === s.product)?.cost || 0) * 100,
          )) /
          100,
      0,
    );
  const alerts = data.branches
    .filter((b) => branch === 'all' || b.id === branch)
    .flatMap((b) =>
      data.products
        .filter((p) => qty(p.id, b.id) <= p.minimum)
        .map((p) => ({ p, b, q: qty(p.id, b.id) })),
    )
    .sort((a, b) => a.q - b.q);
  const branchOptions = [
    { value: 'all', label: 'Todas las sucursales' },
    ...data.branches.map((b) => ({ value: b.id, label: b.name })),
  ];
  const moves = data.movements.filter(
    (m) =>
      (branch === 'all' || m.branch === branch || m.destination === branch) &&
      (
        (data.products.find((p) => p.id === m.product)?.name || '') +
        ' ' +
        m.note +
        ' ' +
        m.type
      )
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const chart = useMemo(
    () =>
      Array.from({ length: Number(period) }, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - Number(period) + 1 + i);
        const key = d.toISOString().slice(0, 10);
        const ms = data.daily.filter(
          (m) =>
            m.day === key &&
            (branch === 'all' ||
              m.branch === branch ||
              m.destination === branch),
        );
        return {
          day: d.toLocaleDateString('es-EC', {
            day: '2-digit',
            month: 'short',
          }),
          Entradas: ms
            .filter((m) => m.type === 'Entrada')
            .reduce((n, m) => n + m.quantity, 0),
          Salidas: ms
            .filter((m) => m.type === 'Salida')
            .reduce((n, m) => n + m.quantity, 0),
        };
      }),
    [data.daily, period, branch],
  );
  const bName = (id: string | null) =>
    data.branches.find((b) => b.id === id)?.name || '—';
  function open(type: string, p?: Product | Branch | Supplier) {
    setError('');
    setModal(type);
    setForm(
      p
        ? Object.fromEntries(
            Object.entries(p).map(([k, v]) => [k, String(v ?? '')]),
          )
        : {
            type: 'Entrada',
            product: data.products[0]?.id || '',
            branch: branch === 'all' ? data.branches[0]?.id || '' : branch,
            destination: data.branches[1]?.id || '',
            category: 'Alimentos',
            unit: 'Unidad',
            minimum: '10',
            cost: '0',
            price: '0',
            kind: 'Tienda',
            supplier: '',
            quantity: '1',
            id: crypto.randomUUID(),
            expected_version: String(
              data.stock.find(
                (s) =>
                  s.product === data.products[0]?.id &&
                  s.branch ===
                    (branch === 'all' ? data.branches[0]?.id : branch),
              )?.version || 0,
            ),
          },
    );
  }
  async function mutate(body: object) {
    if (!navigator.onLine)
      throw Error('No hay conexión. No se envió la operación.');
    const r = await fetch('/api/inventory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const j = (await r.json()) as { id?: string; error?: string };
    if (!r.ok) throw Error(j.error || 'No se pudo completar la operación');
    await refresh(true);
    return j;
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const payload = { ...form, action: modal };
      if (
        modal !== 'movement' &&
        ![...data.products, ...data.branches, ...data.suppliers].some(
          (p) => p.id === form.id,
        )
      )
        delete (payload as any).id;
      await mutate(payload);
      setModal(null);
      setNotice('Operación confirmada por el servidor.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo guardar.');
    } finally {
      setBusy(false);
    }
  }
  async function demo() {
    setBusy(true);
    try {
      await mutate({ action: 'demo' });
      setNotice('Datos de ejemplo cargados. Ya puedes explorar la operación.');
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }
  async function download() {
    let exportMoves = moves;
    if (view === 'Movimientos') {
      try {
        const r = await fetch(
          '/api/inventory?' +
            new URLSearchParams({ mode: 'history_export', branch, search }),
          { cache: 'no-store' },
        );
        const j = (await r.json()) as any;
        if (!r.ok) throw Error(j.error);
        exportMoves = j.rows;
      } catch (e) {
        setError(e instanceof Error ? e.message : 'No se pudo exportar');
        return;
      }
    }
    const csvCell = (v: unknown) =>
      '"' +
      String(v ?? '')
        .replace(/^[=+@-]/, "'$&")
        .replaceAll('"', '""') +
      '"';
    const columns =
      view === 'Sucursales'
        ? ['Sucursal', 'Ciudad', 'Tipo', 'Unidades']
        : view === 'Proveedores'
          ? ['Proveedor', 'Correo', 'Teléfono']
          : view === 'Movimientos'
            ? [
                'Fecha',
                'Tipo',
                'Producto',
                'Origen',
                'Destino',
                'Cantidad',
                'Referencia',
              ]
            : [
                'SKU',
                'Producto',
                'Categoría',
                'Unidad',
                'Existencias',
                'Costo USD',
                'Precio USD',
                'Mínimo',
                'Vencimiento',
              ];
    const records =
      view === 'Sucursales'
        ? data.branches.map((b) => [
            b.name,
            b.city,
            b.kind,
            data.stock
              .filter((s) => s.branch === b.id)
              .reduce((n, s) => n + s.quantity, 0),
          ])
        : view === 'Proveedores'
          ? data.suppliers.map((s) => [s.name, s.email, s.phone])
          : view === 'Movimientos'
            ? exportMoves.map((m) => [
                m.created,
                m.type,
                data.products.find((p) => p.id === m.product)?.name,
                bName(m.branch),
                m.destination ? bName(m.destination) : '',
                m.quantity,
                m.note,
              ])
            : rows.map((p) => [
                p.sku,
                p.name,
                p.category,
                p.unit,
                qty(p.id),
                p.cost,
                p.price,
                p.minimum,
                p.expiry,
              ]);
    const url = URL.createObjectURL(
      new Blob(
        [
          '\uFEFF' +
            [columns, ...records]
              .map((r) => r.map(csvCell).join(','))
              .join('\r\n'),
        ],
        { type: 'text/csv;charset=utf-8;' },
      ),
    );
    const a = document.createElement('a');
    a.href = url;
    a.download = `nexo-${view.toLowerCase()}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    setNotice('Archivo CSV exportado.');
  }
  function field(name: string, label: string, type = 'text', required = true) {
    return (
      <label className="field" key={name}>
        {label}
        <input
          type={type}
          required={required}
          value={form[name] || ''}
          maxLength={type === 'text' ? 180 : undefined}
          min={type === 'number' ? 0 : undefined}
          step={
            type === 'number'
              ? name === 'price' || name === 'cost'
                ? '0.01'
                : '1'
              : undefined
          }
          onChange={(e) => setForm({ ...form, [name]: e.target.value })}
        />
      </label>
    );
  }
  function selectField(
    name: string,
    label: string,
    options: { value: string; label: string }[],
  ) {
    return (
      <label className="field">
        {label}
        <Picker
          value={form[name] || ''}
          onChange={(v) =>
            setForm({
              ...form,
              [name]: v,
              ...(['product', 'branch'].includes(name)
                ? {
                    expected_version: String(
                      data.stock.find(
                        (s) =>
                          s.product ===
                            (name === 'product' ? v : form.product) &&
                          s.branch === (name === 'branch' ? v : form.branch),
                      )?.version || 0,
                    ),
                  }
                : {}),
            })
          }
          options={options}
          label={label}
        />
      </label>
    );
  }
  function go(v: string) {
    setView(v);
    setSearch('');
    setCategory('all');
    setStatus('all');
  }
  const productTable = (compact = false) => (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Producto</TableHead>
            <TableHead>Categoría</TableHead>
            <TableHead className="numeric">Existencias</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead className="numeric">Costo unitario</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {(compact
            ? rows.slice(0, 5)
            : rows.slice((page - 1) * 10, page * 10)
          ).map((p) => (
            <TableRow key={p.id}>
              <TableCell>
                <button
                  className="product-name"
                  onClick={() => open('product', p)}
                >
                  <ProductIcon p={p} />
                  <span>
                    <b>{p.name}</b>
                    <small>{p.sku}</small>
                  </span>
                </button>
              </TableCell>
              <TableCell>
                <span className="category-label">{p.category}</span>
              </TableCell>
              <TableCell className="numeric">
                <b>{integer(qty(p.id))}</b>
                <small className="unit-label">{p.unit.toLowerCase()}</small>
              </TableCell>
              <TableCell>
                <span
                  className={
                    'badge ' +
                    (qty(p.id) === 0 ? 'red' : low(p) ? 'amber' : 'green')
                  }
                >
                  <i />
                  {qty(p.id) === 0
                    ? 'Agotado'
                    : low(p)
                      ? 'Stock bajo'
                      : 'Disponible'}
                </span>
              </TableCell>
              <TableCell className="numeric">{money(p.cost)}</TableCell>
              <TableCell>
                <button
                  className="icon-button"
                  aria-label={'Editar ' + p.name}
                  onClick={() => open('product', p)}
                >
                  <Pencil size={15} />
                </button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {rows.length === 0 && (
        <div className="empty-state">
          <Package />
          <h2>
            {loading ? 'Cargando inventario…' : 'Sin productos para mostrar'}
          </h2>
          <p>
            {search || category !== 'all' || status !== 'all'
              ? 'Prueba otros filtros.'
              : 'Agrega tu primer producto o carga datos de ejemplo.'}
          </p>
        </div>
      )}
    </>
  );
  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader>
          <div className="brand">
            <Boxes /> nexo<span>INVENTARIO</span>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <div className="workspace">
            <span className="workspace-icon">N</span>
            <div>
              <b>Mi organización</b>
              <small>Gestión multisucursal</small>
            </div>
          </div>
          <p className="nav-label">OPERACIÓN</p>
          <Nav view={view} onChange={go} />
        </SidebarContent>
        <SidebarFooter>
          <button className="help-card" onClick={() => setModal('help')}>
            <CircleHelp size={20} />
            <b>Cada movimiento cuenta</b>
            <p>
              Conoce tu espacio de trabajo <ArrowUpRight size={13} />
            </p>
          </button>
          <div className="profile">
            <span className="avatar">AD</span>
            <div>
              <b>Administrador</b>
              <small>Espacio privado</small>
            </div>
            <span className="live-dot" />
          </div>
        </SidebarFooter>
      </Sidebar>
      <div className="app-body">
        <header className="topbar">
          <div>
            <SidebarTrigger />
            <span>Espacio de trabajo</span>
            <ChevronRight size={14} />
            <b>{view}</b>
          </div>
          <div>
            <span className={connection ? 'live-dot' : 'offline-dot'} />
            <span>{connection ? 'Conectado' : 'Conectando'}</span>
            <button
              className="notification-button"
              aria-label="Ver alertas de inventario"
              onClick={() => setModal('alerts')}
            >
              <Bell size={19} />
              {alerts.length > 0 && <i />}
            </button>
            <span className="top-avatar">AD</span>
          </div>
        </header>
        <main className="main">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                {view === 'Resumen' ? 'VISTA GENERAL' : 'GESTIÓN DE INVENTARIO'}
              </div>
              <h1>
                {view === 'Resumen' ? (
                  <>
                    Tu operación, en un vistazo<span>.</span>
                  </>
                ) : (
                  view
                )}
              </h1>
              <p>
                {
                  {
                    Resumen:
                      'El pulso de tu inventario, en todas tus sucursales.',
                    Inventario:
                      'Cada producto, cada unidad, en el lugar correcto.',
                    Movimientos:
                      'La trazabilidad de todas tus entradas, salidas y transferencias.',
                    Sucursales:
                      'Conecta tus tiendas y centros de distribución.',
                    Proveedores:
                      'Tus aliados de abastecimiento, en un solo lugar.',
                    Control:
                      'Verifica saldos, revisa cambios y conserva una copia de tu operación.',
                    Reportes:
                      'Información de tu inventario para tomar mejores decisiones.',
                  }[view]
                }
              </p>
            </div>
            <div className="heading-actions">
              {view !== 'Resumen' && view !== 'Control' && (
                <button className="secondary" onClick={download}>
                  <Download size={16} />
                  <span>Exportar</span>
                </button>
              )}
              <button
                className="primary"
                onClick={() =>
                  open(
                    view === 'Inventario'
                      ? 'product'
                      : view === 'Sucursales'
                        ? 'branch'
                        : view === 'Proveedores'
                          ? 'supplier'
                          : 'movement',
                  )
                }
              >
                <Plus size={17} />
                {view === 'Inventario'
                  ? 'Agregar producto'
                  : view === 'Sucursales'
                    ? 'Nueva sucursal'
                    : view === 'Proveedores'
                      ? 'Nuevo proveedor'
                      : 'Nuevo movimiento'}
              </button>
            </div>
          </div>
          {(error || syncError) && !modal && (
            <div className="error-banner" role="alert">
              {error || syncError}
              <button onClick={() => void refresh()}>
                <RefreshCw size={15} /> Reintentar
              </button>
            </div>
          )}
          <div className="overview-note">
            <Warehouse size={17} />
            <Picker
              value={branch}
              onChange={setBranch}
              options={branchOptions}
              label="Filtrar sucursal"
            />
            <span>
              <span className="mini-dot" />{' '}
              {connection ? 'Actualizado ' + lastSync : 'Sin sincronizar'}
            </span>
          </div>
          {data.products.some((p) => p.id === 'p1') && (
            <div className="demo-note">
              <span>DATOS DE EJEMPLO</span> Catálogo multirubro para explorar la
              aplicación.
            </div>
          )}
          {!loading && data.products.length === 0 && (
            <div className="welcome-banner">
              <div>
                <b>Un espacio listo para tu operación</b>
                <p>
                  Empieza con una sucursal y tus productos, o explora un
                  inventario de ejemplo.
                </p>
              </div>
              <button className="secondary" disabled={busy} onClick={demo}>
                Cargar ejemplo <ArrowUpRight size={15} />
              </button>
            </div>
          )}
          {(view === 'Resumen' || view === 'Reportes') && (
            <>
              <div className="stats">
                {[
                  [
                    'Productos activos',
                    integer(data.products.length),
                    'Referencias en tu catálogo',
                    Package,
                  ],
                  [
                    'Unidades disponibles',
                    integer(total),
                    'En las ubicaciones seleccionadas',
                    Boxes,
                  ],
                  [
                    'Valor del inventario',
                    money(value),
                    'Valorización al costo de compra',
                    ChartNoAxesCombined,
                  ],
                  [
                    'Stock por reponer',
                    integer(alerts.length),
                    'Alertas por producto y sucursal',
                    AlertTriangle,
                  ],
                ].map(([title, n, sub, Icon]: any, i) => (
                  <button
                    className={'stat stat-' + i}
                    key={title}
                    onClick={() => {
                      if (i === 3) setModal('alerts');
                      else go(i === 2 ? 'Reportes' : 'Inventario');
                    }}
                  >
                    <div>
                      {title}
                      <span className="stat-icon">
                        <Icon size={18} />
                      </span>
                    </div>
                    <strong>{n}</strong>
                    <small>
                      {i === 3 ? (
                        <span className="amber-text">
                          Requieren atención <ArrowUpRight size={12} />
                        </span>
                      ) : (
                        sub
                      )}
                    </small>
                  </button>
                ))}
              </div>
              <div className="dashboard-grid">
                <section className="panel activity-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Movimiento de inventario</h2>
                      <p>Entradas y salidas externas · días en UTC</p>
                    </div>
                    <Picker
                      value={period}
                      onChange={setPeriod}
                      label="Período del gráfico"
                      options={[
                        { value: '7', label: 'Últimos 7 días' },
                        { value: '30', label: 'Últimos 30 días' },
                      ]}
                    />
                  </div>
                  <div className="chart-legend">
                    <span>
                      <i />
                      Entradas
                    </span>
                    <span>
                      <i />
                      Salidas
                    </span>
                  </div>
                  <div className="chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={chart}
                        margin={{ top: 12, right: 22, left: -17, bottom: 0 }}
                      >
                        <defs>
                          <linearGradient
                            id="entradas"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor="#309779"
                              stopOpacity={0.2}
                            />
                            <stop
                              offset="100%"
                              stopColor="#309779"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                        <CartesianGrid
                          strokeDasharray="3 4"
                          vertical={false}
                          stroke="#edf0f1"
                        />
                        <XAxis
                          dataKey="day"
                          tickLine={false}
                          axisLine={false}
                          tick={{ fontSize: 11, fill: '#909aa2' }}
                          minTickGap={28}
                        />
                        <YAxis
                          tickLine={false}
                          axisLine={false}
                          tick={{ fontSize: 11, fill: '#909aa2' }}
                        />
                        <Tooltip
                          contentStyle={{
                            borderRadius: 9,
                            border: '1px solid #e7eaed',
                            fontSize: 13,
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="Entradas"
                          stroke="#298767"
                          fill="url(#entradas)"
                          strokeWidth={2.5}
                        />
                        <Area
                          type="monotone"
                          dataKey="Salidas"
                          stroke="#b0b8bc"
                          fill="transparent"
                          strokeDasharray="5 5"
                          strokeWidth={2}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="chart-footer">
                    <span>
                      <i className="live-dot" /> Datos de movimientos
                      registrados
                    </span>
                    <button onClick={() => go('Movimientos')}>
                      Ver movimientos <ArrowUpRight size={14} />
                    </button>
                  </div>
                </section>
                <section className="panel locations-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Inventario por sucursal</h2>
                      <p>Distribución de unidades disponibles</p>
                    </div>
                    <Warehouse size={19} color="#8c9992" />
                  </div>
                  <div className="locations">
                    {data.branches
                      .filter((b) => branch === 'all' || b.id === branch)
                      .slice(0, 5)
                      .map((b, i) => {
                        const q = data.stock
                          .filter((s) => s.branch === b.id)
                          .reduce((n, s) => n + s.quantity, 0);
                        return (
                          <button
                            className="location"
                            key={b.id}
                            onClick={() => {
                              setBranch(b.id);
                              go('Inventario');
                            }}
                          >
                            <div>
                              <span className={'location-symbol loc-' + i}>
                                <Warehouse size={17} />
                              </span>
                              <span>
                                <b>{b.name}</b>
                                <small>
                                  {b.city} · {b.kind}
                                </small>
                              </span>
                              <strong>{integer(q)}</strong>
                            </div>
                            <Progress
                              value={total ? (q / total) * 100 : 0}
                              className={'location-progress progress-' + i}
                            />
                          </button>
                        );
                      })}
                    {!data.branches.length && (
                      <div className="empty-state">
                        <Warehouse />
                        <p>Añade tu primera sucursal.</p>
                        <button
                          className="text-link"
                          onClick={() => open('branch')}
                        >
                          Crear sucursal <Plus size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                  <button
                    className="panel-bottom-link"
                    onClick={() => go('Sucursales')}
                  >
                    Administrar sucursales <ChevronRight size={14} />
                  </button>
                </section>
              </div>
              {view === 'Resumen' ? (
                <>
                  <div className="section-title">
                    <div>
                      <h2>Tu inventario</h2>
                      <span>Disponibilidad de productos en tiempo real</span>
                    </div>
                    <button onClick={() => go('Inventario')}>
                      Ver todo el inventario <ArrowUpRight size={15} />
                    </button>
                  </div>
                  <section className="panel">
                    {productTable(true)}
                    <div className="table-footer">
                      <span>
                        {Math.min(rows.length, 5)} de {rows.length} productos
                      </span>
                      <span>Moneda: USD</span>
                    </div>
                  </section>
                </>
              ) : (
                <div className="report-grid">
                  {[...new Set(data.products.map((p) => p.category))].map(
                    (c) => {
                      const ps = data.products.filter((p) => p.category === c);
                      const val = ps.reduce(
                        (n, p) => n + qty(p.id) * p.cost,
                        0,
                      );
                      return (
                        <section className="panel report-card" key={c}>
                          <span className="category-label">{c}</span>
                          <h2>{money(val)}</h2>
                          <p>
                            {ps.length} productos ·{' '}
                            {integer(ps.reduce((n, p) => n + qty(p.id), 0))}{' '}
                            unidades
                          </p>
                          <Progress value={value ? (val / value) * 100 : 0} />
                        </section>
                      );
                    },
                  )}
                </div>
              )}
            </>
          )}
          {view === 'Control' && (
            <ControlCenter
              products={data.products}
              branches={data.branches}
              revision={data.revision}
            />
          )}
          {view === 'Inventario' && (
            <section className="panel">
              <div className="filters">
                <div className="search-box">
                  <Search size={17} />
                  <input
                    aria-label="Buscar productos"
                    placeholder="Buscar por nombre, SKU o código de barras…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  {search && (
                    <button
                      aria-label="Limpiar búsqueda"
                      onClick={() => setSearch('')}
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>
                <Picker
                  value={category}
                  onChange={setCategory}
                  label="Categoría"
                  options={[
                    { value: 'all', label: 'Todas las categorías' },
                    ...[
                      ...new Set([
                        ...categories,
                        ...data.products.map((p) => p.category),
                      ]),
                    ].map((c) => ({ value: c, label: c })),
                  ]}
                />
                <Picker
                  value={status}
                  onChange={setStatus}
                  label="Estado de inventario"
                  options={[
                    { value: 'all', label: 'Todos los estados' },
                    { value: 'low', label: 'Stock bajo / agotado' },
                    { value: 'ok', label: 'Disponible' },
                  ]}
                />
              </div>
              {productTable()}
              <div className="table-footer">
                <span>{rows.length} productos encontrados</span>
                <div className="pagination">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
                  >
                    Anterior
                  </button>
                  <span>
                    {page} / {Math.max(1, Math.ceil(rows.length / 10))}
                  </span>
                  <button
                    disabled={page * 10 >= rows.length}
                    onClick={() => setPage(page + 1)}
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </section>
          )}
          {view === 'Movimientos' && (
            <section className="panel">
              <div className="filters">
                <div className="search-box">
                  <Search size={17} />
                  <input
                    aria-label="Buscar movimientos"
                    placeholder="Buscar producto, tipo o referencia…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
                <span className="subtle">
                  Historial con búsqueda en todos los registros
                </span>
              </div>
              <MovementHistory
                branch={branch}
                search={search}
                branches={data.branches}
                revision={data.revision}
              />
            </section>
          )}
          {view === 'Sucursales' && (
            <div className="branch-grid">
              {data.branches.map((b) => {
                const units = data.stock
                  .filter((s) => s.branch === b.id)
                  .reduce((n, s) => n + s.quantity, 0);
                return (
                  <section className="panel branch-card" key={b.id}>
                    <div className="branch-top">
                      <span className="branch-icon">
                        <Warehouse size={25} />
                      </span>
                      <div className="heading-actions">
                        <span className="badge green">
                          <i />
                          Activa
                        </span>
                        <button
                          className="icon-button"
                          aria-label={'Editar ' + b.name}
                          onClick={() => open('branch', b)}
                        >
                          <Pencil size={16} />
                        </button>
                      </div>
                    </div>
                    <h2>{b.name}</h2>
                    <p>
                      <MapPin size={14} />
                      {b.city} · {b.kind}
                    </p>
                    <div className="branch-metrics">
                      <div>
                        <strong>{integer(units)}</strong>
                        <small>Unidades</small>
                      </div>
                      <div>
                        <strong>
                          {
                            data.stock.filter(
                              (s) => s.branch === b.id && s.quantity > 0,
                            ).length
                          }
                        </strong>
                        <small>Productos con stock</small>
                      </div>
                    </div>
                    <button
                      className="panel-bottom-link"
                      onClick={() => {
                        setBranch(b.id);
                        go('Inventario');
                      }}
                    >
                      Ver inventario <ArrowUpRight size={15} />
                    </button>
                  </section>
                );
              })}
              <button className="add-card" onClick={() => open('branch')}>
                <Plus size={27} />
                <b>Añadir una ubicación</b>
                <span>Tienda, almacén o centro de distribución</span>
              </button>
            </div>
          )}
          {view === 'Proveedores' && (
            <div className="branch-grid">
              {data.suppliers.map((s) => (
                <section className="panel supplier-card" key={s.id}>
                  <div className="branch-top">
                    <div className="branch-icon">
                      <Truck size={24} />
                    </div>
                    <button
                      className="icon-button"
                      aria-label={'Editar ' + s.name}
                      onClick={() => open('supplier', s)}
                    >
                      <Pencil size={16} />
                    </button>
                  </div>
                  <h2>{s.name}</h2>
                  <p>{s.email || 'Sin correo registrado'}</p>
                  <p>{s.phone || 'Sin teléfono registrado'}</p>
                  <div className="supplier-bottom">
                    <Package size={16} />
                    {
                      data.products.filter((p) => p.supplier === s.id).length
                    }{' '}
                    productos asociados
                  </div>
                </section>
              ))}
              <button className="add-card" onClick={() => open('supplier')}>
                <Plus size={27} />
                <b>Añadir proveedor</b>
                <span>Organiza tus contactos de abastecimiento</span>
              </button>
            </div>
          )}
          <footer className="app-footer">
            <span>
              <Boxes size={14} /> nexo <i /> Inventario conectado
            </span>
            <span>Todo en su lugar.</span>
          </footer>
        </main>
      </div>
      {notice && (
        <div className="toast-message" role="status">
          <Check size={18} />
          {notice}
        </div>
      )}
      <Dialog
        open={!!modal}
        onOpenChange={(o) => {
          if (!o && !busy) {
            setModal(null);
            setError('');
          }
        }}
      >
        <DialogContent className="inventory-dialog">
          <DialogTitle>
            {
              {
                product:
                  form.id && data.products.some((p) => p.id === form.id)
                    ? 'Editar producto'
                    : 'Nuevo producto',
                movement: 'Registrar movimiento',
                branch: data.branches.some((b) => b.id === form.id)
                  ? 'Editar sucursal'
                  : 'Nueva sucursal',
                supplier: data.suppliers.some((s) => s.id === form.id)
                  ? 'Editar proveedor'
                  : 'Nuevo proveedor',
                alerts: 'Alertas de inventario',
                help: 'Tu operación con Nexo',
              }[modal || '']
            }
          </DialogTitle>
          <DialogDescription>
            {
              {
                product:
                  'Información del catálogo. Las existencias se actualizan con movimientos.',
                movement:
                  'Cada operación queda registrada y actualiza las existencias.',
                branch:
                  'Añade una tienda o un lugar donde almacenas productos.',
                supplier:
                  'Registra los datos de tu contacto de abastecimiento.',
                alerts: 'Productos por debajo del mínimo y próximos a vencer.',
                help: 'Un espacio privado para organizar productos y existencias entre sucursales.',
              }[modal || '']
            }
          </DialogDescription>
          {['product', 'movement', 'branch', 'supplier'].includes(
            modal || '',
          ) && (
            <form onSubmit={submit}>
              <div className="form-grid">
                {modal === 'product' && (
                  <>
                    {field('name', 'Nombre del producto')}
                    {field('sku', 'SKU único')}
                    {field('barcode', 'Código de barras', 'text', false)}
                    {selectField(
                      'category',
                      'Categoría',
                      categories.map((c) => ({ value: c, label: c })),
                    )}
                    {selectField(
                      'unit',
                      'Unidad de medida',
                      [
                        'Unidad',
                        'Caja',
                        'Bolsa',
                        'Par',
                        'Paquete',
                        'Botella',
                      ].map((c) => ({ value: c, label: c })),
                    )}
                    {field('minimum', 'Stock mínimo por sucursal', 'number')}
                    {field('cost', 'Costo de compra (USD)', 'number')}
                    {field('price', 'Precio de venta (USD)', 'number')}
                    {selectField('supplier', 'Proveedor', [
                      { value: '', label: 'Sin proveedor' },
                      ...data.suppliers.map((s) => ({
                        value: s.id,
                        label: s.name,
                      })),
                    ])}
                    {field(
                      'expiry',
                      'Vencimiento de referencia',
                      'date',
                      false,
                    )}
                    {data.products.some((p) => p.id === form.id) && (
                      <div className="form-full stock-detail">
                        <b>Existencias por ubicación</b>
                        {data.branches.map((b) => (
                          <div key={b.id}>
                            <span>{b.name}</span>
                            <strong>
                              {qty(form.id, b.id)} {form.unit.toLowerCase()}
                            </strong>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
                {modal === 'movement' && (
                  <>
                    {selectField(
                      'type',
                      'Tipo de movimiento',
                      ['Entrada', 'Salida', 'Transferencia', 'Conteo'].map(
                        (c) => ({ value: c, label: c }),
                      ),
                    )}
                    {selectField(
                      'product',
                      'Producto',
                      data.products.map((p) => ({
                        value: p.id,
                        label: `${p.sku} · ${p.name}`,
                      })),
                    )}
                    {selectField(
                      'branch',
                      form.type === 'Transferencia'
                        ? 'Sucursal de origen'
                        : 'Sucursal',
                      data.branches.map((b) => ({
                        value: b.id,
                        label: b.name,
                      })),
                    )}
                    {form.type === 'Transferencia' &&
                      selectField(
                        'destination',
                        'Sucursal de destino',
                        data.branches
                          .filter((b) => b.id !== form.branch)
                          .map((b) => ({ value: b.id, label: b.name })),
                      )}
                    {field(
                      'quantity',
                      form.type === 'Conteo'
                        ? 'Cantidad física contada'
                        : 'Cantidad de unidades',
                      'number',
                    )}
                    {field('note', 'Referencia o motivo')}
                    <p className="form-full form-hint">
                      Existencia actual:{' '}
                      <b>{qty(form.product, form.branch)} unidades</b>.{' '}
                      {form.type === 'Conteo'
                        ? 'El conteo registra la diferencia. Si el saldo cambió desde que abriste este formulario, se rechazará para evitar sobrescribir otra operación.'
                        : 'La operación se guarda al confirmar.'}
                    </p>
                    {(!data.products.length || !data.branches.length) && (
                      <p className="form-full error-text">
                        Primero crea al menos un producto y una sucursal.
                      </p>
                    )}
                  </>
                )}
                {modal === 'branch' && (
                  <>
                    {field('name', 'Nombre de la sucursal')}
                    {field('city', 'Ciudad')}
                    {selectField(
                      'kind',
                      'Tipo de ubicación',
                      ['Tienda', 'Almacén', 'Centro de distribución'].map(
                        (c) => ({ value: c, label: c }),
                      ),
                    )}
                  </>
                )}
                {modal === 'supplier' && (
                  <>
                    {field('name', 'Nombre del proveedor')}
                    {field('email', 'Correo electrónico', 'email', false)}
                    {field('phone', 'Teléfono', 'tel', false)}
                  </>
                )}
              </div>
              {error && (
                <p role="alert" className="error-text">
                  {error}
                </p>
              )}
              <div className="form-footer">
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() => setModal(null)}
                >
                  Cancelar
                </button>
                <button
                  className="primary"
                  disabled={
                    busy ||
                    !connection ||
                    (modal === 'movement' &&
                      (!data.products.length || !data.branches.length))
                  }
                >
                  {busy
                    ? 'Guardando…'
                    : modal === 'movement'
                      ? 'Confirmar movimiento'
                      : 'Guardar'}
                </button>
              </div>
            </form>
          )}
          {modal === 'alerts' && (
            <div className="alert-list">
              {alerts.map(({ p, b, q }) => (
                <div key={p.id + b.id} className="alert-row">
                  <span className="alert-icon">
                    <AlertTriangle size={18} />
                  </span>
                  <div>
                    <b>{p.name}</b>
                    <small>
                      {b.name} · {q} disponibles / mínimo {p.minimum}
                    </small>
                  </div>
                  <button
                    className="text-link"
                    onClick={() => {
                      open('movement');
                      setForm((f) => ({
                        ...f,
                        product: p.id,
                        branch: b.id,
                        type: 'Entrada',
                        quantity: String(Math.max(1, p.minimum - q)),
                        expected_version: String(
                          data.stock.find(
                            (s) => s.product === p.id && s.branch === b.id,
                          )?.version || 0,
                        ),
                        note: 'Reposición de inventario',
                      }));
                    }}
                  >
                    Reponer <Plus size={14} />
                  </button>
                </div>
              ))}
              {data.products
                .filter(
                  (p) =>
                    p.expiry &&
                    new Date(p.expiry + 'T23:59:59').getTime() <
                      Date.now() + 30 * 86400000,
                )
                .map((p) => (
                  <div className="alert-row" key={p.id}>
                    <AlertTriangle size={18} />
                    <div>
                      <b>{p.name}</b>
                      <small>Vencimiento de referencia: {p.expiry}</small>
                    </div>
                  </div>
                ))}
              {!alerts.length &&
                !data.products.some(
                  (p) =>
                    p.expiry &&
                    new Date(p.expiry).getTime() < Date.now() + 30 * 86400000,
                ) && (
                  <div className="empty-state">
                    <Check />
                    <h2>Todo al día</h2>
                    <p>No hay alertas de reposición o vencimiento.</p>
                  </div>
                )}
            </div>
          )}
          {modal === 'help' && (
            <div className="help-content">
              <ol>
                <li>Crea las sucursales y proveedores de tu organización.</li>
                <li>
                  Agrega productos con un SKU único, costo y stock mínimo.
                </li>
                <li>
                  Registra entradas, salidas, transferencias y conteos físicos.
                </li>
                <li>
                  Consulta alertas y exporta el catálogo o historial a CSV.
                </li>
              </ol>
              <p>
                La información se guarda de forma centralizada. Abre el mismo
                enlace desde tu teléfono o PC para acceder a este espacio
                privado.
              </p>
              <p className="form-hint">
                Esta primera versión no incluye permisos por empleado, compras,
                reservas, variantes ni trazabilidad por lote. El vencimiento es
                una referencia por producto. Las cantidades se registran en
                unidades enteras.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
}
