import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from dotenv import load_dotenv

import os

load_dotenv()

path = os.getenv('GOOGLE_CREDENTIALS_JSON_PATH', 'path/to/your/serviceAccountKey.json')

cred = credentials.Certificate(path)

app = firebase_admin.initialize_app(cred)

db = firestore.client()
