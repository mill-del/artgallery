# app.py
import os
from flask import Flask
from datetime import timedelta
from database import db  # Импортируем db из database.py
from blog import blog  # Импортируем blog после определения db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:malika@localhost:5432/artgallery'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['MAX_FILE_SIZE'] = 5 * 1024 * 1024  # 5 MB

db.init_app(app)  # Привязываем db к приложению

app.register_blueprint(blog)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)