import psycopg2
import time
import random
import datetime
import os

# PostgreSQL connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")  # Use 'postgres' if running in a container
DB_NAME = "hudi_db"
DB_USER = "hudi_user"
DB_PASSWORD = "hudi_password"

def create_orders_table(conn):
    """Creates an orders table if it doesn't already exist."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50),
                    product_id VARCHAR(50),
                    order_time TIMESTAMP,
                    amount DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            conn.commit()
            print("Table 'orders' checked/created successfully.")
    except psycopg2.Error as e:
        print(f"Error creating table: {e}")
        raise

def generate_order_data():
    """Generates random order data."""
    user_id = f"user_{random.randint(1, 1000)}"
    product_id = f"product_{random.randint(1, 200)}"
    order_time = datetime.datetime.now()
    amount = round(random.uniform(10.0, 500.0), 2)
    return user_id, product_id, order_time, amount

def insert_order_data(conn, order_data):
    """Inserts a new order record into the orders table."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO orders (user_id, product_id, order_time, amount)
                VALUES (%s, %s, %s, %s)
            """, order_data)
            conn.commit()
    except psycopg2.Error as e:
        print(f"Error inserting order data: {e}")
        # Potentially rollback if the connection is in an error state
        if conn and not conn.closed:
            conn.rollback()
        raise

if __name__ == "__main__":
    conn = None  # Initialize conn to None
    print(f"Attempting to connect to PostgreSQL: host={DB_HOST}, dbname={DB_NAME}, user={DB_USER}")
    try:
        conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        print("Successfully connected to PostgreSQL.")
        create_orders_table(conn)

        while True:
            order_data = generate_order_data()
            insert_order_data(conn, order_data)
            print(f"Inserted order: User {order_data[0]}, Product {order_data[1]}, Amount ${order_data[3]:.2f}")
            time.sleep(random.randint(1, 5))

    except psycopg2.OperationalError as e:
        print(f"Could not connect to PostgreSQL database: {e}")
        print("Please ensure PostgreSQL is running and accessible, and that the credentials are correct.")
        print(f"Using connection parameters: host={DB_HOST}, dbname={DB_NAME}, user={DB_USER}")
    except psycopg2.Error as e:
        print(f"An error occurred with PostgreSQL: {e}")
    except KeyboardInterrupt:
        print("\nOrder simulator stopped by user.")
    finally:
        if conn and not conn.closed:
            conn.close()
            print("PostgreSQL connection closed.")
