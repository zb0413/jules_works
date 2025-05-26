-- Set execution environment parameters (Dinky might handle some of these)
SET 'pipeline.name' = 'HudiStreamingAnalytics';
SET 'execution.runtime-mode' = 'streaming';
SET 'table.dynamic-table-options.enabled' = 'true'; -- Important for Hudi tables

-- =====================================================================================
-- Define Hudi Table for Reading Orders (Streaming)
-- =====================================================================================
CREATE TABLE orders_hudi_ro (
    order_id INT,
    user_id VARCHAR(50),
    product_id VARCHAR(50),
    order_time TIMESTAMP(3),
    amount DECIMAL(10, 2),
    created_at TIMESTAMP(3),
    created_at_date VARCHAR(10),
    PRIMARY KEY (order_id) NOT ENFORCED,
    WATERMARK FOR order_time AS order_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'hudi',
    'path' = 'hdfs:///user/hudi/tables/orders_hudi',
    'table.type' = 'MERGE_ON_READ',
    'read.streaming.enabled' = 'true',          -- Enable streaming reads
    'read.streaming.check-interval' = '60'      -- Check for new data every 60 seconds
    -- 'hoodie.datasource.query.type' = 'snapshot' -- For batch-like queries, if not streaming
);

-- =====================================================================================
-- Define Hudi Table for Reading Requests (Nginx Logs) (Streaming)
-- =====================================================================================
CREATE TABLE requests_hudi_ro (
    request_id STRING,
    remote_addr STRING,
    event_time TIMESTAMP(3),    -- This was TIMESTAMP_LTZ(3) in sink, but Hudi might store as UTC TIMESTAMP
                                -- For simplicity in RO queries, TIMESTAMP(3) is often fine if timezone context isn't critical for the query logic itself
                                -- or if data is consistently UTC. If LTZ features are needed, ensure compatibility.
    event_date VARCHAR(10),
    request_method STRING,
    request_uri STRING,
    server_protocol STRING,
    status_code INT,
    body_bytes_sent BIGINT,
    http_user_agent STRING,
    processing_time TIMESTAMP_LTZ(3), -- This was metadata in the sink, might not be directly queryable as a regular field unless explicitly handled
    PRIMARY KEY (request_id) NOT ENFORCED,
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'hudi',
    'path' = 'hdfs:///user/hudi/tables/requests_hudi',
    'table.type' = 'MERGE_ON_READ',
    'read.streaming.enabled' = 'true',
    'read.streaming.check-interval' = '60'
    -- 'hoodie.datasource.query.type' = 'snapshot' -- For batch-like queries, if not streaming
);

-- =====================================================================================
-- Analytics Query 1: Order Volume and Amount per Minute (Continuous Query)
-- To run in Dinky, you would typically submit this SELECT statement.
-- Dinky can then visualize the results or send them to another sink.
-- =====================================================================================
-- SELECT
--     TUMBLE_START(order_time, INTERVAL '1' MINUTE) AS window_start,
--     COUNT(order_id) AS order_count,
--     SUM(amount) AS total_amount
-- FROM orders_hudi_ro
-- GROUP BY
--     TUMBLE(order_time, INTERVAL '1' MINUTE);

-- =====================================================================================
-- Analytics Query 2: Request Volume per Minute (Continuous Query)
-- =====================================================================================
-- SELECT
--     TUMBLE_START(event_time, INTERVAL '1' MINUTE) AS window_start,
--     COUNT(request_id) AS request_count
-- FROM requests_hudi_ro
-- GROUP BY
--     TUMBLE(event_time, INTERVAL '1' MINUTE);

-- =====================================================================================
-- Analytics Query 3: Top 5 Requested URIs in the last 10 minutes (Continuous Query)
-- This query uses a tumbling window and ROW_NUMBER to find top N.
-- =====================================================================================
-- SELECT
--     window_start,
--     window_end,
--     request_uri,
--     request_count
-- FROM (
--     SELECT
--         *,
--         ROW_NUMBER() OVER (PARTITION BY window_start, window_end ORDER BY request_count DESC) as row_num
--     FROM (
--         SELECT
--             TUMBLE_START(event_time, INTERVAL '10' MINUTE) AS window_start,
--             TUMBLE_END(event_time, INTERVAL '10' MINUTE) AS window_end,
--             request_uri,
--             COUNT(*) as request_count
--         FROM requests_hudi_ro
--         GROUP BY
--             TUMBLE(event_time, INTERVAL '10' MINUTE),
--             request_uri
--     )
-- )
-- WHERE row_num <= 5;

-- Note: The actual SELECT statements for analytics queries are commented out.
-- In Dinky, you would typically copy one of these SELECT blocks (without the surrounding comments)
-- and execute it as a Flink SQL job. Dinky provides the UI to run and manage these.
-- The CREATE TABLE statements define the necessary source tables for these queries.
-- Ensure the Hudi tables exist and are populated before running these queries.
