'use strict';

const token = document.querySelector('meta[name="nexo-token"]').content;
const app = document.getElementById('app');
const modal = document.getElementById('modal');
let state, currentPage = 'dashboard', companyId = localStorage.getItem('nexo-company') || '', pageNumber = 1;
let filters = {search:'', category:'', warehouse:'', status:'', kind:''};
let toastTimer;
const icons = {
 box:'M21 8l-9 5-9-5M12 13v9M3 7l9-5 9 5v10l-9 5-9-5z',
 grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
 arrows:'M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4',
 warehouse:'M3 21V8l9-5 9 5v13M7 21V11h10v10M7 15h10M7 18h10',
 cart:'M3 3h2l3 12h11l2-8H6M10 20h.01M18 20h.01',
 users:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M20 21v-2a4 4 0 0 0-3-3.8M16 3.2a4 4 0 0 1 0 7.6',
 chart:'M4 3v18h17M8 16v-5M13 16V7M18 16v-8',
 settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M4 4l3 1 3-3h4l3 3 3-1 2 4-2 3v2l2 3-2 4-3-1-3 3h-4l-3-3-3 1-2-4 2-3v-2L2 8z',
 plus:'M12 5v14M5 12h14', search:'M21 21l-5-5M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14',
 download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5', upload:'M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5',
 arrow:'M5 12h14m-5-5 5 5-5 5', chevron:'m9 5 7 7-7 7', close:'m6 6 12 12M6 18 18 6',
 check:'m5 12 4 4L19 6', alert:'M12 3 2 21h20zM12 9v5M12 17h.01',
 edit:'m16 3 5 5-12 12-6 1 1-6zM13 6l5 5', money:'M12 2v20M17 6H9a4 4 0 0 0 0 8h6a4 4 0 0 1 0 8H6',
 file:'M14 2H4v20h16V8zM14 2v6h6M8 12h8M8 16h6', clock:'M12 8v5l3 2M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
 menu:'M4 6h16M4 12h16M4 18h16', shield:'m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6zM8 12l3 3 5-6',
 trash:'M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7', building:'M4 21V3h12v18M16 10h4v11M8 7h4M8 11h4M8 15h4M2 21h20',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${icons[name] || icons.box}"/></svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const qty = value => new Intl.NumberFormat('es-EC', {maximumFractionDigits:3}).format(value / 1000);
const number = value => new Intl.NumberFormat('es-EC', {maximumFractionDigits:0}).format(value);
const money = value => new Intl.NumberFormat('es-EC', {style:'currency', currency:state?.company?.currency || 'USD', maximumFractionDigits:2}).format(value / 100);
const date = value => new Date(value).toLocaleDateString('es-EC', {day:'2-digit', month:'short', year:'numeric'});
const time = value => new Date(value).toLocaleTimeString('es-EC', {hour:'2-digit', minute:'2-digit'});
const totalCost = p => p.total_qty * p.cost_cents / 1000;
const stockStatus = p => p.total_qty === 0 ? 'zero' : p.total_qty <= p.min_qty ? 'low' : 'ok';
const stockBadge = p => `<span class="badge ${stockStatus(p)}">${{zero:'Agotado',low:'Stock bajo',ok:'Disponible'}[stockStatus(p)]}</span>`;
const kinds = {in:'Entrada',out:'Salida',transfer:'Traslado',count:'Ajuste por conteo'};
const statuses = {pending:'Pendiente',received:'Recibida',cancelled:'Cancelada'};
const button = (text, action, ico='plus', cls='primary', extra='') => `<button class="btn ${cls}" data-action="${action}" ${extra}>${icon(ico)}${text}</button>`;
const empty = (title, description, action='', btn='') => `<div class="empty">${icon('box')}<h3>${esc(title)}</h3><div>${esc(description)}</div>${action ? button(btn, action) : ''}</div>`;

async function request(path, body) {
 const response = await fetch(path + (path.includes('?') ? '&' : '?') + 'company=' + encodeURIComponent(companyId), {
  method:body === undefined ? 'GET' : 'POST', headers:{'X-Nexo-Token':token, ...(body === undefined ? {} : {'Content-Type':'application/json'})},
  ...(body === undefined ? {} : {body:JSON.stringify(body)}),
 });
 const result = await response.json();
 if (!response.ok) throw new Error(result.error || 'No se pudo completar la operación.');
 return result;
}

async function load() {
 try {state = await request('/api/state');}
 catch (error) {
  if (companyId && error.message.includes('empresa válida')) {companyId=''; state=await request('/api/state');}
  else throw error;
 }
 if (state.company) {companyId=state.company.id; localStorage.setItem('nexo-company', companyId);}
 render();
}

function toast(message) {
 const el = document.getElementById('toast');
 el.textContent=message; el.classList.add('visible');
 clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.classList.remove('visible'), 4500);
}

