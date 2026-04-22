from flask import Blueprint, request, jsonify, current_app, render_template, redirect, url_for, flash, session
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_login import login_user, logout_user, login_required, current_user
from marshmallow import ValidationError
from app import db
from app.models import User, Post, Category, Tag, Comment
from app.schemas import (
    UserRegistrationSchema, UserLoginSchema, UserSchema, PostCreateSchema, 
    PostSchema, CategorySchema, TagSchema, CommentCreateSchema, CommentSchema
)
from datetime import datetime

print("Routes module imported")

main_bp = Blueprint('main', __name__)

@main_bp.route('/test', methods=['POST'])
def test():
    print("Test route called")
    return "Test OK"

# ======================== HEALTH CHECK ========================
@main_bp.route('/', methods=['GET'])
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    posts = Post.query.filter_by(status='published').order_by(Post.create_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    categories = Category.query.all()
    tags = Tag.query.all()
    
    return render_template('index.html', posts=posts, categories=categories, tags=tags)

# ======================== АУТЕНТИФИКАЦИЯ ========================
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    print("Register function called")
    current_app.logger.info("Register route called")
    current_app.logger.info(f"Request method: {request.method}")
    if request.method == 'POST':
        print("POST request received")
        print(f"Request form: {request.form}")
        username = request.form.get('username')
        print(f"Username: {username}")
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('register.html')
        
        user = User(username=username, full_name=full_name)
        user.set_password(password)
        try:
            print(f"Creating user: {username}")
            print(f"User object created: {user}")
            print("Password set")
            db.session.add(user)
            print("Added to session")
            db.session.commit()
            print("User committed")
            # login_user(user)  # Временно отключим
            print("User logged in")
            # flash('Регистрация прошла успешно. Теперь войдите в систему.', 'success')
            return "Registration successful"  # redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            current_app.logger.error(f'Registration error: {str(e)}')
            # flash('Ошибка при регистрации', 'error')
            return "Error: " + str(e)
    
    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Вы успешно вошли в систему', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('main.index'))

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

@main_bp.route('/posts', methods=['GET'])
def posts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    posts = Post.query.filter_by(status='published').order_by(Post.create_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('posts.html', posts=posts)

@main_bp.route('/create-post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        id_category = request.form.get('id_category')
        tags_str = request.form.get('tags')
        status = request.form.get('status', 'published')
        
        post = Post(
            title=title,
            content=content,
            id_user=current_user.id_user,
            id_category=id_category if id_category else None,
            status=status
        )
        
        if tags_str:
            tag_names = [name.strip() for name in tags_str.split(',') if name.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                post.tags.append(tag)
        
        db.session.add(post)
        db.session.commit()
        
        flash('Пост создан успешно', 'success')
        return redirect(url_for('main.post_detail', post_id=post.post_id))
    
    categories = Category.query.all()
    return render_template('create_post.html', categories=categories)

@main_bp.route('/post/<int:post_id>', methods=['GET'])
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    author_posts = Post.query.filter_by(id_user=post.id_user, status='published').limit(5).all()
    return render_template('post_detail.html', post=post, author_posts=author_posts)

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

@main_bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    text = request.form.get('text')
    
    if not text:
        flash('Комментарий не может быть пустым', 'error')
        return redirect(url_for('main.post_detail', post_id=post_id))
    
    comment = Comment(text=text, id_post=post_id, id_user=current_user.id_user)
    db.session.add(comment)
    db.session.commit()
    
    flash('Комментарий добавлен', 'success')
    return redirect(url_for('main.post_detail', post_id=post_id))

@main_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post = comment.post
    
    if comment.id_user != current_user.id_user and post.id_user != current_user.id_user:
        flash('У вас нет прав на удаление этого комментария', 'error')
        return redirect(url_for('main.post_detail', post_id=post.post_id))
    
    db.session.delete(comment)
    db.session.commit()
    
    flash('Комментарий удален', 'success')
    return redirect(url_for('main.post_detail', post_id=post.post_id))

@main_bp.route('/category/<int:category_id>')
def posts_by_category(category_id):
    category = Category.query.get_or_404(category_id)
    posts = Post.query.filter_by(id_category=category_id, status='published').order_by(Post.create_date.desc()).all()
    return render_template('posts_by_category.html', category=category, posts=posts)

@main_bp.route('/my-posts')
@login_required
def my_posts():
    posts = Post.query.filter_by(id_user=current_user.id_user).order_by(Post.create_date.desc()).all()
    return render_template('my_posts.html', posts=posts)
