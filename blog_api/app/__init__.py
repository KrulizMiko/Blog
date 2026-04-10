import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
ma = Marshmallow()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Настройки
    if config_name == 'testing':
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///blog.db')
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key-change-in-production')
    app.json.ensure_ascii = False  # Чтобы русский текст в JSON отображался корректно

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)

    # Логирование
    setup_logging(app)
    
    # Регистрация обработчиков ошибок
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f'Bad Request: {str(error)}')
        return jsonify({'error': 'Bad Request', 'message': str(error.description)}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        app.logger.warning('Unauthorized access attempt')
        return jsonify({'error': 'Unauthorized', 'message': 'Требуется аутентификация'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning('Forbidden access attempt')
        return jsonify({'error': 'Forbidden', 'message': 'Доступ запрещен'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not Found', 'message': 'Ресурс не найден'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal Server Error: {str(error)}')
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error', 'message': 'Внутренняя ошибка сервера'}), 500
    
    # Импорт моделей и инициализация БД
    from app import models 
    
    with app.app_context():
        db.create_all()
    
    # Импорт и регистрация маршрутов
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app

def setup_logging(app):
    """Настройка логирования приложения"""
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler('logs/blog_api.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Blog API startup')
