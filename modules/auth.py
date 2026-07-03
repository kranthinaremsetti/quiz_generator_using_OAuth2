
# Robust Google OAuth for Streamlit web app
import os
import pickle
import streamlit as st
import tempfile
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/drive.file'
]

TOKEN_PATH = os.path.abspath('google_oauth_token.pickle')

def get_redirect_uri():
    """Resolve OAuth redirect URI from secrets/env, or default to local Streamlit URL."""
    if hasattr(st, 'secrets') and 'REDIRECT_URI' in st.secrets:
        return str(st.secrets['REDIRECT_URI']).strip()

    if 'REDIRECT_URI' in os.environ:
        return os.environ['REDIRECT_URI'].strip()

    port = st.get_option("server.port") or 8501
    return f"http://localhost:{port}"

# Helper to get credentials path (local or from Streamlit secrets)
def get_credentials_path():
    # Check if credentials are in Streamlit secrets
    if hasattr(st, 'secrets') and 'CREDENTIALS_JSON' in st.secrets:
        # Write the credentials to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(st.secrets['CREDENTIALS_JSON'])
            return f.name
    
    # Check if credentials are in environment variable
    if 'CREDENTIALS_JSON' in os.environ:
        # Write the credentials to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(os.environ['CREDENTIALS_JSON'])
            return f.name
    
    # Fall back to local credentials.json path in project root for local development
    local_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
    local_path = os.path.abspath(local_path)
    return local_path

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
    credentials_path = get_credentials_path()
    if not os.path.exists(credentials_path):
        st.error("❌ credentials.json not found. Please ensure you have OAuth2 credentials set up.")
        st.stop()

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    flow.redirect_uri = get_redirect_uri()

    query_params = st.query_params
    if 'code' in query_params:
        try:
            code = query_params['code']
            flow.fetch_token(code=code)
            creds = flow.credentials
            save_credentials(creds)
            if 'code' in st.query_params:
                del st.query_params['code']
            st.success("✅ Authentication successful! Redirecting...")
            time.sleep(1)
            st.rerun()
            return creds
        except Exception as e:
            st.error(f"❌ Authentication failed: {e}")
            if 'code' in st.query_params:
                del st.query_params['code']
            st.stop()

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    st.markdown("### 🔐 Google Authorization Required")
    st.markdown("Click the button below to authorize with Google:")
    st.link_button(
        "🔑 Authorize with Google",
        auth_url,
        type="primary",
        use_container_width=True
    )
    st.info(f"Authorized redirect URI in use: {flow.redirect_uri}")
    st.info("After authorization, you'll be redirected back to this app automatically.")
    st.stop()

def setup_services():
    """Set up Google API services using OAuth credentials"""
    creds = load_saved_credentials()
    if not creds:
        st.warning("🔐 Please log in with Google to use the app.")
        st.stop()
    
    return {
        "forms": build("forms", "v1", credentials=creds),
        "drive": build("drive", "v3", credentials=creds)
    }

def get_current_user_info(credentials):
    """Get current user info from Google Drive API"""
    try:
        drive_service = build("drive", "v3", credentials=credentials)
        about = drive_service.about().get(fields="user").execute()
        return about.get('user', {})
    except Exception:
        return {}
