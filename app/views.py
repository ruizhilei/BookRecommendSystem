# app/views.py
from app.recommend import get_popular_books, get_user_recommendations
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app.models import Book, Rating
from app import db  
# ⭐ 新增

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        rec_books = get_user_recommendations(current_user.id, limit=10)
        title = "为你推荐的书籍"
    else:
        rec_books = get_popular_books(limit=10)
        title = "热门书籍"

    return render_template(
        "index.html",
        user=current_user,
        rec_books=rec_books,
        rec_title=title,
    )

@main_bp.route("/profile")
@login_required
def profile():
    user = current_user

    # 获取该用户所有评分，按时间倒序
    ratings = (
        Rating.query
        .filter_by(user_id=user.id)
        .order_by(Rating.created_at.desc())
        .all()
    )

    # 简单统计一下
    total_rated = len(ratings)
    avg_rating = None
    if total_rated > 0:
        avg_rating = sum(r.rating for r in ratings) / total_rated

    return render_template(
        "profile.html",
        user=user,
        ratings=ratings,
        total_rated=total_rated,
        avg_rating=avg_rating,
    )



@main_bp.route("/books")
def books_list():
    # 获取查询参数
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "", type=str)

    query = Book.query

    if q:
        like_pattern = f"%{q}%"
        query = query.filter(
            (Book.title.ilike(like_pattern)) |
            (Book.authors.ilike(like_pattern))
        )

    # 简单分页：每页 20 本书
    pagination = query.order_by(Book.book_id).paginate(
        page=page, per_page=20, error_out=False
    )
    books = pagination.items

    return render_template(
        "books.html",
        books=books,
        pagination=pagination,
        q=q,
    )

@main_bp.route("/books/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    user_rating = None
    if current_user.is_authenticated:
        user_rating = Rating.query.filter_by(
            user_id=current_user.id, book_id=book_id
        ).first()
    
    
    
    return render_template("book_detail.html", book=book, user_rating=user_rating)
    
    
@main_bp.route("/books/<int:book_id>/rate", methods=["POST"])
@login_required
def rate_book(book_id):
    book = Book.query.get_or_404(book_id)
    try:
        rating_value = int(request.form.get("rating", 0))
    except ValueError:
        rating_value = 0

    if rating_value < 1 or rating_value > 5:
        flash("评分必须在 1 到 5 之间", "danger")
        return redirect(url_for("main.book_detail", book_id=book_id))

    # 查一下用户之前有没有评过这本书，有的话就更新
    rating = Rating.query.filter_by(
        user_id=current_user.id, book_id=book_id
    ).first()

    if rating:
        rating.rating = rating_value
    else:
        rating = Rating(
            user_id=current_user.id,
            book_id=book_id,
            rating=rating_value,
        )
        db.session.add(rating)

    db.session.commit()
    flash("评分已保存，谢谢你的反馈！", "success")
    return redirect(url_for("main.book_detail", book_id=book_id))


