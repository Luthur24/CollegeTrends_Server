# app.py - CollegeTrends Backend
# Single-file Flask backend with PostgreSQL + Cloudinary

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
DB_HOST = "dpg-d70himndiees73dlbeig-a.frankfurt-postgres.render.com"
DB_NAME = "trends_db2"
DB_USER = "trends_db2_user"
DB_PASSWORD = "h5NO8WY8nxLF64WSM7jwYZ7b8B7dCOiR"
DB_PORT = 5432

CLOUDINARY_CLOUD_NAME = "ddusfl7pi"
CLOUDINARY_API_KEY = "599965682593626"
CLOUDINARY_API_SECRET = "pUcb90_1jtv-rDlHXRRsfDcBK5k"

JWT_SECRET = "collegetrends_secret_key_2025"
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

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.teardown_appcontext
def teardown_db(exception):
    close_db()

def init_db():
    """Initialize all tables with collegetrends_ prefix"""
    db = get_db()
    cur = db.cursor()
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS collegetrends_institutions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            location VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_courses (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            institution_id INTEGER REFERENCES collegetrends_institutions(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_users (
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
        CREATE TABLE IF NOT EXISTS collegetrends_posts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            caption TEXT,
            media_url VARCHAR(500),
            media_type VARCHAR(10) CHECK (media_type IN ('image', 'video')),
            tags TEXT[],
            course_id INTEGER REFERENCES collegetrends_courses(id),
            institution_id INTEGER REFERENCES collegetrends_institutions(id),
            likes_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            upvotes_count INTEGER DEFAULT 0,
            downvotes_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_post_likes (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES collegetrends_posts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_votes (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES collegetrends_posts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            vote_type VARCHAR(4) CHECK (vote_type IN ('up', 'down')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_comments (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES collegetrends_posts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_follows (
            id SERIAL PRIMARY KEY,
            follower_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            following_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_id, following_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_bookmarks (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES collegetrends_posts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            actor_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            type VARCHAR(20) CHECK (type IN ('like', 'comment', 'follow', 'vote')),
            post_id INTEGER REFERENCES collegetrends_posts(id) ON DELETE CASCADE,
            message TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_conversations (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_conversation_participants (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES collegetrends_conversations(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            last_read_at TIMESTAMP,
            UNIQUE(conversation_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collegetrends_messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES collegetrends_conversations(id) ON DELETE CASCADE,
            sender_id INTEGER REFERENCES collegetrends_users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    for table_sql in tables:
        cur.execute(table_sql)
    
    # Create indexes for performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_posts_user_id ON collegetrends_posts(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_posts_created_at ON collegetrends_posts(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_likes_post_id ON collegetrends_post_likes(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_likes_user_id ON collegetrends_post_likes(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_votes_post_id ON collegetrends_votes(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_comments_post_id ON collegetrends_comments(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_follows_follower ON collegetrends_follows(follower_id)",
        "CREATE INDEX IF NOT EXISTS idx_follows_following ON collegetrends_follows(following_id)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_user ON collegetrends_notifications(user_id, is_read)",
        "CREATE INDEX IF NOT EXISTS idx_messages_conv ON collegetrends_messages(conversation_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON collegetrends_bookmarks(user_id)"
    ]
    
    for idx_sql in indexes:
        cur.execute(idx_sql)
    
    db.commit()
    cur.close()

# ── AUTH HELPERS ───────────────────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Token malformed'}), 401
        
        if not token:
            return jsonify({'message': 'Token missing'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            current_user_id = data['user_id']
            g.current_user_id = current_user_id
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    
    return decorated

def get_user_stats(user_id):
    db = get_db()
    cur = db.cursor()
    
    # Count posts
    cur.execute("SELECT COUNT(*) as count FROM collegetrends_posts WHERE user_id = %s", (user_id,))
    posts_count = cur.fetchone()['count']
    
    # Count followers
    cur.execute("SELECT COUNT(*) as count FROM collegetrends_follows WHERE following_id = %s", (user_id,))
    followers_count = cur.fetchone()['count']
    
    # Count following
    cur.execute("SELECT COUNT(*) as count FROM collegetrends_follows WHERE follower_id = %s", (user_id,))
    following_count = cur.fetchone()['count']
    
    cur.close()
    return posts_count, followers_count, following_count

# ── AUTH ROUTES ────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').lower().strip()
    email = data.get('email', '').lower().strip()
    password = data.get('password')
    full_name = data.get('full_name', '')
    university = data.get('university', '')
    course = data.get('course', '')
    
    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate username (alphanumeric + underscore)
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400
    
    db = get_db()
    cur = db.cursor()
    
    # Check existing
    cur.execute("SELECT id FROM collegetrends_users WHERE username = %s OR email = %s", (username, email))
    if cur.fetchone():
        return jsonify({'error': 'Username or email already exists'}), 409
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cur.execute("""
        INSERT INTO collegetrends_users (username, email, password_hash, full_name, university, course)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    """, (username, email, password_hash, full_name, university, course))
    
    user_id = cur.fetchone()['id']
    db.commit()
    cur.close()
    
    # Generate token
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return jsonify({
        'token': token,
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
    username_or_email = data.get('username', '').lower().strip()
    password = data.get('password')
    
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        SELECT id, username, email, password_hash, full_name, university, course, bio, avatar_url, is_verified
        FROM collegetrends_users 
        WHERE username = %s OR email = %s
    """, (username_or_email, username_or_email))
    
    user = cur.fetchone()
    cur.close()
    
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = jwt.encode({
        'user_id': user['id'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    posts_count, followers_count, following_count = get_user_stats(user['id'])
    
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'university': user['university'],
            'course': user['course'],
            'bio': user['bio'],
            'avatar': user['avatar_url'],
            'verified': user['is_verified'],
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
        SELECT id, username, email, full_name, university, course, bio, avatar_url, is_verified, is_private
        FROM collegetrends_users 
        WHERE id = %s
    """, (g.current_user_id,))
    
    user = cur.fetchone()
    posts_count, followers_count, following_count = get_user_stats(user['id'])
    cur.close()
    
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
        'posts_count': posts_count,
        'followers_count': followers_count,
        'following_count': following_count
    })

# ── FEED ALGORITHM ─────────────────────────────────────────────────
@app.route('/api/feed', methods=['GET'])
@token_required
def get_feed():
    """
    Algorithm: 
    - Base score: (likes + comments*2 + upvotes*3) / (hours_since_post + 2)^1.2
    - Similarity bonus: +50 same course, +30 same university
    - Randomness: Multiply by (0.9 to 1.1)
    - 70% weight to followed users + same course, 30% discovery
    """
    db = get_db()
    cur = db.cursor()
    
    # Get current user info for similarity
    cur.execute("SELECT course, university FROM collegetrends_users WHERE id = %s", (g.current_user_id,))
    user_info = cur.fetchone()
    user_course = user_info['course'] if user_info else ''
    user_university = user_info['university'] if user_info else ''
    
    # Complex query with algorithmic scoring
    cur.execute("""
        WITH scored_posts AS (
            SELECT 
                p.id, p.caption, p.media_url, p.media_type, p.tags, p.created_at,
                p.likes_count, p.comments_count, p.upvotes_count,
                u.id as user_id, u.username, u.avatar_url, u.university as user_university, 
                u.course as user_course, u.is_verified,
                CASE WHEN pl.id IS NOT NULL THEN TRUE ELSE FALSE END as user_liked,
                CASE WHEN b.id IS NOT NULL THEN TRUE ELSE FALSE END as user_bookmarked,
                v.vote_type as user_vote,
                -- Base popularity score (engagement per hour, with decay)
                (p.likes_count + p.comments_count*2 + p.upvotes_count*3)::FLOAT / 
                    POWER(EXTRACT(EPOCH FROM (NOW() - p.created_at))/3600 + 2, 1.2) as popularity_score,
                -- Similarity score
                CASE 
                    WHEN u.course = %s AND u.course != '' THEN 50
                    WHEN u.university = %s AND u.university != '' THEN 30
                    ELSE 0
                END as similarity_score,
                -- Is followed
                CASE WHEN f.following_id IS NOT NULL THEN 1 ELSE 0 END as is_followed,
                RANDOM() as rand_factor
            FROM collegetrends_posts p
            JOIN collegetrends_users u ON p.user_id = u.id
            LEFT JOIN collegetrends_post_likes pl ON p.id = pl.post_id AND pl.user_id = %s
            LEFT JOIN collegetrends_bookmarks b ON p.id = b.post_id AND b.user_id = %s
            LEFT JOIN collegetrends_votes v ON p.id = v.post_id AND v.user_id = %s
            LEFT JOIN collegetrends_follows f ON f.following_id = p.user_id AND f.follower_id = %s
            WHERE p.created_at > NOW() - INTERVAL '30 days'
        )
        SELECT *,
            (popularity_score + similarity_score) * (0.9 + rand_factor * 0.2) as final_score
        FROM scored_posts
        ORDER BY 
            CASE WHEN is_followed = 1 OR similarity_score > 0 THEN 1 ELSE 0 END DESC,
            final_score DESC
        LIMIT 50
    """, (user_course, user_university, g.current_user_id, g.current_user_id, g.current_user_id, g.current_user_id))
    
    posts = cur.fetchall()
    
    # Format response
    result = []
    for post in posts:
        # Get latest comment for preview
        cur.execute("""
            SELECT c.text, u.username 
            FROM collegetrends_comments c
            JOIN collegetrends_users u ON c.user_id = u.id
            WHERE c.post_id = %s
            ORDER BY c.created_at DESC
            LIMIT 1
        """, (post['id'],))
        latest_comment = cur.fetchone()
        
        result.append({
            'id': post['id'],
            'caption': post['caption'],
            'tags': post['tags'] if post['tags'] else [],
            'media_url': post['media_url'],
            'media_type': post['media_type'],
            'created_at': post['created_at'].isoformat() if post['created_at'] else None,
            'likes_count': post['likes_count'],
            'upvotes_count': post['upvotes_count'],
            'comments_count': post['comments_count'],
            'vote_count': post['upvotes_count'] - post.get('downvotes_count', 0),
            'user_liked': post['user_liked'],
            'user_bookmarked': post['user_bookmarked'],
            'user_vote': post['user_vote'],
            'username': post['username'],
            'user_avatar': post['avatar_url'],
            'university': post['user_university'],
            'course': post['user_course'],
            'verified': post['is_verified'],
            'latest_comment': {
                'username': latest_comment['username'],
                'text': latest_comment['text']
            } if latest_comment else None
        })
    
    cur.close()
    return jsonify(result)

# ── POSTS ──────────────────────────────────────────────────────────
@app.route('/api/posts', methods=['POST'])
@token_required
def create_post():
    caption = request.form.get('caption', '')
    tags_str = request.form.get('tags', '[]')
    course_id = request.form.get('course_id') or None
    
    import json
    try:
        tags = json.loads(tags_str)
    except:
        tags = []
    
    media_url = None
    media_type = None
    
    # Handle file upload
    if 'media' in request.files:
        file = request.files['media']
        if file.filename:
            try:
                upload_result = cloudinary.uploader.upload(file, resource_type="auto")
                media_url = upload_result['secure_url']
                media_type = 'video' if file.content_type and 'video' in file.content_type else 'image'
            except Exception as e:
                return jsonify({'error': 'Upload failed', 'details': str(e)}), 500
    
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        INSERT INTO collegetrends_posts 
        (user_id, caption, media_url, media_type, tags, course_id)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    """, (g.current_user_id, caption, media_url, media_type, tags, course_id))
    
    post_id = cur.fetchone()['id']
    db.commit()
    cur.close()
    
    return jsonify({
        'id': post_id,
        'message': 'Post created',
        'media_url': media_url
    }), 201

@app.route('/api/posts/<int:post_id>', methods=['GET'])
@token_required
def get_post(post_id):
    db = get_db()
    cur = db.cursor()
    
    # Get post with user info
    cur.execute("""
        SELECT p.*, u.username, u.avatar_url, u.university as user_university, 
               u.course as user_course, u.is_verified
        FROM collegetrends_posts p
        JOIN collegetrends_users u ON p.user_id = u.id
        WHERE p.id = %s
    """, (post_id,))
    
    post = cur.fetchone()
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    # Get user interactions
    cur.execute("SELECT 1 FROM collegetrends_post_likes WHERE post_id = %s AND user_id = %s", 
                (post_id, g.current_user_id))
    user_liked = cur.fetchone() is not None
    
    cur.execute("SELECT vote_type FROM collegetrends_votes WHERE post_id = %s AND user_id = %s", 
                (post_id, g.current_user_id))
    vote_row = cur.fetchone()
    user_vote = vote_row['vote_type'] if vote_row else None
    
    cur.execute("SELECT 1 FROM collegetrends_bookmarks WHERE post_id = %s AND user_id = %s", 
                (post_id, g.current_user_id))
    user_bookmarked = cur.fetchone() is not None
    
    # Get comments
    cur.execute("""
        SELECT c.*, u.username, u.avatar_url
        FROM collegetrends_comments c
        JOIN collegetrends_users u ON c.user_id = u.id
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
        'comments_count': post['comments_count'],
        'vote_count': post['upvotes_count'] - post.get('downvotes_count', 0),
        'user_liked': user_liked,
        'user_bookmarked': user_bookmarked,
        'user_vote': user_vote,
        'username': post['username'],
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
    
    # Verify ownership
    cur.execute("SELECT user_id FROM collegetrends_posts WHERE id = %s", (post_id,))
    post = cur.fetchone()
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    if post['user_id'] != g.current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    cur.execute("DELETE FROM collegetrends_posts WHERE id = %s", (post_id,))
    db.commit()
    cur.close()
    
    return jsonify({'message': 'Post deleted'})

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@token_required
def toggle_like(post_id):
    data = request.get_json() or {}
    should_like = data.get('like', True)
    
    db = get_db()
    cur = db.cursor()
    
    if should_like:
        try:
            cur.execute("""
                INSERT INTO collegetrends_post_likes (post_id, user_id) 
                VALUES (%s, %s)
            """, (post_id, g.current_user_id))
            # Increment count
            cur.execute("UPDATE collegetrends_posts SET likes_count = likes_count + 1 WHERE id = %s", (post_id,))
            # Create notification
            cur.execute("SELECT user_id FROM collegetrends_posts WHERE id = %s", (post_id,))
            post_owner = cur.fetchone()
            if post_owner and post_owner['user_id'] != g.current_user_id:
                cur.execute("""
                    INSERT INTO collegetrends_notifications (user_id, actor_id, type, post_id, message)
                    SELECT %s, %s, 'like', %s, 'liked your post'
                    WHERE NOT EXISTS (
                        SELECT 1 FROM collegetrends_notifications 
                        WHERE user_id = %s AND actor_id = %s AND type = 'like' AND post_id = %s 
                        AND created_at > NOW() - INTERVAL '1 hour'
                    )
                """, (post_owner['user_id'], g.current_user_id, post_id, 
                      post_owner['user_id'], g.current_user_id, post_id))
        except psycopg2.IntegrityError:
           db.rollback()
           return jsonify({'success': True, 'message': 'Already liked'})

    else:
        cur.execute("DELETE FROM collegetrends_post_likes WHERE post_id = %s AND user_id = %s", 
                    (post_id, g.current_user_id))
        cur.execute("UPDATE collegetrends_posts SET likes_count = GREATEST(0, likes_count - 1) WHERE id = %s", (post_id,))
    
    db.commit()
    cur.close()
    return jsonify({'success': True})

@app.route('/api/posts/<int:post_id>/vote', methods=['POST'])
@token_required
def vote_post(post_id):
    data = request.get_json() or {}
    vote_type = data.get('vote')  # 'up', 'down', or null to remove
    
    db = get_db()
    cur = db.cursor()
    
    # Get current vote
    cur.execute("SELECT vote_type FROM collegetrends_votes WHERE post_id = %s AND user_id = %s", 
                (post_id, g.current_user_id))
    existing = cur.fetchone()
    
    if vote_type is None:
        # Remove vote
        if existing:
            cur.execute("DELETE FROM collegetrends_votes WHERE post_id = %s AND user_id = %s", 
                        (post_id, g.current_user_id))
            if existing['vote_type'] == 'up':
                cur.execute("UPDATE collegetrends_posts SET upvotes_count = GREATEST(0, upvotes_count - 1) WHERE id = %s", (post_id,))
            else:
                cur.execute("UPDATE collegetrends_posts SET downvotes_count = GREATEST(0, downvotes_count - 1) WHERE id = %s", (post_id,))
    else:
        # Set new vote
        if existing:
            # Update existing
            if existing['vote_type'] != vote_type:
                cur.execute("UPDATE collegetrends_votes SET vote_type = %s WHERE post_id = %s AND user_id = %s",
                            (vote_type, post_id, g.current_user_id))
                if vote_type == 'up':
                    cur.execute("UPDATE collegetrends_posts SET upvotes_count = upvotes_count + 1, downvotes_count = GREATEST(0, downvotes_count - 1) WHERE id = %s", (post_id,))
                else:
                    cur.execute("UPDATE collegetrends_posts SET upvotes_count = GREATEST(0, upvotes_count - 1), downvotes_count = downvotes_count + 1 WHERE id = %s", (post_id,))
        else:
            # Insert new
            cur.execute("INSERT INTO collegetrends_votes (post_id, user_id, vote_type) VALUES (%s, %s, %s)",
                        (post_id, g.current_user_id, vote_type))
            if vote_type == 'up':
                cur.execute("UPDATE collegetrends_posts SET upvotes_count = upvotes_count + 1 WHERE id = %s", (post_id,))
            else:
                cur.execute("UPDATE collegetrends_posts SET downvotes_count = downvotes_count + 1 WHERE id = %s", (post_id,))
            
            # Notification
            cur.execute("SELECT user_id FROM collegetrends_posts WHERE id = %s", (post_id,))
            post_owner = cur.fetchone()
            if post_owner and post_owner['user_id'] != g.current_user_id:
                cur.execute("""
                    INSERT INTO collegetrends_notifications (user_id, actor_id, type, post_id, message)
                    VALUES (%s, %s, 'vote', %s, 'upvoted your post')
                """, (post_owner['user_id'], g.current_user_id, post_id))
    
    db.commit()
    cur.close()
    return jsonify({'success': True})

@app.route('/api/posts/<int:post_id>/bookmark', methods=['POST'])
@token_required
def toggle_bookmark(post_id):
    db = get_db()
    cur = db.cursor()
    
    cur.execute("SELECT id FROM collegetrends_bookmarks WHERE post_id = %s AND user_id = %s", 
                (post_id, g.current_user_id))
    
    if cur.fetchone():
        cur.execute("DELETE FROM collegetrends_bookmarks WHERE post_id = %s AND user_id = %s", 
                    (post_id, g.current_user_id))
        bookmarked = False
    else:
        cur.execute("INSERT INTO collegetrends_bookmarks (post_id, user_id) VALUES (%s, %s)", 
                    (post_id, g.current_user_id))
        bookmarked = True
    
    db.commit()
    cur.close()
    return jsonify({'bookmarked': bookmarked})

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@token_required
def add_comment(post_id):
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'error': 'Comment text required'}), 400
    
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        INSERT INTO collegetrends_comments (post_id, user_id, text) 
        VALUES (%s, %s, %s) RETURNING id
    """, (post_id, g.current_user_id, text))
    
    comment_id = cur.fetchone()['id']
    
    # Update count
    cur.execute("UPDATE collegetrends_posts SET comments_count = comments_count + 1 WHERE id = %s", (post_id,))
    
    # Notify post owner
    cur.execute("SELECT user_id FROM collegetrends_posts WHERE id = %s", (post_id,))
    post_owner = cur.fetchone()
    if post_owner and post_owner['user_id'] != g.current_user_id:
        cur.execute("""
            INSERT INTO collegetrends_notifications (user_id, actor_id, type, post_id, message)
            VALUES (%s, %s, 'comment', %s, 'commented on your post')
        """, (post_owner['user_id'], g.current_user_id, post_id))
    
    db.commit()
    cur.close()
    
    return jsonify({'id': comment_id, 'success': True}), 201

# ── USERS ──────────────────────────────────────────────────────────
@app.route('/api/users/<int:user_id>/posts', methods=['GET'])
@token_required
def get_user_posts(user_id):
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        SELECT p.*, u.username, u.avatar_url, u.university as user_university, u.course as user_course, u.is_verified
        FROM collegetrends_posts p
        JOIN collegetrends_users u ON p.user_id = u.id
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

@app.route('/api/users/<int:user_id>/follow', methods=['POST'])
@token_required
def toggle_follow(user_id):
    if user_id == g.current_user_id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    
    data = request.get_json() or {}
    should_follow = data.get('follow', True)
    
    db = get_db()
    cur = db.cursor()
    
    if should_follow:
        try:
            cur.execute("""
                INSERT INTO collegetrends_follows (follower_id, following_id) 
                VALUES (%s, %s)
            """, (g.current_user_id, user_id))
            # Notify
            cur.execute("""
                INSERT INTO collegetrends_notifications (user_id, actor_id, type, message)
                VALUES (%s, %s, 'follow', 'started following you')
            """, (user_id, g.current_user_id))
        except psycopg2.IntegrityError:
            db.rollback()
            return jsonify({'error': 'Username or email already exists'}), 409

    else:
        cur.execute("DELETE FROM collegetrends_follows WHERE follower_id = %s AND following_id = %s", 
                    (g.current_user_id, user_id))
    
    db.commit()
    cur.close()
    return jsonify({'success': True})

@app.route('/api/users/me', methods=['PATCH'])
@token_required
def update_profile():
    data = request.get_json()
    allowed_fields = ['full_name', 'username', 'university', 'course', 'bio', 'avatar_url']
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    # Check username uniqueness if changing
    if 'username' in updates:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM collegetrends_users WHERE username = %s AND id != %s", 
                    (updates['username'], g.current_user_id))
        if cur.fetchone():
            return jsonify({'error': 'Username taken'}), 409
        cur.close()
    
    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
    values = list(updates.values()) + [g.current_user_id]
    
    db = get_db()
    cur = db.cursor()
    cur.execute(f"UPDATE collegetrends_users SET {set_clause}, updated_at = NOW() WHERE id = %s", values)
    db.commit()
    cur.close()
    
    return jsonify({'success': True})

@app.route('/api/users/me/password', methods=['POST'])
@token_required
def change_password():
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE collegetrends_users SET password_hash = %s WHERE id = %s", 
                (password_hash, g.current_user_id))
    db.commit()
    cur.close()
    
    return jsonify({'success': True})

@app.route('/api/suggestions', methods=['GET'])
@token_required
def get_suggestions():
    """Suggest users not followed yet, same university/course prioritized"""
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        SELECT u.id, u.username, u.avatar_url, u.university
        FROM collegetrends_users u
        WHERE u.id != %s 
        AND u.id NOT IN (
            SELECT following_id FROM collegetrends_follows WHERE follower_id = %s
        )
        AND u.is_private = FALSE
        ORDER BY 
            CASE 
                WHEN u.university = (SELECT university FROM collegetrends_users WHERE id = %s) THEN 1 
                ELSE 2 
            END,
            RANDOM()
        LIMIT 10
    """, (g.current_user_id, g.current_user_id, g.current_user_id))
    
    users = cur.fetchall()
    cur.close()
    
    return jsonify([{
        'id': u['id'],
        'username': u['username'],
        'avatar': u['avatar_url'] or '',
        'university': u['university'],
        'following': False
    } for u in users])

# ── SEARCH ─────────────────────────────────────────────────────────
@app.route('/api/search', methods=['GET'])
@token_required
def search():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'posts')  # posts, trending, people
    
    if not query and search_type != 'trending':
        return jsonify([])
    
    db = get_db()
    cur = db.cursor()
    
    if search_type == 'people':
        cur.execute("""
            SELECT id, username, avatar_url, university, 
                   EXISTS(SELECT 1 FROM collegetrends_follows WHERE follower_id = %s AND following_id = u.id) as following
            FROM collegetrends_users u
            WHERE (username ILIKE %s OR full_name ILIKE %s) AND id != %s
            LIMIT 20
        """, (g.current_user_id, f'%{query}%', f'%{query}%', g.current_user_id))
        
        users = cur.fetchall()
        return jsonify([{
            'id': u['id'],
            'username': u['username'],
            'avatar': u['avatar_url'] or '',
            'university': u['university'],
            'following': u['following']
        } for u in users])
    
    elif search_type == 'trending':
        # Get popular tags from last 7 days
        cur.execute("""
            SELECT UNNEST(tags) as tag, COUNT(*) as count
            FROM collegetrends_posts
            WHERE created_at > NOW() - INTERVAL '7 days' AND tags IS NOT NULL
            GROUP BY tag
            ORDER BY count DESC
            LIMIT 20
        """)
        tags = cur.fetchall()
        return jsonify([{
            'name': t['tag'],
            'count': t['count']
        } for t in tags])
    
    else:  # posts
        cur.execute("""
            SELECT p.*, u.username, u.avatar_url, u.university as user_university, u.course as user_course, u.is_verified
            FROM collegetrends_posts p
            JOIN collegetrends_users u ON p.user_id = u.id
            WHERE p.caption ILIKE %s OR %s = ANY(p.tags)
            ORDER BY p.created_at DESC
            LIMIT 20
        """, (f'%{query}%', query))
        
        posts = cur.fetchall()
        return jsonify([{
            'id': p['id'],
            'caption': p['caption'],
            'media_url': p['media_url'],
            'username': p['username'],
            'user_avatar': p['avatar_url'],
            'university': p['user_university'],
            'course': p['user_course'],
            'verified': p['is_verified'],
            'likes_count': p['likes_count'],
            'created_at': p['created_at'].isoformat() if p['created_at'] else None
        } for p in posts])

# ── NOTIFICATIONS ──────────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications():
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        SELECT n.*, u.username as actor_username, p.media_url as post_image
        FROM collegetrends_notifications n
        JOIN collegetrends_users u ON n.actor_id = u.id
        LEFT JOIN collegetrends_posts p ON n.post_id = p.id
        WHERE n.user_id = %s
        ORDER BY n.created_at DESC
        LIMIT 50
    """, (g.current_user_id,))
    
    notifications = cur.fetchall()
    cur.close()
    
    return jsonify([{
        'id': n['id'],
        'type': n['type'],
        'actor_username': n['actor_username'],
        'message': n['message'],
        'read': n['is_read'],
        'created_at': n['created_at'].isoformat() if n['created_at'] else None,
        'post_image': n['post_image']
    } for n in notifications])

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@token_required
def mark_notification_read(notif_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE collegetrends_notifications SET is_read = TRUE WHERE id = %s AND user_id = %s", 
                (notif_id, g.current_user_id))
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
            CASE 
                WHEN u1.id = %s THEN u2.username 
                ELSE u1.username 
            END as partner_name,
            CASE 
                WHEN u1.id = %s THEN u2.avatar_url 
                ELSE u1.avatar_url 
            END as partner_avatar,
            m.content as last_message,
            m.created_at as last_message_at,
            (SELECT COUNT(*) FROM collegetrends_messages 
             WHERE conversation_id = c.id AND sender_id != %s AND is_read = FALSE) as unread_count
        FROM collegetrends_conversations c
        JOIN collegetrends_conversation_participants cp1 ON c.id = cp1.conversation_id
        JOIN collegetrends_conversation_participants cp2 ON c.id = cp2.conversation_id AND cp2.user_id != cp1.user_id
        JOIN collegetrends_users u1 ON cp1.user_id = u1.id
        JOIN collegetrends_users u2 ON cp2.user_id = u2.id
        LEFT JOIN LATERAL (
            SELECT content, created_at 
            FROM collegetrends_messages 
            WHERE conversation_id = c.id 
            ORDER BY created_at DESC 
            LIMIT 1
        ) m ON TRUE
        WHERE cp1.user_id = %s
        ORDER BY m.created_at DESC NULLS LAST
    """, (g.current_user_id, g.current_user_id, g.current_user_id, g.current_user_id))
    
    conversations = cur.fetchall()
    cur.close()
    
    return jsonify([{
        'id': c['id'],
        'partner_name': c['partner_name'],
        'partner_avatar': c['partner_avatar'] or '',
        'last_message': c['last_message'],
        'last_message_at': c['last_message_at'].isoformat() if c['last_message_at'] else None,
        'unread_count': c['unread_count']
    } for c in conversations])

@app.route('/api/conversations/<int:conv_id>/messages', methods=['GET'])
@token_required
def get_messages(conv_id):
    db = get_db()
    cur = db.cursor()
    
    # Verify participant
    cur.execute("SELECT 1 FROM collegetrends_conversation_participants WHERE conversation_id = %s AND user_id = %s", 
                (conv_id, g.current_user_id))
    if not cur.fetchone():
        return jsonify({'error': 'Unauthorized'}), 403
    
    cur.execute("""
        SELECT m.*, u.username
        FROM collegetrends_messages m
        JOIN collegetrends_users u ON m.sender_id = u.id
        WHERE m.conversation_id = %s
        ORDER BY m.created_at ASC
    """, (conv_id,))
    
    messages = cur.fetchall()
    
    # Mark as read
    cur.execute("""
        UPDATE collegetrends_messages SET is_read = TRUE 
        WHERE conversation_id = %s AND sender_id != %s AND is_read = FALSE
    """, (conv_id, g.current_user_id))
    
    db.commit()
    cur.close()
    
    return jsonify([{
        'id': m['id'],
        'sender_id': m['sender_id'],
        'content': m['content'],
        'is_read': m['is_read'],
        'created_at': m['created_at'].isoformat() if m['created_at'] else None
    } for m in messages])

@app.route('/api/conversations/<int:conv_id>/messages', methods=['POST'])
@token_required
def send_message(conv_id):
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Content required'}), 400
    
    db = get_db()
    cur = db.cursor()
    
    # Verify participant
    cur.execute("SELECT 1 FROM collegetrends_conversation_participants WHERE conversation_id = %s AND user_id = %s", 
                (conv_id, g.current_user_id))
    if not cur.fetchone():
        return jsonify({'error': 'Unauthorized'}), 403
    
    cur.execute("""
        INSERT INTO collegetrends_messages (conversation_id, sender_id, content) 
        VALUES (%s, %s, %s) RETURNING id, created_at
    """, (conv_id, g.current_user_id, content))
    
    result = cur.fetchone()
    
    # Update conversation timestamp
    cur.execute("UPDATE collegetrends_conversations SET updated_at = NOW() WHERE id = %s", (conv_id,))
    
    db.commit()
    cur.close()
    
    return jsonify({
        'id': result['id'],
        'sender_id': g.current_user_id,
        'content': content,
        'created_at': result['created_at'].isoformat(),
        'is_read': False
    }), 201

@app.route('/api/conversations/<int:conv_id>/messages/check', methods=['GET'])
@token_required
def check_new_messages(conv_id):
    """Check if there are new messages after a certain count"""
    after = request.args.get('after', 0, type=int)
    
    db = get_db()
    cur = db.cursor()
    
    cur.execute("SELECT COUNT(*) as count FROM collegetrends_messages WHERE conversation_id = %s", (conv_id,))
    total = cur.fetchone()['count']
    
    cur.close()
    return jsonify({'has_new': total > after, 'total': total})

@app.route('/api/conversations/start', methods=['POST'])
@token_required
def start_conversation():
    """Start or get existing conversation with a user"""
    data = request.get_json()
    other_user_id = data.get('user_id')
    
    if not other_user_id or other_user_id == g.current_user_id:
        return jsonify({'error': 'Invalid user'}), 400
    
    db = get_db()
    cur = db.cursor()
    
    # Check if conversation exists
    cur.execute("""
        SELECT c.id 
        FROM collegetrends_conversations c
        JOIN collegetrends_conversation_participants cp1 ON c.id = cp1.conversation_id AND cp1.user_id = %s
        JOIN collegetrends_conversation_participants cp2 ON c.id = cp2.conversation_id AND cp2.user_id = %s
    """, (g.current_user_id, other_user_id))
    
    existing = cur.fetchone()
    if existing:
        return jsonify({'conversation_id': existing['id']})
    
    # Create new conversation
    cur.execute("INSERT INTO collegetrends_conversations DEFAULT VALUES RETURNING id",)
    conv_id = cur.fetchone()['id']
    
    cur.execute("INSERT INTO collegetrends_conversation_participants (conversation_id, user_id) VALUES (%s, %s)", 
                (conv_id, g.current_user_id))
    cur.execute("INSERT INTO collegetrends_conversation_participants (conversation_id, user_id) VALUES (%s, %s)", 
                (conv_id, other_user_id))
    
    db.commit()
    cur.close()
    
    return jsonify({'conversation_id': conv_id}), 201

# ── INIT ───────────────────────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({'status': 'CollegeTrends API Running', 'version': '1.0.0'})

# Auto-create tables on startup (works with Gunicorn too)
with app.app_context():
    init_db()
    print("Database initialized")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