const nav = [['dashboard','grid','Vista general'],['products','box','Productos'],['movements','arrows','Movimientos'],['warehouses','warehouse','Bodegas'],['orders','cart','Compras'],['suppliers','users','Proveedores'],['reports','chart','Reportes']];
function render() {
 if (!state.company) return renderWelcome();
 const pageTitle = [...nav,['settings','settings','Configuración']].find(p=>p[0]===currentPage)?.[2] || 'Vista general';
 app.innerHTML=`<div class="shell"><aside class="sidebar" id="sidebar">
  <div class="brand"><img src="/icon.svg" alt="">nexo<small>Inventario</small></div>
  <div class="workspace"><label for="company-select">Espacio de trabajo</label><select id="company-select">${state.companies.map(c=>`<option value="${c.id}" ${c.id===state.company.id?'selected':''}>${esc(c.name)}</option>`).join('')}</select></div>
  <div class="nav-label">Administración</div><nav aria-label="Menú principal">${nav.map(([id,ico,name])=>`<button class="nav-item ${currentPage===id?'active':''}" data-page="${id}" ${currentPage===id?'aria-current="page"':''}>${icon(ico)}${name}${id==='products'?`<span class="nav-count">${state.products.length}</span>`:''}</button>`).join('')}</nav>
  <div class="sidebar-bottom"><button class="nav-item ${currentPage==='settings'?'active':''}" data-page="settings">${icon('settings')}Configuración</button><div class="local-badge"><span class="dot"></span>Guardado en este equipo</div></div>
 </aside><main class="main"><header class="topbar"><div class="crumb"><button class="icon-btn mobile-menu" aria-label="Abrir menú" data-action="menu">${icon('menu')}</button>Mi negocio ${icon('chevron')} <strong>${pageTitle}</strong></div><div class="top-actions"><span class="date">${new Date().toLocaleDateString('es-EC',{day:'numeric',month:'long',year:'numeric'})}</span><span class="badge ok">${state.company.name.includes('· Demo')?'Demostración':'Edición local'}</span><div class="avatar" title="${esc(state.company.name)}">${esc(state.company.name.slice(0,2).toUpperCase())}</div></div></header>
 <div class="content">${({dashboard:dashboard,products:productsPage,movements:movementsPage,warehouses:warehousesPage,orders:ordersPage,suppliers:suppliersPage,reports:reportsPage,settings:settingsPage}[currentPage])()}<footer class="app-footer"><span>Nexo Inventario · Tu negocio, en orden.</span><span>Versión 0.1 · Local</span></footer></div></main></div>`;
}

