from flask import Flask, request, jsonify, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
from enum import Enum
import sqlite3
from itsdangerous import URLSafeTimedSerializer
import os
import uuid
import sys
import requests
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['TEMPLATES_AUTO_RELOAD'] = True



UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp3', 'wav', 'ogg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CORS(app, supports_credentials=True, origins=["http://192.168.0.116:5173"])

login_manager = LoginManager()
login_manager.init_app(app)

s = URLSafeTimedSerializer(app.secret_key)

DB_FILE =  os.getenv("DATABASE_PATH")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", os.getenv("SECRET_KEY"))  
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,   # must be False for local http dev
    SESSION_COOKIE_DOMAIN=None
)

class Post:
    def __init__(self, id, title, blurb, writeup, media_type, media_href, timestamp, is_visible):
        self.id = id
        self.title = title
        self.blurb = blurb
        self.writeup = writeup
        self.media_type = media_type
        self.media_href = media_href
        self.timestamp = timestamp
        self.is_visible = is_visible
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'blurb': self.blurb,
            'writeup': self.writeup,
            'media_type': self.media_type,
            'media_href': self.media_href,
            'timestamp': self.timestamp,
            'is_visible': self.is_visible
        }

class MediaType(Enum):
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    LINK = "link"
    NONE = "none"

class Admin(UserMixin):
    def __init__(self):
        self.id = '1'

    def get_id(self):
        return self.id

