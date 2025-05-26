-- Set execution environment parameters
SET 'execution.checkpointing.interval' = '1min';
SET 'pipeline.name' = 'PostgresOrdersToHudiCDC';

-- Create table for PostgreSQL CDC source
CREATE TABLE orders_cdc (
    order_id INT,
    user_id VARCHAR(50),
    product_id VARCHAR(50),
    order_time TIMESTAMP(3),
    amount DECIMAL(10, 2),
    created_at TIMESTAMP(3),
    PRIMARY KEY (order_id) NOT ENFORCED -- Primary key for CDC connector
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = 'postgres',
    'port' = '5432',
    'username' = 'hudi_user',
    'password' = 'hudi_password',
    'database-name' = 'hudi_db',
    'schema-name' = 'public',
    'table-name' = 'orders',
    'decoding.plugin.name' = 'pgoutput' -- or 'wal2json' if preferred and configured
);

-- Create table for Hudi sink
CREATE TABLE orders_hudi (
    order_id INT,
    user_id VARCHAR(50),
    product_id VARCHAR(50),
    order_time TIMESTAMP(3),
    amount DECIMAL(10, 2),
    created_at TIMESTAMP(3),
    created_at_date VARCHAR(10), -- Partition field
    PRIMARY KEY (order_id) NOT ENFORCED -- Hudi requires a primary key
)
PARTITIONED BY (created_at_date)
WITH (
    'connector' = 'hudi',
    'path' = 'hdfs:///user/hudi/tables/orders_hudi',
    'table.type' = 'MERGE_ON_READ',
    'hoodie.datasource.write.recordkey.field' = 'order_id',
    'hoodie.datasource.write.partitionpath.field' = 'created_at_date',
    'hoodie.datasource.write.precombine.field' = 'order_time', -- Using order_time for precombine
    'write.tasks' = '1', -- For local testing
    'compaction.tasks' = '1', -- For local testing
    'hoodie.index.type' = 'FLINK_STATE', -- Simpler for local setup
    'hoodie.compact.schedule.inline' = 'true', -- For local testing, trigger compaction more eagerly
    'hoodie.compact.inline.max.delta.commits' = '1' -- For local testing
);

-- Insert data from CDC source to Hudi sink
INSERT INTO orders_hudi
SELECT
    order_id,
    user_id,
    product_id,
    order_time,
    amount,
    created_at,
    DATE_FORMAT(created_at, 'yyyy-MM-dd') AS created_at_date -- Derive partition field
FROM orders_cdc;
