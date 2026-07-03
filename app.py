import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file (only in local development)
if os.path.exists('.env'):
    load_dotenv()

# Required environment variables
REQUIRED_KEYS = [
    "MONGO_URI",
    "GEMINI_API_KEY",
    "EMAIL",
    "EMAIL_PASSWORD"
]


def get_config_value(key):
    """Read config from environment first, then Streamlit secrets."""
    value = os.environ.get(key)
    if value:
        return value
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return None


def load_required_config():
    """Collect required config from env or Streamlit secrets."""
    config = {}
    missing_keys = []
    for key in REQUIRED_KEYS:
        value = get_config_value(key)
        if value is not None and value != "":
            config[key] = value
        else:
            missing_keys.append(key)
    return config, missing_keys


secrets, missing_keys = load_required_config()

if missing_keys:
    st.error(f"❌ Missing required configuration values: {', '.join(missing_keys)}")
    st.info("Please set them in your .env file, environment variables, or Streamlit secrets.")
    st.stop()


from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment
import io
import tempfile
# import psycopg2
from pymongo import MongoClient
from modules.auth import setup_services, clear_saved_credentials, get_current_user_info, load_saved_credentials, authenticate_oauth
from modules.file_processor import parse_topic_from_files
from modules.quiz_generator import generate_quiz
from modules.forms_manager import create_quiz_form, generate_fib_variants
from insert_quiz import insert_quiz

st.set_page_config("Smart Quiz Generator")


def preview_quiz(quiz):
    st.subheader("🧪 Draft Quiz Preview")

    mcq_questions = quiz.get("mcq", [])
    fill_questions = quiz.get("fill", [])

    if mcq_questions:
        st.markdown("**Multiple Choice Questions**")
        for index, question in enumerate(mcq_questions, start=1):
            with st.expander(f"MCQ {index}: {question.get('question', 'Untitled question')}"):
                st.write("Options:")
                for option in question.get("options", []):
                    st.write(f"- {option}")
                st.write(f"Correct answer: {question.get('answer', '')}")

    if fill_questions:
        st.markdown("**Fill in the Blanks**")
        for index, question in enumerate(fill_questions, start=1):
            with st.expander(f"FIB {index}: {question.get('question', 'Untitled question')}"):
                accepted_answers = generate_fib_variants(question.get("answer", ""))
                st.write(f"Expected answer: {question.get('answer', '')}")
                st.caption("Accepted answers are treated case-insensitively:")
                st.write(", ".join(accepted_answers))


def clear_draft_state():
    for key in [
        "draft_quiz",
        "draft_inputs",
        "draft_form_link",
        "draft_ready",
        "draft_created"
    ]:
        if key in st.session_state:
            del st.session_state[key]

# --- Authentication Panel ---
st.sidebar.markdown("## 🔐 Authentication Status")

# Check for OAuth callback code in URL first
query_params = st.query_params
if 'code' in query_params:
    # We're being redirected back from Google OAuth
    st.sidebar.info("🔄 Processing Google authorization...")

credentials = load_saved_credentials()

if credentials and credentials.valid:
    user_info = get_current_user_info(credentials)
    user_name = user_info.get('displayName', 'User')
    user_email = user_info.get('emailAddress', 'Unknown')
    st.sidebar.success(f"✅ **Authenticated as:**\n{user_name}\n{user_email}")
    if st.sidebar.button("🚪 Logout"):
        clear_saved_credentials()
        st.rerun()
else:
    # Check if we're in the middle of OAuth flow
    if 'code' in query_params:
        # Process the OAuth callback
        authenticate_oauth()
    else:
        st.sidebar.warning("🔐 Not authenticated. Please log in to use Google Forms.")
        if st.sidebar.button("🔑 Login with Google", type="primary"):
            authenticate_oauth()

st.sidebar.markdown("---")

# Main panel: show welcome if not authenticated, else show app
if not credentials or not credentials.valid:
    # Don't show the welcome message if we're processing OAuth
    if 'code' not in query_params:
        st.title("🧠 Smart Quiz Generator")
        st.info("Welcome! Please log in with Google using the sidebar to access the quiz generator features.")
    st.stop()

st.title("🧠 Smart Quiz Generator")


api_key = secrets["GEMINI_API_KEY"]
col1, col2, col3 = st.columns(3)
with col1:
    num_mcq = st.number_input("Number of MCQs", min_value=0, max_value=10, value=5)
