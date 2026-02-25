#!/usr/bin/env python3
"""Initialize SQLite database for database.

This script is intended to be re-runnable and idempotent:
- It creates the base schema if it does not exist.
- It performs lightweight schema upgrades (migrations) if needed.
- It updates app_info metadata such as schema_version.
"""

import os
import sqlite3

DB_NAME = "myapp.db"
DB_USER = "kaviasqlite"  # Not used for SQLite, but kept for consistency
DB_PASSWORD = "kaviadefaultpassword"  # Not used for SQLite, but kept for consistency
DB_PORT = "5000"  # Not used for SQLite, but kept for consistency

# Increment this when schema changes require an upgrade path.
SCHEMA_VERSION = 1


def _get_app_info_value(cursor: sqlite3.Cursor, key: str) -> str | None:
    """Get a value from app_info by key, returning None if not found."""
    cursor.execute("SELECT value FROM app_info WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None


def _set_app_info_value(cursor: sqlite3.Cursor, key: str, value: str) -> None:
    """Insert/update a value in app_info."""
    cursor.execute(
        "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
        (key, value),
    )


def _ensure_base_schema(cursor: sqlite3.Cursor) -> None:
    """Create core tables needed by the application."""
    # app_info stores metadata (including schema version).
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Note: users table is kept because it already existed in this template container.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _ensure_tasks_schema(cursor: sqlite3.Cursor) -> None:
    """Create tasks table schema for the To-Do application.

    Fields:
      - id: integer PK
      - title: task text
      - completed: 0/1 boolean flag
      - created_at: creation timestamp
      - updated_at: last modification timestamp
      - completed_at: timestamp when marked completed (nullable)
    """
    # Using INTEGER for completed to align with SQLite conventions and simplify interop.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL
        )
        """
    )

    # Helpful indexes for common filters/sorts
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")


def _apply_migrations(conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Apply schema upgrades as needed.

    This is intentionally simple (SQLite container). For more complex changes,
    add new migration steps keyed by schema version.
    """
    current_version_raw = _get_app_info_value(cursor, "schema_version")
    try:
        current_version = int(current_version_raw) if current_version_raw is not None else 0
    except ValueError:
        current_version = 0

    # Migration path to schema v1: create tasks table and related indexes.
    if current_version < 1:
        _ensure_tasks_schema(cursor)
        _set_app_info_value(cursor, "schema_version", "1")
        conn.commit()
        current_version = 1

    # If future versions are added, extend here:
    # if current_version < 2:
    #   ...
    #   _set_app_info_value(cursor, "schema_version", "2")
    #   conn.commit()


print("Starting SQLite setup...")

# Check if database already exists
db_exists = os.path.exists(DB_NAME)
if db_exists:
    print(f"SQLite database already exists at {DB_NAME}")
    # Verify it's accessible
    try:
        conn_check = sqlite3.connect(DB_NAME)
        conn_check.execute("SELECT 1")
        conn_check.close()
        print("Database is accessible and working.")
    except Exception as e:
        print(f"Warning: Database exists but may be corrupted: {e}")
else:
    print("Creating new SQLite database...")

# Create/connect database
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Keep foreign keys enabled for future schema expansions
cursor.execute("PRAGMA foreign_keys = ON")

# Ensure base schema exists
_ensure_base_schema(cursor)

# Insert initial metadata (idempotent)
_set_app_info_value(cursor, "project_name", "database")
_set_app_info_value(cursor, "version", "0.1.0")
_set_app_info_value(cursor, "author", "John Doe")
_set_app_info_value(cursor, "description", "")

# Apply migrations/upgrades (including tasks schema)
_apply_migrations(conn, cursor)

# Ensure the current schema version key exists even on brand new DBs.
if _get_app_info_value(cursor, "schema_version") is None:
    _set_app_info_value(cursor, "schema_version", str(SCHEMA_VERSION))

conn.commit()

# Get database statistics
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
table_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM app_info")
record_count = cursor.fetchone()[0]

conn.close()

# Save connection information to a file
current_dir = os.getcwd()
connection_string = f"sqlite:///{current_dir}/{DB_NAME}"

try:
    with open("db_connection.txt", "w") as f:
        f.write("# SQLite connection methods:\n")
        f.write(f"# Python: sqlite3.connect('{DB_NAME}')\n")
        f.write(f"# Connection string: {connection_string}\n")
        f.write(f"# File path: {current_dir}/{DB_NAME}\n")
    print("Connection information saved to db_connection.txt")
except Exception as e:
    print(f"Warning: Could not save connection info: {e}")

# Create environment variables file for Node.js viewer
db_path = os.path.abspath(DB_NAME)

# Ensure db_visualizer directory exists
if not os.path.exists("db_visualizer"):
    os.makedirs("db_visualizer", exist_ok=True)
    print("Created db_visualizer directory")

try:
    with open("db_visualizer/sqlite.env", "w") as f:
        f.write(f'export SQLITE_DB="{db_path}"\n')
    print("Environment variables saved to db_visualizer/sqlite.env")
except Exception as e:
    print(f"Warning: Could not save environment variables: {e}")

print("\nSQLite setup complete!")
print(f"Database: {DB_NAME}")
print(f"Location: {current_dir}/{DB_NAME}")
print("")

print("To use with Node.js viewer, run: source db_visualizer/sqlite.env")

print("\nTo connect to the database, use one of the following methods:")
print(f"1. Python: sqlite3.connect('{DB_NAME}')")
print(f"2. Connection string: {connection_string}")
print(f"3. Direct file access: {current_dir}/{DB_NAME}")
print("")

print("Database statistics:")
print(f"  Tables: {table_count}")
print(f"  App info records: {record_count}")

# If sqlite3 CLI is available, show how to use it
try:
    import subprocess

    result = subprocess.run(["which", "sqlite3"], capture_output=True, text=True)
    if result.returncode == 0:
        print("")
        print("SQLite CLI is available. You can also use:")
        print(f"  sqlite3 {DB_NAME}")
except Exception:
    pass

# Exit successfully
print("\nScript completed successfully.")
