# config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change_this_to_a_random_secret"
    # MySQL 连接串，按你创建的用户和密码来改
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://book_user:your_password@localhost/book_recommend"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