function header(eyebrow,title,description,actions='') {
 return `<div class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="subtitle">${description}</p></div><div class="actions">${actions}</div></div>`;
}
function stat(title,value,foot,ico,featured=false) {
 return `<div class="stat ${featured?'featured':''}"><div class="stat-top">${title}<span class="stat-icon">${icon(ico)}</span></div><div class="stat-number">${value}</div><div class="stat-foot">${featured?icon('shield'):''}${foot}</div></div>`;
}
function metrics() {
 return `<div class="stats">${stat('Valor del inventario',money(state.products.reduce((s,p)=>s+totalCost(p),0)),'Existencias × costo de referencia','money',true)}${stat('Productos registrados',number(state.products.length),`${state.warehouses.length} bodegas conectadas`,'box')}${stat('Por reponer',number(state.products.filter(p=>stockStatus(p)!=='ok').length),'Stock bajo o agotado','alert')}${stat('Compras pendientes',number(state.orders.filter(o=>o.status==='pending').length),'Órdenes por recibir','cart')}</div>`;
}
function dashboard() {
 const alerts=state.products.filter(p=>stockStatus(p)!=='ok').sort((a,b)=>a.total_qty-b.total_qty).slice(0,4);
 return header('El pulso de tu negocio','Todo bajo control.','Un vistazo a tus existencias, compras y movimientos.',button('Ver reportes','reports','chart','')+button('Nuevo movimiento','movement'))+
 metrics()+`<div class="dashboard-grid"><section class="card"><div class="card-head"><div><h2>Actividad del inventario</h2><p>Entradas y salidas · últimos 7 días</p></div><span class="badge">Operaciones</span></div>${activityChart()}</section>
 <section class="card"><div class="card-head"><div><h2>Necesitan atención</h2><p>Anticípate a la próxima reposición</p></div><span class="badge low">${state.products.filter(p=>stockStatus(p)!=='ok').length}</span></div>${alerts.length?`<div class="alert-list">${alerts.map(p=>`<div class="alert-row"><div class="product-icon">${icon('box')}</div><div class="alert-info"><strong>${esc(p.name)}</strong><small>${qty(p.total_qty)} ${esc(p.unit)} · mínimo ${qty(p.min_qty)}</small></div>${stockBadge(p)}</div>`).join('')}</div><div class="alert-footer"><button class="text-btn" data-action="low-stock">Revisar productos por reponer ${icon('arrow')}</button></div>`:empty('Sin alertas',state.products.length?'Tus productos están por encima del mínimo.':'Registra productos para controlar sus existencias.')}</section></div>
 <section class="card"><div class="card-head"><div><h2>Últimos movimientos</h2><p>La historia de cada entrada y salida</p></div><button class="text-btn" data-page="movements">Ver todos ${icon('arrow')}</button></div>${movementTable(state.movements.slice(0,5),true)}</section>`;
}
function activityChart() {
 const days=Array.from({length:7},(_,i)=>{const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()-6+i);return {d,in:0,out:0};});
 state.movements.forEach(m=>{const d=days.find(day=>new Date(m.created_at).toDateString()===day.d.toDateString());if(d&&['in','out'].includes(m.kind))d[m.kind]++;});
 const max=Math.max(4,...days.map(d=>Math.max(d.in,d.out)));
 return `<div class="chart" role="img" aria-label="Operaciones de entrada y salida de los últimos siete días"><div class="chart-scale"><span>${max}</span><span>${Math.round(max/2)}</span><span>0</span></div><div class="bars">${days.map(d=>`<div class="bar-group" title="${date(d.d)}: ${d.in} entradas, ${d.out} salidas"><div class="bar" style="height:${d.in/max*100}%"></div><div class="bar light" style="height:${d.out/max*100}%"></div><span class="bar-label">${d.d.toLocaleDateString('es-EC',{weekday:'short'})} ${d.d.getDate()}</span></div>`).join('')}</div></div><div class="legend"><span><i class="square"></i>Entradas</span><span><i class="square light"></i>Salidas</span>${state.movement_count>500?'<span>Sobre los últimos 500 movimientos</span>':''}</div>`;
}
function searchInput(placeholder) {return `<div class="search">${icon('search')}<input id="search" type="search" aria-label="${placeholder}" placeholder="${placeholder}" value="${esc(filters.search)}"></div>`;}
function filterSelect(name,placeholder,options) {return `<select class="filter" data-filter="${name}" aria-label="${placeholder}"><option value="">${placeholder}</option>${options.map(([value,text])=>`<option value="${esc(value)}" ${String(filters[name])===String(value)?'selected':''}>${esc(text)}</option>`).join('')}</select>`;}
function pagination(count) {
 const pages=Math.max(1,Math.ceil(count/12));
 return `<div class="table-footer"><span>${count?`${(pageNumber-1)*12+1}–${Math.min(pageNumber*12,count)} de ${count}`:'0 resultados'}</span><div class="actions"><button class="btn small" data-action="previous" ${pageNumber<=1?'disabled':''}>Anterior</button><span>${pageNumber} / ${pages}</span><button class="btn small" data-action="next" ${pageNumber>=pages?'disabled':''}>Siguiente</button></div></div>`;
}
function filteredProducts() {
 const term=filters.search.toLocaleLowerCase();
 return state.products.map(p=>filters.warehouse?{...p,total_qty:state.balances.find(b=>b.product_id===p.id&&String(b.warehouse_id)===filters.warehouse)?.qty||0}:p)
 .filter(p=>(!term||`${p.name} ${p.sku} ${p.barcode}`.toLocaleLowerCase().includes(term))&&(!filters.category||p.category===filters.category)&&(!filters.status||stockStatus(p)===filters.status));
}
function productsPage() {
 const products=filteredProducts(), rows=products.slice((pageNumber-1)*12,pageNumber*12);
 return header('Catálogo','Un lugar para cada producto.','Organiza tus artículos, variantes, unidades y niveles de reposición.',button('Importar CSV','import','upload','')+button('Nuevo producto','product'))+
 `<section class="card"><div class="toolbar">${searchInput('Buscar nombre, SKU o código de barras…')}${filterSelect('category','Todas las categorías',[...new Set(state.products.map(p=>p.category))].sort().map(c=>[c,c]))}${filterSelect('warehouse','Todas las bodegas',state.warehouses.map(w=>[w.id,w.name]))}${filterSelect('status','Todos los estados',[['ok','Disponible'],['low','Stock bajo'],['zero','Agotado']])}<button class="icon-btn" data-action="export-products" title="Exportar catálogo completo" aria-label="Exportar catálogo completo">${icon('download')}</button></div>${filters.warehouse?'<div class="note">Existencias de la bodega seleccionada. El mínimo de referencia corresponde al producto.</div>':''}
 ${rows.length?`<div class="table-wrap"><table><thead><tr><th>Producto</th><th>Categoría</th><th class="numeric">Existencias</th><th class="numeric">Costo</th><th class="numeric">Precio</th><th>Estado</th><th aria-label="Acciones"></th></tr></thead><tbody>${rows.map(p=>`<tr><td><div class="product-cell"><span class="product-icon">${icon('box')}</span><div><strong>${esc(p.name)}</strong><small class="mono">${esc(p.sku)}</small></div></div></td><td>${esc(p.category)}</td><td class="numeric"><strong>${qty(p.total_qty)}</strong><small>${esc(p.unit)}</small></td><td class="numeric">${money(p.cost_cents)}</td><td class="numeric">${money(p.price_cents)}</td><td>${stockBadge(p)}</td><td><button class="icon-btn" data-action="edit-product" data-id="${p.id}" aria-label="Editar ${esc(p.name)}">${icon('edit')}</button></td></tr>`).join('')}</tbody></table></div>`:empty('Aquí empieza tu catálogo',state.products.length?'No hay productos con estos filtros.':'Agrega tu primer producto. Después registra su stock inicial.','product','Crear producto')}${pagination(products.length)}</section>`;
}
function movementTable(rows,compact=false) {
 if (!rows.length) return empty('Cada movimiento deja una historia','Registra una entrada, salida, traslado o conteo.','movement','Registrar movimiento');
 return `<div class="table-wrap"><table><thead><tr><th>Producto</th><th>Movimiento</th><th>Bodega</th><th class="numeric">Cantidad</th>${compact?'':'<th>Motivo / referencia</th>'}<th>Fecha</th></tr></thead><tbody>${rows.map(m=>`<tr><td><strong>${esc(m.product_name)}</strong><small class="mono">${esc(m.sku)}</small></td><td><span class="badge ${m.kind==='in'?'ok':m.kind==='out'?'low':'info'}">${kinds[m.kind]}</span></td><td>${esc(m.warehouse_name)}${m.destination_name?`<small>→ ${esc(m.destination_name)}</small>`:''}</td><td class="numeric ${m.delta>0?'positive':'negative'}">${m.kind==='transfer'?'↔':m.delta>0?'+':'−'}${qty(m.qty)}<small>${esc(m.unit)}</small></td>${compact?'':`<td title="${esc(m.note)}">${esc(m.note.length>60?m.note.slice(0,60)+'…':m.note)}</td>`}<td>${date(m.created_at)}<small>${time(m.created_at)}</small></td></tr>`).join('')}</tbody></table></div>`;
}
function movementsPage() {
 const term=filters.search.toLowerCase();
 const rows=state.movements.filter(m=>(!term||`${m.product_name} ${m.sku} ${m.note}`.toLowerCase().includes(term))&&(!filters.kind||m.kind===filters.kind)&&(!filters.warehouse||[String(m.warehouse_id),String(m.destination_id)].includes(filters.warehouse)));
 return header('Trazabilidad','Cada unidad, con historia.','Entradas, salidas, traslados y ajustes registrados sin sobrescribir el historial.',button('Exportar historial','export-movements','download','')+button('Nuevo movimiento','movement'))+
 `<section class="card"><div class="toolbar">${searchInput('Buscar producto, SKU o referencia…')}${filterSelect('kind','Todos los movimientos',Object.entries(kinds))}${filterSelect('warehouse','Todas las bodegas',state.warehouses.map(w=>[w.id,w.name]))}</div>${movementTable(rows.slice((pageNumber-1)*12,pageNumber*12))}${pagination(rows.length)}</section>${state.movement_count>500?'<p class="subtitle">Se muestran los 500 movimientos más recientes. La exportación incluye el historial completo.</p>':''}`;
}
function warehousesPage() {
 return header('Ubicaciones','Tu inventario, donde esté.','Controla bodegas, sucursales, almacenes o áreas de tu negocio.',button('Nueva bodega','warehouse'))+
 `<div class="cards-grid">${state.warehouses.map(w=>{const balances=state.balances.filter(b=>b.warehouse_id===w.id);const value=balances.reduce((s,b)=>s+b.qty*(state.products.find(p=>p.id===b.product_id)?.cost_cents||0)/1000,0);return `<section class="entity-card"><div class="entity-icon">${icon('warehouse')}</div><h2>${esc(w.name)}</h2><p>${esc(w.location||'Sin ubicación registrada')}</p><footer><span>${balances.filter(b=>b.qty>0).length} productos con stock</span><strong>${money(value)}</strong></footer><button class="text-btn" style="margin-top:18px" data-action="warehouse-stock" data-id="${w.id}">Ver existencias ${icon('arrow')}</button></section>`;}).join('')}</div>`;
}
const orderTotal=o=>o.lines.reduce((s,l)=>s+l.qty*l.cost_cents/1000,0);
function ordersPage() {
 const term=filters.search.toLowerCase();
 const rows=state.orders.filter(o=>(!term||`${o.supplier_name} OC-${String(o.id).padStart(4,'0')} ${o.note}`.toLowerCase().includes(term))&&(!filters.status||o.status===filters.status));
 return header('Abastecimiento','Compra con claridad.','Crea órdenes y recibe sus productos directamente en la bodega elegida.',button('Nueva compra','order'))+
 `<section class="card"><div class="toolbar">${searchInput('Buscar proveedor o número de compra…')}${filterSelect('status','Todos los estados',Object.entries(statuses))}</div>${rows.length?`<div class="table-wrap"><table><thead><tr><th>Orden</th><th>Proveedor</th><th>Bodega</th><th>Estado</th><th class="numeric">Total sin impuestos</th><th>Fecha</th><th></th></tr></thead><tbody>${rows.slice((pageNumber-1)*12,pageNumber*12).map(o=>`<tr><td><strong>OC-${String(o.id).padStart(4,'0')}</strong><small>${o.lines.length} productos</small></td><td>${esc(o.supplier_name)}</td><td>${esc(o.warehouse_name)}</td><td><span class="badge ${o.status==='received'?'ok':o.status==='pending'?'low':''}">${statuses[o.status]}</span></td><td class="numeric">${money(orderTotal(o))}</td><td>${date(o.created_at)}</td><td><button class="btn small" data-action="order-detail" data-id="${o.id}">Ver orden ${icon('arrow')}</button></td></tr>`).join('')}</tbody></table></div>`:empty('Planifica tu próxima reposición','Necesitas al menos un proveedor y un producto para crear una compra.','order','Crear compra')}${pagination(rows.length)}</section>`;
}
function suppliersPage() {
 const rows=state.suppliers.filter(s=>`${s.name} ${s.contact}`.toLowerCase().includes(filters.search.toLowerCase()));
 return header('Aliados de tu negocio','Proveedores a mano.','Centraliza los contactos que mantienen tu operación en marcha.',button('Nuevo proveedor','supplier'))+
 `<div style="margin-bottom:20px">${searchInput('Buscar proveedor o contacto…')}</div>${rows.length?`<div class="cards-grid">${rows.map(s=>`<section class="entity-card"><div class="entity-icon">${icon('users')}</div><h2>${esc(s.name)}</h2><p>${esc(s.contact||'Sin contacto registrado')}<br>${esc(s.email||'Sin correo')}<br>${esc(s.phone||'Sin teléfono')}</p>${s.notes?`<p>${esc(s.notes)}</p>`:''}<footer><span>${state.orders.filter(o=>o.supplier_id===s.id).length} órdenes de compra</span><button class="text-btn" data-action="order-supplier" data-id="${s.id}">Crear compra ${icon('arrow')}</button></footer></section>`).join('')}</div>`:empty('Construye tu directorio','Agrega los proveedores de tu negocio.','supplier','Agregar proveedor')}`;
}
function reportsPage() {
 const categories=[...new Set(state.products.map(p=>p.category))].map(name=>{const ps=state.products.filter(p=>p.category===name);return {name,count:ps.length,value:ps.reduce((s,p)=>s+totalCost(p),0),sale:ps.reduce((s,p)=>s+p.total_qty*p.price_cents/1000,0)};}).sort((a,b)=>b.value-a.value);
 const total=categories.reduce((s,c)=>s+c.value,0);
 return header('Decisiones con datos','Conoce lo que tienes.','Valoración a costo de referencia y necesidades de reposición.',button('Exportar productos','export-products','download','')+button('Imprimir reporte','print','file','primary'))+
 metrics()+`<div class="note">La valoración usa el costo de referencia que defines para cada producto. No aplica costo promedio, FIFO ni impuestos. Las recepciones conservan el costo pactado en la orden sin cambiar el costo del catálogo.</div>
 <section class="card"><div class="card-head"><h2>Inventario por categoría</h2><span class="badge">${esc(state.company.currency)}</span></div>${categories.length?`<div class="table-wrap"><table><thead><tr><th>Categoría</th><th class="numeric">Productos</th><th class="numeric">Valor a costo</th><th class="numeric">Valor a precio de venta</th><th>Participación</th></tr></thead><tbody>${categories.map(c=>`<tr><td><strong>${esc(c.name)}</strong></td><td class="numeric">${c.count}</td><td class="numeric">${money(c.value)}</td><td class="numeric">${money(c.sale)}</td><td><span class="spark"><i style="width:${total?c.value/total*100:0}%"></i></span> ${total?(c.value/total*100).toFixed(1):0}%</td></tr>`).join('')}</tbody></table></div>`:empty('Aún no hay datos','Agrega productos y registra sus existencias.')}</section>
 <section class="card report-table"><div class="card-head"><h2>Lista de reposición</h2><button class="text-btn" data-action="order">Crear compra ${icon('arrow')}</button></div>${restockTable()}</section>`;
}
function restockTable() {
 const rows=state.products.filter(p=>stockStatus(p)!=='ok');
 if (!rows.length) return empty('Sin pendientes de reposición','Los productos registrados están por encima de su mínimo.');
 return `<div class="table-wrap"><table><thead><tr><th>Producto</th><th class="numeric">Actual</th><th class="numeric">Mínimo</th><th class="numeric">Faltante hasta mínimo</th><th>Estado</th></tr></thead><tbody>${rows.map(p=>`<tr><td><strong>${esc(p.name)}</strong><small>${esc(p.sku)} · ${esc(p.unit)}</small></td><td class="numeric">${qty(p.total_qty)}</td><td class="numeric">${qty(p.min_qty)}</td><td class="numeric">${qty(Math.max(0,p.min_qty-p.total_qty))}</td><td>${stockBadge(p)}</td></tr>`).join('')}</tbody></table></div>`;
}
function settingsPage() {
 return header('Tu espacio','Hecho para tu negocio.','Administra tus empresas y conserva una copia de tu información.')+
 `<div class="settings-grid"><section class="card setting"><div class="entity-icon">${icon('building')}</div><h2 style="margin-top:15px">${esc(state.company.name)}</h2><p>${esc(state.company.sector)}<br>Moneda: ${esc(state.company.currency)}<br>${state.warehouses.length} bodegas · ${state.products.length} productos</p>${button('Crear otra empresa','company','plus','')}</section>
 <section class="card setting">${icon('shield')}<h2 style="margin-top:15px">Tu información, a salvo</h2><p>Descarga una copia completa de la base de datos. Incluye todas las empresas, productos, existencias y movimientos de este equipo.</p>${button('Descargar respaldo','backup','download','')}</section>
 <section class="card setting">${icon('upload')}<h2 style="margin-top:15px">Trae tu catálogo</h2><p>Importa productos desde un CSV con SKU, nombre, categoría, unidad, costo y precio. Las existencias iniciales se registran mediante movimientos.</p>${button('Importar productos','import','upload','')}</section>
 <section class="card setting">${icon('box')}<h2 style="margin-top:15px">Explora con datos de ejemplo</h2><p>Crea una empresa de demostración independiente para probar el flujo de inventario sin modificar tus negocios existentes.</p>${button('Crear empresa demo','demo','arrow','')}</section></div><p class="version">Nexo Inventario 0.1.0 · Edición local para un operador. No requiere Internet. Todos los espacios de trabajo son accesibles desde este equipo; esta versión no incluye cuentas ni permisos por usuario.</p>`;
}

