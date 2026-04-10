from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app import db
from app.models import User, Post, Category, Tag, Comment
from app.schemas import (
    UserRegistrationSchema, UserLoginSchema, UserSchema, PostCreateSchema, 
    PostSchema, CategorySchema, TagSchema, CommentCreateSchema, CommentSchema
)
from datetime import datetime

main_bp = Blueprint('main', __name__)

# ======================== HEALTH CHECK ========================
@main_bp.route('/', methods=['GET'])
def index():
    current_app.logger.info('Health check performed')
    return jsonify({"message": "Блог API работает!", "version": "1.0"}), 200

# ======================== АУТЕНТИФИКАЦИЯ ========================
@main_bp.route('/api/auth/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    try:
        schema = UserRegistrationSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        current_app.logger.warning(f'Validation error during registration: {err.messages}')
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    # Проверка что пользователь не существует
    if User.query.filter_by(username=data['username']).first():
        current_app.logger.warning(f'User {data["username"]} already exists')
        return jsonify({'error': 'User already exists'}), 409
    
    # Создание пользователя
    user = User(
        username=data['username'],
        full_name=data.get('full_name')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    current_app.logger.info(f'User {user.username} registered successfully')
    
    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201

@main_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Вход пользователя"""
    try:
        schema = UserLoginSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        current_app.logger.warning(f'Failed login attempt for user {data.get("username")}')
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'User account is inactive'}), 403
    
    access_token = create_access_token(identity=user.id_user)
    current_app.logger.info(f'User {user.username} logged in successfully')
    
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

# ======================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ========================
@main_bp.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Получить информацию о пользователе"""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200

@main_bp.route('/api/users', methods=['GET'])
def get_all_users():
    """Получить список всех пользователей"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

# ======================== КАТЕГОРИИ ========================
@main_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """Получить список всех категорий"""
    categories = Category.query.all()
    return jsonify([cat.to_dict() for cat in categories]), 200

@main_bp.route('/api/categories', methods=['POST'])
@jwt_required()
def create_category():
    """Создать новую категорию (только для авторизованных)"""
    data = request.get_json()
    
    schema = CategorySchema()
    try:
        cat_data = schema.load(data, partial=True)
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    if not data.get('name'):
        return jsonify({'error': 'Category name is required'}), 400
    
    # Проверка что категория не существует
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Category already exists'}), 409
    
    category = Category(name=data['name'])
    db.session.add(category)
    db.session.commit()
    
    current_app.logger.info(f'Category "{category.name}" created by user {get_jwt_identity()}')
    
    return jsonify({'message': 'Category created', 'category': category.to_dict()}), 201

@main_bp.route('/api/categories/<int:cat_id>', methods=['GET'])
def get_category(cat_id):
    """Получить категорию по ID"""
    category = Category.query.get_or_404(cat_id)
    return jsonify(category.to_dict()), 200

# ======================== ТЕГИ ========================
@main_bp.route('/api/tags', methods=['GET'])
def get_tags():
    """Получить список всех тегов"""
    tags = Tag.query.all()
    return jsonify([tag.to_dict() for tag in tags]), 200

@main_bp.route('/api/tags', methods=['POST'])
@jwt_required()
def create_tag():
    """Создать новый тег"""
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Tag name is required'}), 400
    
    if Tag.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Tag already exists'}), 409
    
    tag = Tag(name=data['name'])
    db.session.add(tag)
    db.session.commit()
    
    current_app.logger.info(f'Tag "{tag.name}" created by user {get_jwt_identity()}')
    
    return jsonify({'message': 'Tag created', 'tag': tag.to_dict()}), 201

# ======================== ПОСТЫ (CRUD) ========================
@main_bp.route('/api/posts', methods=['GET'])
def get_posts():
    """Получить список всех постов"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status', 'published')
    
    query = Post.query.filter_by(status=status)
    
    if request.args.get('category_id'):
        query = query.filter_by(id_category=request.args.get('category_id', type=int))
    
    posts = query.order_by(Post.create_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'posts': [post.to_dict() for post in posts.items],
        'total': posts.total,
        'pages': posts.pages,
        'current_page': page
    }), 200

@main_bp.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    """Создать новый пост"""
    user_id = get_jwt_identity()
    
    try:
        schema = PostCreateSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    post = Post(
        title=data['title'],
        content=data['content'],
        id_user=user_id,
        id_category=data.get('id_category'),
        status=data.get('status', 'published')
    )
    
    # Добавление тегов
    if data.get('id_tag'):
        tag = Tag.query.get(data['id_tag'])
        if tag:
            post.tags.append(tag)
    
    db.session.add(post)
    db.session.commit()
    
    current_app.logger.info(f'Post "{post.title}" created by user {user_id}')
    
    return jsonify({'message': 'Post created', 'post': post.to_dict()}), 201

@main_bp.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Получить пост по ID"""
    post = Post.query.get_or_404(post_id)
    return jsonify(post.to_dict(include_comments=True)), 200

@main_bp.route('/api/posts/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    """Обновить пост"""
    user_id = get_jwt_identity()
    post = Post.query.get_or_404(post_id)
    
    # Проверка прав: может обновлять только автор
    if post.id_user != user_id:
        current_app.logger.warning(f'Unauthorized update attempt for post {post_id} by user {user_id}')
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        schema = PostCreateSchema()
        data = schema.load(request.get_json(), partial=True)
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    if 'title' in data:
        post.title = data['title']
    if 'content' in data:
        post.content = data['content']
    if 'id_category' in data:
        post.id_category = data['id_category']
    if 'status' in data:
        post.status = data['status']
    
    post.update_date = datetime.utcnow()
    db.session.commit()
    
    current_app.logger.info(f'Post {post_id} updated by user {user_id}')
    
    return jsonify({'message': 'Post updated', 'post': post.to_dict()}), 200

@main_bp.route('/api/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Удалить пост"""
    user_id = get_jwt_identity()
    post = Post.query.get_or_404(post_id)
    
    # Проверка прав: может удалять только автор
    if post.id_user != user_id:
        current_app.logger.warning(f'Unauthorized delete attempt for post {post_id} by user {user_id}')
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(post)
    db.session.commit()
    
    current_app.logger.info(f'Post {post_id} deleted by user {user_id}')
    
    return jsonify({'message': 'Post deleted'}), 200

# ======================== КОММЕНТАРИИ ========================
@main_bp.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    """Получить комментарии к посту"""
    post = Post.query.get_or_404(post_id)
    
    comments = Comment.query.filter_by(id_post=post_id).order_by(Comment.date.desc()).all()
    
    return jsonify([comment.to_dict() for comment in comments]), 200

@main_bp.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@jwt_required()
def create_comment(post_id):
    """Добавить комментарий к посту"""
    user_id = get_jwt_identity()
    post = Post.query.get_or_404(post_id)
    
    try:
        schema = CommentCreateSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    comment = Comment(
        text=data['text'],
        id_post=post_id,
        id_user=user_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    current_app.logger.info(f'Comment added to post {post_id} by user {user_id}')
    
    return jsonify({'message': 'Comment created', 'comment': comment.to_dict()}), 201

@main_bp.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    """Удалить комментарий"""
    user_id = get_jwt_identity()
    comment = Comment.query.get_or_404(comment_id)
    
    # Может удалять только автор или автор поста
    post = comment.post
    if comment.id_user != user_id and post.id_user != user_id:
        current_app.logger.warning(f'Unauthorized delete attempt for comment {comment_id} by user {user_id}')
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(comment)
    db.session.commit()
    
    current_app.logger.info(f'Comment {comment_id} deleted by user {user_id}')
    
    return jsonify({'message': 'Comment deleted'}), 200

# ======================== ПОИСК И ФИЛЬТРАЦИЯ ========================
@main_bp.route('/api/posts/search', methods=['GET'])
def search_posts():
    """Поиск постов по названию или содержанию"""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters long'}), 400
    
    posts = Post.query.filter(
        (Post.title.ilike(f'%{query}%') | Post.content.ilike(f'%{query}%')) &
        (Post.status == 'published')
    ).order_by(Post.create_date.desc()).all()
    
    return jsonify([post.to_dict() for post in posts]), 200

@main_bp.route('/api/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    """Получить все посты пользователя"""
    user = User.query.get_or_404(user_id)
    
    posts = Post.query.filter_by(id_user=user_id, status='published').order_by(
        Post.create_date.desc()
    ).all()
    
    return jsonify([post.to_dict() for post in posts]), 200
