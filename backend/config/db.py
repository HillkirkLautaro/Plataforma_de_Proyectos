import mysql.connector
from mysql.connector import pooling
import os

db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'portfolio_db'),
    'pool_name': 'portfolio_pool',
    'pool_size': 5
}

try:
    connection_pool = pooling.MySQLConnectionPool(**db_config)
except Exception as e:
    connection_pool = None

def get_db_connection():
    if connection_pool:
        return connection_pool.get_connection()
    return mysql.connector.connect(**{k: v for k, v in db_config.items() if k not in ['pool_name', 'pool_size']})