const currencies=['USD','EUR','MXN','COP','PEN','CLP','ARS','GBP'];
function field(name,title,value='',type='text',extra='') {
 return `<div class="field"><label for="f-${name}">${title}</label><input id="f-${name}" name="${name}" type="${type}" value="${esc(value)}" ${extra}></div>`;
}
function selectField(name,title,options,selected='',extra='') {
 return `<div class="field"><label for="f-${name}">${title}</label><select id="f-${name}" name="${name}" ${extra}>${options.map(([value,text])=>`<option value="${esc(value)}" ${String(selected)===String(value)?'selected':''}>${esc(text)}</option>`).join('')}</select></div>`;
}
function textarea(name,title,value='',required=false) {return `<div class="field full"><label for="f-${name}">${title}</label><textarea id="f-${name}" name="${name}" maxlength="500" ${required?'required':''}>${esc(value)}</textarea></div>`;}
function companyFields() {return field('name','Nombre del negocio','','text','required maxlength="160" placeholder="Ej. Comercial del Pacífico"')+field('sector','Sector o tipo de negocio','Comercio','text','required maxlength="160" placeholder="Ferretería, alimentos, textil…"')+selectField('currency','Moneda',currencies.map(c=>[c,c]),'USD');}
function renderWelcome() {
 app.innerHTML=`<div class="welcome"><div class="welcome-layout"><div class="welcome-story"><div class="brand"><img src="/icon.svg" alt="">nexo<small>Inventario</small></div><div><div class="eyebrow" style="color:#c1dda8">Espacio para crecer</div><h1>Tu inventario.<br>Tu negocio.<br>Todo conectado.</h1><p>Del primer estante a la próxima sucursal. Dale a cada producto su lugar y a cada decisión, información.</p><div class="chips"><span>Múltiples bodegas</span><span>Compras</span><span>Trazabilidad</span></div></div><div class="local-badge" style="padding:20px 0 0"><span class="dot"></span>Local, privado y sin conexión</div></div><div class="welcome-form"><div class="onboarding-step">Empecemos por lo tuyo</div><h2>Bienvenido a Nexo.</h2><p>Crea tu empresa para comenzar con un inventario vacío, listo para tus productos.</p><form id="welcome-form" class="stack">${companyFields()}<div class="form-error" role="alert"></div><button class="btn primary" type="submit">Crear mi espacio ${icon('arrow')}</button></form><div class="divider">o conoce el producto primero</div>${button('Explorar una demostración','demo','arrow','')}<p class="subtitle" style="font-size:10px">Edición local · Sin registro ni conexión a servicios externos.</p></div></div></div>`;
 document.getElementById('welcome-form').addEventListener('submit',async e=>{
  e.preventDefault();const form=e.currentTarget, submit=form.querySelector('[type=submit]');submit.disabled=true;
  try {const result=await request('/api/companies',Object.fromEntries(new FormData(form)));companyId=result.id;await load();toast('Tu empresa está lista. Agrega tu primer producto.');}
  catch(error){form.querySelector('.form-error').textContent=error.message;submit.disabled=false;}
 });
}

