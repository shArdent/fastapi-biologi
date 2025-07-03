import json
from dotenv import load_dotenv

import os

from google.cloud.firestore_v1.async_client import AsyncClient
from google.oauth2 import service_account

load_dotenv()

cred_json = os.getenv("GOOGLE_CREDENTIALS")

if cred_json is None:
    raise RuntimeError("Environment variable GOOGLE_CREDENTIALS is not set")

cred_dict = json.loads(cred_json)


creds = service_account.Credentials.from_service_account_info(cred_dict)

db = AsyncClient(credentials=creds, project=cred_dict["project_id"])
