# server.py - CollegeTrends Backend (Rewrite)
# Flask + PostgreSQL + Cloudinary | All tables: collegetrendsxx_

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import jwt
import datetime
import bcrypt
import cloudinary
import cloudinary.uploader
import re
from functools import wraps

app = Flask(__name__)
CORS(app)

# ── CONFIGURATION ─────────────────────────────────────────────────
DB_HOST     = "dpg-d70himndiees73dlbeig-a.frankfurt-postgres.render.com"
DB_NAME     = "trends_db2"
DB_USER     = "trends_db2_user"
DB_PASSWORD = "h5NO8WY8nxLF64WSM7jwYZ7b8B7dCOiR"
DB_PORT     = 5432

CLOUDINARY_CLOUD_NAME  = "ddusfl7pi"
CLOUDINARY_API_KEY     = "599965682593626"
CLOUDINARY_API_SECRET  = "pUcb90_1jtv-rDlHXRRsfDcBK5k"

JWT_SECRET    = "collegetrends_secret_key_2025"
JWT_ALGORITHM = "HS256"

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# ── DATABASE ───────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            sslmode='require'
        )
        g.db.cursor_factory = psycopg2.extras.RealDictCursor
    return g.db

@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Create all collegetrendsxx_ tables fresh"""
    db = get_db()
    cur = db.cursor()

    tables = [
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_institutions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            location VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_courses (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            institution_id INTEGER REFERENCES collegetrendsxx_institutions(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            university VARCHAR(100),
            course VARCHAR(100),
            bio TEXT,
            avatar_url VARCHAR(500),
            is_verified BOOLEAN DEFAULT FALSE,
            is_private BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_posts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            caption TEXT,
            media_url VARCHAR(500),
            media_type VARCHAR(10) CHECK (media_type IN ('image', 'video')),
            tags TEXT[],
            course_id INTEGER REFERENCES collegetrendsxx_courses(id),
            institution_id INTEGER REFERENCES collegetrendsxx_institutions(id),
            likes_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            upvotes_count INTEGER DEFAULT 0,
            downvotes_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_post_likes (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES collegetrendsxx_posts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_votes (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES collegetrendsxx_posts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            vote_type VARCHAR(4) CHECK (vote_type IN ('up', 'down')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_comments (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES collegetrendsxx_posts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_follows (
            id SERIAL PRIMARY KEY,
            follower_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            following_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_id, following_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_bookmarks (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES collegetrendsxx_posts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            actor_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE SET NULL,
            type VARCHAR(20) CHECK (type IN ('like', 'comment', 'follow', 'vote')),
            post_id INTEGER REFERENCES collegetrendsxx_posts(id) ON DELETE CASCADE,
            message TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_conversations (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_conversation_participants (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES collegetrendsxx_conversations(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            last_read_at TIMESTAMP,
            UNIQUE(conversation_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrendsxx_messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES collegetrendsxx_conversations(id) ON DELETE CASCADE,
            sender_id INTEGER REFERENCES collegetrendsxx_users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]

    for sql in tables:
        cur.execute(sql)

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_xx_posts_user_id   ON collegetrendsxx_posts(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_xx_posts_created   ON collegetrendsxx_posts(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_xx_likes_post      ON collegetrendsxx_post_likes(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_xx_likes_user      ON collegetrendsxx_post_likes(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_xx_votes_post      ON collegetrendsxx_votes(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_xx_comments_post   ON collegetrendsxx_comments(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_xx_follows_follower ON collegetrendsxx_follows(follower_id)",
        "CREATE INDEX IF NOT EXISTS idx_xx_follows_following ON collegetrendsxx_follows(following_id)",
        "CREATE INDEX IF NOT EXISTS idx_xx_notifs_user     ON collegetrendsxx_notifications(user_id, is_read)",
        "CREATE INDEX IF NOT EXISTS idx_xx_messages_conv   ON collegetrendsxx_messages(conversation_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_xx_bookmarks_user  ON collegetrendsxx_bookmarks(user_id)"
    ]

    for sql in indexes:
        cur.execute(sql)

    db.commit()
    cur.close()


# ── AUTH HELPERS ───────────────────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header:
            parts = auth_header.split(" ")
            if len(parts) == 2:
                token = parts[1]
            else:
                return jsonify({'message': 'Token malformed'}), 401

        if not token:
            return jsonify({'message': 'Token missing'}), 401

        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            g.current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated


def get_user_stats(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) as count FROM collegetrendsxx_posts WHERE user_id = %s", (user_id,))
    posts_count = cur.fetchone()['count']
    cur.execute("SELECT COUNT(*) as count FROM collegetrendsxx_follows WHERE following_id = %s", (user_id,))
    followers_count = cur.fetchone()['count']
    cur.execute("SELECT COUNT(*) as count FROM collegetrendsxx_follows WHERE follower_id = %s", (user_id,))
    following_count = cur.fetchone()['count']
    cur.close()
    return posts_count, followers_count, following_count


def make_token(user_id):
    return jwt.encode(
        {'user_id': user_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )


# ── AUTH ───────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username  = data.get('username', '').lower().strip()
    email     = data.get('email', '').lower().strip()
    password  = data.get('password', '')
    full_name = data.get('full_name', '')
    university = data.get('university', '')
    course    = data.get('course', '')

    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    cur = db.cursor()

    cur.execute(
        "SELECT id FROM collegetrendsxx_users WHERE username = %s OR email = %s",
        (username, email)
    )
    if cur.fetchone():
        cur.close()
        return jsonify({'error': 'Username or email already exists'}), 409

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cur.execute("""
        INSERT INTO collegetrendsxx_users (username, email, password_hash, full_name, university, course)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    """, (username, email, password_hash, full_name, university, course))

    user_id = cur.fetchone()['id']
    db.commit()
    cur.close()

    return jsonify({
        'token': make_token(user_id),
        'user': {
            'id': user_id,
            'username': username,
            'full_name': full_name,
            'university': university,
            'course': course
        }
    })


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('username', '').lower().strip()
    password   = data.get('password', '')

    if not identifier or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, username, email, password_hash, full_name, university, course,
               bio, avatar_url, is_verified, is_private
        FROM collegetrendsxx_users
        WHERE username = %s OR email = %s
    """, (identifier, identifier))

    user = cur.fetchone()
    cur.close()

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401

    posts_count, followers_count, following_count = get_user_stats(user['id'])

    return jsonify({
        'token': make_token(user['id']),
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'university': user['university'],
            'course': user['course'],
            'bio': user['bio'],
            'avatar': user['avatar_url'],
            'verified': user['is_verified'],
            'is_private': user['is_private'],
            'posts_count': posts_count,
            'followers_count': followers_count,
            'following_count': following_count
        }
    })


