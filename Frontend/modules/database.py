from pathlib import Path
from tinydb import TinyDB, Query
from datetime import datetime
import uuid

# Persistent Database setup
# Use Home directory so accounts are NOT wiped when the temp PyInstaller folder is deleted
DB_DIR = Path.home() / ".deceptron"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DB_DIR / 'db.json')
db = TinyDB(DB_PATH)
users_table = db.table('users')
uploads_table = db.table('uploads')

def signup_user(user_data):
    """
    Register a new user in the database.
    """
    User = Query()
    # Check for existing user with same email OR username in one query
    result = users_table.search((User.email == user_data['email']) | (User.username == user_data['username']))
    
    if result:
        existing = result[0]
        if existing.get('email') == user_data['email']:
             return {'success': False, 'message': 'Email already registered'}
        if existing.get('username') == user_data['username']:
             return {'success': False, 'message': 'Username already taken'}
    
    users_table.insert(user_data)
    return {'success': True, 'message': 'User registered successfully'}

def login_user(identity, password):
    """
    Verify user credentials (email or username).
    """
    User = Query()
    # Search for matching email OR username with the given password
    result = users_table.search(((User.email == identity) | (User.username == identity)) & (User.password == password))
    if result:
        user = result[0]
        # Return a copy without password
        return {'success': True, 'user': {k: v for k, v in user.items() if k != 'password'}}
    return {'success': False, 'message': 'Invalid credentials'}

def add_upload(username, file_name, file_type, file_size, file_path=""):
    """
    Record a new file upload for a specific user.
    """
    upload_data = {
        'id': str(uuid.uuid4()),
        'username': username,
        'filename': file_name,
        'type': file_type,
        'size': file_size,
        'filepath': file_path,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    uploads_table.insert(upload_data)
    return {'success': True, 'data': upload_data}

def get_user_uploads(username):
    """
    Retrieve all uploads for a specific user.
    """
    Upload = Query()
    return uploads_table.search(Upload.username == username)

def delete_upload(upload_id, username):
    """
    Delete an upload record if it belongs to the user.
    """
    Upload = Query()
    # Find the item first to get the filepath
    item = uploads_table.get((Upload.id == upload_id) & (Upload.username == username))
    
    if item:
        uploads_table.remove(doc_ids=[item.doc_id])
        return {'success': True, 'data': item}
    
    return {'success': False, 'message': 'Record not found or access denied'}

def update_user_profile(username, new_data):
    """
    Update a user's profile details.
    """
    User = Query()
    users_table.update(new_data, User.username == username)
    # Return updated user info (excluding password)
    updated_user = users_table.search(User.username == username)[0]
    return {'success': True, 'user': {k: v for k, v in updated_user.items() if k != 'password'}}

def change_password(username, current_pwd, new_pwd):
    """
    Update a user's password after verifying current one.
    """
    User = Query()
    user = users_table.get(User.username == username)
    if user and user['password'] == current_pwd:
        users_table.update({'password': new_pwd}, User.username == username)
        return {'success': True}
    return {'success': False, 'message': 'Current password incorrect'}

def update_user_preferences(username, preferences):
    """
    Update a user's preferences (e.g., default camera/mic).
    """
    User = Query()
    # upsert=True is not available in basic update, so we use a search-then-update approach or set
    # TinyDB 'update' merges dictionaries, which is what we want for nested 'preferences'
    
    # First, ensure the 'preferences' field exists
    user = users_table.get(User.username == username)
    if not user:
         return {'success': False, 'message': 'User not found'}
    
    current_prefs = user.get('preferences') or {}
    # Merge new prefs with existing ones (guard against None stored in DB)
    updated_prefs = {**(current_prefs if isinstance(current_prefs, dict) else {}), **preferences}

    
    users_table.update({'preferences': updated_prefs}, User.username == username)
    return {'success': True, 'preferences': updated_prefs}

def get_user_preferences(username):
    """
    Get a user's preferences.
    """
    User = Query()
    user = users_table.get(User.username == username)
    if user:
        return {'success': True, 'preferences': user.get('preferences', {})}
    return {'success': False, 'message': 'User not found'}

def update_last_login(username):
    """
    Update the last_login timestamp for a user.
    """
    User = Query()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    users_table.update({'last_login': timestamp}, User.username == username)
    return {'success': True, 'timestamp': timestamp}
