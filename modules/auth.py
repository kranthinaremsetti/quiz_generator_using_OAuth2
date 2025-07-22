
# Minimal, robust Google Service Account auth for Streamlit web app
import os
import json
import streamlit as st
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/forms.responses.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# Helper to get service account credentials
def get_service_account_credentials():
    # Check if service account JSON is in Streamlit secrets
    if hasattr(st, 'secrets') and 'SERVICE_ACCOUNT_JSON' in st.secrets:
        service_account_info = json.loads(st.secrets['SERVICE_ACCOUNT_JSON'])
        return service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
    
    # Check if service account JSON is in environment variable
    if 'SERVICE_ACCOUNT_JSON' in os.environ:
        service_account_info = json.loads(os.environ['SERVICE_ACCOUNT_JSON'])
        return service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
    
    # Fall back to local service-account.json file
    local_path = os.path.join(os.path.dirname(__file__), '..', 'service-account.json')
    if os.path.exists(local_path):
        return service_account.Credentials.from_service_account_file(
            local_path, scopes=SCOPES
        )
    
    return None

def setup_services():
    """Set up Google API services using service account credentials"""
    creds = get_service_account_credentials()
    if not creds:
        st.error("❌ Service account credentials not found. Please ensure you have service-account.json set up or SERVICE_ACCOUNT_JSON in secrets.")
        st.stop()
    
    return {
        "forms": build("forms", "v1", credentials=creds),
        "drive": build("drive", "v3", credentials=creds)
    }

def get_current_user_info(credentials):
    """Get service account info (not user info since it's a service account)"""
    try:
        # Service accounts don't have user info, so return service account email
        if hasattr(credentials, 'service_account_email'):
            return {"email": credentials.service_account_email}
        return {"email": "Service Account"}
    except Exception:
        return {"email": "Service Account"}
