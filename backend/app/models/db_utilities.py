import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import os
#get connection to postgres db
def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    return conn