import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from roboflow import Roboflow

IMAGE_DIR = "data"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SAMPLE_SPREADSHEET_ID = ""
SPREADSHEET_RANGE = "Predictions!A:Z"
ROBOFLOW_PROJECT = ""

rf = Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])
project = rf.workspace().project(ROBOFLOW_PROJECT)
model = project.version(6).model

def get_all_predictions() -> list:
    """
    Retrieve predictions for each image in a folder from a model hosted on Roboflow and save them to a list of dictionaries.
    """
    all_images = os.listdir(IMAGE_DIR)

    all_predictions = []

    for i in range(len(all_images)):
        predictions = model.predict(os.path.join(IMAGE_DIR, all_images[i]), confidence=70).json()

        predictions["file_name"] = all_images[i]
        predictions["datetime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        all_predictions.append(predictions)

    return all_predictions


def save_to_spreadsheet(all_predictions) -> None:
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("sheets", "v4", credentials=creds)

    try:
        # Call the Sheets API
        sheet = service.spreadsheets()

        for p in all_predictions:
            print("saving predictions for", p["file_name"])
            for bounding_box in p["predictions"]:
                sheet.values().append(
                    spreadsheetId=SAMPLE_SPREADSHEET_ID,
                    range=SPREADSHEET_RANGE,
                    valueInputOption="USER_ENTERED",
                    body={
                        "values": [
                            [
                                bounding_box["class"],
                                bounding_box["confidence"],
                                bounding_box["x"],
                                bounding_box["y"],
                                bounding_box["width"],
                                bounding_box["height"],
                                p["file_name"],
                                p["datetime"],
                            ]
                        ]
                    },
                ).execute()

    except HttpError as err:
        print(err)


if __name__ == "__main__":
    all_predictions = get_all_predictions()
    save_to_spreadsheet(all_predictions)