with col2:
    num_options = st.number_input("Options per MCQ", min_value=2, max_value=6, value=4)
with col3:
    num_fill = st.number_input("Number of Fill-in-the-Blanks", min_value=0, max_value=10, value=2)

uploaded_files = st.file_uploader("Upload PDF or TXT files (multiple allowed)", type=["pdf", "txt"], accept_multiple_files=True)

# --- Audio input section ---
import whisper
import warnings

st.subheader("🎤 Speak your quiz topic")
audio_dict = mic_recorder(start_prompt="Click to record", stop_prompt="Stop recording", key='recorder')
audio_text = ""

if audio_dict and audio_dict.get("bytes"):
    audio_bytes = audio_dict["bytes"]
    mic_format = audio_dict.get("format", "webm")  # default format from Chrome

    st.audio(audio_bytes, format="audio/wav")

    try:
        # STEP 1: Save raw audio bytes to file (webm or wav)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{mic_format}") as temp_in:
            temp_in.write(audio_bytes)
            temp_in.flush()
            input_path = temp_in.name

        # STEP 2: Convert to proper WAV format for Whisper
        # This works even without FFmpeg for basic formats
        try:
            audio_segment = AudioSegment.from_file(input_path, format=mic_format)
            audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)  # Mono + 16kHz is ideal
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_out:
                audio_segment.export(temp_out, format="wav")
                wav_path = temp_out.name
        except Exception as e:
            # Fallback: try to use the file directly if conversion fails
            st.info("🔄 Using direct audio file processing...")
            wav_path = input_path

        # STEP 3: Transcribe using Whisper
        st.info("🔍 Transcribing audio using Whisper...")

        @st.cache_resource
        def load_whisper_model():
            import whisper
            return whisper.load_model("base")

        model = load_whisper_model()
        result = model.transcribe(wav_path, language="en", fp16=False)

        audio_text = result["text"]
        st.success(f"Whisper Transcription: {audio_text}")

        # Clean up temporary files
        try:
            os.unlink(input_path)
            if wav_path != input_path:
                os.unlink(wav_path)
        except:
            pass  # Ignore cleanup errors

    except Exception as e:
        st.error(f"❌ Whisper transcription failed: {e}")
        st.info("💡 **Tip:** Try recording again or use text input instead.")

# Use recognized audio text as default for user_prompt
user_prompt = st.text_area(
    "📘 Enter Topic or Custom Prompt (optional)",
    value=audio_text,
    help="You can either describe the topic (e.g., 'Photosynthesis for class 8') or add extra information "
)

difficulty = st.selectbox("Select Difficulty Level", ["Easy", "Medium", "Hard"])

form_title = st.text_input("Form Title", value="Generated Quiz Form")
educator_emails_input = st.text_input(
    "📧 Email(s) for Form Access",
    help="Enter multiple email addresses separated by commas (e.g., alice@gmail.com, bob@gmail.com)"
)
educator_emails = [email.strip() for email in educator_emails_input.split(",") if email.strip()]
release_scores_immediately = True
shuffle_questions = st.checkbox(
    "Shuffle question order",
    value=True,
    help="Randomizes the order in which questions are added to the form."
)
shuffle_options = st.checkbox(
    "Shuffle MCQ options",
    value=True,
    help="Randomizes answer choices for multiple-choice questions."
)

# Database connection test
# try:
#     with psycopg2.connect() as conn:
#         with conn.cursor() as cur:
#             cur.execute("SELECT 1")
#     st.success("✅ Database connection successful.")
# except Exception as e:
#     st.error(f"❌ Database connection failed: {e}")

try:
    client = MongoClient(secrets["MONGO_URI"])
    db = client.get_database()  # quizdb
    # Simple test: list collections
    db.list_collection_names()
    st.success("✅ MongoDB connection successful.")
except Exception as e:
    st.error(f"❌ MongoDB connection failed: {e}")

