
# Minimal, robust Google OAuth for Streamlit web app
import os
import pickle
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/forms.responses.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

TOKEN_PATH = os.path.abspath('google_oauth_token.pickle')
CREDENTIALS_PATH = os.path.abspath('credentials.json')

def load_saved_credentials():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_PATH, 'wb') as token:
                    pickle.dump(creds, token)
                return creds
            except Exception:
                os.remove(TOKEN_PATH)
    return None

def save_credentials(creds):
    with open(TOKEN_PATH, 'wb') as token:
        pickle.dump(creds, token)

def clear_saved_credentials():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
        st.success("✅ Logged out successfully!")

def authenticate_oauth():
    if not os.path.exists(CREDENTIALS_PATH):
        st.error("❌ credentials.json not found. Please ensure you have OAuth2 credentials set up.")
        st.stop()
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=8000)
    save_credentials(creds)
    st.success("✅ Authentication successful!")
    st.rerun()
    return creds

def setup_services():
    creds = load_saved_credentials()
    if not creds:
        st.warning("� Please log in with Google to use the app.")
        st.stop()
    return {
        "forms": build("forms", "v1", credentials=creds),
        "drive": build("drive", "v3", credentials=creds)
    }

def get_current_user_info(credentials):
    try:
        drive_service = build("drive", "v3", credentials=credentials)
        about = drive_service.about().get(fields="user").execute()
        return about.get('user', {})
    except Exception:
        return {}
