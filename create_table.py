import os
import psycopg
from dotenv import load_dotenv
load_dotenv()
def drop_table():
    """Drop the quiz_results table if it exists."""
    with psycopg.connect(
        host=os.environ["PGHOST"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode=os.environ.get("PGSSLMODE", "require")
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS quiz_results;")
            conn.commit()
    print("Table dropped!")

def create_table():
    with psycopg.connect(
        host=os.environ["PGHOST"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode=os.environ.get("PGSSLMODE", "require")
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quiz_results (
                    quiz_id SERIAL PRIMARY KEY,
                    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    files_uploaded TEXT,
                    user_prompt TEXT,
                    difficulty TEXT,
                    form_title TEXT NOT NULL,
                    form_link TEXT NOT NULL,
                    editor_emails TEXT NOT NULL
                );
            """)
            conn.commit()
    print("Table created!")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'drop':
        drop_table()
    else:
        create_table()
# ...existing code from quiz_generator/create_table.py...
