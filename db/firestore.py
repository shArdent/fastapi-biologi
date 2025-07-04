import json
from dotenv import load_dotenv

import os

import firebase_admin
from firebase_admin import credentials

from google.cloud.firestore_v1.async_client import AsyncClient
from google.oauth2 import service_account
from proto.message import Parse

load_dotenv()

cred_json = os.getenv("GOOGLE_CREDENTIALS")

if cred_json is None:
    raise RuntimeError("Environment variable GOOGLE_CREDENTIALS is not set")

cred_dict = json.loads(cred_json)

creds = service_account.Credentials.from_service_account_info(cred_dict)

cert = credentials.Certificate(cred_dict)

app = firebase_admin.initialize_app(cert)

db = AsyncClient(credentials=creds, project=cred_dict["project_id"])