function openModal(title,description,body,onSubmit,submitText='Guardar',wide=false) {
 if(modal.open)modal.close();
 modal.style.width=wide?'min(800px,calc(100% - 30px))':'';
 modal.innerHTML=`<form id="modal-form"><div class="modal-head"><div><h2 id="modal-title">${title}</h2><p>${description}</p></div><button type="button" class="icon-btn" data-action="close" aria-label="Cerrar">${icon('close')}</button></div><div class="modal-body">${body}<div class="form-error" role="alert" style="margin-top:16px"></div></div><div class="modal-actions"><button class="btn" type="button" data-action="close">Cancelar</button>${onSubmit?`<button class="btn primary" type="submit">${submitText}</button>`:''}</div></form>`;
 modal.showModal();
 if(onSubmit)document.getElementById('modal-form').addEventListener('submit',async e=>{
  e.preventDefault();const form=e.currentTarget, btn=form.querySelector('[type=submit]');btn.disabled=true;
  form.querySelector('.form-error').textContent='';
  try {await onSubmit(Object.fromEntries(new FormData(form)),form);modal.close();await load();}
  catch(error){form.querySelector('.form-error').textContent=error.message;btn.disabled=false;}
 });
}

function productModal(pid) {
 const p=state.products.find(p=>p.id===Number(pid));
 const body=`<div class="form-grid">${field('sku','SKU / código único',p?.sku||'','text','required maxlength="64" placeholder="Ej. CAM-AZ-M"')}${field('name','Nombre del producto',p?.name||'','text','required maxlength="160"')}${field('category','Categoría',p?.category||'General','text','required maxlength="80" list="categories"')}${field('unit','Unidad de medida',p?.unit||'unidad','text','required maxlength="30" list="units"')}${field('barcode','Código de barras (opcional)',p?.barcode||'','text','maxlength="80"')}${field('min_stock','Stock mínimo global',p?p.min_qty/1000:0,'number','required min="0" step="0.001"')}${field('cost',`Costo de referencia (${esc(state.company.currency)})`,p?p.cost_cents/100:0,'number','required min="0" step="0.01"')}${field('price',`Precio de venta (${esc(state.company.currency)})`,p?p.price_cents/100:0,'number','required min="0" step="0.01"')}${textarea('notes','Descripción, variante o notas',p?.notes||'')}</div><datalist id="categories">${[...new Set(state.products.map(p=>p.category))].map(c=>`<option value="${esc(c)}">`).join('')}</datalist><datalist id="units">${['unidad','kg','gramo','litro','metro','caja','paquete','par','rollo'].map(u=>`<option value="${u}">`).join('')}</datalist><p class="subtitle">Cada variante puede tener su propio SKU. Para cambiar existencias, registra un movimiento; así conservas su historial.</p>`;
 openModal(p?'Editar producto':'Nuevo producto','Un catálogo flexible para cualquier tipo de artículo.',body,async data=>{await request(p?`/api/products/${p.id}`:'/api/products',data);toast(p?'Producto actualizado.':'Producto creado. Ya puedes registrar sus existencias.');});
}
function movementModal() {
 if(!state.products.length)return toast('Primero agrega un producto al catálogo.');
 const key=crypto.randomUUID();
 openModal('Registrar movimiento','Una operación, con su bodega y motivo.',`<div class="form-grid">${selectField('kind','Tipo de movimiento',Object.entries(kinds),'in')}${selectField('product_id','Producto',state.products.map(p=>[p.id,`${p.sku} · ${p.name}`]))}${selectField('warehouse_id','Bodega de origen / recepción',state.warehouses.map(w=>[w.id,w.name]))}<div id="destination-field" hidden>${selectField('destination_id','Bodega de destino',state.warehouses.map(w=>[w.id,w.name]),state.warehouses[1]?.id)}</div>${field('quantity','Cantidad',1,'number','required min="0.001" step="0.001"')}${textarea('note','Motivo o referencia (obligatorio)','',true)}</div><div class="note" id="balance-hint" style="margin-top:18px;margin-bottom:0"></div>`,async data=>{await request('/api/movements',{...data,request_key:key});toast('Movimiento registrado. Existencias actualizadas.');},'Registrar movimiento');
 const form=document.getElementById('modal-form');
 function hint(){const data=Object.fromEntries(new FormData(form)),p=state.products.find(p=>String(p.id)===data.product_id),balance=state.balances.find(b=>String(b.product_id)===data.product_id&&String(b.warehouse_id)===data.warehouse_id)?.qty||0;
  document.getElementById('destination-field').hidden=data.kind!=='transfer';
  form.querySelector('[name=quantity]').min=data.kind==='count'?'0':'0.001';
  form.querySelector('label[for=f-quantity]').textContent=data.kind==='count'?'Cantidad física contada':'Cantidad';
  document.getElementById('balance-hint').textContent=`Stock disponible en esta bodega: ${qty(balance)} ${p.unit}. ${data.kind==='count'?'Ingresa el total que contaste físicamente. Se registrará la diferencia.':data.kind==='transfer'?'El traslado conserva el stock total de tu empresa.':'La operación se guardará en el historial.'}`;
 }
 form.addEventListener('change',hint);hint();
}
function warehouseModal(){openModal('Nueva bodega','Un nuevo lugar para organizar tus existencias.',`<div class="stack">${field('name','Nombre de la bodega','','text','required maxlength="160"')}${field('location','Dirección o ubicación','','text','maxlength="240"')}</div>`,async data=>{await request('/api/warehouses',data);toast('Bodega creada.');});}
function supplierModal(){openModal('Nuevo proveedor','Los datos esenciales para mantener el contacto.',`<div class="form-grid">${field('name','Razón social o nombre','','text','required maxlength="160"')}${field('contact','Persona de contacto','','text','maxlength="160"')}${field('email','Correo electrónico','','email','maxlength="160"')}${field('phone','Teléfono','','tel','maxlength="100"')}${textarea('notes','Notas')}</div>`,async data=>{await request('/api/suppliers',data);toast('Proveedor creado.');});}
function companyModal(){openModal('Crear otra empresa','Tendrá su propio catálogo, bodegas, compras y movimientos.',`<div class="stack">${companyFields()}</div>`,async data=>{const result=await request('/api/companies',data);companyId=result.id;currentPage='dashboard';resetFilters();toast('Empresa creada.');},'Crear empresa');}
function orderModal(supplierId) {
 if(!state.products.length||!state.suppliers.length)return toast('Agrega al menos un producto y un proveedor antes de crear una compra.');
 const key=crypto.randomUUID();
 openModal('Nueva orden de compra','La compra sumará existencias cuando confirmes su recepción.',`<div class="form-grid">${selectField('supplier_id','Proveedor',state.suppliers.map(s=>[s.id,s.name]),supplierId)}${selectField('warehouse_id','Bodega de recepción',state.warehouses.map(w=>[w.id,w.name]))}</div><div class="divider">Productos de la compra</div><div id="order-lines"></div><button class="btn small" type="button" data-action="add-line">${icon('plus')}Agregar línea</button><div style="margin-top:20px">${textarea('note','Referencia o notas')}</div><p class="subtitle">Importes sin impuestos. Recepción completa en una sola operación.</p>`,async (data,form)=>{
  const lines=[...form.querySelectorAll('.order-line')].map(row=>({product_id:row.querySelector('[data-line=product]').value,quantity:row.querySelector('[data-line=quantity]').value,cost:row.querySelector('[data-line=cost]').value}));
  await request('/api/orders',{...data,lines,request_key:key});toast('Orden de compra creada.');
 },'Crear orden',true);addOrderLine();
}
function addOrderLine(){
 const container=document.getElementById('order-lines'), id=crypto.randomUUID();
 container.insertAdjacentHTML('beforeend',`<div class="order-line"><div class="field"><label for="line-p-${id}">Producto</label><select id="line-p-${id}" data-line="product">${state.products.map(p=>`<option value="${p.id}">${esc(p.sku+' · '+p.name)}</option>`).join('')}</select></div><div class="field"><label for="line-q-${id}">Cantidad</label><input id="line-q-${id}" data-line="quantity" type="number" min="0.001" step="0.001" value="1" required></div><div class="field"><label for="line-c-${id}">Costo unitario</label><input id="line-c-${id}" data-line="cost" type="number" min="0" step="0.01" value="${state.products[0].cost_cents/100}" required></div><button type="button" class="icon-btn" data-action="remove-line" aria-label="Quitar producto">${icon('trash')}</button></div>`);
 container.lastElementChild.querySelector('select').addEventListener('change',e=>{e.target.closest('.order-line').querySelector('[data-line=cost]').value=state.products.find(p=>String(p.id)===e.target.value).cost_cents/100;});
}
function orderDetail(id) {
 const o=state.orders.find(o=>o.id===Number(id));
 openModal(`Orden OC-${String(o.id).padStart(4,'0')}`,`${esc(o.supplier_name)} · ${statuses[o.status]}`,`<div class="order-detail"><div class="detail-row"><span>Bodega de recepción</span><strong>${esc(o.warehouse_name)}</strong></div>${o.lines.map(l=>`<div class="detail-row"><span>${esc(l.product_name)}<small style="display:block;margin-top:5px;color:#8a9680">${qty(l.qty)} ${esc(l.unit)} × ${money(l.cost_cents)}</small></span><strong>${money(l.qty*l.cost_cents/1000)}</strong></div>`).join('')}<div class="detail-row"><strong>Total sin impuestos</strong><strong>${money(orderTotal(o))}</strong></div><p>${esc(o.note||'Sin notas adicionales.')}</p></div>${o.status==='pending'?'<div class="note">Al confirmar la recepción, se sumarán todos los productos a la bodega. Esta orden no podrá recibirse dos veces.</div>':''}`,o.status==='pending'?async()=>{await request(`/api/orders/${o.id}/receive`,{});toast('Compra recibida. Stock actualizado.');}:null,'Confirmar recepción');
 if(o.status==='pending')modal.querySelector('.modal-actions').insertAdjacentHTML('afterbegin',`<button type="button" class="btn danger" data-action="cancel-order" data-id="${o.id}">Cancelar orden</button>`);
}
function importModal(){
 openModal('Importar catálogo CSV','Agrega hasta 5.000 productos por archivo.',`<div class="note">Campos requeridos: <strong>sku, name</strong>. Opcionales: category, unit, barcode, cost, price, min_stock, notes. Usa punto para decimales y coma para separar columnas. Los SKU existentes no se sobrescriben. El archivo completo se valida antes de guardar.</div><button class="btn" type="button" data-action="csv-template">${icon('download')}Descargar plantilla</button><div class="field" style="margin-top:20px"><label for="csv-file">Archivo CSV</label><input id="csv-file" type="file" accept=".csv,text/csv" required><small>Importa el catálogo sin stock; registra las existencias iniciales con entradas o conteos.</small></div>`,async()=>{const file=document.getElementById('csv-file').files[0];if(!file||file.size>2_000_000)throw new Error('Selecciona un CSV de hasta 2 MB.');const result=await request('/api/import',{content:await file.text()});toast(`${result.count} productos importados.`);},'Importar productos');
}
function saveBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function download(path,name){const r=await fetch(`${path}${path.includes('?')?'&':'?'}company=${encodeURIComponent(companyId)}`,{headers:{'X-Nexo-Token':token}});if(!r.ok)throw new Error((await r.json()).error);saveBlob(await r.blob(),name);toast('Archivo descargado.');}
function resetFilters(){filters={search:'',category:'',warehouse:'',status:'',kind:''};pageNumber=1;}
function go(page){currentPage=page;resetFilters();render();window.scrollTo(0,0);}

