import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

# Load environment variables from .env file (only in local development)
if os.path.exists('.env'):
    load_dotenv()

# Required environment variables
REQUIRED_KEYS = [
    "PGHOST", "PGUSER", "PGDATABASE", "PGSSLMODE", "PGPASSWORD",
    "GEMINI_API_KEY", "EMAIL", "EMAIL_PASSWORD"
]

# Load secrets from environment variables
secrets = {}
missing_keys = []
for key in REQUIRED_KEYS:
    value = os.environ.get(key)
    if value is not None:
        secrets[key] = value
    else:
        missing_keys.append(key)

if missing_keys:
    import streamlit as st
    st.error(f"❌ Missing required environment variables: {', '.join(missing_keys)}")
    st.info("Please set these in your .env file or environment variables.")
    st.stop()


import streamlit as st
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment
import io
import tempfile
import psycopg2
from modules.auth import setup_services, clear_saved_credentials, get_current_user_info, load_saved_credentials, authenticate_oauth
from modules.file_processor import parse_topic_from_files
from modules.quiz_generator import generate_quiz
from modules.forms_manager import create_quiz_form
from insert_quiz import insert_quiz

st.set_page_config("Smart Quiz Generator")




# --- Authentication Panel ---
st.sidebar.markdown("## 🔐 Authentication Status")

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
    st.sidebar.warning("🔐 Not authenticated. Please log in to use Google Forms.")
    if st.sidebar.button("🔑 Login with Google", type="primary"):
        authenticate_oauth()

st.sidebar.markdown("---")

# Main panel: show welcome if not authenticated, else show app
if not credentials or not credentials.valid:
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

# Database connection test
try:
    with psycopg2.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    st.success("✅ Database connection successful.")
except Exception as e:
    st.error(f"❌ Database connection failed: {e}")

if st.button("⚡ Generate Form") and (uploaded_files or user_prompt):

    file_topic = parse_topic_from_files(uploaded_files) if uploaded_files else ""
    if not (user_prompt or file_topic):
        st.error("❌ Please provide either a topic prompt or a file.")
        st.stop()

    from datetime import datetime
    services = setup_services()
    quiz_func = generate_quiz(file_topic, api_key, num_mcq, num_fill, difficulty)
    quiz = quiz_func(user_prompt, num_options)
    form_link = create_quiz_form(services["forms"], services["drive"], quiz, educator_emails, form_title)
    files_uploaded = ",".join([f.name for f in uploaded_files]) if uploaded_files else ""
    editor_emails_str = ",".join(educator_emails)
    st.success(f"Form created: {form_link}")
    
    insert_quiz(
        datetime.now(),
        files_uploaded,
        user_prompt,
        difficulty,
        form_title,
        form_link,
        editor_emails_str
    )
    # Send notification email to educators
    def send_email(subject, body, to_emails, from_email, from_password):
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_emails

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_email, from_password)
            server.sendmail(from_email, to_emails.split(","), msg.as_string())

    try:
        subject = "Your Quiz Form is Ready!"
        body = f"Hello,<br><br>Your quiz form has been created: <a href='{form_link}'>{form_link}</a><br><br>Best regards,<br>Quiz Generator"
        send_email(subject, body, editor_emails_str, secrets["EMAIL"], secrets["EMAIL_PASSWORD"])
        st.info("Notification email sent to educators.")
    except Exception as e:
        st.warning(f"No Educators email provided")
    
# Note: Do not use st.secrets directly in production. Always use the 'secrets' dict loaded above.
