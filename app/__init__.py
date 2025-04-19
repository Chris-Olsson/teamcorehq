# app/__init__.py (relevant del)

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import logging
from logging.handlers import RotatingFileHandler
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
# VIKTIGT: Uppdatera login_view för att använda blueprint-syntax!
login_manager.login_view = 'main.login' # ÄNDRAD HÄR!
login_manager.login_message_category = 'info'
bcrypt = Bcrypt()
mail = Mail()

# Importera modeller här på toppnivå så de säkert hittas
from app import models

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db) # Migrate behöver känna till db och app
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    # Importera och registrera Blueprint
    from .routes import main as main_blueprint # Importera blueprint-objektet
    app.register_blueprint(main_blueprint) # Registrera det på appen

    # Ta bort den gamla importen härifrån:
    # with app.app_context():
    #      from app import routes, models # RADERA/KOMMENTERA BORT

    # ... (Felhantering och loggning som tidigare) ...
    if not app.debug and not app.testing:
         # ... (loggningskod) ...
         pass # Placeholder om du kommenterade bort loggningen


    return app