from flask import Flask
from routes import main
from models import db
from dotenv import load_dotenv
from datetime import timedelta
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DevSplit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days = 30)

db.init_app(app)
app.register_blueprint(main)


with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)