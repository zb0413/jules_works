-- Set execution environment parameters
SET 'execution.checkpointing.interval' = '2min';
SET 'pipeline.name' = 'NginxLogsToHudi';
SET 'table.dynamic-table-options.enabled' = 'true'; -- Required for PROCTIME_UUID()

-- Create table for HDFS (text/csv) source for Nginx logs
-- Nginx log_format hudi_custom: '$remote_addr\t$time_local\t$request_method\t$request_uri\t$server_protocol\t$status\t$body_bytes_sent\t"$http_user_agent"';
-- Example line: 172.18.0.1	24/Jul/2024:15:47:03 +0000	GET	/index.html	HTTP/1.1	200	612	"Mozilla/5.0..."
CREATE TABLE nginx_logs_source (
    remote_addr STRING,
    time_local STRING,          -- e.g., '24/Jul/2024:15:47:03 +0000'
    request_method STRING,
    request_uri STRING,
    server_protocol STRING,
    status_code_str STRING,     -- Read as STRING first
    body_bytes_sent_str STRING, -- Read as STRING first
    http_user_agent STRING
    -- If Nginx log has $request_time, it could be useful for event time
    -- For now, we'll use time_local and generate a watermark on it.
    -- processing_time AS PROCTIME() -- Define processing time attribute
    -- WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND -- Example watermark
) WITH (
    'connector' = 'filesystem',
    'path' = 'hdfs:///user/nginx_logs/raw/', -- Path on HDFS where logs will be placed
    'format' = 'csv',
    'csv.field-delimiter' = '\t',          -- Tab character
    'csv.quote-character' = '"',           -- User agent is quoted
    'csv.allow-comments' = 'true',         -- To skip potential header lines or malformed lines starting with #
    'csv.ignore-parse-errors' = 'true'     -- Recommended for log files
);

-- Create table for Hudi sink
CREATE TABLE requests_hudi (
    request_id STRING,                     -- Unique ID for each request
    remote_addr STRING,
    event_time TIMESTAMP_LTZ(3),           -- Parsed from time_local, using TIMESTAMP_LTZ for timezone handling
    event_date VARCHAR(10),                -- Partition field, e.g., 'yyyy-MM-dd'
    request_method STRING,
    request_uri STRING,
    server_protocol STRING,
    status_code INT,
    body_bytes_sent BIGINT,
    http_user_agent STRING,
    processing_time TIMESTAMP_LTZ(3) METADATA FROM 'timestamp' VIRTUAL, -- For watermark or precombine if time_local is not good
    PRIMARY KEY (request_id) NOT ENFORCED
)
PARTITIONED BY (event_date)
WITH (
    'connector' = 'hudi',
    'path' = 'hdfs:///user/hudi/tables/requests_hudi',
    'table.type' = 'MERGE_ON_READ', -- Or COPY_ON_WRITE
    'hoodie.datasource.write.recordkey.field' = 'request_id',
    'hoodie.datasource.write.partitionpath.field' = 'event_date',
    'hoodie.datasource.write.precombine.field' = 'event_time', -- Use the parsed event_time for precombine
    'write.tasks' = '1',
    'compaction.tasks' = '1',
    'hoodie.index.type' = 'FLINK_STATE',
    'hoodie.compact.schedule.inline' = 'true', -- For local testing
    'hoodie.compact.inline.max.delta.commits' = '1' -- For local testing
);

-- Insert data from HDFS source to Hudi sink
INSERT INTO requests_hudi
SELECT
    PROCTIME_UUID() AS request_id, -- Generate a unique ID for each request
    remote_addr,
    -- Nginx $time_local format: 28/Sep/2000:12:00:00 +0200
    -- We need to parse this. Flink's TO_TIMESTAMP_LTZ is suitable.
    -- The 'XXX' pattern handles ISO 8601 time-zone offset like +0000, +0200, Z
    TO_TIMESTAMP_LTZ(time_local, 'dd/MMM/yyyy:HH:mm:ss XXX') AS event_time,
    DATE_FORMAT(TO_TIMESTAMP_LTZ(time_local, 'dd/MMM/yyyy:HH:mm:ss XXX'), 'yyyy-MM-dd') AS event_date,
    request_method,
    request_uri,
    server_protocol,
    CAST(status_code_str AS INT) AS status_code,
    CAST(body_bytes_sent_str AS BIGINT) AS body_bytes_sent,
    http_user_agent
    -- processing_time is a metadata field and should not be in the SELECT for direct insertion
FROM nginx_logs_source
WHERE remote_addr IS NOT NULL AND time_local IS NOT NULL; -- Basic filtering for essential fields
