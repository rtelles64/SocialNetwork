import datetime

# Older format of import
# from flask.ext.login import UserMixin  # to check if user logged in
from flask_login import UserMixin
from flask_bcrypt import generate_password_hash
from peewee import *

DATABASE = SqliteDatabase("social.db")


# In this inheritance, Model is the ultimate Parent class
class User(UserMixin, Model):
    username = CharField(unique=True)
    email = CharField(unique=True)
    password = CharField(max_length=100)
    # Set default to datetime.datetime.now WITHOUT parens!
    # RECALL: without parens so that we lock the time when the script runs,
    #         not when the Model is created
    joined_at = DateTimeField(default=datetime.datetime.now)
    is_admin = BooleanField(default=False)

    class Meta:
        database = DATABASE
        # order view by descending
        order_by = ('-joined_at',)

    def get_posts(self):
        return Post.select().where(Post.user == self)

    def get_stream(self):
        return Post.select().where(
            # Find all the posts where the post user is inside of the people
            # that I follow
            (Post.user << self.following()) |  # or
            (Post.user == self)  # my posts
        )

    def following(self):
        """The users that we are following"""
        # we're selecting from multiple tables at once, so we use .join()
        # Select from Relationship on to_user field
        # Where from_user is self (i.e. me)
        return (
            User.select().join(
                Relationship, on=Relationship.to_user
            ).where(
                Relationship.from_user == self
            )
        )

    def followers(self):
        """Get users following the current user"""
        return (
            User.select().join(
                Relationship, on=Relationship.from_user
            ).where(
                Relationship.to_user == self
            )
        )

    @classmethod  # describes a method that belongs to a Class that can create
    #               the class it belongs to:
    # If we don't have classmethod, we have to create the User instance, to
    # call create_user which will create a User instance
    def create_user(cls, username, email, password, admin=False):
        try:
            # if it works, move on
            # if not, remove it
            with DATABASE.transaction():
                cls.create(
                    username=username,
                    email=email,
                    password=generate_password_hash(password),
                    is_admin=admin
                )
        except IntegrityError:  # thrown if username/email are not unique
            raise ValueError("User already exists")


class Post(Model):
    # related name is what the related model would call this model
    # (i.e. if you're a User, what do you call the Post model instances
    # that you created? Posts!)
    timestamp = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(
        model=User,  # points to User model
        related_name='posts'
    )
    content = TextField()

    class Meta:
        database = DATABASE
        order_by = ('-timestamp',)  # newest items first (a tuple)


class Relationship(Model):
    from_user = ForeignKeyField(User, related_name='relationships')
    to_user = ForeignKeyField(User, related_name='related_to')

    class Meta:
        database = DATABASE
        indexes = (  # tells data base how to find users
        #   Don't forget comma after first tuple! (this ensures "tupl-ity")
            (('from_user', 'to_user'), True),  # unique index
        )


def initialize():
    DATABASE.connect()
    DATABASE.create_tables([User, Post, Relationship], safe=True)
    DATABASE.close()
