import time
import random
import datetime
import os

# Log file path (relative to the script's location in data_simulators)
LOG_FILE_PATH = "../nginx/logs/access.log"

# Predefined lists for generating log data
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"]
REQUEST_PATHS = ["/api/products", "/api/users", "/index.html", "/images/pic.jpg", "/api/orders", "/admin/login"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "python-requests/2.25.1",
    "curl/7.68.0"
]
# Weighted status codes: (code, weight)
STATUS_CODES = [(200, 10), (201, 5), (400, 2), (401, 1), (403, 1), (404, 3), (500, 2), (502, 1), (503, 1)]
FLAT_STATUS_CODES = [code for code, weight in STATUS_CODES for _ in range(weight)]


def generate_log_line():
    """Generates a realistic-looking Nginx access log line."""
    ip_address = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"
    
    # Timestamp: [dd/MMM/yyyy:HH:mm:ss +0000]
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.strftime("[%d/%b/%Y:%H:%M:%S %z]") # %z includes UTC offset like +0000
    # Ensure +0000 format if %z gives something else on some systems (though it shouldn't for UTC)
    if len(timestamp) == 28 and timestamp[-5] in ['+', '-'] and timestamp[-3:-2] == ':': # e.g. +00:00
        timestamp = timestamp[:-3] + timestamp[-2:] # convert to +0000


    http_method = random.choice(HTTP_METHODS)
    request_path = random.choice(REQUEST_PATHS)
    http_version = "HTTP/1.1" # Or random.choice(["HTTP/1.0", "HTTP/1.1", "HTTP/2.0"])
    
    status_code = random.choice(FLAT_STATUS_CODES)
    response_size = random.randint(50, 5000) if status_code == 200 else random.randint(0, 500)
    
    user_agent = random.choice(USER_AGENTS)
    
    # Format: IP - user - [timestamp] "METHOD path version" status size "referer" "user_agent"
    # Simplified for this simulator: IP - - [timestamp] "METHOD path version" status size
    # Adding a placeholder for user and referer for more realism if desired later
    log_line = f'{ip_address} - - {timestamp} "{http_method} {request_path} {http_version}" {status_code} {response_size} "-" "{user_agent}"'
    return log_line

if __name__ == "__main__":
    print(f"Log simulator started. Writing logs to: {os.path.abspath(LOG_FILE_PATH)}")

    # Ensure the log directory exists
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        print(f"Log directory '{log_dir}' does not exist. Creating it...")
        try:
            os.makedirs(log_dir)
            print(f"Log directory '{log_dir}' created successfully.")
        except OSError as e:
            print(f"Error: Could not create log directory '{log_dir}': {e}")
            exit(1)
    
    try:
        with open(LOG_FILE_PATH, "a") as f:
            while True:
                log_line = generate_log_line()
                f.write(log_line + "\n")
                f.flush()  # Ensure data is written to disk immediately
                print(f"Generated log: {log_line}")
                time.sleep(random.uniform(0.1, 1.0)) # Random interval between 0.1 and 1 second
    except FileNotFoundError:
        print(f"Error: Could not open or create log file at '{os.path.abspath(LOG_FILE_PATH)}'.")
        print("Please ensure the directory structure is correct and permissions are set.")
    except KeyboardInterrupt:
        print("\nLog simulator stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Log simulator finished.")
