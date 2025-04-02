import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate(
    "multi-fach-firebase-adminsdk-fbsvc-6a21166fa1.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

try:
    docs = db.collection("listings").stream()
    for doc in docs:
        print(f"{doc.id} => {doc.to_dict()}")
    print("Połączenie z Firestore działa poprawnie.")
except Exception as e:
    print(f"Błąd połączenia z Firestore: {str(e)}")
