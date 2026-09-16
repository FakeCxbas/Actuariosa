CREATE TABLE `app_state` (
	`id` text PRIMARY KEY NOT NULL,
	`revision` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE TABLE `audit` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`entity` text NOT NULL,
	`entity_id` text NOT NULL,
	`action` text NOT NULL,
	`before` text,
	`after` text,
	`created` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_audit_created` ON `audit` (`created`);--> statement-breakpoint
ALTER TABLE `branches` ADD `version` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `movements` ADD `request_hash` text;--> statement-breakpoint
ALTER TABLE `movements` ADD `cost_cents` integer;--> statement-breakpoint
CREATE INDEX `idx_movements_created` ON `movements` (`created`);--> statement-breakpoint
CREATE INDEX `idx_movements_product_branch` ON `movements` (`product`,`branch`);--> statement-breakpoint
ALTER TABLE `products` ADD `version` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `stock` ADD `version` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `suppliers` ADD `version` integer DEFAULT 0 NOT NULL;
--> statement-breakpoint
CREATE TRIGGER rev_products_insert AFTER INSERT ON products BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_products_update AFTER UPDATE ON products BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_products_delete AFTER DELETE ON products BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_branches_insert AFTER INSERT ON branches BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_branches_update AFTER UPDATE ON branches BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_branches_delete AFTER DELETE ON branches BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_suppliers_insert AFTER INSERT ON suppliers BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_suppliers_update AFTER UPDATE ON suppliers BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_suppliers_delete AFTER DELETE ON suppliers BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_stock_insert AFTER INSERT ON stock BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_stock_update AFTER UPDATE ON stock BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_stock_delete AFTER DELETE ON stock BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_movements_insert AFTER INSERT ON movements BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_movements_update AFTER UPDATE ON movements BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER rev_movements_delete AFTER DELETE ON movements BEGIN INSERT INTO app_state(id,revision) VALUES ('inventory',1) ON CONFLICT(id) DO UPDATE SET revision=revision+1; END;

--> statement-breakpoint
CREATE TRIGGER audit_products_insert AFTER INSERT ON products BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('products',NEW.id,'INSERT',NULL,json_object('id',NEW.id,'name',NEW.name,'sku',NEW.sku,'barcode',NEW.barcode,'category',NEW.category,'unit',NEW.unit,'cost',NEW.cost,'price',NEW.price,'minimum',NEW.minimum,'supplier',NEW.supplier,'expiry',NEW.expiry,'version',NEW.version),strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;

--> statement-breakpoint
CREATE TRIGGER audit_products_update AFTER UPDATE ON products BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('products',NEW.id,'UPDATE',json_object('id',OLD.id,'name',OLD.name,'sku',OLD.sku,'barcode',OLD.barcode,'category',OLD.category,'unit',OLD.unit,'cost',OLD.cost,'price',OLD.price,'minimum',OLD.minimum,'supplier',OLD.supplier,'expiry',OLD.expiry,'version',OLD.version),json_object('id',NEW.id,'name',NEW.name,'sku',NEW.sku,'barcode',NEW.barcode,'category',NEW.category,'unit',NEW.unit,'cost',NEW.cost,'price',NEW.price,'minimum',NEW.minimum,'supplier',NEW.supplier,'expiry',NEW.expiry,'version',NEW.version),strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;

--> statement-breakpoint
CREATE TRIGGER audit_products_delete AFTER DELETE ON products BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('products',OLD.id,'DELETE',json_object('id',OLD.id,'name',OLD.name,'sku',OLD.sku,'barcode',OLD.barcode,'category',OLD.category,'unit',OLD.unit,'cost',OLD.cost,'price',OLD.price,'minimum',OLD.minimum,'supplier',OLD.supplier,'expiry',OLD.expiry,'version',OLD.version),NULL,strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;

--> statement-breakpoint
CREATE TRIGGER audit_branches_insert AFTER INSERT ON branches BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('branches',NEW.id,'INSERT',NULL,json_object('id',NEW.id,'name',NEW.name,'city',NEW.city,'kind',NEW.kind,'version',NEW.version),strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;

--> statement-breakpoint
CREATE TRIGGER audit_branches_update AFTER UPDATE ON branches BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('branches',NEW.id,'UPDATE',json_object('id',OLD.id,'name',OLD.name,'city',OLD.city,'kind',OLD.kind,'version',OLD.version),json_object('id',NEW.id,'name',NEW.name,'city',NEW.city,'kind',NEW.kind,'version',NEW.version),strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;

--> statement-breakpoint
CREATE TRIGGER audit_branches_delete AFTER DELETE ON branches BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('branches',OLD.id,'DELETE',json_object('id',OLD.id,'name',OLD.name,'city',OLD.city,'kind',OLD.kind,'version',OLD.version),NULL,strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;

--> statement-breakpoint
CREATE TRIGGER audit_suppliers_insert AFTER INSERT ON suppliers BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('suppliers',NEW.id,'INSERT',NULL,json_object('id',NEW.id,'name',NEW.name,'email',NEW.email,'phone',NEW.phone,'version',NEW.version),strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;

--> statement-breakpoint
CREATE TRIGGER audit_suppliers_update AFTER UPDATE ON suppliers BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('suppliers',NEW.id,'UPDATE',json_object('id',OLD.id,'name',OLD.name,'email',OLD.email,'phone',OLD.phone,'version',OLD.version),json_object('id',NEW.id,'name',NEW.name,'email',NEW.email,'phone',NEW.phone,'version',NEW.version),strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;

--> statement-breakpoint
CREATE TRIGGER audit_suppliers_delete AFTER DELETE ON suppliers BEGIN INSERT INTO audit(entity,entity_id,action,before,after,created) VALUES ('suppliers',OLD.id,'DELETE',json_object('id',OLD.id,'name',OLD.name,'email',OLD.email,'phone',OLD.phone,'version',OLD.version),NULL,strftime('%Y-%m-%dT%H:%M:%fZ','now')); END;
