import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, timedelta
import pytz
import uuid
from sqlalchemy.exc import IntegrityError
from io import BytesIO

from config import Config
from models import db, User, File, ShareLink # <--- MAKE SURE THIS LINE IS HERE

app = Flask(__name__,
template_folder='template')
app.config.from_object(Config)

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize extensions
db.init_app(app) # This is line 21 where the error occurs
# ... rest of your app.py
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to login page if not authenticated
login_manager.login_message_category = 'info' # Flash message category

# Initialize Fernet
cipher_suite = Fernet(app.config['ENCRYPTION_KEY'])

# Context processor for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # Use db.session.get for SQLAlchemy 2.0+ compatibility
    return db.session.get(User, int(user_id))

# --- Routes ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login')) # Redirect to login page for unauthenticated users

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('register.html', username=username)

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError: # Catches unique constraint violation (username already exists)
            db.session.rollback()
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('register.html', username=username)
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')
            return render_template('register.html', username=username)

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html', username=username)

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file:
            original_filename = secure_filename(file.filename)
            # Generate a UUID for the encrypted filename
            unique_filename = str(uuid.uuid4())
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            try:
                # Read file content, encrypt, and save
                file_content = file.read()
                encrypted_content = cipher_suite.encrypt(file_content)

                with open(file_path, 'wb') as f:
                    f.write(encrypted_content)

                # Get file size and mimetype
                file_size = len(file_content) # Original size before encryption
                file_mimetype = file.mimetype if file.mimetype else 'application/octet-stream'

                new_file = File(
                    filename=unique_filename,
                    original_filename=original_filename,
                    mimetype=file_mimetype,
                    size=file_size,
                    owner=current_user
                )
                db.session.add(new_file)
                db.session.commit()
                flash('File uploaded and encrypted successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'File upload failed: {e}', 'danger')

            return redirect(url_for('dashboard'))

    # Fetch files for the current user and their share links
    user_files = File.query.filter_by(user_id=current_user.id).all()
    files_with_shares = []
    for f in user_files:
        # Eagerly load share links to avoid N+1 queries if possible, though lazy=True works too
        shares = ShareLink.query.filter_by(file_id=f.id).order_by(ShareLink.created_at.desc()).all()
        files_with_shares.append({'file': f, 'shares': shares})

    return render_template('dashboard.html', user=current_user, files_with_shares=files_with_shares)

@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file_record = db.session.get(File, file_id)

    if not file_record:
        flash('File not found.', 'danger')
        return redirect(url_for('dashboard'))

    if file_record.user_id != current_user.id:
        flash('You do not have permission to download this file.', 'danger')
        abort(403)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.filename)

    try:
        with open(file_path, 'rb') as f:
            encrypted_content = f.read()
        decrypted_content = cipher_suite.decrypt(encrypted_content)

        # --- CHANGE STARTS HERE ---
        # Use BytesIO to create an in-memory file-like object
        return send_file(
            BytesIO(decrypted_content),
            mimetype=file_record.mimetype,
            as_attachment=True,
            download_name=file_record.original_filename
        )
        # --- CHANGE ENDS HERE ---
    except FileNotFoundError:
        flash('Encrypted file not found on server.', 'danger')
        abort(404)
    except InvalidToken:
        flash('Decryption failed: Invalid key or corrupted file.', 'danger')
        abort(500)
    except Exception as e:
        flash(f'An error occurred during download: {e}', 'danger')
        abort(500)

@app.route('/share/<int:file_id>', methods=['GET', 'POST'])
@login_required
def share_file(file_id):
    file_record = db.session.get(File, file_id)

    if not file_record:
        flash('File not found.', 'danger')
        return redirect(url_for('dashboard'))

    if file_record.user_id != current_user.id:
        flash('You do not have permission to share this file.', 'danger')
        abort(403)

    share_link_url = None
    if request.method == 'POST':
        expiry_minutes = request.form.get('expiry_minutes', type=int)
        recipient_info = request.form.get('recipient_info', '').strip()

        expires_at = None
        if expiry_minutes is not None and expiry_minutes > 0:
            expires_at = datetime.now(pytz.utc) + timedelta(minutes=expiry_minutes)

        new_share_link = ShareLink(
            file_id=file_record.id,
            expires_at=expires_at,
            recipient_info=recipient_info if recipient_info else None
        )
        db.session.add(new_share_link)
        db.session.commit()
        share_link_url = url_for('access_file', share_uuid=new_share_link.uuid, _external=True)
        flash('Share link generated successfully!', 'success')

    return render_template('share.html', file=file_record, share_link=share_link_url)

@app.route('/access/<string:share_uuid>')
def access_file(share_uuid):
    share_link = ShareLink.query.filter_by(uuid=share_uuid, is_active=True).first()

    if not share_link:
        flash('Share link is invalid or has been revoked.', 'danger')
        abort(404)

    if share_link.is_expired():
        share_link.is_active = False
        db.session.commit()
        flash('Share link has expired.', 'danger')
        abort(404)

    file_record = db.session.get(File, share_link.file_id)

    if not file_record:
        flash('Associated file not found.', 'danger')
        share_link.is_active = False
        db.session.commit()
        abort(404)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.filename)

    try:
        with open(file_path, 'rb') as f:
            encrypted_content = f.read()
        decrypted_content = cipher_suite.decrypt(encrypted_content)

        # --- CHANGE STARTS HERE ---
        # Use BytesIO to create an in-memory file-like object
        return send_file(
            BytesIO(decrypted_content),
            mimetype=file_record.mimetype,
            as_attachment=True,
            download_name=file_record.original_filename
        )
        # --- CHANGE ENDS HERE ---
    except FileNotFoundError:
        flash('File not found on server.', 'danger')
        abort(404)
    except InvalidToken:
        flash('Decryption failed: File corrupted or key mismatch.', 'danger')
        share_link.is_active = False
        db.session.commit()
        abort(500)
    except Exception as e:
        flash(f'An unexpected error occurred: {e}', 'danger')
        abort(500)

@app.route('/revoke_share/<string:share_uuid>')
@login_required
def revoke_share(share_uuid):
    share_link = ShareLink.query.filter_by(uuid=share_uuid).first()

    if not share_link:
        flash('Share link not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Ensure the current user owns the file associated with the share link
    if share_link.shared_file.user_id != current_user.id:
        flash('You do not have permission to revoke this share link.', 'danger')
        abort(403)

    if share_link.is_active:
        share_link.is_active = False
        db.session.commit()
        flash('Share link has been revoked.', 'success')
    else:
        flash('Share link was already inactive.', 'info')

    return redirect(url_for('dashboard'))


@app.route('/delete_file/<int:file_id>')
@login_required
def delete_file(file_id):
    file_record = db.session.get(File, file_id)

    if not file_record:
        flash('File not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Ensure the current user owns the file
    if file_record.user_id != current_user.id:
        flash('You do not have permission to delete this file.', 'danger')
        abort(403)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.filename)

    try:
        # Delete file from filesystem
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            flash('File not found on disk, removing record from database.', 'warning')

        # Delete file record and associated share links from database
        db.session.delete(file_record)
        db.session.commit()
        flash(f'File "{file_record.original_filename}" and all its share links deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting file: {e}', 'danger')

    return redirect(url_for('dashboard'))


# Database initialization on app startup
with app.app_context():
    db.create_all()

# ... your Flask app code ...

if __name__ == '__main__':
    app.run(debug=True, ssl_context='adhoc', port=5001) 
