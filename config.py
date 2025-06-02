import os
import secrets
from cryptography.fernet import Fernet # <--- ADD THIS IMPORT

class Config:
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    if not ENCRYPTION_KEY:
        # Generate a proper Fernet key which is 32 url-safe base64-encoded bytes
        ENCRYPTION_KEY = Fernet.generate_key()
        print(f"--- DEBUGGING KEYS (REMOVE IN PRODUCTION!) ---")
        print(f"Generated new ENCRYPTION_KEY: {ENCRYPTION_KEY.decode()}") # Decode to string for printing
        print(f"ENCRYPTION_KEY length (base64): {len(ENCRYPTION_KEY)} bytes")
        # In a real application, you'd store this in an environment variable or a secure file.
        # For local development, you might uncomment the next line to save it once:
        # os.environ['ENCRYPTION_KEY'] = ENCRYPTION_KEY.decode()
    else:
        # If ENCRYPTION_KEY is loaded from an environment variable, it should already be a base64 string.
        # Ensure it's bytes for Fernet constructor.
        ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

    # Secret key for Flask sessions and other security features
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key_if_not_set'
    print(f"SECRET_KEY: {SECRET_KEY}")
    print(f"-------------------------------------------")

    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit for uploads