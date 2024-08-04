CREATE TABLE "dim_products" (
    "product_id" VARCHAR(50) PRIMARY KEY,
    "product_name" VARCHAR(255) NOT NULL,
    "category" VARCHAR(255) NOT NULL,
    "price" FLOAT NOT NULL,
    "created_at" timestamp DEFAULT (now()),
    "updated_at" timestamp DEFAULT (now()),
    "deleted_at" timestamp
);

CREATE TABLE "dim_customers" (
    "customer_id" VARCHAR(50) PRIMARY KEY,
    "customer_name" VARCHAR(255), 
    "customer_address" TEXT,
    "created_at" timestamp DEFAULT (now()),
    "updated_at" timestamp DEFAULT (now()),
    "deleted_at" timestamp
);


CREATE TABLE "fact_sales" (
    "transaction_id" VARCHAR(50) PRIMARY KEY,
    "customer_id" VARCHAR(50),
    "product_id" VARCHAR(50),
    "quantity" INT,
    "price" FLOAT, 
    "timestamp" timestamp NOT NULL,
    "created_at" timestamp DEFAULT (now()),
    "updated_at" timestamp DEFAULT (now()),
    "deleted_at" timestamp
);

CREATE INDEX ON "dim_products" ("product_id");
CREATE INDEX ON "dim_customers" ("customer_id");
CREATE INDEX ON "fact_sales" ("transaction_id");

ALTER TABLE "fact_sales" ADD FOREIGN KEY ("product_id") REFERENCES "dim_products" ("product_id");
ALTER TABLE "fact_sales" ADD FOREIGN KEY ("customer_id") REFERENCES "dim_customers" ("customer_id");
