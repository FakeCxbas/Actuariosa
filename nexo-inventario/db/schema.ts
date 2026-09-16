import {
  sqliteTable,
  text,
  integer,
  real,
  primaryKey,
  check,
  index,
} from 'drizzle-orm/sqlite-core';
import { sql } from 'drizzle-orm';
export const branches = sqliteTable('branches', {
  id: text().primaryKey(),
  name: text().notNull(),
  city: text().notNull(),
  kind: text().notNull(),
  version: integer().notNull().default(0),
});
export const suppliers = sqliteTable('suppliers', {
  id: text().primaryKey(),
  name: text().notNull(),
  email: text().notNull(),
  phone: text().notNull(),
  version: integer().notNull().default(0),
});
export const products = sqliteTable(
  'products',
  {
    id: text().primaryKey(),
    name: text().notNull(),
    sku: text().notNull().unique(),
    barcode: text().notNull().default(''),
    category: text().notNull(),
    unit: text().notNull(),
    cost: real().notNull(),
    price: real().notNull(),
    minimum: integer().notNull(),
    supplier: text().references(() => suppliers.id),
    expiry: text().notNull().default(''),
    version: integer().notNull().default(0),
  },
  (t) => [
    check(
      'positive_cost',
      sql`${t.cost} >= 0 AND ${t.price} >= 0 AND ${t.minimum} >= 0`,
    ),
  ],
);
export const stock = sqliteTable(
  'stock',
  {
    product: text()
      .notNull()
      .references(() => products.id),
    branch: text()
      .notNull()
      .references(() => branches.id),
    quantity: integer().notNull().default(0),
    version: integer().notNull().default(0),
  },
  (t) => [
    primaryKey({ columns: [t.product, t.branch] }),
    check('nonnegative_stock', sql`${t.quantity} >= 0`),
  ],
);
export const movements = sqliteTable(
  'movements',
  {
    id: text().primaryKey(),
    product: text()
      .notNull()
      .references(() => products.id),
    branch: text()
      .notNull()
      .references(() => branches.id),
    destination: text().references(() => branches.id),
    type: text().notNull(),
    quantity: integer().notNull(),
    note: text().notNull(),
    created: text().notNull(),
    request_hash: text(),
    cost_cents: integer(),
  },
  (t) => [
    index('idx_movements_created').on(t.created),
    index('idx_movements_product_branch').on(t.product, t.branch),
  ],
);
export const appState = sqliteTable('app_state', {
  id: text().primaryKey(),
  revision: integer().notNull().default(0),
});
export const audit = sqliteTable(
  'audit',
  {
    id: integer().primaryKey({ autoIncrement: true }),
    entity: text().notNull(),
    entity_id: text().notNull(),
    action: text().notNull(),
    before: text(),
    after: text(),
    created: text().notNull(),
  },
  (t) => [index('idx_audit_created').on(t.created)],
);