@app.route('/api/me', methods=['GET'])
@token_required
def get_me():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, username, email, full_name, university, course, bio, avatar_url,
               is_verified, is_private
        FROM collegetrendsxx_users
        WHERE id = %s
    """, (g.current_user_id,))
    user = cur.fetchone()
    cur.close()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    posts_count, followers_count, following_count = get_user_stats(user['id'])

    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'full_name': user['full_name'],
        'university': user['university'],
        'course': user['course'],
        'bio': user['bio'],
        'avatar': user['avatar_url'],
        'verified': user['is_verified'],
        'is_private': user['is_private'],
        'posts_count': posts_count,
        'followers_count': followers_count,
        'following_count': following_count
    })


# ── PROFILE ────────────────────────────────────────────────────────
@app.route('/api/users/<int:user_id>', methods=['GET'])
@token_required
def get_user_profile(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, username, full_name, university, course, bio, avatar_url,
               is_verified, is_private
        FROM collegetrendsxx_users
        WHERE id = %s
    """, (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        return jsonify({'error': 'User not found'}), 404

    # Check follow status
    cur.execute(
        "SELECT 1 FROM collegetrendsxx_follows WHERE follower_id = %s AND following_id = %s",
        (g.current_user_id, user_id)
    )
    is_following = cur.fetchone() is not None
    cur.close()

    posts_count, followers_count, following_count = get_user_stats(user_id)

    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'university': user['university'],
        'course': user['course'],
        'bio': user['bio'],
        'avatar': user['avatar_url'],
        'verified': user['is_verified'],
        'is_private': user['is_private'],
        'is_following': is_following,
        'posts_count': posts_count,
        'followers_count': followers_count,
        'following_count': following_count
    })


#Express.js - add this simple endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'ok' });
});

@app.route('/api/users/me', methods=['PATCH'])
@token_required
def update_profile():
    data = request.get_json()
    allowed_fields = ['full_name', 'username', 'university', 'course', 'bio', 'avatar_url', 'is_private']
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    db = get_db()
    cur = db.cursor()

    # Validate new username uniqueness
    if 'username' in updates:
        new_username = updates['username'].lower().strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
            cur.close()
            return jsonify({'error': 'Invalid username format'}), 400
        updates['username'] = new_username
        cur.execute(
            "SELECT id FROM collegetrendsxx_users WHERE username = %s AND id != %s",
            (new_username, g.current_user_id)
        )
        if cur.fetchone():
            cur.close()
            return jsonify({'error': 'Username already taken'}), 409

    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
    values = list(updates.values()) + [g.current_user_id]

    cur.execute(
        f"UPDATE collegetrendsxx_users SET {set_clause}, updated_at = NOW() WHERE id = %s",
        values
    )
    db.commit()
    cur.close()
    return jsonify({'success': True})


@app.route('/api/users/me/password', methods=['POST'])
@token_required
def change_password():
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'error': 'Both old_password and new_password are required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT password_hash FROM collegetrendsxx_users WHERE id = %s", (g.current_user_id,))
    user = cur.fetchone()

    if not user or not bcrypt.checkpw(old_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        cur.close()
        return jsonify({'error': 'Current password is incorrect'}), 401

    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cur.execute(
        "UPDATE collegetrendsxx_users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
        (new_hash, g.current_user_id)
    )
    db.commit()
    cur.close()
    return jsonify({'success': True})


# ── AVATAR UPLOAD ──────────────────────────────────────────────────
@app.route('/api/users/me/avatar', methods=['POST'])
@token_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['avatar']
    if not file.filename:
        return jsonify({'error': 'Empty file'}), 400

    try:
        result = cloudinary.uploader.upload(file, resource_type="image", folder="collegetrends/avatars")
        avatar_url = result['secure_url']
    except Exception as e:
        return jsonify({'error': 'Upload failed', 'details': str(e)}), 500

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE collegetrendsxx_users SET avatar_url = %s, updated_at = NOW() WHERE id = %s",
        (avatar_url, g.current_user_id)
    )
    db.commit()
    cur.close()
    return jsonify({'avatar_url': avatar_url})


