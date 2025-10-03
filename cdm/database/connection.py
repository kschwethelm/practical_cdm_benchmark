import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv
from loguru import logger


def get_db_connection() -> psycopg.Connection:
    """
    Create and return a database connection using environment variables.

    Loads DB_NAME and DB_USER from .env file and connects to localhost.

    Returns:
        psycopg.Connection: Active database connection
    """
    load_dotenv()

    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")

    if not db_name or not db_user:
        raise ValueError("DB_NAME and DB_USER must be set in .env file")

    connection_string = f"dbname={db_name} user={db_user} host=127.0.0.1"

    logger.info(f"Connecting to database: {db_name} as user: {db_user}")

    try:
        conn = psycopg.connect(connection_string)
        logger.success("Database connection established")
        return conn
    except psycopg.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


@contextmanager
def db_cursor():
    """
    Context manager for database cursor operations.

    Automatically handles connection and cursor lifecycle.

    Yields:
        psycopg.Cursor: Database cursor for executing queries
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        conn.close()
        logger.debug("Database connection closed")
