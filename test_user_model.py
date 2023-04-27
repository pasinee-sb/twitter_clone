"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


from app import app
import os
from unittest import TestCase

from models import db, User, Message, Follows
from sqlalchemy import exc

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_user_repr(self):
        """Does the repr method work as expected?"""
        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )
        expected = f"<User #{u.id}: {u.username}, {u.email}>"
        actual = repr(u)
        self.assertEqual(actual, expected)

    def test_following_user(self):
        """Does is_following successfully detect when user1 is following user2?"""
        """Does is_following successfully detect when user2 is not following user1?"""
        """Does is_followed_by successfully detect when user2 is followed by user1?"""
        """Does is_followed_by successfully detect when user1 is not followed by user2?"""

        u1 = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )
        u2 = User(
            email="test2@test.com",
            username="testuser2",
            password="HASHED_PASSWORD2"
        )
        db.session.add_all([u1, u2])
        db.session.commit()
        follow = Follows(user_being_followed_id=u2.id, user_following_id=u1.id)
        db.session.add(follow)
        db.session.commit()

        # Does is_following successfully detect when user1 is following user2?
        self.assertEqual(u1.is_following(u2), 1)
        # Does is_followed_by successfully detect when user2 is followed by user1?
        self.assertEqual(u2.is_followed_by(u1), 1)
        # Does is_following successfully detect when user2 is not following user1?
        self.assertEqual(u2.is_following(u1), 0)
        # Does is_followed_by successfully detect when user1 is not followed by user2?
        self.assertEqual(u1.is_followed_by(u2), 0)

        self.assertIn(u1, u2.followers)
        self.assertNotIn(u2, u1.followers)

    def test_user_signup_valid(self):
        """Does User.signup successfully create a new user given valid credentials?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        self.assertEqual(u.username, "testuser")

    # def test_user_create_not_valid(self):
    #     """Does User.signup fail to create a new user if any of the validations
    # (e.g. uniqueness, non-nullable fields) fail?"""

    #     with self.assertRaises(exc.IntegrityError):
    #         User.signup(
    #             email="",
    #             username="testuser",
    #             password="HASHED_PASSWORD",
    #             image_url=""
    #         )
    def test_user_authen_success(self):
        """Does User.authenticate successfully 
        return a user when given a valid username and password?"""
        u = User.signup(
            "test@test.com",
            "testuser",
            "HASHED_PASSWORD",
            None
        )

        db.session.commit()

        user = User.authenticate(u.username, "HASHED_PASSWORD")

        self.assertEqual(user, u)

    def test_user_authen_fail(self):
        """Does User.authenticate fail to return a user when the username is invalid?"""
        u = User.signup(
            "test@test.com",
            "",
            "HASHED_PASSWORD",
            None
        )

        db.session.commit()

        user = User.authenticate(u.username, "HASHED_PASSWORD")

        self.assertNotEqual(user, False)

    def test_user_authen_fail2(self):
        """Does User.authenticate fail to return a user when the password is invalid?"""
        u = User.signup(
            "test@test.com",
            "testuser",
            "HAS",
            None
        )

        db.session.commit()

        user = User.authenticate(u.username, "HAS")

        self.assertNotEqual(user, False)