# ── FEED ───────────────────────────────────────────────────────────
@app.route('/api/feed', methods=['GET'])
@token_required
def get_feed():
    db = get_db()
    cur = db.cursor()

    cur.execute(
        "SELECT course, university FROM collegetrendsxx_users WHERE id = %s",
        (g.current_user_id,)
    )
    user_info    = cur.fetchone()
    user_course  = user_info['course'] if user_info else ''
    user_univ    = user_info['university'] if user_info else ''

    # Fixed query with proper followers_count subquery
    cur.execute("""
        WITH scored AS (
            SELECT
                p.id, p.caption, p.media_url, p.media_type, p.tags, p.created_at,
                p.likes_count, p.comments_count, p.upvotes_count, p.downvotes_count,
                u.id   AS user_id,
                u.username, u.avatar_url, u.university AS user_university,
                u.course AS user_course, u.is_verified,
                (SELECT COUNT(*) FROM collegetrendsxx_follows WHERE following_id = u.id) as followers_count,
                CASE WHEN pl.id IS NOT NULL THEN TRUE ELSE FALSE END AS user_liked,
                CASE WHEN bk.id IS NOT NULL THEN TRUE ELSE FALSE END AS user_bookmarked,
                v.vote_type AS user_vote,
                CASE
                    WHEN u.course = %s AND u.course != '' THEN 50
                    WHEN u.university = %s AND u.university != '' THEN 30
                    ELSE 0
                END AS similarity_score,
                CASE WHEN f.following_id IS NOT NULL THEN 1 ELSE 0 END AS is_followed,
                (p.likes_count + p.comments_count * 2 + p.upvotes_count * 3)::FLOAT /
                    POWER(EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 3600 + 2, 1.2) AS popularity_score,
                RANDOM() AS rand_factor
            FROM collegetrendsxx_posts p
            JOIN collegetrendsxx_users u ON p.user_id = u.id
            LEFT JOIN collegetrendsxx_post_likes pl
                ON p.id = pl.post_id AND pl.user_id = %s
            LEFT JOIN collegetrendsxx_bookmarks bk
                ON p.id = bk.post_id AND bk.user_id = %s
            LEFT JOIN collegetrendsxx_votes v
                ON p.id = v.post_id AND v.user_id = %s
            LEFT JOIN collegetrendsxx_follows f
                ON f.following_id = p.user_id AND f.follower_id = %s
            WHERE p.created_at > NOW() - INTERVAL '30 days'
        )
        SELECT
            s.*,
            (s.popularity_score + s.similarity_score) * (0.9 + s.rand_factor * 0.2) AS final_score,
            lc.lc_username, lc.lc_text
        FROM scored s
        LEFT JOIN LATERAL (
            SELECT u2.username AS lc_username, c.text AS lc_text
            FROM collegetrendsxx_comments c
            JOIN collegetrendsxx_users u2 ON c.user_id = u2.id
            WHERE c.post_id = s.id
            ORDER BY c.created_at DESC
            LIMIT 1
        ) lc ON TRUE
        ORDER BY
            CASE WHEN s.is_followed = 1 OR s.similarity_score > 0 THEN 1 ELSE 0 END DESC,
            final_score DESC
        LIMIT 50
    """, (user_course, user_univ,
          g.current_user_id, g.current_user_id, g.current_user_id, g.current_user_id))

    posts = cur.fetchall()
    cur.close()

    result = []
    for p in posts:
        result.append({
            'id': p['id'],
            'caption': p['caption'],
            'tags': p['tags'] if p['tags'] else [],
            'media_url': p['media_url'],
            'media_type': p['media_type'],
            'created_at': p['created_at'].isoformat() if p['created_at'] else None,
            'likes_count': p['likes_count'],
            'upvotes_count': p['upvotes_count'],
            'downvotes_count': p['downvotes_count'],
            'comments_count': p['comments_count'],
            'vote_count': p['upvotes_count'] - p['downvotes_count'],
            'user_liked': p['user_liked'],
            'user_bookmarked': p['user_bookmarked'],
            'user_vote': p['user_vote'],
            'username': p['username'],
            'user_id': p['user_id'],
            'user_avatar': p['avatar_url'],
            'university': p['user_university'],
            'course': p['user_course'],
            'verified': p['is_verified'],
            'followers_count': p['followers_count'] or 0,
            'latest_comment': {
                'username': p['lc_username'],
                'text': p['lc_text']
            } if p['lc_username'] else None
        })

    return jsonify(result)



