import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path

# Dynamically construct the path to the service account file
BASE_DIR = Path(__file__).resolve().parent.parent
cred_path = os.path.join(BASE_DIR, "firebase-service-account.json")

# Initialize Firebase with the service account
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

# Initialize Firestore client
db = firestore.client()

def sync_ride_to_firestore(ride):
    ride_data = {
        "host": ride.host.id,
        "ride_code": ride.ride_code,
        "is_completed": ride.is_completed,
    }
    db.collection("ride_chats").document(str(ride.id)).set(ride_data)