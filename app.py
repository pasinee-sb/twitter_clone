import os
import pdb


from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message, Follows

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
app.app_context().push()
uri = os.environ.get('DATABASE_URL', 'postgresql:///warbler')
app.config['SQLALCHEMY_DATABASE_URI'] = uri

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "goodjob")
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config.update(SESSION_COOKIE_SAMESITE="None",
                  SESSION_COOKIE_SECURE=True)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', False)

connect_db(app)


##############################################################################
# User signup/login/logout

#    @app.before_request""" is a decorator in Flask that registers a function to be called before each request
# is processed by the server. This can be used to perform tasks that
#  should be done for every request, such as setting up a database connection,
# checking if the user is logged in, or modifying the request object."""
@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:

        # The g object in Flask is a global object that can be used to store data during the lifetime of a request.
        # It is often used to store objects that need to be accessed by multiple functions during the handling of a request.
        # The g object is specific to each request and is not shared between different requests.
        # It is created at the start of a request and destroyed at the end of the request.
        g.user = User.query.get(session[CURR_USER_KEY])

    else:

        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:

        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()

    flash("See you later!", "success")
    return redirect('/login')


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized", "danger")
        return redirect("/")

    form = UserEditForm(obj=g.user)

    if form.validate_on_submit():
        user = User.authenticate(g.user.username, form.password.data)

        if user:

            edited_user = User.query.get(user.id)
            edited_user.username = form.username.data
            edited_user.email = form.email.data
            edited_user.image_url = form.image_url.data
            edited_user.header_image_url = form.header_image_url.data
            edited_user.bio = form.bio.data
            db.session.commit()
            return redirect(f"/users/{user.id}")

        else:
            flash("Edit unauthorized.", "danger")
            return redirect('/')

    return render_template("users/edit.html", form=form)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        # add list of id of users that the current user is following
        users_being_followed = [user.id for user in g.user.following]
        # add user's own id as part of the list
        users_being_followed.append(g.user.id)

        # get all messages from users that are being followed and user's own message
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(users_being_followed))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())
        likes = [like.id for like in g.user.likes]

        return render_template('home.html', messages=messages, likes=likes)

    else:
        return render_template('home-anon.html')

# Add likes to users


@app.route('/users/add_like/<int:msg_id>', methods=['POST'])
def add_like(msg_id):

    if g.user:
        message = Message.query.get(msg_id)

        if message in g.user.likes:
            g.user.likes.remove(message)
            db.session.commit()
            return redirect('/')
        else:
            g.user.likes.append(message)
            db.session.commit()
            return redirect('/')

    return redirect("/")


@app.route('/users/<int:user_id>/likes')
def shoe_like_msgs(user_id):
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get(user_id)
    likes = [like.id for like in g.user.likes]

    return render_template("users/likes.html", likes=likes, user=user)


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask
@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