# ── POSTS ──────────────────────────────────────────────────────────
@app.route('/api/posts', methods=['POST'])
@token_required
def create_post():
    import json
    caption   = request.form.get('caption', '')
    tags_raw  = request.form.get('tags', '[]')
    course_id = request.form.get('course_id') or None

    try:
        tags = json.loads(tags_raw)
        if not isinstance(tags, list):
            tags = []
    except Exception:
        tags = []

    media_url  = None
    media_type = None

    if 'media' in request.files:
        file = request.files['media']
        if file.filename:
            try:
                upload_result = cloudinary.uploader.upload(file, resource_type="auto",
                                                           folder="collegetrends/posts")
                media_url  = upload_result['secure_url']
                media_type = 'video' if file.content_type and 'video' in file.content_type else 'image'
            except Exception as e:
                return jsonify({'error': 'Upload failed', 'details': str(e)}), 500

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO collegetrendsxx_posts (user_id, caption, media_url, media_type, tags, course_id)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, created_at
    """, (g.current_user_id, caption, media_url, media_type, tags, course_id))

    row = cur.fetchone()
    db.commit()
    cur.close()

    return jsonify({
        'id': row['id'],
        'created_at': row['created_at'].isoformat(),
        'media_url': media_url,
        'message': 'Post created'
    }), 201


@app.route('/api/posts/<int:post_id>', methods=['GET'])
@token_required
def get_post(post_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT p.*, u.username, u.avatar_url,
               u.university AS user_university, u.course AS user_course, u.is_verified
        FROM collegetrendsxx_posts p
        JOIN collegetrendsxx_users u ON p.user_id = u.id
        WHERE p.id = %s
    """, (post_id,))
    post = cur.fetchone()

    if not post:
        cur.close()
        return jsonify({'error': 'Post not found'}), 404

    cur.execute("SELECT 1 FROM collegetrendsxx_post_likes WHERE post_id = %s AND user_id = %s",
                (post_id, g.current_user_id))
    user_liked = cur.fetchone() is not None

    cur.execute("SELECT vote_type FROM collegetrendsxx_votes WHERE post_id = %s AND user_id = %s",
                (post_id, g.current_user_id))
    vote_row   = cur.fetchone()
    user_vote  = vote_row['vote_type'] if vote_row else None

    cur.execute("SELECT 1 FROM collegetrendsxx_bookmarks WHERE post_id = %s AND user_id = %s",
                (post_id, g.current_user_id))
    user_bookmarked = cur.fetchone() is not None

    cur.execute("""
        SELECT c.*, u.username, u.avatar_url
        FROM collegetrendsxx_comments c
        JOIN collegetrendsxx_users u ON c.user_id = u.id
        WHERE c.post_id = %s
        ORDER BY c.created_at ASC
    """, (post_id,))
    comments = cur.fetchall()
    cur.close()

    return jsonify({
        'id': post['id'],
        'caption': post['caption'],
        'tags': post['tags'] if post['tags'] else [],
        'media_url': post['media_url'],
        'media_type': post['media_type'],
        'created_at': post['created_at'].isoformat() if post['created_at'] else None,
        'likes_count': post['likes_count'],
        'upvotes_count': post['upvotes_count'],
        'downvotes_count': post['downvotes_count'],
        'comments_count': post['comments_count'],
        'vote_count': post['upvotes_count'] - post['downvotes_count'],
        'user_liked': user_liked,
        'user_bookmarked': user_bookmarked,
        'user_vote': user_vote,
        'username': post['username'],
        'user_id': post['user_id'],
        'user_avatar': post['avatar_url'],
        'university': post['user_university'],
        'course': post['user_course'],
        'verified': post['is_verified'],
        'comments': [{
            'id': c['id'],
            'text': c['text'],
            'username': c['username'],
            'user_avatar': c['avatar_url'],
            'created_at': c['created_at'].isoformat() if c['created_at'] else None
        } for c in comments]
    })


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(post_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT user_id FROM collegetrendsxx_posts WHERE id = %s", (post_id,))
    post = cur.fetchone()

    if not post:
        cur.close()
        return jsonify({'error': 'Post not found'}), 404

    if post['user_id'] != g.current_user_id:
        cur.close()
        return jsonify({'error': 'Unauthorized'}), 403

    cur.execute("DELETE FROM collegetrendsxx_posts WHERE id = %s", (post_id,))
    db.commit()
    cur.close()
    return jsonify({'message': 'Post deleted'})


# ── LIKES ──────────────────────────────────────────────────────────
@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@token_required
def toggle_like(post_id):
    data        = request.get_json() or {}
    should_like = data.get('like', True)

    db = get_db()
    cur = db.cursor()

    if should_like:
        try:
            cur.execute("""
                INSERT INTO collegetrendsxx_post_likes (post_id, user_id) VALUES (%s, %s)
            """, (post_id, g.current_user_id))
            cur.execute(
                "UPDATE collegetrendsxx_posts SET likes_count = likes_count + 1 WHERE id = %s",
                (post_id,)
            )
            # Notify post owner (deduplicated per hour)
            cur.execute("SELECT user_id FROM collegetrendsxx_posts WHERE id = %s", (post_id,))
            owner = cur.fetchone()
            if owner and owner['user_id'] != g.current_user_id:
                cur.execute("""
                    INSERT INTO collegetrendsxx_notifications
                        (user_id, actor_id, type, post_id, message)
                    SELECT %s, %s, 'like', %s, 'liked your post'
                    WHERE NOT EXISTS (
                        SELECT 1 FROM collegetrendsxx_notifications
                        WHERE user_id = %s AND actor_id = %s AND type = 'like'
                          AND post_id = %s AND created_at > NOW() - INTERVAL '1 hour'
                    )
                """, (owner['user_id'], g.current_user_id, post_id,
                      owner['user_id'], g.current_user_id, post_id))
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            cur.close()
            return jsonify({'success': True, 'message': 'Already liked'})
    else:
        cur.execute("""
            DELETE FROM collegetrendsxx_post_likes WHERE post_id = %s AND user_id = %s
        """, (post_id, g.current_user_id))
        cur.execute("""
            UPDATE collegetrendsxx_posts
            SET likes_count = GREATEST(0, likes_count - 1)
            WHERE id = %s
        """, (post_id,))
        db.commit()

    cur.close()
    return jsonify({'success': True})


# ── VOTES ──────────────────────────────────────────────────────────
@app.route('/api/posts/<int:post_id>/vote', methods=['POST'])
@token_required
def vote_post(post_id):
    data      = request.get_json() or {}
    vote_type = data.get('vote')  # 'up' | 'down' | null

    if vote_type not in ('up', 'down', None):
        return jsonify({'error': "vote must be 'up', 'down', or null"}), 400

    db = get_db()
    cur = db.cursor()

    cur.execute(
        "SELECT vote_type FROM collegetrendsxx_votes WHERE post_id = %s AND user_id = %s",
        (post_id, g.current_user_id)
    )
    existing = cur.fetchone()

    if vote_type is None:
        # Remove vote
        if existing:
            cur.execute(
                "DELETE FROM collegetrendsxx_votes WHERE post_id = %s AND user_id = %s",
                (post_id, g.current_user_id)
            )
            if existing['vote_type'] == 'up':
                cur.execute(
                    "UPDATE collegetrendsxx_posts SET upvotes_count = GREATEST(0, upvotes_count - 1) WHERE id = %s",
                    (post_id,)
                )
            else:
                cur.execute(
                    "UPDATE collegetrendsxx_posts SET downvotes_count = GREATEST(0, downvotes_count - 1) WHERE id = %s",
                    (post_id,)
                )

    elif existing:
        # Change vote only if different
        if existing['vote_type'] != vote_type:
            cur.execute(
                "UPDATE collegetrendsxx_votes SET vote_type = %s WHERE post_id = %s AND user_id = %s",
                (vote_type, post_id, g.current_user_id)
            )
            if vote_type == 'up':
                cur.execute("""
                    UPDATE collegetrendsxx_posts
                    SET upvotes_count   = upvotes_count + 1,
                        downvotes_count = GREATEST(0, downvotes_count - 1)
                    WHERE id = %s
                """, (post_id,))
            else:
                cur.execute("""
                    UPDATE collegetrendsxx_posts
                    SET downvotes_count = downvotes_count + 1,
                        upvotes_count   = GREATEST(0, upvotes_count - 1)
                    WHERE id = %s
                """, (post_id,))

    else:
        # New vote
        cur.execute(
            "INSERT INTO collegetrendsxx_votes (post_id, user_id, vote_type) VALUES (%s, %s, %s)",
            (post_id, g.current_user_id, vote_type)
        )
        if vote_type == 'up':
            cur.execute(
                "UPDATE collegetrendsxx_posts SET upvotes_count = upvotes_count + 1 WHERE id = %s",
                (post_id,)
            )
        else:
            cur.execute(
                "UPDATE collegetrendsxx_posts SET downvotes_count = downvotes_count + 1 WHERE id = %s",
                (post_id,)
            )
        # Notify only on upvote
        if vote_type == 'up':
            cur.execute("SELECT user_id FROM collegetrendsxx_posts WHERE id = %s", (post_id,))
            owner = cur.fetchone()
            if owner and owner['user_id'] != g.current_user_id:
                cur.execute("""
                    INSERT INTO collegetrendsxx_notifications
                        (user_id, actor_id, type, post_id, message)
                    VALUES (%s, %s, 'vote', %s, 'upvoted your post')
                """, (owner['user_id'], g.current_user_id, post_id))

    db.commit()
    cur.close()
    return jsonify({'success': True})


# ── BOOKMARKS ──────────────────────────────────────────────────────
@app.route('/api/posts/<int:post_id>/bookmark', methods=['POST'])
@token_required
def toggle_bookmark(post_id):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id FROM collegetrendsxx_bookmarks WHERE post_id = %s AND user_id = %s",
        (post_id, g.current_user_id)
    )
    if cur.fetchone():
        cur.execute(
            "DELETE FROM collegetrendsxx_bookmarks WHERE post_id = %s AND user_id = %s",
            (post_id, g.current_user_id)
        )
        bookmarked = False
    else:
        cur.execute(
            "INSERT INTO collegetrendsxx_bookmarks (post_id, user_id) VALUES (%s, %s)",
            (post_id, g.current_user_id)
        )
        bookmarked = True

    db.commit()
    cur.close()
    return jsonify({'bookmarked': bookmarked})


