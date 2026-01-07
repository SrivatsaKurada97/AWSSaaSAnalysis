from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.database import test_connection
import os

# Set database connection parameters
os.environ['DB_SERVER'] = 'localhost\\SQLEXPRESS'
os.environ['DB_NAME'] = 'AWSSaaSDB'
os.environ['DB_DRIVER'] = 'ODBC Driver 17 for SQL Server'
os.environ['DB_TRUSTED'] = 'yes'

# Test the database connection
print(test_connection())