# app/recommend.py
import os
import csv
import math
from typing import List, Dict, Tuple

import numpy as np
from sqlalchemy import func

from app.models import Book, Rating
from app import db

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ITEM_FACTORS_CSV = os.path.join(DATA_DIR, "als_item_factors.csv")

# 全局缓存
ITEM_FACTORS: Dict[int, np.ndarray] = {}
CONTENT_FEATURES: Dict[int, np.ndarray] = {}

def _load_item_factors():
    global ITEM_FACTORS
    if ITEM_FACTORS:
        return
    if not os.path.exists(ITEM_FACTORS_CSV):
        print("WARN: ALS item factors file not found:", ITEM_FACTORS_CSV)
        return

    with open(ITEM_FACTORS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        factor_cols = [c for c in reader.fieldnames if c != "book_id"]
        for row in reader:
            try:
                book_id = int(row["book_id"])
                vec = np.array([float(row[c]) for c in factor_cols], dtype=np.float32)
                ITEM_FACTORS[book_id] = vec
            except Exception:
                continue

    print(f"Loaded ALS item factors for {len(ITEM_FACTORS)} books.")


def _build_content_features():
    """
    使用书籍的元信息构建一个简单的内容向量：
    [标准化后的出版年份, 标准化后的平均评分, 标准化后的 log(评分人数+1)]
    """
    global CONTENT_FEATURES
    if CONTENT_FEATURES:
        return

    books = Book.query.all()
    years, avgs, counts = [], [], []
    tmp = {}

    for b in books:
        year = b.original_publication_year or 0
        avg = b.average_rating or 0.0
        cnt = b.ratings_count or 0
        tmp[b.book_id] = (year, avg, cnt)
        years.append(year)
        avgs.append(avg)
        counts.append(math.log1p(cnt))

    # 计算均值和标准差
    def norm(arr):
        arr = np.array(arr, dtype=np.float32)
        mean = arr.mean() if len(arr) > 0 else 0.0
        std = arr.std() if arr.std() > 0 else 1.0
        return mean, std

    year_mean, year_std = norm(years)
    avg_mean, avg_std = norm(avgs)
    cnt_mean, cnt_std = norm(counts)

    for book_id, (year, avg, cnt) in tmp.items():
        v_year = (year - year_mean) / year_std
        v_avg = (avg - avg_mean) / avg_std
        v_cnt = (math.log1p(cnt) - cnt_mean) / cnt_std
        CONTENT_FEATURES[book_id] = np.array(
            [v_year, v_avg, v_cnt], dtype=np.float32
        )

    print(f"Built content features for {len(CONTENT_FEATURES)} books.")


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return 0.0
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def get_popular_books(limit=10):
    return (
        Book.query
        .filter(Book.ratings_count != None)
        .order_by(Book.average_rating.desc(), Book.ratings_count.desc())
        .limit(limit)
        .all()
    )


def get_user_recommendations(user_id: int, limit: int = 10):
    """
    混合推荐：
    - 用户评分 < 3 本：直接用热门推荐
    - 否则：
        1. 用 ALS item 向量做“协同过滤”得分（用户向量 = 打分加权平均）
        2. 用内容特征做相似度（用户内容向量 = 打分加权平均）
        3. 综合得分 = 0.7 * ALS分 + 0.3 * 内容分
    """
    _load_item_factors()
    _build_content_features()

    # 用户所有评分
    user_ratings: List[Rating] = (
        Rating.query.filter_by(user_id=user_id).all()
    )

    if len(user_ratings) < 3 or not ITEM_FACTORS:
        # 冷启动：评分太少或者没训练 ALS，直接给热门
        return get_popular_books(limit=limit)

    # 1. 构建用户的 ALS 向量（打分加权平均）
    user_vec_cf_list = []
    user_vec_cb_list = []
    rated_book_ids = set()

    for r in user_ratings:
        b_id = r.book_id
        rated_book_ids.add(b_id)
        w = float(r.rating)

        cf_vec = ITEM_FACTORS.get(b_id)
        if cf_vec is not None:
            user_vec_cf_list.append(cf_vec * w)

        cb_vec = CONTENT_FEATURES.get(b_id)
        if cb_vec is not None:
            user_vec_cb_list.append(cb_vec * w)

    if not user_vec_cf_list:
        # 用户评分的书都不在 ALS 模型里 → 退回内容推荐或热门
        if user_vec_cb_list:
            user_content_vec = np.mean(user_vec_cb_list, axis=0)
        else:
            return get_popular_books(limit=limit)
    else:
        user_cf_vec = np.mean(user_vec_cf_list, axis=0)
        user_content_vec = (
            np.mean(user_vec_cb_list, axis=0) if user_vec_cb_list else None
        )

    # 2. 遍历候选书籍，计算混合得分
    candidates: List[Tuple[int, float]] = []

    # 为简单起见，只在有 ALS 向量的书里选
    for book_id, item_vec in ITEM_FACTORS.items():
        if book_id in rated_book_ids:
            continue

        cf_score = _cosine(user_cf_vec, item_vec)  # 协同过滤分数
        cb_vec = CONTENT_FEATURES.get(book_id)
        cb_score = _cosine(user_content_vec, cb_vec) if user_content_vec is not None else 0.0

        hybrid_score = 0.7 * cf_score + 0.3 * cb_score
        candidates.append((book_id, hybrid_score))

    # 3. 排序取前 limit 个
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_ids = [bid for bid, s in candidates[:limit] if s > 0]

    if not top_ids:
        return get_popular_books(limit=limit)

    # 4. 按 id 列表顺序取出 Book 对象
    books_by_id = {
        b.book_id: b for b in Book.query.filter(Book.book_id.in_(top_ids)).all()
    }
    result = [books_by_id[bid] for bid in top_ids if bid in books_by_id]

    # 如果不足 limit 再用热门补齐
    if len(result) < limit:
        extra = [
            b for b in get_popular_books(limit=limit * 2)
            if b.book_id not in top_ids
        ]
        result.extend(extra[: limit - len(result)])

    return result