@app.route('/api/bookmarks', methods=['GET'])
@token_required
def get_bookmarks():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.id, p.caption, p.media_url, p.media_type, p.likes_count,
               p.comments_count, p.created_at,
               u.username, u.avatar_url, u.is_verified
        FROM collegetrendsxx_bookmarks bk
        JOIN collegetrendsxx_posts p ON bk.post_id = p.id
        JOIN collegetrendsxx_users u ON p.user_id = u.id
        WHERE bk.user_id = %s
        ORDER BY bk.created_at DESC
    """, (g.current_user_id,))
    posts = cur.fetchall()
    cur.close()
    return jsonify([{
        'id': p['id'],
        'caption': p['caption'],
        'media_url': p['media_url'],
        'media_type': p['media_type'],
        'likes_count': p['likes_count'],
        'comments_count': p['comments_count'],
        'created_at': p['created_at'].isoformat() if p['created_at'] else None,
        'username': p['username'],
        'user_avatar': p['avatar_url'],
        'verified': p['is_verified']
    } for p in posts])


# ── COMMENTS ───────────────────────────────────────────────────────
@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@token_required
def add_comment(post_id):
    data = request.get_json()
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'error': 'Comment text required'}), 400

    db = get_db()
    cur = db.cursor()

    # Verify post exists
    cur.execute("SELECT user_id FROM collegetrendsxx_posts WHERE id = %s", (post_id,))
    post = cur.fetchone()
    if not post:
        cur.close()
        return jsonify({'error': 'Post not found'}), 404

    cur.execute("""
        INSERT INTO collegetrendsxx_comments (post_id, user_id, text)
        VALUES (%s, %s, %s) RETURNING id, created_at
    """, (post_id, g.current_user_id, text))
    row = cur.fetchone()

    cur.execute(
        "UPDATE collegetrendsxx_posts SET comments_count = comments_count + 1 WHERE id = %s",
        (post_id,)
    )

    if post['user_id'] != g.current_user_id:
        cur.execute("""
            INSERT INTO collegetrendsxx_notifications
                (user_id, actor_id, type, post_id, message)
            VALUES (%s, %s, 'comment', %s, 'commented on your post')
        """, (post['user_id'], g.current_user_id, post_id))

    db.commit()
    cur.close()
    return jsonify({'id': row['id'], 'created_at': row['created_at'].isoformat(), 'success': True}), 201


@app.route('/api/posts/<int:post_id>/comments/<int:comment_id>', methods=['DELETE'])
@token_required
def delete_comment(post_id, comment_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT user_id FROM collegetrendsxx_comments WHERE id = %s AND post_id = %s",
                (comment_id, post_id))
    comment = cur.fetchone()

    if not comment:
        cur.close()
        return jsonify({'error': 'Comment not found'}), 404

    if comment['user_id'] != g.current_user_id:
        cur.close()
        return jsonify({'error': 'Unauthorized'}), 403

    cur.execute("DELETE FROM collegetrendsxx_comments WHERE id = %s", (comment_id,))
    cur.execute(
        "UPDATE collegetrendsxx_posts SET comments_count = GREATEST(0, comments_count - 1) WHERE id = %s",
        (post_id,)
    )
    db.commit()
    cur.close()
    return jsonify({'success': True})


# ── USER POSTS ─────────────────────────────────────────────────────
@app.route('/api/users/<int:user_id>/posts', methods=['GET'])
@token_required
def get_user_posts(user_id):
    db = get_db()
    cur = db.cursor()

    # Enforce privacy
    cur.execute("SELECT is_private FROM collegetrendsxx_users WHERE id = %s", (user_id,))
    target = cur.fetchone()
    if not target:
        cur.close()
        return jsonify({'error': 'User not found'}), 404

    if target['is_private'] and user_id != g.current_user_id:
        # Check if current user follows them
        cur.execute(
            "SELECT 1 FROM collegetrendsxx_follows WHERE follower_id = %s AND following_id = %s",
            (g.current_user_id, user_id)
        )
        if not cur.fetchone():
            cur.close()
            return jsonify({'error': 'This profile is private'}), 403

    cur.execute("""
        SELECT p.id, p.media_url, p.media_type, p.caption,
               p.likes_count, p.comments_count, p.created_at
        FROM collegetrendsxx_posts p
        WHERE p.user_id = %s
        ORDER BY p.created_at DESC
    """, (user_id,))
    posts = cur.fetchall()
    cur.close()

    return jsonify([{
        'id': p['id'],
        'media_url': p['media_url'],
        'media_type': p['media_type'],
        'caption': p['caption'],
        'likes_count': p['likes_count'],
        'comments_count': p['comments_count'],
        'created_at': p['created_at'].isoformat() if p['created_at'] else None
    } for p in posts])


# ── FOLLOW ─────────────────────────────────────────────────────────
@app.route('/api/users/<int:user_id>/follow', methods=['POST'])
@token_required
def toggle_follow(user_id):
    if user_id == g.current_user_id:
        return jsonify({'error': 'Cannot follow yourself'}), 400

    data          = request.get_json() or {}
    should_follow = data.get('follow', True)

    db = get_db()
    cur = db.cursor()

    if should_follow:
        try:
            cur.execute("""
                INSERT INTO collegetrendsxx_follows (follower_id, following_id) VALUES (%s, %s)
            """, (g.current_user_id, user_id))
            cur.execute("""
                INSERT INTO collegetrendsxx_notifications (user_id, actor_id, type, message)
                VALUES (%s, %s, 'follow', 'started following you')
            """, (user_id, g.current_user_id))
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            cur.close()
            return jsonify({'success': True, 'message': 'Already following'})
    else:
        cur.execute("""
            DELETE FROM collegetrendsxx_follows WHERE follower_id = %s AND following_id = %s
        """, (g.current_user_id, user_id))
        db.commit()

    cur.close()
    return jsonify({'success': True})


# ── SUGGESTIONS ────────────────────────────────────────────────────
@app.route('/api/suggestions', methods=['GET'])
@token_required
def get_suggestions():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.avatar_url, u.university, u.course
        FROM collegetrendsxx_users u
        WHERE u.id != %s
          AND u.is_private = FALSE
          AND u.id NOT IN (
              SELECT following_id FROM collegetrendsxx_follows WHERE follower_id = %s
          )
        ORDER BY
            CASE
                WHEN u.university = (SELECT university FROM collegetrendsxx_users WHERE id = %s) THEN 0
                WHEN u.course    = (SELECT course    FROM collegetrendsxx_users WHERE id = %s) THEN 1
                ELSE 2
            END,
            RANDOM()
        LIMIT 10
    """, (g.current_user_id, g.current_user_id, g.current_user_id, g.current_user_id))
    users = cur.fetchall()
    cur.close()
    return jsonify([{
        'id': u['id'],
        'username': u['username'],
        'avatar': u['avatar_url'] or '',
        'university': u['university'],
        'course': u['course'],
        'following': False
    } for u in users])


