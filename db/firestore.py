import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from dotenv import load_dotenv

import os

load_dotenv()

cred_json = os.getenv("GOOGLE_CREDENTIALS")

if cred_json is None:
    raise RuntimeError("Environment variable GOOGLE_CREDENTIALS is not set")

cred_dict = json.loads(cred_json)


cred = credentials.Certificate(cred_dict)

app = firebase_admin.initialize_app(cred)

db = firestore.client()
