"""
Google Forms API tools — wraps the Forms REST API for use by the ADK agent.
Each function is a standalone tool with full docstrings so the model
understands exactly what to pass.
"""

import os
import mimetypes
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


# ── Auth ──────────────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def _get_creds():
    """Return valid OAuth2 credentials, refreshing or re-authenticating as needed."""
    creds = None
    token_path = os.environ.get("GOOGLE_TOKEN_PATH", "token.json")
 
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
 
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_path = os.environ.get(
                "GOOGLE_CREDENTIALS_PATH", "./form_agent/tools/credentials.json"
            )
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"OAuth credentials file not found: {credentials_path}\n"
                    "Download it from Google Cloud Console and set "
                    "GOOGLE_CREDENTIALS_PATH env var."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
 
        with open(token_path, "w") as f:
            f.write(creds.to_json())
 
    return creds
 
 
def _get_forms_service():
    return build("forms", "v1", credentials=_get_creds())
 
 
def _get_drive_service():
    return build("drive", "v3", credentials=_get_creds())


# ── Tool functions ────────────────────────────────────────────────────────────


def create_form(title: str, description: str = "") -> dict:
    """Create a new Google Form.
 
    Args:
        title: The title of the form (required).
        description: Optional description shown below the title.
 
    Returns:
        dict with keys: formId, title, description, responderUri, editUri
    """
    service = _get_forms_service()
 
    # Google Forms API only allows info.title on initial create
    form = service.forms().create(body={"info": {"title": title}}).execute()
    form_id = form["formId"]
 
    # Set description via batchUpdate if provided
    if description:
        service.forms().batchUpdate(
            formId=form_id,
            body={
                "requests": [
                    {
                        "updateFormInfo": {
                            "info": {"description": description},
                            "updateMask": "description",
                        }
                    }
                ]
            },
        ).execute()
 
    return {
        "formId": form_id,
        "title": title,
        "description": description,
        "responderUri": f"https://docs.google.com/forms/d/{form_id}/viewform",
        "editUri": f"https://docs.google.com/forms/d/{form_id}/edit",
    }

def add_text_question(
    form_id: str,
    question_title: str,
    required: bool = False,
    paragraph: bool = False,
    index: int = 0,
) -> dict:
    """Add a short-answer or paragraph text question to a form.

    Args:
        form_id: The ID of the target form.
        question_title: The question text shown to respondents.
        required: Whether respondents must answer this question.
        paragraph: If True, shows a multi-line text box; otherwise single-line.
        index: Position to insert the question (0 = top).

    Returns:
        dict with success status and question details.
    """
    service = _get_forms_service()

    request_body = {
        "requests": [
            {
                "createItem": {
                    "item": {
                        "title": question_title,
                        "questionItem": {
                            "question": {
                                "required": required,
                                "textQuestion": {"paragraph": paragraph},
                            }
                        },
                    },
                    "location": {"index": index},
                }
            }
        ]
    }

    service.forms().batchUpdate(formId=form_id, body=request_body).execute()

    return {
        "success": True,
        "message": "Text question added",
        "questionTitle": question_title,
        "type": "paragraph" if paragraph else "short_answer",
        "required": required,
    }


def add_multiple_choice_question(
    form_id: str,
    question_title: str,
    options: list[str],
    required: bool = False,
    index: int = 0,
) -> dict:
    """Add a multiple-choice (radio button) question — respondents pick ONE option.

    Args:
        form_id: The ID of the target form.
        question_title: The question text.
        options: List of answer choices, e.g. ["Yes", "No", "Maybe"].
        required: Whether respondents must answer.
        index: Position to insert the question (0 = top).

    Returns:
        dict with success status and question details.
    """
    service = _get_forms_service()

    request_body = {
        "requests": [
            {
                "createItem": {
                    "item": {
                        "title": question_title,
                        "questionItem": {
                            "question": {
                                "required": required,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [{"value": o} for o in options],
                                },
                            }
                        },
                    },
                    "location": {"index": index},
                }
            }
        ]
    }

    service.forms().batchUpdate(formId=form_id, body=request_body).execute()

    return {
        "success": True,
        "message": "Multiple-choice question added",
        "questionTitle": question_title,
        "options": options,
        "required": required,
    }