# ── SEARCH ─────────────────────────────────────────────────────────
@app.route('/api/search', methods=['GET'])
@token_required
def search():
    query       = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'posts')

    if not query and search_type != 'trending':
        return jsonify([])

    db = get_db()
    cur = db.cursor()

    if search_type == 'people':
        cur.execute("""
            SELECT u.id, u.username, u.avatar_url, u.university, u.course,
                   EXISTS(
                       SELECT 1 FROM collegetrendsxx_follows
                       WHERE follower_id = %s AND following_id = u.id
                   ) AS following
            FROM collegetrendsxx_users u
            WHERE (u.username ILIKE %s OR u.full_name ILIKE %s) AND u.id != %s
            LIMIT 20
        """, (g.current_user_id, f'%{query}%', f'%{query}%', g.current_user_id))
        users = cur.fetchall()
        cur.close()
        return jsonify([{
            'id': u['id'],
            'username': u['username'],
            'avatar': u['avatar_url'] or '',
            'university': u['university'],
            'course': u['course'],
            'following': u['following']
        } for u in users])

    elif search_type == 'trending':
        cur.execute("""
            SELECT UNNEST(tags) AS tag, COUNT(*) AS count
            FROM collegetrendsxx_posts
            WHERE created_at > NOW() - INTERVAL '7 days' AND tags IS NOT NULL
            GROUP BY tag
            ORDER BY count DESC
            LIMIT 20
        """)
        tags = cur.fetchall()
        cur.close()
        return jsonify([{'name': t['tag'], 'count': t['count']} for t in tags])

    else:  # posts
        cur.execute("""
            SELECT p.id, p.caption, p.media_url, p.likes_count, p.created_at,
                   u.username, u.avatar_url, u.university AS user_university,
                   u.course AS user_course, u.is_verified
            FROM collegetrendsxx_posts p
            JOIN collegetrendsxx_users u ON p.user_id = u.id
            WHERE p.caption ILIKE %s OR %s = ANY(p.tags)
            ORDER BY p.created_at DESC
            LIMIT 20
        """, (f'%{query}%', query))
        posts = cur.fetchall()
        cur.close()
        return jsonify([{
            'id': p['id'],
            'caption': p['caption'],
            'media_url': p['media_url'],
            'likes_count': p['likes_count'],
            'created_at': p['created_at'].isoformat() if p['created_at'] else None,
            'username': p['username'],
            'user_avatar': p['avatar_url'],
            'university': p['user_university'],
            'course': p['user_course'],
            'verified': p['is_verified']
        } for p in posts])


