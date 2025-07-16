import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()
def main():
    connection = psycopg2.connect(
        host=os.environ["PGHOST"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode=os.environ.get("PGSSLMODE", "require")
    )
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM quiz_results')
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    cursor.close()
    connection.close()

if __name__ == '__main__':
    main()
