import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
const base = process.env.INVENTORY_TEST_URL || 'http://localhost:3000';
async function get(q = '') {
  const r = await fetch(base + '/api/inventory' + q);
  assert.equal(r.status, 200);
  assert.match(r.headers.get('cache-control'), /no-store/);
  return r.json();
}
async function post(body, status = 200) {
  const r = await fetch(base + '/api/inventory', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  const j = await r.json();
  assert.equal(r.status, status, JSON.stringify(j));
  return j;
}
const b = await post({
  action: 'branch',
  name: 'Control origen',
  city: 'Test',
  kind: 'Almacén',
});
const dest = await post({
  action: 'branch',
  name: 'Control destino',
  city: 'Test',
  kind: 'Tienda',
});
const p = await post({
  action: 'product',
  name: 'Control prueba',
  sku: 'HARD-' + crypto.randomUUID(),
  category: 'Otros',
  unit: 'Unidad',
  cost: 1.25,
  price: 2,
  minimum: 2,
});
const move = (type, quantity, other = {}) => ({
  action: 'movement',
  id: crypto.randomUUID(),
  product: p.id,
  branch: b.id,
  type,
  quantity,
  note: 'Prueba de control',
  ...other,
});
const entry = move('Entrada', 10);
const replay = await Promise.all([post(entry), post(entry)]);
assert.equal(replay[0].id, replay[1].id);
await post({ ...entry, quantity: 20 }, 409);
let d = await get();
const pos = () => d.stock.find((s) => s.product === p.id && s.branch === b.id);
assert.equal(pos().quantity, 10);
const oldVersion = pos().version;
await post(move('Entrada', 5));
await post(move('Conteo', 12, { expected_version: oldVersion }), 409);
d = await get();
assert.equal(pos().quantity, 15);
const counts = await Promise.all([
  fetch(base + '/api/inventory', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(
      move('Conteo', 11, { expected_version: pos().version }),
    ),
  }),
  fetch(base + '/api/inventory', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(
      move('Conteo', 9, { expected_version: pos().version }),
    ),
  }),
]);
assert.deepEqual(counts.map((r) => r.status).sort(), [200, 409]);
d = await get();
const beforeQty = pos().quantity;
const concurrentExits = await Promise.all([
  fetch(base + '/api/inventory', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(move('Salida', beforeQty - 1)),
  }),
  fetch(base + '/api/inventory', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(move('Salida', beforeQty - 1)),
  }),
]);
assert.deepEqual(concurrentExits.map((r) => r.status).sort(), [200, 400]);
d = await get();
assert.equal(pos().quantity, 1);
let item = d.products.find((x) => x.id === p.id);
await post({ ...item, action: 'product', name: 'Control actualizado' });
await post({ ...item, action: 'product', name: 'Edición obsoleta' }, 409);
d = await get();
item = d.products.find((x) => x.id === p.id);
await post({ ...item, action: 'product', unit: 'Caja' }, 400);
const unchanged = await get('?since=' + d.revision);
assert.equal(unchanged.unchanged, true);
assert.equal(unchanged.products, undefined);
const bad = await fetch(base + '/api/inventory', {
  method: 'POST',
  headers: {
    'content-type': 'application/json',
    origin: 'https://invalid.example',
  },
  body: JSON.stringify(move('Entrada', 1)),
});
assert.equal(bad.status, 403);
const control = await get('?mode=control');
assert.deepEqual(control.discrepancies, []);
assert(control.logs.some((x) => x.entity_id === p.id && x.action === 'UPDATE'));
const history = await get(
  '?mode=history&search=Control%20actualizado&branch=' + b.id,
);
assert(history.rows.length > 0);
assert(history.rows.length <= 25);
assert.equal(history.rows[0].product_name, 'Control actualizado');
assert(history.rows.every((m) => m.cost_cents === 125));
const backup = await get('?mode=backup');
const sha = Array.from(
  new Uint8Array(
    await crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(backup.payload),
    ),
  ),
)
  .map((b) => b.toString(16).padStart(2, '0'))
  .join('');
assert.equal(sha, backup.sha256);
const tables = JSON.parse(backup.payload);
assert(tables.products.some((x) => x.id === p.id));
await writeFile('/tmp/nexo-tested-backup.json', JSON.stringify(backup));
console.log(
  'PASS: concurrent replay, payload mismatch, stale and concurrent counts, concurrent exits, stale edits, unit history protection, lightweight revision, CSRF, reconciliation, audit, paginated history, frozen cost and backup checksum.',
);
