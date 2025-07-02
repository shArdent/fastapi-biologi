from google.cloud.firestore_v1 import DocumentReference


def get_category_data(category_ref: DocumentReference) -> dict:
    try:
        doc = category_ref.get()
        data = doc.to_dict()
        return {
            "id": doc.id,
            "name": data.get("name", "None") if data else "None",
            "description": data.get("description", "None") if data else "None",
        }
    except Exception:
        return {"id": None, "name": "None", "description": "None"}
