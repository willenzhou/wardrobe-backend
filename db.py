from flask_sqlalchemy import SQLAlchemy
import hashlib
import os
import bcrypt
import base64
import boto3
import datetime
from io import BytesIO
from mimetypes import guess_extension, guess_type
from PIL import Image
import random
import re
import string

db = SQLAlchemy()

EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET = "wardrobe"
S3_BASE_URL = f"https://{S3_BUCKET}.s3-us-east-2.amazonaws.com"

# outfits and tags
association_table = db.Table(
    'association',
    db.Column('outfit_id', db.Integer, db.ForeignKey('outfit.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)


class Asset(db.Model):
    __tablename__ = "asset"
    id = db.Column(db.Integer, primary_key=True)
    base_url = db.Column(db.String, nullable=True)
    salt = db.Column(db.String, nullable=False)
    extension = db.Column(db.String, nullable=False)
    width = db.Column(db.String, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    create_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs):
        self.create(kwargs.get("image_data"))

    def serialize(self):
        return{
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "create_at": str(self.create_at),
        }

    def create(self, image_data):
        try:
            # base64 string ---> .png ---> png
            ext = guess_extension(guess_type(image_data)[0])[1:]
            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} not supported!")

            # secure way of generating random string for image name
            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.create_at = datetime.datetime.now()

            img_filename = f"{salt}.{ext}"
            self.upload(img, img_filename)

        except Exception as e:
            print(f"Unable to create an image due to {e}")

    def upload(self, img, img_filename):
        try:
            # saves image temporarily on server
            img_temploc = f"{BASE_DIR}/{img_filename}"
            img.save(img_temploc)

            # upload image to S3
            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temploc, S3_BUCKET, img_filename)

            # make s3 URL public
            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET, img_filename)
            object_acl.put(ACL="public-read")

            os.remove(img_temploc)

        except Exception as e:
            print(f"Unable to upload an image due to {e}")


class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)

    # User information
    email = db.Column(db.String, nullable=False, unique=True)
    password_digest = db.Column(db.String, nullable=False)

    # Session information
    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)

    # one-to-many outfits
    outfits = db.relationship(
        'Outfit', cascade='delete', back_populates='user')

    def __init__(self, **kwargs):
        self.email = kwargs.get("email")
        self.username = kwargs.get('username')
        self.password_digest = bcrypt.hashpw(kwargs.get(
            "password").encode("utf8"), bcrypt.gensalt(rounds=13))
        self.renew_session()

    # Used to randomly generate session/update tokens
    def _urlsafe_base_64(self):
        return hashlib.sha1(os.urandom(64)).hexdigest()

    # Generates new tokens, and resets expiration time
    def renew_session(self):
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_password(self, password):
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

    # Checks if session token is valid and hasn't expired
    def verify_session_token(self, session_token):
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

    def verify_update_token(self, update_token):
        return update_token == self.update_token

    def serialize(self):
        return {
            "id": self.id,
            "username": self.username,
            "outfits": [o.serialize() for o in self.outfits]}


class Outfit(db.Model):
    __tablename__ = 'outfit'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    text = db.Column(db.String, nullable=False)
    public = db.Column(db.Integer, nullable=False)
    clean = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String, nullable=False)

    # many to one users
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='outfits')

    # many to many tags
    tags = db.relationship(
        'Tag', secondary=association_table, back_populates='outfits')

    # one to many comments
    comments = db.relationship('Comment', cascade='delete')

    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.text = kwargs.get('text')
        self.public = kwargs.get('public')
        self.clean = kwargs.get('clean')
        self.image_url = kwargs.get('image_url', '')
        self.user_id = kwargs.get('user_id')

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "public": self.public,
            "clean": self.clean,
            "image_url": self.image_url,
            "comments": [a.serialize2 for a in self.comments],
            "user": self.user.serialize(),
            "tags": [t.serialize() for t in self.tags]
        }

    def partial_serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "public": self.public,
            "clean": self.clean,
            "comments": [a.partial_serialize() for a in self.comments],
            "image_url": self.image_url,
            "tags": [t.serialize() for t in self.tags]
        }

    def serialize_no_comments(self):
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "public": self.public,
            "clean": self.clean,
            "image_url": self.image_url
        }


class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    # many to many outfits
    outfits = db.relationship(
        'Outfit', secondary=association_table, back_populates='tags')

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name
        }


class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)

    # many to one
    user = db.Column(db.Integer, db.ForeignKey('user.id'))
    outfit = db.Column(db.Integer, db.ForeignKey('outfit.id'))

    def __init__(self, **kwargs):
        self.text = kwargs.get('text')
        self.user_id = kwargs.get('user')

    def serialize(self):
        return {
            "id": self.id,
            "user": self.user,
            "text": self.text,
            "outfit": Outfit.query.filter_by(id=self.outfit).first().serialize_no_comments()
        }

    def partial_serialize(self):
        return {
            "id": self.id,
            "user": self.user,
            "text": self.text
        }
