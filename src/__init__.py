import os
from flask import Flask 
from flask_mail import Mail
from flask_login import (
    LoginManager,
)
import pymongo
mongo_host = os.environ.get('MONGODB_HOST')
mongo_client = pymongo.MongoClient(mongo_host)
app_secrete = os.environ.get('SECRET_KEY')
mail_password = os.environ.get('MAIL_PASSWORD')
mail_server = os.environ.get('MAIL_SERVER')
mail_username = os.environ.get('MAIL_USERNAME')

global login_manager 
login_manager = LoginManager()

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.secret_key = app_secrete
    app.config['MAIL_SERVER'] = mail_server
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = mail_username
    app.config['MAIL_PASSWORD'] = mail_password

    mail = Mail(app)

    # User session management setup
    # https://flask-login.readthedocs.io/en/latest
    login_manager.init_app(app)

    from .views import views

    app.register_blueprint(views)

    return app

