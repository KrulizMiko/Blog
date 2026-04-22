import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import User, Category, Tag

load_dotenv()

# Получить конфигурацию из переменной окружения
environ = os.getenv('FLASK_ENV', 'development')
app = create_app(environ)

@app.shell_context_processor
def make_shell_context():
    """Контекст для flask shell"""
    return {'db': db, 'User': User, 'Category': Category, 'Tag': Tag}

@app.cli.command()
def init_db():
    """Инициализировать БД"""
    db.create_all()
    print('Database initialized.')

@app.cli.command()
def seed_db():
    """Заполнить БД тестовыми данными"""
    # Создание тестовых категорий
    if Category.query.count() == 0:
        categories = [
            Category(name='Технология'),
            Category(name='Путешествия'),
            Category(name='Еда'),
            Category(name='Образование'),
        ]
        db.session.add_all(categories)
        db.session.commit()
        print(f'Created {len(categories)} categories.')
    
    # Создание тестовых тегов
    if Tag.query.count() == 0:
        tags = [
            Tag(name='python'),
            Tag(name='web'),
            Tag(name='tutorial'),
            Tag(name='news'),
            Tag(name='tips'),
        ]
        db.session.add_all(tags)
        db.session.commit()
        print(f'Created {len(tags)} tags.')

if __name__ == '__main__':
    print("Starting Flask app")
    app.run(debug=os.getenv('FLASK_ENV') == 'development')
