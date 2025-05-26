# Real-time Order and Request Analysis with Hudi, Flink, and Dinky

## Overview

This project demonstrates a real-time data analytics pipeline. It captures order data from PostgreSQL using Flink CDC and Nginx web server logs, processes them in real-time with Apache Flink, and stores them in Apache Hudi, an open-source data lake platform. Dinky is used for managing and submitting Flink SQL jobs, and the entire environment is orchestrated using Docker Compose.

The primary goals are to:
*   Ingest relational database changes (orders) into Hudi.
*   Ingest semi-structured log data (Nginx requests) into Hudi.
*   Perform streaming analytics on the Hudi tables using Flink SQL.

## Architecture Diagram (Conceptual)

```
1. PostgreSQL (Orders Data)
   |
   v
   Flink CDC (via flink-sql-connector-postgres-cdc)
   |
   v
   Apache Hudi (orders_hudi table on HDFS)

2. Nginx Web Server
   |
   v
   access.log (local filesystem: ./nginx/logs/access.log)
   |
   v
   Manual/Scripted Copy (e.g., using 'docker cp' or 'hdfs dfs -put')
   |
   v
   HDFS (e.g., /user/nginx_logs/raw/)
   |
   v
   Apache Flink (reading from HDFS)
   |
   v
   Apache Hudi (requests_hudi table on HDFS)

3. Apache Hudi Tables (orders_hudi, requests_hudi)
   |
   v
   Apache Flink SQL (managed and executed via Dinky)
   |
   v
   Analytics Results (e.g., dashboards, reports, alerts)
```

## Prerequisites

