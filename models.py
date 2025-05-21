from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB # PostgreSQLのJSONB型をインポート

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    # 役割: 'general', 'moderator', 'admin'
    role = db.Column(db.String(20), default='general', nullable=False)

    threads = db.relationship('Thread', backref='author', lazy=True)
    posts = db.relationship('Post', backref='author', lazy=True)

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    posts = db.relationship('Post', backref='thread', lazy=True, cascade="all, delete-orphan") # スレッド削除で投稿も削除

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # JSONB型でコメント内容を保存
    content = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
