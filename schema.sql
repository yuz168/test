DROP TABLE IF EXISTS posts;
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    password_id TEXT,  -- パスワードから生成したIDカラムを追加
    text TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
