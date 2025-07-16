import re
import streamlit as st

def generate_fib_variants(answer: str) -> list:
    """
    Generate different variants of fill-in-the-blank answers to handle
    different formatting (capitalization, spacing, etc.).
    
    Args:
        answer (str): The correct answer
        
    Returns:
        list: List of answer variants
    """
    base = answer.strip()
    no_spaces = base.replace(" ", "")
    with_spaces = re.sub(r"\s*,\s*", ", ", base)
    capitalized = base.title()
    lower = base.lower()
    upper = base.upper()
    return list(set([
        base, with_spaces, capitalized, lower, upper, no_spaces,
        base.replace(" ,", ",").replace(", ", ",")
    ]))

def create_quiz_form(forms_service, drive_service, quiz, educator_emails, form_title):
    """
    Create a Google Form with quiz questions and auto-grading.
    
    Args:
        forms_service: Google Forms API service object
        drive_service: Google Drive API service object
        quiz (dict): Generated quiz data with 'mcq' and 'fill' arrays
        educator_emails (list): List of email addresses to share form with
        form_title (str): Title for the Google Form
    """
    form_title = form_title.strip() or "Generated Quiz Form"
    # Google Forms API does not support collectEmail via API; must be set manually in UI
    form = forms_service.forms().create(body={
        "info": {"title": form_title}
    }).execute()
    form_id = form["formId"]

    drive_service.files().update(
        fileId=form_id,
        body={"name": form_title},
        fields="id"
    ).execute()

    # Initial settings + Name field
    requests = [
        {
            "updateSettings": {
                "settings": {"quizSettings": {"isQuiz": True}},
                "updateMask": "quizSettings.isQuiz"
            }
        },
        {
            "createItem": {
                "item": {
                    "title": "Name",
                    "questionItem": {
                        "question": {"required": True, "textQuestion": {}}
                    }
                },
                "location": {"index": 0}
            }
        }
    ]

    idx = 1
    def remove_duplicates(options):
        seen = set()
        unique = []
        for opt in options:
            if opt not in seen:
                unique.append(opt)
                seen.add(opt)
        return unique

    for q in quiz.get("mcq", []):
        # Remove duplicate options before sending to Google Forms
        unique_options = remove_duplicates(q["options"])
        requests.append({
            "createItem": {
                "item": {
                    "title": q["question"],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [{"value": opt} for opt in unique_options],
                                "shuffle": False
                            }
                        }
                    }
                },
                "location": {"index": idx}
            }
        })
        idx += 1

    for q in quiz.get("fill", []):
        requests.append({
            "createItem": {
                "item": {
                    "title": q["question"],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "textQuestion": {}
                        }
                    }
                },
                "location": {"index": idx}
            }
        })
        idx += 1

    forms_service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    # Share form with educator emails
    for email in educator_emails:
        drive_service.permissions().create(
            fileId=form_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": email
            },
            fields="id"
        ).execute()

    form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    return form_url
