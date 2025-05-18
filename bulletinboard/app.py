from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import os
import hashlib
import pytz  # タイムゾーン変換ライブラリ

app = Flask(__name__)
DATABASE = 'bulletinboard.db'
DATABASE_PATH = os.path.join('/tmp', DATABASE)
MAX_TEXT_LENGTH = 60
MAX_POSTS = 1000
JST = pytz.timezone('Asia/Tokyo')  # 日本標準時のタイムゾーンオブジェクト

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    last_row_id = cur.lastrowid
    cur.close()
    return last_row_id

def clear_all_posts():
    db = get_db()
    try:
        db.execute('DROP TABLE IF EXISTS posts')
        db.commit()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
    except sqlite3.Error as e:
        print(f"Error clearing and resetting posts table: {e}")
        db.rollback()

def get_post_count():
    result = query_db('SELECT COUNT(*) FROM posts', one=True)
    return result[0] if result else 0

def get_post_by_id(post_id):
    return query_db('SELECT id, name, password_id, text, created_at FROM posts WHERE id = ?', [post_id], one=True)

def format_datetime_jst(dt_str):
    """UTCの文字列を日本標準時のdatetimeオブジェクトに変換し、フォーマットする"""
    utc_dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    jst_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(JST)
    return jst_dt.strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():
    posts = query_db('SELECT id, name, password_id, text, created_at FROM posts ORDER BY id DESC')
    formatted_posts = []
    for post in posts:
        formatted_post = dict(post)
        formatted_post['created_at'] = format_datetime_jst(post['created_at'])
        formatted_posts.append(formatted_post)
    return render_template('index.html', posts=formatted_posts, error=None)

@app.route('/post_async', methods=['POST'])
def post_async():
    name = request.form.get('name')
    password = request.form.get('password')
    text = request.form['text']
    now_utc = datetime.now(pytz.utc)  # UTCで現在時刻を取得
    created_at_utc_str = now_utc.strftime('%Y-%m-%d %H:%M:%S')
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    short_password_id = hashed_password[:8]

    if not name:
        return jsonify({'error': '名前を入力してください。'}), 400
    elif not password:
        return jsonify({'error': 'パスワードを入力してください。'}), 400
    elif len(text) > MAX_TEXT_LENGTH:
        return jsonify({'error': f'投稿内容は{MAX_TEXT_LENGTH}文字以内で入力してください。'}), 400
    else:
        last_id = execute_db('INSERT INTO posts (name, password_id, text, created_at) VALUES (?, ?, ?, ?)', (name, short_password_id, text, created_at_utc_str))
        post_count = get_post_count()
        if post_count > MAX_POSTS:
            clear_all_posts()
        new_post = get_post_by_id(last_id)
        formatted_created_at = format_datetime_jst(new_post['created_at'])
        return jsonify({'post': {'id': new_post['id'], 'name': new_post['name'], 'password_id': new_post['password_id'], 'text': new_post['text'], 'created_at': formatted_created_at}}), 201

if __name__ == '__main__':
    app.run(debug=True)

with app.app_context():
    if not os.path.exists(DATABASE_PATH):
        init_db()
