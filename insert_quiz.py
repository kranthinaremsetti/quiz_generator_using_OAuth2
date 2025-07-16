import psycopg2
import os

def insert_quiz(date_created, files_uploaded, user_prompt, difficulty, form_title, form_link, editor_emails):
    try:
        print("Connecting to DB:")
        print("  HOST:", os.environ["PGHOST"])
        print("  DBNAME:", os.environ["PGDATABASE"])
        print("  USER:", os.environ["PGUSER"])
        conn = psycopg2.connect(
            host=os.environ["PGHOST"],
            dbname=os.environ["PGDATABASE"],
            user=os.environ["PGUSER"],
            password=os.environ["PGPASSWORD"],
            sslmode=os.environ.get("PGSSLMODE", "require")
        )
        cur = conn.cursor()
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
            )
        """)
        cur.execute(
            '''INSERT INTO quiz_results (date_created, files_uploaded, user_prompt, difficulty, form_title, form_link, editor_emails)
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (date_created, files_uploaded, user_prompt, difficulty, form_title, form_link, editor_emails)
        )
        conn.commit()
        cur.close()
        conn.close()
        print("Quiz inserted!")
    except Exception as e:
        print(f"⚠️ Could not save to database: {e}")
