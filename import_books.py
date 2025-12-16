# import_books.py
import csv
from app import create_app, db
from app.models import Book

app = create_app()

CSV_PATH = "data/books.csv"

def import_books():
    with app.app_context():
        count = 0
        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 有些年份是浮点，比如 "2008.0"
                year_str = row.get("original_publication_year")
                try:
                    year = int(float(year_str)) if year_str else None
                except ValueError:
                    year = None

                avg_str = row.get("average_rating")
                try:
                    avg_rating = float(avg_str) if avg_str else None
                except ValueError:
                    avg_rating = None

                ratings_count_str = row.get("ratings_count")
                try:
                    ratings_count = int(float(ratings_count_str)) if ratings_count_str else None
                except ValueError:
                    ratings_count = None

                book = Book(
                    book_id=int(row["book_id"]),
                    title=row["title"] or "",
                    authors=row.get("authors"),
                    original_title=row.get("original_title"),
                    language_code=row.get("language_code"),
                    original_publication_year=year,
                    average_rating=avg_rating,
                    ratings_count=ratings_count,
                    image_url=row.get("image_url"),
                    small_image_url=row.get("small_image_url"),
                )

                db.session.merge(book)  # 如果已存在就更新，否则插入
                count += 1
                if count % 1000 == 0:
                    db.session.commit()
                    print(f"Imported {count} books...")

        db.session.commit()
        print(f"Import finished, total {count} books.")

if __name__ == "__main__":
    import_books()

