"""Database connection helpers for SQL Server using pyodbc.

Functions
- get_connection(): returns an active pyodbc connection
- test_connection(): returns True if a simple test query succeeds, else False

Environment variables (defaults provided):
- DB_DRIVER: ODBC driver name (default: 'ODBC Driver 17 for SQL Server')
- DB_SERVER: server name (default: 'localhost\\SQLEXPRESS')
- DB_NAME: database name (default: 'AWSSaaSDB')
- DB_TRUSTED: Trusted_Connection value (default: 'yes')
"""

from typing import Optional
import os
import logging

import pyodbc

logger = logging.getLogger(__name__)
if not logger.handlers:
	handler = logging.StreamHandler()
	formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def _build_connection_string(driver: str, server: str, database: str, trusted: str) -> str:
	return f"Driver={{{driver}}};Server={server};Database={database};Trusted_Connection={trusted};"


def get_connection(timeout: int = 5) -> pyodbc.Connection:
	"""Create and return a pyodbc connection to SQL Server.

	Reads connection details from environment variables with sensible defaults.

	Raises:
		pyodbc.Error: if the connection or test query fails.

	Returns:
		pyodbc.Connection: an open DB connection (caller is responsible for closing it).
	"""
	driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
	server = os.getenv("DB_SERVER", "localhost\\SQLEXPRESS")
	database = os.getenv("DB_NAME", "AWSSaaSDB")
	trusted = os.getenv("DB_TRUSTED", "yes")

	conn_str = _build_connection_string(driver, server, database, trusted)
	logger.debug("Connecting with connection string: %s", conn_str)

	try:
		conn = pyodbc.connect(conn_str, timeout=timeout)
		# quick sanity check
		cursor = conn.cursor()
		cursor.execute("SELECT 1")
		_ = cursor.fetchone()
		cursor.close()
		logger.info("Successfully connected to database '%s' on server '%s'", database, server)
		return conn
	except pyodbc.Error:
		logger.exception("pyodbc failed to connect using connection string: %s", conn_str)
		raise
	except Exception:
		logger.exception("Unexpected error while connecting to database")
		raise


def test_connection() -> bool:
	"""Test the database connection. Returns True if a connection can be opened and a test query runs.

	This function swallows exceptions and returns False on failure.
	"""
	try:
		conn = get_connection()
		try:
			conn.close()
		except Exception:
			logger.debug("Error closing connection after test, ignoring")
		return True
	except Exception:
		return False


__all__ = ["get_connection", "test_connection"]

