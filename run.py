# run.py
from app import create_app, db
from app.models import User

app = create_app()

# 可选：让 flask shell 有这些对象
@app.shell_context_processor
def make_shell_context():
    return {"db": db, "User": User}

if __name__ == "__main__":
    app.run(debug=True,port=5001)

