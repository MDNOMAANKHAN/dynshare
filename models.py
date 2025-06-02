from datetime import datetime, timedelta
import pytz # Import pytz for timezone awareness
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import uuid

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # Store hashed passwords
    files = db.relationship('File', backref='owner', lazy=True, cascade="all, delete-orphan")

    def get_id(self):
        return str(self.id) # Flask-Login expects string ID

    def __repr__(self):
        return f"User('{self.username}', ID: {self.id})"

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), unique=True, nullable=False) # Stored encrypted filename
    original_filename = db.Column(db.String(255), nullable=False) # Original filename
    mimetype = db.Column(db.String(100), nullable=False) # File MIME type
    size = db.Column(db.BigInteger, nullable=False) # File size in bytes
    upload_date = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.now(pytz.utc)) # <--- THIS LINE
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    share_links = db.relationship('ShareLink', backref='shared_file', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"File('{self.original_filename}', '{self.upload_date}', User: {self.user_id})"

class ShareLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())) # UUID for the share link
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.now(pytz.utc)) # <--- THIS LINE
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True) # <--- THIS LINE
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    recipient_info = db.Column(db.String(255), nullable=True) # Optional info about recipient

    def is_expired(self):
        # Compare with current UTC time, ensuring both are timezone-aware
        return datetime.now(pytz.utc) > self.expires_at if self.expires_at else False

