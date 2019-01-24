from flask import (Flask, g,  # g is some global variable
                   render_template, flash, redirect, url_for,
                   abort  # lets us end a request
                   )
from flask_bcrypt import check_password_hash
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)

import forms
import models

DEBUG = True
PORT = 8000
HOST = '0.0.0.0'

app = Flask(__name__)
app.secret_key = "ahf832hlnboi8ayshf.>829^697Y$)&lkahsohhowh"

# sets up login manager for our app
# setting up our views, controlling users, getting global objects, etc.
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(userid):
    try:
        return models.User.get(models.User.id == userid)
    except models.DoesNotExist:
        return None


@app.before_request
def before_request():
    """Connect to database before each request."""
    g.db = models.DATABASE
    g.db.connect()
    g.user = current_user


@app.after_request
def after_request(response):
    """Close the database connection after each request."""
    g.db.close()
    return response


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.RegisterForm()
    if form.validate_on_submit():
        # "success" here is for our html code
        flash("Yay, you registered!", "success")
        models.User.create_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.LoginForm()
    if form.validate_on_submit():
        try:
            user = models.User.get(models.User.email == form.email.data)
        except models.DoesNotExist:
            flash("Your email or password doesn't match!", "error")
        else:
            if check_password_hash(user.password, form.password.data):
                login_user(user)  # creates session on users browser
                flash("You've been logged in!", "success")
                return redirect(url_for('index'))
            else:
                flash("Your email or password doesn't match!", "error")
    return render_template("login.html", form=form)


@app.route('/logout')  # GET is the default method
@login_required
def logout():
    logout_user()  # deletes the session cookie
    flash("You've been logged out! Come back soon!", "success")
    return redirect(url_for('index'))


@app.route('/new_post', methods=['GET', 'POST'])
@login_required
def post():
    form = forms.PostForm()
    if form.validate_on_submit():
        models.Post.create(user=g.user._get_current_object(),
                           content=form.content.data.strip())
        flash("Message posted! Thanks!", "success")
        return redirect(url_for('index'))
    return render_template("post.html", form=form)


@app.route('/')
def index():
    stream = models.Post.select().limit(100)
    return render_template("stream.html", stream=stream)


@app.route('/stream')
@app.route('/stream/<username>')
def stream(username=None):
    template = "stream.html"
    if username and username != current_user.username:
        try:
            # where User.username "is like (regardless of case) username"
            user = models.User.select().where(
                models.User.username**username).get()
        except models.DoesNotExist:
            abort(404)  # file (user) does not exist
        else:
            stream = user.posts.limit(100)
    else:
        stream = current_user.get_stream().limit(100)
        user = current_user

    if username:
        template = "user_stream.html"

    return render_template(template, stream=stream, user=user)


# Add ability to look at an individual post
@app.route('/post/<int:post_id>')
def view_post(post_id):
    posts = models.Post.select().where(models.Post.id == post_id)
    if posts.count() == 0:
        abort(404)
    return render_template('stream.html', stream=posts)


@app.route('/follow/<username>')
@login_required
def follow(username):
    try:
        to_user = models.User.get(models.User.username**username)
    except models.DoesNotExist:
        abort(404)
    else:
        try:
            models.Relationship.create(
                from_user=g.user._get_current_object(),
                to_user=to_user
            )
        except models.IntegrityError:  # in case we try to follow someone twice
            pass
        else:
            flash("You're now following {}!".format(to_user.username),
                  "success")
    return redirect(url_for('stream', username=to_user.username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    try:
        to_user = models.User.get(models.User.username**username)
    except models.DoesNotExist:
        abort(404)
    else:
        try:
            models.Relationship.get(
                from_user=g.user._get_current_object(),
                to_user=to_user
            ).delete_instance()
        except models.IntegrityError:  # in case we try to follow someone twice
            pass
        else:
            flash("You've unfollowed {}!".format(to_user.username), "success")
    return redirect(url_for('stream', username=to_user.username))


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404  # render this template as a 404


if __name__ == '__main__':
    models.initialize()
    try:
        models.User.create_user(
            username="RoyTelles",
            email="rtelles64@gmail.com",
            password="password",
            admin=True
        )
    except ValueError:
        pass
    app.run(debug=DEBUG, host=HOST, port=PORT)