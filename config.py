import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # Laddar variabler från .env

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'du-borde-verkligen-ändra-detta'
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Stänger av onödiga notiser

    # Flask-Mail konfiguration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
    SUPPORT_MAIL_RECIPIENT = os.environ.get('SUPPORT_MAIL_RECIPIENT')

    #Other configs
    THREADS_PER_PAGE = int(os.environ.get('THREADS_PER_PAGE') or 20)
    POSTS_PER_PAGE = int(os.environ.get('POSTS_PER_PAGE') or 10)