# ── NOTIFICATIONS ──────────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT n.id, n.type, n.message, n.is_read, n.created_at, n.post_id,
               u.username AS actor_username,
               p.media_url AS post_image
        FROM collegetrendsxx_notifications n
        JOIN collegetrendsxx_users u ON n.actor_id = u.id
        LEFT JOIN collegetrendsxx_posts p ON n.post_id = p.id
        WHERE n.user_id = %s
        ORDER BY n.created_at DESC
        LIMIT 50
    """, (g.current_user_id,))
    notifs = cur.fetchall()
    cur.close()
    return jsonify([{
        'id': n['id'],
        'type': n['type'],
        'actor_username': n['actor_username'],
        'message': n['message'],
        'read': n['is_read'],
        'post_id': n['post_id'],
        'post_image': n['post_image'],
        'created_at': n['created_at'].isoformat() if n['created_at'] else None
    } for n in notifs])


@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@token_required
def mark_notification_read(notif_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        UPDATE collegetrendsxx_notifications SET is_read = TRUE
        WHERE id = %s AND user_id = %s
    """, (notif_id, g.current_user_id))
    db.commit()
    cur.close()
    return jsonify({'success': True})


@app.route('/api/notifications/read-all', methods=['POST'])
@token_required
def mark_all_notifications_read():
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE collegetrendsxx_notifications SET is_read = TRUE WHERE user_id = %s",
        (g.current_user_id,)
    )
    db.commit()
    cur.close()
    return jsonify({'success': True})


