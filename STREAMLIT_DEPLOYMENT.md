# Streamlit Deployment Guide

## What to deploy
This app is Streamlit-based and works best on Streamlit Cloud.

## Before deployment
1. Rotate any exposed credentials in `credentials.json`, `.streamlit/secrets.toml`, and any copied environment files.
2. Keep `credentials.json` out of the deployed source if you want Streamlit Cloud to use `CREDENTIALS_JSON` from secrets.
3. Make sure your Google OAuth client has the Streamlit Cloud redirect URI registered.

## Streamlit Cloud setup
Add these secrets in the Streamlit Cloud Secrets editor:

- `MONGO_URI`
- `GEMINI_API_KEY`
- `EMAIL`
- `EMAIL_PASSWORD`
- `REDIRECT_URI`
- `CREDENTIALS_JSON`

Use the template in [`.streamlit/secrets.example.toml`](.streamlit/secrets.example.toml).

## Google OAuth redirect URIs
Add the exact app URL to your Google OAuth client, for example:

- `https://<your-app-name>.streamlit.app/`

If you test locally, also keep:

- `http://localhost:8501`
- `http://localhost:8501/`
- `http://127.0.0.1:8501`
- `http://127.0.0.1:8501/`

## Repository checklist
- `requirements.txt` must include every runtime dependency.
- `app.py` must read config from `st.secrets` when environment variables are absent.
- `modules/auth.py` must prefer `CREDENTIALS_JSON` from secrets for cloud runs.

## Suggested Streamlit Cloud deployment flow
1. Push the branch to GitHub.
2. Create a new Streamlit Cloud app from that repo.
3. Paste the required secrets.
4. Add the Google OAuth redirect URI.
5. Deploy and test login, quiz generation, and form creation.