def add_checkbox_question(
    form_id: str,
    question_title: str,
    options: list[str],
    required: bool = False,
    index: int = 0,
) -> dict:
    """Add a checkbox question — respondents may pick MULTIPLE options.

    Args:
        form_id: The ID of the target form.
        question_title: The question text.
        options: List of answer choices.
        required: Whether respondents must select at least one option.
        index: Position to insert the question (0 = top).

    Returns:
        dict with success status and question details.
    """
    service = _get_forms_service()

    request_body = {
        "requests": [
            {
                "createItem": {
                    "item": {
                        "title": question_title,
                        "questionItem": {
                            "question": {
                                "required": required,
                                "choiceQuestion": {
                                    "type": "CHECKBOX",
                                    "options": [{"value": o} for o in options],
                                },
                            }
                        },
                    },
                    "location": {"index": index},
                }
            }
        ]
    }

    service.forms().batchUpdate(formId=form_id, body=request_body).execute()

    return {
        "success": True,
        "message": "Checkbox question added",
        "questionTitle": question_title,
        "options": options,
        "required": required,
    }


def add_dropdown_question(
    form_id: str,
    question_title: str,
    options: list[str],
    required: bool = False,
    index: int = 0,
) -> dict:
    """Add a dropdown question — respondents pick ONE option from a drop-down list.

    Args:
        form_id: The ID of the target form.
        question_title: The question text.
        options: List of dropdown choices.
        required: Whether respondents must answer.
        index: Position to insert the question (0 = top).

    Returns:
        dict with success status and question details.
    """
    service = _get_forms_service()

    request_body = {
        "requests": [
            {
                "createItem": {
                    "item": {
                        "title": question_title,
                        "questionItem": {
                            "question": {
                                "required": required,
                                "choiceQuestion": {
                                    "type": "DROP_DOWN",
                                    "options": [{"value": o} for o in options],
                                },
                            }
                        },
                    },
                    "location": {"index": index},
                }
            }
        ]
    }

    service.forms().batchUpdate(formId=form_id, body=request_body).execute()

    return {
        "success": True,
        "message": "Dropdown question added",
        "questionTitle": question_title,
        "options": options,
        "required": required,
    }


def add_linear_scale_question(
    form_id: str,
    question_title: str,
    low: int = 1,
    high: int = 5,
    low_label: str = "",
    high_label: str = "",
    required: bool = False,
    index: int = 0,
) -> dict:
    """Add a linear scale (rating) question.

    Args:
        form_id: The ID of the target form.
        question_title: The question text.
        low: Lowest value on the scale (1 or 0).
        high: Highest value on the scale (2–10).
        low_label: Label for the lowest value, e.g. "Not satisfied".
        high_label: Label for the highest value, e.g. "Very satisfied".
        required: Whether respondents must answer.
        index: Position to insert the question (0 = top).

    Returns:
        dict with success status and question details.
    """
    service = _get_forms_service()

    scale = {"low": low, "high": high}
    if low_label:
        scale["lowLabel"] = low_label
    if high_label:
        scale["highLabel"] = high_label

    request_body = {
        "requests": [
            {
                "createItem": {
                    "item": {
                        "title": question_title,
                        "questionItem": {
                            "question": {
                                "required": required,
                                "scaleQuestion": scale,
                            }
                        },
                    },
                    "location": {"index": index},
                }
            }
        ]
    }

    service.forms().batchUpdate(formId=form_id, body=request_body).execute()

    return {
        "success": True,
        "message": "Linear scale question added",
        "questionTitle": question_title,
        "scale": f"{low}–{high}",
        "required": required,
    }


def get_form(form_id: str) -> dict:
    """Retrieve full details of a Google Form including all items.

    Args:
        form_id: The ID of the form to retrieve.

    Returns:
        The raw form object from the Google Forms API.
    """
    service = _get_forms_service()
    return service.forms().get(formId=form_id).execute()


def get_form_responses(form_id: str) -> dict:
    """Retrieve all responses submitted to a Google Form.

    Args:
        form_id: The ID of the form.

    Returns:
        dict with 'responses' list and 'totalResponses' count.
    """
    service = _get_forms_service()
    result = service.forms().responses().list(formId=form_id).execute()

    responses = result.get("responses", [])
    return {
        "totalResponses": len(responses),
        "responses": responses,
    }


def delete_item(form_id: str, item_index: int) -> dict:
    """Delete an item (question or section) from a form by its index.

    Args:
        form_id: The ID of the form.
        item_index: Zero-based index of the item to delete.

    Returns:
        dict with success status.
    """
    service = _get_forms_service()

    request_body = {
        "requests": [
            {"deleteItem": {"location": {"index": item_index}}}
        ]
    }

    service.forms().batchUpdate(formId=form_id, body=request_body).execute()

    return {"success": True, "message": f"Item at index {item_index} deleted"}


