import assert from 'node:assert/strict';
const base = process.env.INVENTORY_TEST_URL || 'http://localhost:3000';
async function post(b, expected = 200) {
  const r = await fetch(base + '/api/inventory', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(b),
  });
  const j = await r.json();
  assert.equal(r.status, expected, JSON.stringify(j));
  return j;
}
async function state() {
  const r = await fetch(base + '/api/inventory');
  assert.equal(r.status, 200);
  return r.json();
}
const a = await post({
  action: 'branch',
  name: 'Prueba origen',
  city: 'Test',
  kind: 'Almacén',
});
const b = await post({
  action: 'branch',
  name: 'Prueba destino',
  city: 'Test',
  kind: 'Tienda',
});
const sku = 'TEST-' + crypto.randomUUID();
const p = await post({
  action: 'product',
  name: 'Producto de prueba',
  sku,
  category: 'Otros',
  unit: 'Unidad',
  cost: 10,
  price: 20,
  minimum: 3,
});
const stock = (d, branch) =>
  d.stock.find((s) => s.product === p.id && s.branch === branch)?.quantity || 0;
const entry = {
  action: 'movement',
  id: crypto.randomUUID(),
  product: p.id,
  branch: a.id,
  type: 'Entrada',
  quantity: 20,
  note: 'Prueba entrada',
};
await post(entry);
await post(entry);
assert.equal(stock(await state(), a.id), 20, 'Idempotencia');
await post({
  action: 'movement',
  id: crypto.randomUUID(),
  product: p.id,
  branch: a.id,
  destination: b.id,
  type: 'Transferencia',
  quantity: 7,
  note: 'Prueba transferencia',
});
let d = await state();
assert.equal(stock(d, a.id), 13);
assert.equal(stock(d, b.id), 7);
const before = d.movements.length;
await post(
  {
    action: 'movement',
    id: crypto.randomUUID(),
    product: p.id,
    branch: a.id,
    destination: b.id,
    type: 'Transferencia',
    quantity: 99,
    note: 'Debe fallar',
  },
  400,
);
d = await state();
assert.equal(d.movements.length, before);
assert.equal(stock(d, a.id), 13);
assert.equal(stock(d, b.id), 7);
await post({
  action: 'movement',
  id: crypto.randomUUID(),
  product: p.id,
  branch: a.id,
  type: 'Salida',
  quantity: 4,
  note: 'Prueba salida',
});
assert.equal(stock(await state(), a.id), 9);
await post({
  action: 'movement',
  id: crypto.randomUUID(),
  product: p.id,
  branch: a.id,
  type: 'Conteo',
  expected_version: (await state()).stock.find(
    (s) => s.product === p.id && s.branch === a.id,
  ).version,
  quantity: 5,
  note: 'Prueba conteo',
});
d = await state();
assert.equal(stock(d, a.id), 5);
assert.equal(
  d.movements.find((m) => m.product === p.id && m.type === 'Conteo').quantity,
  -4,
);
await post(
  {
    action: 'movement',
    id: crypto.randomUUID(),
    product: p.id,
    branch: a.id,
    type: 'Entrada',
    quantity: -1,
    note: 'Inválido',
  },
  400,
);
await post(
  {
    action: 'product',
    name: 'Duplicado',
    sku,
    category: 'Otros',
    unit: 'Unidad',
    cost: 10,
    price: 20,
    minimum: 3,
  },
  400,
);
await post(
  {
    action: 'movement',
    id: crypto.randomUUID(),
    product: p.id,
    branch: a.id,
    destination: a.id,
    type: 'Transferencia',
    quantity: 1,
    note: 'Inválido',
  },
  400,
);
console.log(
  'PASS: entrada, salida, transferencia atómica, prevención de stock negativo, idempotencia, conteo, SKU único y validación.',
);
