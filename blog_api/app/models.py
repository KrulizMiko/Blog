from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Таблица связи для многие-ко-многим между Post и Tag
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.post_id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id_tag'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'
    id_user = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150))
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Связи: один пользователь может иметь много постов и комментариев
    posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='author', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        """Хеширует и устанавливает пароль"""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Проверяет пароль"""
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        return {
            'id_user': self.id_user,
            'username': self.username,
            'full_name': self.full_name
        }

class Category(db.Model):
    __tablename__ = 'categories'
    id_category = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    posts = db.relationship('Post', backref='category', lazy=True)
    
    def to_dict(self):
        return {
            'id_category': self.id_category,
            'name': self.name,
            'created_date': self.created_date.isoformat()
        }

class Tag(db.Model):
    __tablename__ = 'tags'
    id_tag = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    
    posts = db.relationship('Post', secondary=post_tags, backref='tags', lazy=True)
    
    def to_dict(self):
        return {
            'id_tag': self.id_tag,
            'name': self.name
        }

class Post(db.Model):
    __tablename__ = 'posts'
    post_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    create_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    update_date = db.Column(db.DateTime, onupdate=datetime.utcnow)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id_user'), nullable=False, index=True)
    status = db.Column(db.String(50), default='published')  # draft, published, archived
    id_category = db.Column(db.Integer, db.ForeignKey('categories.id_category'))
    
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self, include_comments=False):
        data = {
            'post_id': self.post_id,
            'title': self.title,
            'content': self.content,
            'create_date': self.create_date.isoformat(),
            'update_date': self.update_date.isoformat() if self.update_date else None,
            'status': self.status,
            'author': self.author.to_dict() if self.author else None,
            'category': self.category.to_dict() if self.category else None,
            'tags': [tag.to_dict() for tag in self.tags]
        }
        if include_comments:
            data['comments'] = [comment.to_dict() for comment in self.comments]
        return data

class Comment(db.Model):
    __tablename__ = 'comments'
    id_comment = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    id_post = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False, index=True)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id_user'), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    
    def to_dict(self):
        return {
            'id_comment': self.id_comment,
            'text': self.text,
            'date': self.date.isoformat(),
            'author': self.author.to_dict() if self.author else None
        }