*   **Docker and Docker Compose:** Ensure they are installed and running. (https://docs.docker.com/get-docker/, https://docs.docker.com/compose/install/)
*   **Git:** Required to clone this repository.
*   **Internet Connection:** Needed to download Docker images and dependency JARs.
*   **Sufficient RAM:** At least 8GB RAM is recommended for running all services.

## Setup and Installation

### 1. Clone Repository

```bash
git clone <your_repository_url> # Replace with the actual URL
cd <repository_directory_name>
```

### 2. Download Required JARs

The Flink jobs require specific connector JARs to interact with Hudi and PostgreSQL CDC. You need to download these manually and place them in the `./flink-jars/` directory. This directory is mounted into the Flink JobManager and TaskManager containers.

*   **Hudi Flink Bundle:**
    *   This bundle contains Hudi connectors for Flink. The version should match your Flink version. For Flink 1.17.x and Scala 2.12, you can use:
    *   `hudi-flink1.17-bundle_2.12-0.14.0.jar`
    *   Download from: [Apache Hudi Downloads](https://hudi.apache.org/releases/) (Look for the appropriate Flink bundle, e.g., `hudi-flink1.17-bundle_2.12-VERSION.jar`)
*   **PostgreSQL CDC Connector:**
    *   This connector allows Flink to capture changes from PostgreSQL.
    *   `flink-sql-connector-postgres-cdc-2.4.1.jar` (or a version compatible with Flink 1.17 and your PostgreSQL version)
    *   Download from: [Maven Central](https://mvnrepository.com/artifact/com.ververica/flink-sql-connector-postgres-cdc) or [Flink CDC Connectors Releases](https://github.com/ververica/flink-cdc-connectors/releases)

**Action:**
Place the downloaded JAR files into the `./flink-jars/` directory. The directory should look like this:

```
./flink-jars/
├── hudi-flink1.17-bundle_2.12-0.14.0.jar
├── flink-sql-connector-postgres-cdc-2.4.1.jar
└── .gitkeep  # (if you have it)
```

### 3. Start Infrastructure

Use Docker Compose to build and start all the services defined in `docker-compose.yml`.

```bash
docker-compose up -d
```

This will start the following key services:
*   **PostgreSQL:** `localhost:5432` (Database for orders)
*   **HDFS NameNode:** `localhost:9870` (Web UI), `namenode:9000` (Filesystem URI for Flink)
*   **Flink JobManager:** `localhost:8081` (Web UI)
*   **Nginx:** `localhost:80` (Web server generating access logs)
*   **Dinky:** `localhost:8888` (UI for Flink SQL job management)

You can check the status of the containers:
```bash
docker-compose ps
```

## Data Simulation

Two Python scripts are provided to simulate data generation.

### 1. PostgreSQL Orders

This script inserts sample order data into the `orders` table in the `hudi_db` PostgreSQL database.

*   Navigate to the data simulators directory:
    ```bash
    cd data_simulators/
    ```
*   Install Python dependencies (preferably in a virtual environment):
    ```bash
    pip install -r requirements.txt
    ```
*   Run the order simulator:
    ```bash
    # Ensure DB_HOST is set to 'postgres' if running from outside Docker network,
    # or let it default to 'localhost' if your Python env can resolve it.
    # The script defaults to 'localhost', but for Dockerized setup, 'postgres' is the service name.
    # You might need to set DB_HOST=postgres if the script can't connect.
    # For simplicity if running locally and connecting to Docker's exposed port:
    python order_simulator.py
    ```
    The script will start inserting new orders every few seconds. Keep it running.
    The `DB_HOST` environment variable in `order_simulator.py` defaults to `localhost`. If you run this script from your host machine, it will connect to the PostgreSQL instance exposed by Docker on `localhost:5432`.

### 2. Nginx Logs

This script generates Nginx access logs in the format expected by the Flink job.

*   Navigate to the data simulators directory (if not already there):
    ```bash
    cd data_simulators/  # Or use `python data_simulators/log_simulator.py` from root
    ```
*   Run the log simulator:
    ```bash
    python log_simulator.py
    ```
    This will append log lines to `./nginx/logs/access.log`. Keep it running.

## Ingesting Nginx Logs into HDFS (Manual Step)

The Nginx logs are generated on the local filesystem (mounted into the Nginx container). You need to periodically copy these logs into HDFS for Flink to process.

1.  **Create the HDFS directory (if it doesn't exist):**
    Execute this command from your host machine's terminal:
    ```bash
    docker-compose exec namenode hdfs dfs -mkdir -p /user/nginx_logs/raw
    ```

2.  **Copy the log file to HDFS:**
    ```bash
    # Create a unique name for the log file to avoid overwrites if run multiple times
    docker-compose exec namenode hdfs dfs -put ./nginx/logs/access.log /user/nginx_logs/raw/access_$(date +%s).log
    ```
    **Note:** For a production setup, you would automate this process using a tool like Fluentd, Flume, or a scheduled script to continuously move logs to HDFS. For this demo, you'll need to re-run the `put` command to ingest newer logs.

## Deploying Flink Jobs with Dinky

Dinky provides a UI to manage and submit Flink SQL jobs.

1.  **Access Dinky:** Open your browser and go to `http://localhost:8888`.
    *   Default credentials: `admin` / `admin`.

2.  **Configure Flink Cluster (if not auto-detected):**
    *   Navigate to "Registration Center" (on the left sidebar).
    *   Select "Cluster Management" -> "Flink Instance".
    *   Click the "New" button (or "+" icon).
    *   Fill in the details:
        *   **Name:** `LocalFlinkCluster` (or any name you prefer)
        *   **JobManager HA Address:** `jobmanager:8081` (This is the internal Docker network address)
        *   **Hadoop Config File Path:** (Optional, but can be useful if specific HDFS configs are needed beyond what Flink auto-detects from classpath. For this setup, usually not required as Hudi connectors handle HDFS interaction.)
    *   Click "Test Connection". If successful, click "Save".

3.  **Submit `PostgresOrdersToHudiCDC` Job:**
    *   Go to "Studio" (on the left sidebar).
    *   In the "Catalogue" panel (usually on the left), right-click on "Catalogue" (or a sub-folder).
    *   Select "New Task" -> "FlinkSQL".
    *   **Name:** `PostgresOrdersToHudiCDC`
    *   **Content:** Copy the entire content of `flink_jobs/sql/postgres_orders_to_hudi.sql` and paste it into the SQL editor.
    *   **Flink Cluster:** Select the `LocalFlinkCluster` you configured.
    *   **Savepoint Strategy:** (Optional, can be set to default)
    *   Click the "Check SQL" button (checkmark icon) to validate the SQL.
    *   If validation is successful, click the "Submit" button (play icon).
    *   You can monitor the job in the Flink UI (`http://localhost:8081`).

4.  **Submit `NginxLogsToHudi` Job:**
    *   **Important:** Ensure you have copied Nginx logs to HDFS as described in the "Ingesting Nginx Logs into HDFS" section before running this job.
    *   Follow the same steps as above:
        *   Create a new FlinkSQL task in Dinky Studio.
        *   **Name:** `NginxLogsToHudi`
        *   **Content:** Copy the entire content of `flink_jobs/sql/hdfs_nginx_logs_to_hudi.sql`.
        *   **Flink Cluster:** Select `LocalFlinkCluster`.
        *   Check SQL and Submit.

## Running Analytics Queries in Dinky

The `flink_jobs/sql/hudi_analytics_queries.sql` file contains table definitions for reading from Hudi and example analytical queries.

**General Steps for Each Analytics Query:**

1.  Go to "Studio" in Dinky.
2.  Create a new FlinkSQL task.
3.  **Name:** Give it a descriptive name (e.g., `OrdersPerMinuteAnalytics`).
4.  **Content:**
    *   First, copy the `CREATE TABLE orders_hudi_ro ...` and `CREATE TABLE requests_hudi_ro ...` definitions from the top of `flink_jobs/sql/hudi_analytics_queries.sql` into the Dinky SQL editor. These define the tables for *reading* from Hudi in a streaming fashion.
    *   Then, append *one* of the `SELECT` queries from `hudi_analytics_queries.sql` (e.g., the "Order Volume and Amount per Minute" query).
5.  **Flink Cluster:** Select `LocalFlinkCluster`.
6.  **Execution Mode:** Ensure it's set to "Streaming".
7.  Check SQL and Submit.
8.  Dinky should display the results in a "Result" tab or you can check the Flink JobManager logs/UI for output.

**Example Analytics Queries (from `hudi_analytics_queries.sql`):**

*   **Order Volume and Amount per Minute:**
    ```sql
    -- (Paste CREATE TABLE orders_hudi_ro here)
    -- (Paste CREATE TABLE requests_hudi_ro here if needed by other queries in same task, though not for this specific one)

    SELECT
        TUMBLE_START(order_time, INTERVAL '1' MINUTE) AS window_start,
        COUNT(order_id) AS order_count,
        SUM(amount) AS total_amount
    FROM orders_hudi_ro
    GROUP BY
        TUMBLE(order_time, INTERVAL '1' MINUTE);
    ```

*   **Request Volume per Minute:**
    ```sql
    -- (Paste CREATE TABLE orders_hudi_ro here if needed)
    -- (Paste CREATE TABLE requests_hudi_ro here)

    SELECT
        TUMBLE_START(event_time, INTERVAL '1' MINUTE) AS window_start,
        COUNT(request_id) AS request_count
    FROM requests_hudi_ro
    GROUP BY
        TUMBLE(event_time, INTERVAL '1' MINUTE);
    ```

*   **Top 5 Requested URIs in the last 10 minutes:**
    ```sql
    -- (Paste CREATE TABLE orders_hudi_ro here if needed)
    -- (Paste CREATE TABLE requests_hudi_ro here)

    SELECT
        window_start,
        window_end,
        request_uri,
        request_count
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY window_start, window_end ORDER BY request_count DESC) as row_num
        FROM (
            SELECT
                TUMBLE_START(event_time, INTERVAL '10' MINUTE) AS window_start,
                TUMBLE_END(event_time, INTERVAL '10' MINUTE) AS window_end,
                request_uri,
                COUNT(*) as request_count
            FROM requests_hudi_ro
            GROUP BY
                TUMBLE(event_time, INTERVAL '10' MINUTE),
                request_uri
        )
    )
    WHERE row_num <= 5;
    ```

## Verification

### Check Hudi tables in HDFS

You can list the files created by Hudi in HDFS:

```bash
docker-compose exec namenode hdfs dfs -ls /user/hudi/tables/orders_hudi
docker-compose exec namenode hdfs dfs -ls /user/hudi/tables/requests_hudi
```
You should see directories corresponding to partitions (e.g., `created_at_date=...` or `event_date=...`) and Parquet files within them.

### Query Hudi tables (Batch Mode)

You can run simple batch queries using Flink SQL in Dinky to inspect the data in Hudi tables.

1.  Create a new FlinkSQL task in Dinky.
2.  Paste the `CREATE TABLE orders_hudi_ro ...` and/or `CREATE TABLE requests_hudi_ro ...` definitions.
3.  Change `'read.streaming.enabled' = 'true'` to `'read.streaming.enabled' = 'false'` or remove it (defaults to batch). Also remove `'read.streaming.check-interval'` and any watermarks.
4.  Append a `SELECT` query.
5.  Set Execution Mode to "Batch".
6.  Submit.

Example batch query for `orders_hudi_ro`:
```sql
-- Table definition for orders_hudi_ro (modified for batch)
CREATE TABLE orders_hudi_ro (
    order_id INT, user_id VARCHAR(50), product_id VARCHAR(50),
    order_time TIMESTAMP(3), amount DECIMAL(10, 2), created_at TIMESTAMP(3),
    created_at_date VARCHAR(10)
) WITH (
    'connector' = 'hudi',
    'path' = 'hdfs:///user/hudi/tables/orders_hudi',
    'table.type' = 'MERGE_ON_READ',
    'hoodie.datasource.query.type' = 'snapshot' -- Explicitly batch/snapshot
);

SELECT * FROM orders_hudi_ro LIMIT 10;
```

Example batch query for `requests_hudi_ro`:
```sql
-- Table definition for requests_hudi_ro (modified for batch)
CREATE TABLE requests_hudi_ro (
    request_id STRING, remote_addr STRING, event_time TIMESTAMP(3),
    event_date VARCHAR(10), request_method STRING, request_uri STRING,
    server_protocol STRING, status_code INT, body_bytes_sent BIGINT,
    http_user_agent STRING
) WITH (
    'connector' = 'hudi',
    'path' = 'hdfs:///user/hudi/tables/requests_hudi',
    'table.type' = 'MERGE_ON_READ',
    'hoodie.datasource.query.type' = 'snapshot'
);

SELECT * FROM requests_hudi_ro LIMIT 10;
```

## Stopping the Environment

To stop all services and remove the containers:
```bash
docker-compose down
```
Data stored in Docker volumes (PostgreSQL data, HDFS data, Dinky data) will persist across `docker-compose down` and `up` cycles. To remove the volumes and start fresh (WARNING: this deletes data):
```bash
docker-compose down -v
```

## Troubleshooting (Optional)

*   **Port Conflicts:** If any of the default ports (5432, 9870, 8081, 80, 8888) are already in use on your system, you can change them in the `docker-compose.yml` file.
*   **JAR Version Mismatches:** Ensure the Hudi bundle and CDC connector JAR versions are compatible with Flink 1.17. Using incorrect versions is a common source of errors.
*   **HDFS Permissions:** If Flink jobs have trouble writing to HDFS, it might be due to permissions. The current HDFS setup is generally permissive for local development.
*   **Insufficient Resources:** If services fail to start or run slowly, ensure your Docker environment has enough resources (CPU, RAM) allocated.
*   **Dinky Flink Cluster Connection:** If Dinky cannot connect to `jobmanager:8081`, ensure the Flink cluster is running correctly and that Docker networking is properly configured.
*   **Log Simulators not Connecting (DB_HOST):** The `order_simulator.py` uses `DB_HOST = os.getenv("DB_HOST", "localhost")`. When running `docker-compose up`, services can reach each other using their service names (e.g., `postgres`). If you run `order_simulator.py` from your *host machine*, `localhost` is correct because Docker maps `5432` on the container to `localhost:5432` on the host. If you were to run the Python script *inside a Docker container separate from docker-compose*, you'd need to set `DB_HOST=postgres` and ensure it's on the same Docker network.
```