class About:
    def __init__(self, id, header, body, last_updated=None):
        self.id = id
        self.header = header
        self.body = body
        self.last_updated = last_updated

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                blurb TEXT,
                writeup TEXT,
                media_type TEXT NOT NULL,
                media_href TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_visible INTEGER DEFAULT 1
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS about (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                header TEXT,
                body TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
    return True

init_db()

def get_about():
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, header, body, last_updated FROM about')
        row = cursor.fetchone()
    if row:
        about = About(
            row['id'],
            row['header'],
            row['body'],
            row['last_updated']
        )
        return about
    else:
        return None


def get_post_by_id(post_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, blurb, writeup, media_type, media_href, timestamp, is_visible FROM posts WHERE id = ?', (post_id,))
        row = cursor.fetchone()
    if row:
        post = Post(
            row['id'],
            row['title'],
            row['blurb'],
            row['writeup'],
            row['media_type'],
            row['media_href'],
            row['timestamp'],
            row['is_visible']
        )
        return post
    else:
        return None


def get_all_posts():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, blurb, writeup, media_type, media_href, timestamp, is_visible FROM posts ORDER BY timestamp DESC')
        posts = [Post(row['id'], row['title'], row['blurb'], row['writeup'], row['media_type'], row['media_href'], row['timestamp'], row['is_visible']) for row in cursor.fetchall()]
    return posts


@login_manager.user_loader
def load_user(user_id):
    if user_id == '1':
        return Admin()
    return None

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not data or 'password' not in data:
        return jsonify({"error": "Missing password"}), 400

    if data['password'] == os.getenv('ADMIN_PASSWORD'):
        admin = Admin()
        login_user(admin)
        return jsonify({"message": "Logged in"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/logout', methods = ['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"})

@app.route('/api/posts', methods=['GET'])
def get_posts():
    posts = get_all_posts()
    return jsonify([post.to_dict() for post in posts])

@app.route('/api/post/<int:id>', methods=['GET'])
def get_post(id):
    return jsonify(get_post_by_id(id).to_dict())

@app.route('/api/admin')
@login_required
def admin():
    return jsonify({"message": f"Hello {current_user.id}"})


@app.route("/api/check-auth")
def check_auth():
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "user_id": current_user.get_id()})
    return jsonify({"authenticated": False})

@app.route('/api/posts', methods=['POST'])
@login_required
def create_post():
    
    title = request.form.get('title')
    blurb = request.form.get('blurb')
    writeup = request.form.get('writeup')
    media_type = request.form.get('media_type')
    # Check for file uploads (image or audio)
    image_file = request.files.get('image')
    audio_file = request.files.get('audio')
    # check if user wants post visible
    is_visible = request.form.get('is_visible')

    media_href = None
    saved_file_path = None
    if media_type == 'image' and image_file and allowed_file(image_file.filename):
        ext = os.path.splitext(secure_filename(image_file.filename))[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        image_file.save(filepath)
        media_href = f'/uploads/{unique_filename}'
        saved_file_path = filepath
    elif media_type == 'audio' and audio_file and allowed_file(audio_file.filename):
        ext = os.path.splitext(secure_filename(audio_file.filename))[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        audio_file.save(filepath)
        media_href = f'/uploads/{unique_filename}'
        saved_file_path = filepath
    else:
        # maybe user sent a video URL or external media href
        media_href = request.form.get('media_href')

    # validate
    if not (title and (blurb or writeup or (media_type and media_href))):
        # If we saved an uploaded file but validation failed, remove the file to avoid orphaned uploads
        try:
            if saved_file_path and os.path.exists(saved_file_path):
                os.remove(saved_file_path)
        except Exception:
            pass
        return jsonify({"error": "Missing fields"}), 400

    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                'INSERT INTO posts (title, blurb, writeup, media_type, media_href, is_visible) VALUES (?,?,?,?,?,?)',
                (title, blurb, writeup, media_type, media_href, is_visible)
            )
            conn.commit()
            new_id = cur.lastrowid
    except Exception as e:
        # Cleanup saved file if DB insert failed
        try:
            if 'saved_file_path' in locals() and saved_file_path and os.path.exists(saved_file_path):
                os.remove(saved_file_path)
        except Exception:
            pass
        return jsonify({"error": f"Failed to create post: {str(e)}"}), 500

    return jsonify({
        "id": new_id,
        "title": title,
        "blurb": blurb,
        "writeup": writeup,
        "media_type": media_type,
        "media_href": media_href,
        "is_visible": is_visible
    }), 201


@app.route('/api/posts/<int:post_id>', methods=['POST'])
@login_required
def update_post(post_id):
    with get_db_connection() as conn:
        post = get_post_by_id(post_id)
        if post is None:
            return jsonify({"error": "Post not found"}), 404

        # Get form fields, fallback to current values
        title = request.form.get('title') or post.title
        blurb = request.form.get('blurb') or post.blurb
        writeup = request.form.get('writeup') or post.writeup
        media_type = request.form.get('media_type') or post.media_type
        is_visible_raw = request.form.get('is_visible')
        if is_visible_raw is not None:
            # Convert form string ("true", "on", "1", etc.) to  integer 1 or 0
            if str(is_visible_raw).lower() in ("true", "on", "1"):
                is_visible = 1
            else:
                is_visible = 0
        else:
            is_visible = post.is_visible
        print(f"updated post {post_id} and changed visibility value to {post.is_visible}")

        old_media_href = post.media_href
        print(title, blurb, writeup)
        # Handle image/audio upload
        image_file = request.files.get('image')
        audio_file = request.files.get('audio')
        new_file_uploaded = False
        saved_file_path = None
        if media_type == 'image' and image_file and allowed_file(image_file.filename):
            # delete old local file if exists
            if old_media_href and old_media_href.startswith('/uploads/'):
                old_filename = old_media_href.split('/uploads/')[-1]
                old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            ext = os.path.splitext(secure_filename(image_file.filename))[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(filepath)
            media_href = f'/uploads/{unique_filename}'
            new_file_uploaded = True
            saved_file_path = filepath
        elif media_type == 'audio' and audio_file and allowed_file(audio_file.filename):
            # delete old local file if exists
            if old_media_href and old_media_href.startswith('/uploads/'):
                old_filename = old_media_href.split('/uploads/')[-1]
                old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            ext = os.path.splitext(secure_filename(audio_file.filename))[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            audio_file.save(filepath)
            media_href = f'/uploads/{unique_filename}'
            new_file_uploaded = True
            saved_file_path = filepath
        else:
            # get incoming media_href (may be None, empty string, or a URL)
            incoming_media_href = request.form.get('media_href')
            media_href = incoming_media_href or old_media_href

        # Only delete the old uploaded file when appropriate:
        # - If a new file was uploaded we already removed the old file above.
        # - If media type changed and the client did NOT provide a new external media_href, delete old file and clear media_href.
        # - If media type changed and the client DID provide a new external media_href, delete old file but keep media_href (incoming value).
        # - If client explicitly cleared media_href (sent empty string), delete old file and clear media_href.
        if old_media_href and old_media_href.startswith('/uploads/'):
            old_filename = old_media_href.split('/uploads/')[-1]
            old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
            incoming_media_href = request.form.get('media_href')
            # case: new file uploaded -> nothing to do here (old file already removed earlier)
            if new_file_uploaded:
                pass
            else:
                # media type changed
                if media_type != post.media_type:
                    # client provided a new external href -> delete old upload but keep incoming href
                    if incoming_media_href:
                        if os.path.exists(old_filepath):
                            os.remove(old_filepath)
                    else:
                        # no incoming href -> delete old upload and clear media_href
                        if os.path.exists(old_filepath):
                            os.remove(old_filepath)
                        media_href = ""
                # client explicitly cleared media_href (empty string)
                elif incoming_media_href == "":
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                    media_href = ""
        # Update DB
        try:
            conn.execute(
                 '''
                UPDATE posts
                SET title=?, blurb=?, writeup=?, media_type=?, media_href=?, is_visible=?
                WHERE id=?
                ''',
                (title, blurb, writeup, media_type, media_href, is_visible, post_id)
            )
            conn.commit()
        except Exception as e:
            # Cleanup newly saved file if DB update failed
            try:
                if 'new_file_uploaded' in locals() and new_file_uploaded and 'saved_file_path' in locals() and saved_file_path and os.path.exists(saved_file_path):
                    os.remove(saved_file_path)
            except Exception:
                pass
            return jsonify({"error": f"Failed to update post: {str(e)}"}), 500

    return jsonify({
        "id": post_id,
        "title": title,
        "blurb": blurb,
        "writeup": writeup,
        "media_type": media_type,
        "media_href": media_href,
        "is_visible": is_visible
    })


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    with get_db_connection() as conn:
        post = get_post_by_id(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Remove file if exists
        if post.media_href and post.media_href.startswith('/uploads/'):
            filename = post.media_href.split('/uploads/')[-1]
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                os.remove(filepath)

        conn.execute('DELETE FROM posts WHERE id=?', (post_id,))
        conn.commit()

    return jsonify({"message": "Post deleted"}), 200

@app.route("/api/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



# Get API key from environment variable
@app.route("/api/check-youtube-embed")
def check_youtube_embed():
    video_id = request.args.get("id")

    if not video_id:
        return jsonify({"embeddable": False, "error": "Missing video id"}), 400

    if not YOUTUBE_API_KEY:
        return jsonify({"embeddable": False, "error": "No API key"}), 500

    api_url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=status,contentDetails&id={video_id}&key={YOUTUBE_API_KEY}"
    )
    print("Fetching:", api_url, file=sys.stderr)

    try:
        response = requests.get(api_url, timeout=5)
        data = response.json()

        items = data.get("items", [])
        if not items:
            return jsonify({"embeddable": False, "error": "Video not found"}), 404

        status = items[0].get("status", {})
        content_details = items[0].get("contentDetails", {})

        embeddable = status.get("embeddable", False)
        privacy_status = status.get("privacyStatus", "")
        region_restrictions = content_details.get("regionRestriction", {})
        content_rating = content_details.get("contentRating", {})

        # Initial check
        can_embed = embeddable and privacy_status == "public"

        # Block region- or age-restricted videos
        if region_restrictions or content_rating.get("ytRating") == "ytAgeRestricted":
            can_embed = False

        # Final oEmbed verification
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        try:
            oembed_resp = requests.get(oembed_url, timeout=5)
            if oembed_resp.status_code != 200:
                can_embed = False
        except Exception as e:
            print("oEmbed check failed:", e, file=sys.stderr)
            can_embed = False

        print("Embeddable (final):", can_embed, file=sys.stderr)
        return jsonify({"embeddable": can_embed})

    except Exception as e:
        print("Error in check_youtube_embed:", str(e), file=sys.stderr)
        return jsonify({"embeddable": False, "error": str(e)}), 500

@app.route("/api/about", methods=["GET"])
def about():
    about = get_about()
    if about:
        return jsonify({
            "id": about.id,
            "header": about.header,
            "body": about.body,
            "last_updated": about.last_updated
        })
    else:
        return jsonify({
            "id": None,
            "header": "",
            "body": "",
            "last_updated": None
        }), 404

@app.route("/api/about", methods=["POST", "PUT"])
def update_about():
    data = request.get_json()
    header = data.get("header")
    body = data.get("body")

    if not header or not body:
        return jsonify({"error": "Missing header or body"}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE about SET header = ?, body = ?, last_updated = CURRENT_TIMESTAMP WHERE id = 1",
            (header, body)
        )
        conn.commit()

    return jsonify({"message": "About page updated successfully"}), 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050,debug=True)



