# app/models.py
from sqlalchemy import UniqueConstraint  # 顶部补这一行
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # 你已经改成足够长了
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Book(db.Model):
    __tablename__ = "books"

    # 用数据集里的 book_id 作为主键（和 ratings.csv 对得上）
    book_id = db.Column(db.Integer, primary_key=True)

    # 常用字段
    title = db.Column(db.String(255), index=True, nullable=False)
    authors = db.Column(db.String(1000))
    original_title = db.Column(db.String(255))
    language_code = db.Column(db.String(32))

    original_publication_year = db.Column(db.Integer)
    average_rating = db.Column(db.Float)
    ratings_count = db.Column(db.Integer)

    image_url = db.Column(db.String(255))
    small_image_url = db.Column(db.String(255))

    # 你以后要的话，可以再加 isbn 等字段

    def __repr__(self):
        return f"<Book {self.book_id} - {self.title}>"

class Rating(db.Model):
    __tablename__ = "user_ratings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("books.book_id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1~5 分
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 一个用户对同一本书只能有一条评分
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uix_user_book"),)

# 可选：加一些 ORM 关系，方便以后用
User.ratings = db.relationship("Rating", backref="user", lazy="dynamic")
Book.ratings = db.relationship("Rating", backref="book", lazy="dynamic")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

