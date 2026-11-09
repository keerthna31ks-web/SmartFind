import mysql.connector
def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
       # password="Keerthuma31",
        database = "smartfind"
    )
    return connection