def update_form_settings(
    form_id: str,
    collect_email: Optional[bool] = None,
    limit_one_response: Optional[bool] = None,
    show_link_to_respond_again: Optional[bool] = None,
    shuffle_questions: Optional[bool] = None,
) -> dict:
    """Update general settings for a Google Form.

    Args:
        form_id: The ID of the form.
        collect_email: If True, require respondents to log in with Google.
        limit_one_response: If True, allow only one response per Google account.
        show_link_to_respond_again: If True, show a link to submit another response.
        shuffle_questions: If True, randomise the order of questions.

    Returns:
        dict with success status and updated settings.
    """
    service = _get_forms_service()

    quiz_settings = {}
    if collect_email is not None:
        quiz_settings["collectEmail"] = collect_email
    if limit_one_response is not None:
        quiz_settings["confirmationMessage"] = {}  # placeholder
    
    settings = {}
    update_mask_fields = []

    if collect_email is not None:
        settings["emailCollectionType"] = (
            "VERIFIED" if collect_email else "DO_NOT_COLLECT"
        )
        update_mask_fields.append("settings.emailCollectionType")

    if limit_one_response is not None:
        settings["limitOneResponsePerUser"] = limit_one_response
        update_mask_fields.append("settings.limitOneResponsePerUser")

    if show_link_to_respond_again is not None:
        settings["publishSettings"] = {
            "publishState": {"isPublished": True}
        }

    if shuffle_questions is not None:
        settings["shuffleQuestionOrder"] = shuffle_questions
        update_mask_fields.append("settings.shuffleQuestionOrder")

    if not update_mask_fields:
        return {"success": False, "message": "No settings to update"}

    request_body = {
        "requests": [
            {
                "updateSettings": {
                    "settings": {"quizSettings": {}, **settings},
                    "updateMask": ",".join(update_mask_fields),
                }
            }
        ]
    }

    service.forms().batchUpdate(formId=form_id, body=request_body).execute()

    return {
        "success": True,
        "message": "Form settings updated",
        "updatedSettings": {k: v for k, v in {
            "collectEmail": collect_email,
            "limitOneResponse": limit_one_response,
            "showLinkToRespondAgain": show_link_to_respond_again,
            "shuffleQuestions": shuffle_questions,
        }.items() if v is not None},
    }

def upload_image_to_drive(image_path: str) -> dict:
    """Upload a local image file to Google Drive and return its Drive file ID.
 
    The Google Forms API requires images to be hosted on Google Drive.
    Call this tool FIRST, then pass the returned driveFileId to
    add_image_question or add_image_item.
 
 
    Args:
        image_path: Absolute or relative path to the image file on disk.
 
    Returns:
        dict with driveFileId, fileName, mimeType, and a GIF warning if applicable.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
 
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/gif"
 
    drive = _get_drive_service()
    file_name = os.path.basename(image_path)
 
    uploaded = (
        drive.files()
        .create(
            body={"name": file_name},
            media_body=MediaFileUpload(image_path, mimetype=mime_type, resumable=False),
            fields="id,name,mimeType",
        )
        .execute()
    )
 
    # Make the file readable by anyone (required for Forms API to embed it)
    drive.permissions().create(
        fileId=uploaded["id"],
        body={"type": "anyone", "role": "reader"},
    ).execute()
 
    result = {
        "driveFileId": uploaded["id"],
        "fileName": uploaded["name"],
        "mimeType": uploaded["mimeType"],
    }
    # if mime_type == "image/gif":
    #     result["warning"] = (
    #         "GIF uploaded successfully, but Google Forms displays only the "
    #         "first frame as a static image — animation is not supported by the API."
    #     )
    return result

def add_image_question(
    form_id: str,
    question_title: str,
    drive_file_id: str,
    alt_text: str = "",
    required: bool = False,
    index: int = 0,
) -> dict:
    """Add a question that displays an image above the answer input field.
 
    The image must already exist on Google Drive. Use upload_image_to_drive
    first if you only have a local file.
 
    Args:
        form_id: The ID of the target form.
        question_title: The question text shown below the image.
        drive_file_id: Google Drive file ID (from upload_image_to_drive).
        alt_text: Accessibility description of the image (recommended).
        required: Whether respondents must answer.
        index: Position to insert the question (0 = top).
 
    Returns:
        dict with success status and question details.
    """
    _get_forms_service().forms().batchUpdate(
        formId=form_id,
        body={
            "requests": [
                {
                    "createItem": {
                        "item": {
                            "title": question_title,
                            "questionItem": {
                                "image": {
                                    "sourceUri": f"https://drive.google.com/uc?export=view&id={drive_file_id}",
                                    "altText": alt_text or question_title,
                                    "properties": {
                                        "alignment": "CENTER",
                                        "width": 740,
                                    },
                                },
                                "question": {
                                    "required": required,
                                    "textQuestion": {"paragraph": False},
                                },
                            },
                        },
                        "location": {"index": index},
                    }
                }
            ]
        },
    ).execute()
 
    return {
        "success": True,
        "message": "Image question added",
        "questionTitle": question_title,
        "driveFileId": drive_file_id,
        "required": required,
    }