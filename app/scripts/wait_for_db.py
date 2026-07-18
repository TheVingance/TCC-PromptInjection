import socket
import time
import os
import sys

def wait_for_db():
    host = os.environ.get("POSTGRES_HOST", "postgres")
    try:
        port = int(os.environ.get("POSTGRES_PORT", 5432))
    except ValueError:
        port = 5432
        
    print(f"Waiting for database connection at {host}:{port}...", flush=True)
    
    max_retries = 30
    delay = 2
    
    for i in range(max_retries):
        try:
            with socket.create_connection((host, port), timeout=2):
                print("Database is ready! Proceeding with migrations and startup.", flush=True)
                sys.exit(0)
        except (socket.error, socket.timeout) as e:
            print(f"Database not ready yet (attempt {i+1}/{max_retries}): {e}. Retrying in {delay}s...", flush=True)
            time.sleep(delay)
            
    print("Error: Database was not reachable after maximum retries. Exiting.", file=sys.stderr, flush=True)
    sys.exit(1)

if __name__ == "__main__":
    wait_for_db()