if st.button("⚡ Generate Form") and (uploaded_files or user_prompt):

    file_topic = parse_topic_from_files(uploaded_files) if uploaded_files else ""
    if not (user_prompt or file_topic):
        st.error("❌ Please provide either a topic prompt or a file.")
        st.stop()

    services = setup_services()
    quiz_func = generate_quiz(file_topic, api_key, num_mcq, num_fill, difficulty)
    quiz = quiz_func(user_prompt, num_options)

    clear_draft_state()

    st.session_state.draft_quiz = quiz
    st.session_state.draft_inputs = {
        "uploaded_files": uploaded_files,
        "user_prompt": user_prompt,
        "difficulty": difficulty,
        "form_title": form_title,
        "educator_emails": educator_emails,
        "release_scores_immediately": release_scores_immediately,
        "shuffle_questions": shuffle_questions,
        "shuffle_options": shuffle_options,
        "num_options": num_options,
        "file_topic": file_topic,
        "num_mcq": num_mcq,
        "num_fill": num_fill
    }
    st.session_state.draft_ready = True
    st.session_state.draft_created = False
    st.success("✅ Draft quiz generated. Review it below and retry if needed before creating the form.")
    st.rerun()

if st.session_state.get("draft_ready") and st.session_state.get("draft_quiz"):
    preview_quiz(st.session_state.draft_quiz)

    col_review_1, col_review_2 = st.columns(2)
    with col_review_1:
        if st.button("🔁 Regenerate Draft"):
            draft_inputs = st.session_state.get("draft_inputs", {})
            file_topic = draft_inputs.get("file_topic", "")
            num_mcq = draft_inputs.get("num_mcq", num_mcq)
            num_fill = draft_inputs.get("num_fill", num_fill)
            difficulty = draft_inputs.get("difficulty", difficulty)
            num_options = draft_inputs.get("num_options", num_options)
            user_prompt = draft_inputs.get("user_prompt", user_prompt)

            quiz_func = generate_quiz(file_topic, api_key, num_mcq, num_fill, difficulty)
            st.session_state.draft_quiz = quiz_func(user_prompt, num_options)
            st.success("✅ New draft generated.")
            st.rerun()

    with col_review_2:
        if st.button("✅ Approve & Create Form"):
            draft_inputs = st.session_state.get("draft_inputs", {})
            services = setup_services()
            form_link = create_quiz_form(
                services["forms"],
                services["drive"],
                st.session_state.draft_quiz,
                draft_inputs.get("educator_emails", educator_emails),
                draft_inputs.get("form_title", form_title),
                release_scores_immediately=draft_inputs.get("release_scores_immediately", release_scores_immediately),
                shuffle_questions=draft_inputs.get("shuffle_questions", shuffle_questions),
                shuffle_options=draft_inputs.get("shuffle_options", shuffle_options)
            )

            files_uploaded = ",".join([f.name for f in draft_inputs.get("uploaded_files", uploaded_files) or []])
            editor_emails_str = ",".join(draft_inputs.get("educator_emails", educator_emails))

            insert_quiz(
                datetime.now(),
                files_uploaded,
                draft_inputs.get("user_prompt", user_prompt),
                draft_inputs.get("difficulty", difficulty),
                draft_inputs.get("form_title", form_title),
                form_link,
                editor_emails_str,
                st.session_state.draft_quiz,
                draft_inputs.get("release_scores_immediately", release_scores_immediately),
                draft_inputs.get("shuffle_questions", shuffle_questions),
                draft_inputs.get("shuffle_options", shuffle_options)
            )

            st.session_state.draft_form_link = form_link
            st.session_state.draft_created = True
            st.session_state.notification_sent = False
            st.success(f"Form created: {form_link}")
            st.rerun()

if st.session_state.get("draft_created") and st.session_state.get("draft_form_link"):
    st.success(f"Form created: {st.session_state.draft_form_link}")

    def send_email(subject, body, to_emails, from_email, from_password):
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_emails

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_email, from_password)
            server.sendmail(from_email, to_emails.split(","), msg.as_string())

    if not st.session_state.get("notification_sent"):
        try:
            subject = "Your Quiz Form is Ready!"
            body = f"Hello,<br><br>Your quiz form has been created: <a href='{st.session_state.draft_form_link}'>{st.session_state.draft_form_link}</a><br><br>Best regards,<br>Quiz Generator"
            draft_emails = ",".join(st.session_state.get("draft_inputs", {}).get("educator_emails", educator_emails))
            send_email(subject, body, draft_emails, secrets["EMAIL"], secrets["EMAIL_PASSWORD"])
            st.session_state.notification_sent = True
            st.info("Notification email sent to educators.")
        except Exception:
            st.warning("No Educators email provided")
    
# Note: Do not use st.secrets directly in production. Always use the 'secrets' dict loaded above.
