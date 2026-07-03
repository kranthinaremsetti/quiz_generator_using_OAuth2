# import psycopg2
from pymongo import MongoClient
import os
import uuid

def insert_quiz(
    date_created,
    files_uploaded,
    user_prompt,
    difficulty,
    form_title,
    form_link,
    editor_emails,
    quiz_data=None,
    release_scores_immediately=True,
    shuffle_questions=True,
    shuffle_options=True
):
    try:
        # Connect to MongoDB using your URI from .env
        mongo_uri = os.environ.get("MONGO_URI")
        client = MongoClient(mongo_uri)

        # Get the database name from the URI (quizdb if you used that)
        db = client.get_database()
        quizzes = db.quizzes  # collection

        # Build the document
        quiz_doc = {
            "generation_id": str(uuid.uuid4()),
            "date_created": date_created,
            "files_uploaded": files_uploaded,
            "user_prompt": user_prompt,
            "difficulty": difficulty,
            "form_title": form_title,
            "form_link": form_link,
            "editor_emails": editor_emails.split(",") if editor_emails else [],
            "quiz_data": quiz_data or {},
            "settings": {
                "release_scores_immediately": release_scores_immediately,
                "shuffle_questions": shuffle_questions,
                "shuffle_options": shuffle_options
            }
        }
      # Insert into MongoDB
        quizzes.insert_one(quiz_doc)
        print("✅ Quiz inserted into MongoDB!")

    except Exception as e:
        print(f"⚠️ Could not save to MongoDB: {e}")
    
    # try:
    #     print("Connecting to DB:")
    #     print("  HOST:", os.environ["PGHOST"])
    #     print("  DBNAME:", os.environ["PGDATABASE"])
    #     print("  USER:", os.environ["PGUSER"])
    #     conn = psycopg2.connect(
    #         host=os.environ["PGHOST"],
    #         dbname=os.environ["PGDATABASE"],
    #         user=os.environ["PGUSER"],
    #         password=os.environ["PGPASSWORD"],
    #         sslmode=os.environ.get("PGSSLMODE", "require")
    #     )
    #     cur = conn.cursor()
    #     cur.execute("""
    #         CREATE TABLE IF NOT EXISTS quiz_results (
    #             quiz_id SERIAL PRIMARY KEY,
    #             date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #             files_uploaded TEXT,
    #             user_prompt TEXT,
    #             difficulty TEXT,
    #             form_title TEXT NOT NULL,
    #             form_link TEXT NOT NULL,
    #             editor_emails TEXT NOT NULL
    #         )
    #     """)
    #     cur.execute(
    #         '''INSERT INTO quiz_results (date_created, files_uploaded, user_prompt, difficulty, form_title, form_link, editor_emails)
    #            VALUES (%s, %s, %s, %s, %s, %s, %s)''',
    #         (date_created, files_uploaded, user_prompt, difficulty, form_title, form_link, editor_emails)
    #     )
    #     conn.commit()
    #     cur.close()
    #     conn.close()
    #     print("Quiz inserted!")
    # except Exception as e:
    #     print(f"⚠️ Could not save to database: {e}")