document.addEventListener('click',async e=>{
 const page=e.target.closest('[data-page]');if(page){go(page.dataset.page);return;}
 const target=e.target.closest('[data-action]');if(!target||target.disabled)return;
 const action=target.dataset.action,id=target.dataset.id;
 try {
  if(action==='product')productModal();
  else if(action==='edit-product')productModal(id);
  else if(action==='movement')movementModal();
  else if(action==='warehouse')warehouseModal();
  else if(action==='supplier')supplierModal();
  else if(action==='company')companyModal();
  else if(action==='order'||action==='order-supplier')orderModal(id);
  else if(action==='order-detail')orderDetail(id);
  else if(action==='add-line')addOrderLine();
  else if(action==='remove-line')target.closest('.order-line').remove();
  else if(action==='close')modal.close();
  else if(action==='import')importModal();
  else if(action==='menu')document.getElementById('sidebar').classList.toggle('open');
  else if(action==='reports')go('reports');
  else if(action==='warehouse-stock'){currentPage='products';resetFilters();filters.warehouse=id;render();}
  else if(action==='low-stock'){go('reports');document.querySelector('.report-table').scrollIntoView({behavior:'smooth'});}
  else if(action==='next'){pageNumber++;render();}
  else if(action==='previous'){pageNumber=Math.max(1,pageNumber-1);render();}
  else if(action==='export-products')await download('/api/export?kind=products','nexo-productos.csv');
  else if(action==='export-movements')await download('/api/export?kind=movements','nexo-movimientos.csv');
  else if(action==='backup')await download('/api/backup',`nexo-respaldo-${new Date().toISOString().slice(0,10)}.sqlite3`);
  else if(action==='print')window.print();
  else if(action==='csv-template')saveBlob(new Blob(['\ufeffsku,name,category,unit,barcode,cost,price,min_stock,notes\r\nPROD-001,Producto de ejemplo,General,unidad,,5.00,8.50,10,\r\n'],{type:'text/csv;charset=utf-8'}),'nexo-plantilla-productos.csv');
  else if(action==='demo'){target.disabled=true;const result=await request('/api/demo',{});companyId=result.id;currentPage='dashboard';resetFilters();await load();toast('Estás en una empresa de demostración independiente.');}
  else if(action==='cancel-order'){openModal('Cancelar orden','Los productos de esta orden no se recibirán.','<p class="subtitle">La orden permanecerá en el historial con estado cancelada. Las existencias no cambiarán.</p>',async()=>{await request(`/api/orders/${id}/cancel`,{});toast('Orden cancelada.');},'Cancelar esta orden');}
 }catch(error){toast(error.message);target.disabled=false;}
});
document.addEventListener('change',async e=>{
 if(e.target.id==='company-select'){
  companyId=e.target.value;currentPage='dashboard';resetFilters();try{await load();}catch(error){toast(error.message);}
 }
 if(e.target.dataset.filter){filters[e.target.dataset.filter]=e.target.value;pageNumber=1;render();}
});
document.addEventListener('input',e=>{
 if(e.target.id==='search'){
  const pos=e.target.selectionStart;filters.search=e.target.value;pageNumber=1;render();const input=document.getElementById('search');input.focus();try{input.setSelectionRange(pos,pos);}catch{}
 }
});
modal.addEventListener('click',e=>{if(e.target===modal)modal.close();});
load().catch(error=>{app.innerHTML=`<div class="welcome">${empty('No se pudo abrir Nexo',error.message)}<button class="btn" id="retry">Volver a intentar</button></div>`;document.getElementById('retry').onclick=()=>location.reload();});
