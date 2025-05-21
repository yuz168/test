from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json
from datetime import datetime

from models import db, User, Thread, Post # models.py からインポート

app = Flask(__name__)
# 本番環境ではより複雑で安全なものに置き換えてください
app.config['SECRET_KEY'] = 'your_super_secret_key_that_is_very_long_and_random'

# PostgreSQLを使用する場合のDB設定例
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@host:port/dbname'
# SQLiteを使用する場合（開発・テスト用）
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- ヘルパー関数とデコレーター ---

# ログイン必須デコレーター
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 権限チェックデコレーター
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('ログインが必要です。', 'danger')
                return redirect(url_for('login'))
            current_user = User.query.get(session['user_id'])
            if current_user.role not in roles:
                flash('この操作を行う権限がありません。', 'danger')
                return redirect(url_for('index')) # 権限がない場合はトップページにリダイレクト
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- データベース初期化 ---
@app.before_first_request
def create_tables():
    db.create_all()
    # 初回起動時に管理者ユーザーが存在しなければ作成
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', password_hash=generate_password_hash('adminpass'), role='admin')
        db.session.add(admin_user)
        db.session.commit()
        print("管理者ユーザー 'admin' が作成されました。パスワードは 'adminpass' です。")
    # テストユーザーを作成 (オプション)
    if not User.query.filter_by(username='testuser').first():
        test_user = User(username='testuser', password_hash=generate_password_hash('password'), role='general')
        db.session.add(test_user)
        db.session.commit()
        print("テストユーザー 'testuser' が作成されました。パスワードは 'password' です。")


# --- ルーティング ---

@app.route('/')
def index():
    threads = Thread.query.order_by(Thread.created_at.desc()).all()
    return render_template('index.html', threads=threads)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('そのユーザー名はすでに使用されています。', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password, role='general')
        db.session.add(new_user)
        db.session.commit()
        flash('登録が完了しました。ログインしてください。', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            flash('ログインしました。', 'success')
            return redirect(url_for('index'))
        else:
            flash('無効なユーザー名またはパスワードです。', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    flash('ログアウトしました。', 'info')
    return redirect(url_for('index'))

@app.route('/thread/new', methods=['GET', 'POST'])
@login_required
def new_thread():
    if request.method == 'POST':
        title = request.form['title']
        if not title:
            flash('タイトルを入力してください。', 'danger')
            return redirect(url_for('new_thread'))

        new_thread = Thread(title=title, user_id=session['user_id'])
        db.session.add(new_thread)
        db.session.commit()
        flash('新しいスレッドが作成されました！', 'success')
        return redirect(url_for('thread_detail', thread_id=new_thread.id))
    return render_template('new_thread.html')

@app.route('/thread/<int:thread_id>')
def thread_detail(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    posts = Post.query.filter_by(thread_id=thread_id).order_by(Post.created_at.asc()).all()
    users = {user.id: user.username for user in User.query.all()} # ユーザー名をマッピング
    return render_template('thread_detail.html', thread=thread, posts=posts, users=users, session=session)

@app.route('/thread/<int:thread_id>/post', methods=['POST'])
@login_required
def create_post(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    content_text = request.form['content'] # フォームからテキストとして受け取る

    if not content_text:
        flash('コメントを入力してください。', 'danger')
        return redirect(url_for('thread_detail', thread_id=thread_id))

    # コメント内容をJSON形式で保存
    post_content_json = {"text": content_text}
    # 必要であれば、ここで画像URLなどの追加情報をJSONに追加するロジックを実装

    new_post = Post(thread_id=thread.id, user_id=session['user_id'], content=post_content_json)
    db.session.add(new_post)
    db.session.commit()
    flash('コメントを投稿しました。', 'success')
    return redirect(url_for('thread_detail', thread_id=thread_id))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    current_user = User.query.get(session['user_id'])

    # 投稿者自身、またはモデレーター・管理者のみ削除可能
    if post.user_id == current_user.id or current_user.role in ['moderator', 'admin']:
        thread_id = post.thread.id
        db.session.delete(post)
        db.session.commit()
        flash('投稿を削除しました。', 'success')
        return redirect(url_for('thread_detail', thread_id=thread_id))
    else:
        flash('この投稿を削除する権限がありません。', 'danger')
        return redirect(url_for('thread_detail', thread_id=post.thread.id))

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    current_user = User.query.get(session['user_id'])

    # 投稿者自身、またはモデレーター・管理者のみ編集可能
    if not (post.user_id == current_user.id or current_user.role in ['moderator', 'admin']):
        flash('この投稿を編集する権限がありません。', 'danger')
        return redirect(url_for('thread_detail', thread_id=post.thread.id))

    if request.method == 'POST':
        new_content_text = request.form['content']
        if not new_content_text:
            flash('コメントを入力してください。', 'danger')
            return redirect(url_for('edit_post', post_id=post_id))

        # JSON contentを更新
        post.content['text'] = new_content_text
        # その他のJSONデータがあれば、ここで更新
        
        post.updated_at = datetime.now() # 更新日時を更新
        db.session.commit()
        flash('投稿を更新しました。', 'success')
        return redirect(url_for('thread_detail', thread_id=post.thread.id))
    
    # GETリクエストの場合、現在の内容をフォームに表示
    return render_template('edit_post.html', post=post)


@app.route('/thread/<int:thread_id>/edit_title', methods=['POST'])
@role_required(['moderator', 'admin']) # モデレーターか管理者のみ
def edit_thread_title(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    new_title = request.form['title']
    if not new_title:
        flash('新しいタイトルを入力してください。', 'danger')
        return redirect(url_for('thread_detail', thread_id=thread_id))

    thread.title = new_title
    db.session.commit()
    flash('スレッドタイトルを更新しました。', 'success')
    return redirect(url_for('thread_detail', thread_id=thread_id))

@app.route('/admin')
@role_required(['admin']) # 管理者のみアクセス可能
def admin_panel():
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/admin/promote_user/<int:user_id>', methods=['POST'])
@role_required(['admin'])
def promote_user(user_id):
    user_to_promote = User.query.get_or_404(user_id)

    if user_to_promote.role == 'admin':
        flash(f'ユーザー {user_to_promote.username} は既に管理者です。', 'info')
    elif user_to_promote.role == 'moderator':
        flash(f'ユーザー {user_to_promote.username} は既にモデレーターです。', 'info')
    else:
        user_to_promote.role = 'moderator' # モデレーターに昇格
        db.session.commit()
        flash(f'ユーザー {user_to_promote.username} をモデレーターに昇格しました。', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/demote_user/<int:user_id>', methods=['POST'])
@role_required(['admin'])
def demote_user(user_id):
    user_to_demote = User.query.get_or_404(user_id)

    if user_to_demote.role == 'general':
        flash(f'ユーザー {user_to_demote.username} は既に一般ユーザーです。', 'info')
    elif user_to_demote.role == 'admin':
        flash(f'管理者は降格できません。', 'danger') # 管理者は自身を降格できないようにするなどのロジックも追加可能
    else:
        user_to_demote.role = 'general' # 一般ユーザーに降格
        db.session.commit()
        flash(f'ユーザー {user_to_demote.username} を一般ユーザーに降格しました。', 'success')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    with app.app_context():
        # スクリプト実行時にテーブルを作成
        db.create_all()
    app.run(debug=True) # debug=True は開発用。本番ではFalseに。
