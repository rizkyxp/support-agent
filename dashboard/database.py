import sqlite3
import os
from contextlib import contextmanager

# Define the local database path
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.agent_data')
DB_PATH = os.path.join(DB_DIR, 'dashboard.sqlite')

def init_db():
    """Initializes the database schema if it doesn't exist."""
    print(f"Initializing database at {DB_PATH}")
    os.makedirs(DB_DIR, exist_ok=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Table for Persistent Configurations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Table for Prompt Templates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id TEXT PRIMARY KEY,
                template_text TEXT NOT NULL
            )
        ''')
        
        # Table for Run History/Logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                mode TEXT,
                status TEXT,
                log_file TEXT
            )
        ''')
        
        conn.commit()

@contextmanager
def get_db():
    """Provides a transactional scope around a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Returns dict-like rows
    try:
        yield conn
    finally:
        conn.close()
