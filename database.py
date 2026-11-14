import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    connection = mysql.connector.connect(
        host=os.getenv("TIDB_HOST"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        user=os.getenv("TIDB_USER"),
        password=os.getenv("TIDB_PASSWORD"),
        database=os.getenv("TIDB_DATABASE"),
        ssl_ca=os.getenv("TIDB_CA_PATH"),
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )

    return connection