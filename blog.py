from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from database import db  # Импортируем db из database.py
from models import User, Post, Tag, post_tags
from forms import RegistrationForm, LoginForm, PostForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid

blog = Blueprint('blog', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

class BlogController:
    @staticmethod
    @blog.route('/')
    def home():
        query = request.args.get('query')
        tag = request.args.get('tag')

        posts_query = Post.query.join(User)

        # Поиск по тексту
        if query:
            posts_query = posts_query.filter(
                (Post.title.contains(query)) |
                (Post.content.contains(query)) |
                (User.username.contains(query))
            )

        # Фильтр по тегу
        if tag:
            posts_query = posts_query.join(Post.tags).filter(Tag.name == tag)

        posts = posts_query.all()
        tags = Tag.query.all()  # Для выпадающего списка тегов
        return render_template('home.html', posts=posts, tags=tags)

    @staticmethod
    @blog.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegistrationForm()
        if form.validate_on_submit():
            hashed_password = generate_password_hash(form.password.data)
            user = User(username=form.username.data, email=form.email.data, password=hashed_password)
            try:
                db.session.add(user)
                db.session.commit()
                flash('Account created successfully!', 'success')
                return redirect(url_for('blog.login'))
            except:
                db.session.rollback()
                flash('Username or email already exists', 'danger')
        return render_template('register.html', form=form)

    @staticmethod
    @blog.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and check_password_hash(user.password, form.password.data):
                session['user_id'] = user.id
                session.permanent = form.remember.data
                flash('Login successful!', 'success')
                return redirect(url_for('blog.home'))
            flash('Login failed. Check email and password', 'danger')
        return render_template('login.html', form=form)

    @staticmethod
    @blog.route('/logout')
    def logout():
        session.pop('user_id', None)
        flash('You have been logged out', 'success')
        return redirect(url_for('blog.login'))

    @staticmethod
    @blog.route('/post/new', methods=['GET', 'POST'])
    def create_post():
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('blog.login'))
        form = PostForm()
        if form.validate_on_submit():
            image_filename = None
            if form.image.data:
                file = form.image.data
                if file and allowed_file(file.filename):
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    if file_size > current_app.config['MAX_FILE_SIZE']:
                        flash('File size exceeds 5MB limit', 'danger')
                        return render_template('create_post.html', form=form)
                    file.seek(0)
                    image_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename))
                else:
                    flash('Invalid file type. Allowed types: png, jpg, jpeg, gif', 'danger')
                    return render_template('create_post.html', form=form)
            post = Post(
                title=form.title.data,
                content=form.content.data,
                image=image_filename,
                user_id=session['user_id']
            )
            if form.tags.data:
                tag_names = [name.strip() for name in form.tags.data.split(',')]
                for tag_name in tag_names:
                    if tag_name:
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            db.session.add(tag)
                        post.tags.append(tag)
            db.session.add(post)
            db.session.commit()
            flash('Post created successfully!', 'success')
            return redirect(url_for('blog.home'))
        return render_template('create_post.html', form=form)

    @staticmethod
    @blog.route('/post/<int:post_id>')
    def view_post(post_id):
        post = Post.query.get_or_404(post_id)
        return render_template('post.html', post=post)

    @staticmethod
    @blog.route('/post/<int:post_id>/edit', methods=['GET', 'PUT'])
    def edit_post(post_id):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('blog.login'))
        post = Post.query.get_or_404(post_id)
        if post.user_id != session['user_id']:
            flash('You can only edit your own posts', 'danger')
            return redirect(url_for('blog.home'))
        form = PostForm()
        if form.validate_on_submit():
            post.title = form.title.data
            post.content = form.content.data
            if form.image.data:
                image_file = form.image.data
                if image_file and allowed_file(image_file.filename):
                    image_file.seek(0, os.SEEK_END)
                    file_size = image_file.tell()
                    if file_size > current_app.config['MAX_FILE_SIZE']:
                        flash('File size exceeds 5MB limit', 'danger')
                        return render_template('edit_post.html', form=form, post=post)
                    image_file.seek(0)
                    if post.image:
                        try:
                            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], post.image))
                        except:
                            pass
                    filename = f"{uuid.uuid4()}_{secure_filename(image_file.filename)}"
                    image_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    post.image = filename
            post.tags.clear()
            if form.tags.data:
                tag_names = [name.strip() for name in form.tags.data.split(',')]
                for tag_name in tag_names:
                    if tag_name:
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            db.session.add(tag)
                        post.tags.append(tag)
            db.session.commit()
            flash('Post updated successfully!', 'success')
            return redirect(url_for('blog.view_post', post_id=post.id))
        elif request.method == 'GET':
            form.title.data = post.title
            form.content.data = post.content
            form.tags.data = ', '.join([tag.name for tag in post.tags])
        return render_template('edit_post.html', form=form, post=post)

    @staticmethod
    @blog.route('/post/<int:post_id>/delete', methods=['DELETE'])
    def delete_post(post_id):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please login first'}), 403
        post = Post.query.get_or_404(post_id)
        if post.user_id != session['user_id']:
            return jsonify({'success': False, 'message': 'You can only delete your own posts'}), 403
        if post.image:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], post.image))
            except:
                pass
        db.session.delete(post)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Post deleted successfully'})

    @staticmethod
    @blog.route('/users')
    def list_users():
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('blog.login'))
        users = User.query.all()
        return render_template('users.html', users=users)