# ── MESSAGES ───────────────────────────────────────────────────────
@app.route('/api/conversations', methods=['GET'])
@token_required
def get_conversations():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT
            c.id,
            u2.id   AS partner_id,
            u2.username AS partner_name,
            u2.avatar_url AS partner_avatar,
            lm.content AS last_message,
            lm.created_at AS last_message_at,
            (
                SELECT COUNT(*) FROM collegetrendsxx_messages
                WHERE conversation_id = c.id
                  AND sender_id != %s AND is_read = FALSE
            ) AS unread_count
        FROM collegetrendsxx_conversations c
        JOIN collegetrendsxx_conversation_participants cp1
            ON c.id = cp1.conversation_id AND cp1.user_id = %s
        JOIN collegetrendsxx_conversation_participants cp2
            ON c.id = cp2.conversation_id AND cp2.user_id != %s
        JOIN collegetrendsxx_users u2 ON cp2.user_id = u2.id
        LEFT JOIN LATERAL (
            SELECT content, created_at
            FROM collegetrendsxx_messages
            WHERE conversation_id = c.id
            ORDER BY created_at DESC
            LIMIT 1
        ) lm ON TRUE
        ORDER BY lm.created_at DESC NULLS LAST
    """, (g.current_user_id, g.current_user_id, g.current_user_id))
    convs = cur.fetchall()
    cur.close()
    return jsonify([{
        'id': c['id'],
        'partner_id': c['partner_id'],
        'partner_name': c['partner_name'],
        'partner_avatar': c['partner_avatar'] or '',
        'last_message': c['last_message'],
        'last_message_at': c['last_message_at'].isoformat() if c['last_message_at'] else None,
        'unread_count': c['unread_count']
    } for c in convs])


@app.route('/api/conversations/start', methods=['POST'])
@token_required
def start_conversation():
    data          = request.get_json()
    other_user_id = data.get('user_id')

    if not other_user_id or other_user_id == g.current_user_id:
        return jsonify({'error': 'Invalid user'}), 400

    db = get_db()
    cur = db.cursor()

    # Verify target user exists
    cur.execute("SELECT id FROM collegetrendsxx_users WHERE id = %s", (other_user_id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'User not found'}), 404

    # Check existing conversation
    cur.execute("""
        SELECT c.id
        FROM collegetrendsxx_conversations c
        JOIN collegetrendsxx_conversation_participants cp1
            ON c.id = cp1.conversation_id AND cp1.user_id = %s
        JOIN collegetrendsxx_conversation_participants cp2
            ON c.id = cp2.conversation_id AND cp2.user_id = %s
    """, (g.current_user_id, other_user_id))
    existing = cur.fetchone()

    if existing:
        cur.close()
        return jsonify({'conversation_id': existing['id']})

    cur.execute("INSERT INTO collegetrendsxx_conversations DEFAULT VALUES RETURNING id")
    conv_id = cur.fetchone()['id']
    cur.execute(
        "INSERT INTO collegetrendsxx_conversation_participants (conversation_id, user_id) VALUES (%s, %s)",
        (conv_id, g.current_user_id)
    )
    cur.execute(
        "INSERT INTO collegetrendsxx_conversation_participants (conversation_id, user_id) VALUES (%s, %s)",
        (conv_id, other_user_id)
    )
    db.commit()
    cur.close()
    return jsonify({'conversation_id': conv_id}), 201


@app.route('/api/conversations/<int:conv_id>/messages', methods=['GET'])
@token_required
def get_messages(conv_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT 1 FROM collegetrendsxx_conversation_participants
        WHERE conversation_id = %s AND user_id = %s
    """, (conv_id, g.current_user_id))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Unauthorized'}), 403

    cur.execute("""
        SELECT m.id, m.sender_id, m.content, m.is_read, m.created_at, u.username
        FROM collegetrendsxx_messages m
        JOIN collegetrendsxx_users u ON m.sender_id = u.id
        WHERE m.conversation_id = %s
        ORDER BY m.created_at ASC
    """, (conv_id,))
    messages = cur.fetchall()

    cur.execute("""
        UPDATE collegetrendsxx_messages SET is_read = TRUE
        WHERE conversation_id = %s AND sender_id != %s AND is_read = FALSE
    """, (conv_id, g.current_user_id))
    db.commit()
    cur.close()

    return jsonify([{
        'id': m['id'],
        'sender_id': m['sender_id'],
        'username': m['username'],
        'content': m['content'],
        'is_read': m['is_read'],
        'created_at': m['created_at'].isoformat() if m['created_at'] else None
    } for m in messages])


@app.route('/api/conversations/<int:conv_id>/messages', methods=['POST'])
@token_required
def send_message(conv_id):
    data    = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': 'Content required'}), 400

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT 1 FROM collegetrendsxx_conversation_participants
        WHERE conversation_id = %s AND user_id = %s
    """, (conv_id, g.current_user_id))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Unauthorized'}), 403

    cur.execute("""
        INSERT INTO collegetrendsxx_messages (conversation_id, sender_id, content)
        VALUES (%s, %s, %s) RETURNING id, created_at
    """, (conv_id, g.current_user_id, content))
    row = cur.fetchone()

    cur.execute(
        "UPDATE collegetrendsxx_conversations SET updated_at = NOW() WHERE id = %s",
        (conv_id,)
    )
    db.commit()
    cur.close()

    return jsonify({
        'id': row['id'],
        'sender_id': g.current_user_id,
        'content': content,
        'is_read': False,
        'created_at': row['created_at'].isoformat()
    }), 201


@app.route('/api/conversations/<int:conv_id>/messages/check', methods=['GET'])
@token_required
def check_new_messages(conv_id):
    """Poll for new messages — participant-gated"""
    db = get_db()
    cur = db.cursor()

    # Auth check
    cur.execute("""
        SELECT 1 FROM collegetrendsxx_conversation_participants
        WHERE conversation_id = %s AND user_id = %s
    """, (conv_id, g.current_user_id))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Unauthorized'}), 403

    after = request.args.get('after', 0, type=int)
    cur.execute(
        "SELECT COUNT(*) AS count FROM collegetrendsxx_messages WHERE conversation_id = %s",
        (conv_id,)
    )
    total = cur.fetchone()['count']
    cur.close()
    return jsonify({'has_new': total > after, 'total': total})


# ── STATUS ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({'status': 'CollegeTrends API Running', 'version': '2.0.0'})


# ── STARTUP ────────────────────────────────────────────────────────
with app.app_context():
    init_db()
    print("✅ Database initialized — collegetrendsxx_ tables ready")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
