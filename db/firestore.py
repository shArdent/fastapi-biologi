import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import os

print(os.getenv('GOOGLE_CREDENTIALS_JSON_PATH'))

cred = credentials.Certificate(os.getenv('GOOGLE_CREDENTIALS_JSON_PATH', 'path/to/your/serviceAccountKey.json'))

app = firebase_admin.initialize_app(cred)

db = firestore.client()