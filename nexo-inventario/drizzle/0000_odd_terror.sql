CREATE TABLE `branches` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`city` text NOT NULL,
	`kind` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `movements` (
	`id` text PRIMARY KEY NOT NULL,
	`product` text NOT NULL,
	`branch` text NOT NULL,
	`destination` text,
	`type` text NOT NULL,
	`quantity` integer NOT NULL,
	`note` text NOT NULL,
	`created` text NOT NULL,
	FOREIGN KEY (`product`) REFERENCES `products`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`branch`) REFERENCES `branches`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`destination`) REFERENCES `branches`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `products` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`sku` text NOT NULL,
	`barcode` text DEFAULT '' NOT NULL,
	`category` text NOT NULL,
	`unit` text NOT NULL,
	`cost` real NOT NULL,
	`price` real NOT NULL,
	`minimum` integer NOT NULL,
	`supplier` text,
	`expiry` text DEFAULT '' NOT NULL,
	FOREIGN KEY (`supplier`) REFERENCES `suppliers`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "positive_cost" CHECK("products"."cost" >= 0 AND "products"."price" >= 0 AND "products"."minimum" >= 0)
);
--> statement-breakpoint
CREATE UNIQUE INDEX `products_sku_unique` ON `products` (`sku`);--> statement-breakpoint
CREATE TABLE `stock` (
	`product` text NOT NULL,
	`branch` text NOT NULL,
	`quantity` integer DEFAULT 0 NOT NULL,
	PRIMARY KEY(`product`, `branch`),
	FOREIGN KEY (`product`) REFERENCES `products`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`branch`) REFERENCES `branches`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "nonnegative_stock" CHECK("stock"."quantity" >= 0)
);
--> statement-breakpoint
CREATE TABLE `suppliers` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`email` text NOT NULL,
	`phone` text NOT NULL
);
