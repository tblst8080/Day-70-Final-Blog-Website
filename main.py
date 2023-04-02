import functools
import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from flask_bcrypt import Bcrypt

ckeditor = CKEditor()
bcrypt = Bcrypt()  # Apply Bcrypt configurations to the app (enable Bcrypt features)
db = SQLAlchemy()
login_manager = LoginManager()

gravatar = Gravatar(
                    size=500,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'


    ##CONNECT TO DB
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['internal']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    login_manager.init_app(app)  # Apply login_manager configurations to the app (enable login features)
    ckeditor.init_app(app)
    Bootstrap(app)
    bcrypt.init_app(app)
    db.init_app(app)
    gravatar.init_app(app)
    return app

app = create_app()

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)

    # Set column as link to parent (User object that wrote blog)
    author_id = db.Column(ForeignKey("users.id"))
    author = relationship("User", back_populates="blog")  # back-populates indicates corresponding column in User
    comments = relationship("Comment", back_populates="b_post")



    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # Set blog as link to child (BlogPost object written by User)  # back-populates indicates corresponding column in BlogPost
    blog = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")

    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    author_id = db.Column(ForeignKey("users.id"))
    author = relationship("User", back_populates="comments")

    blog_id = db.Column(ForeignKey("blog_posts.id"))
    b_post = relationship("BlogPost", back_populates="comments")



def admin_only(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.__dict__.get('id') == 1:
            return func(*args, **kwargs)
        else:
            return abort(403)
    return wrapper

@login_manager.user_loader
def load_user(user_id):
    """This function takes a numerical id and returns the database entry associated with that id"""
    return User.query.filter_by(id=user_id).first()  # searches for entries by id, and return the first entry found


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()[::-1]
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if request.method == "GET":
        return render_template("register.html", form=form)
    else:
        if form.validate_on_submit():

            # Modify response in POST form
            data = form.data  # retrieve input data as dictionary
            del data['csrf_token'], data['submit']  # remove unnecessary data from dictionary

            # Hash password
            data['password'] = bcrypt.generate_password_hash(password=data['password'], rounds=12).decode('utf-8')

            entry = User(**data)  # Create user entry
            db.session.add(entry)  # Add user to database
            db.session.commit() # Save changes

            # Login User
            login_user(entry)

            return redirect(url_for('get_all_posts'))

        # Redirects user back to registration page if input is not valid (show error message)
        else:
            return render_template("register.html", form=form)


@app.route('/login', methods = ["POST", "GET"])
def login():
    form = LoginForm()
    if request.method == "GET":
        return render_template("login.html", form=form)
    elif request.method == "POST":
        # check if input is valid
        if form.validate_on_submit():

            # Check if email is registered
            entry = User.query.filter_by(email=form.email.data).first()
            if entry:

                # Check if password is valid:
                if bcrypt.check_password_hash(entry.password, form.password.data):

                    # Login user
                    login_user(entry)

                    # Redirect user to homepage
                    return redirect(url_for('get_all_posts'))

                # If password is invalid:
                else:
                    # Generate error message with wtforms
                    form.password.errors.append("Invalid password.")
                    return render_template("login.html", form=form)

            # If email isn't found in database:
            else:
                # Generate error message with wtforms
                form.email.errors.append("No account registered using this email")
                return render_template("login.html", form=form)

        # Redirect back to login page with wtforms error message
        else:
            return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()

    if request.method == "GET":
        return render_template("post.html", post=requested_post, form=comment_form)

    elif request.method == "POST":

        if current_user.is_authenticated:
            new_comment = Comment(
                text=comment_form.text.data,
                b_post=requested_post,
                author=current_user,
            )
            db.session.add(new_comment)
            db.session.commit()

        comment_form = CommentForm()
        return render_template("post.html", post=requested_post, form=comment_form)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/new-post", methods=["GET", "POST"])
def add_new_post():
    form = CreatePostForm()
    if request.method == "POST":
        if form.validate_on_submit():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author=current_user,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
    else:
        return render_template("make-post.html", form=form)

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if request.method=="POST":
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.author = current_user
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))
        else:
            return render_template("make-post.html", form=edit_form)
    else:
        return render_template("make-post.html", form=edit_form)

@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000)
