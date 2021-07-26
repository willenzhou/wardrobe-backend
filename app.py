import json
import os
from db import db
from db import Asset, User, Outfit, Tag, Comment
from flask import Flask
from flask import request

db_filename = "wardrobe.db"
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()


def success_response(data, code=200):
    return json.dumps({"success": True, "data": data}), code


def failure_response(message, code=404):
    return json.dumps({"success": False, "error": message}), code


@app.route('/')
def hello():
    return "Wardrobe!"


@app.route("/upload/", methods=["POST"])
def upload():
    body = json.loads(request.data)
    image_data = body.get("image_data")
    if image_data is None:
        return failure_response("no base64 url to be found")
    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()
    return success_response(asset.serialize(), 201)


# -- USER ROUTES -----------------------------------------------------------


@app.route("/users/")
def get_users():
    return success_response([u.serialize() for u in User.query.all()])


# -- OUTFIT ROUTES -----------------------------------------------------------


@app.route("/outfits/")
def get_outfits():
    return success_response([o.partial_serialize() for o in Outfit.query.all()])


@app.route("/outfits/<int:outfit_id>/")
def get_outfit(outfit_id):
    outfit = Outfit.query.filter_by(id=outfit_id).first()
    if outfit is None:
        return failure_response('Outfit not found')
    return success_response(outfit.partial_serialize())


@app.route("/outfits/", methods=["POST"])
def create_outfit():
    body = json.loads(request.data)
    user_id = body.get('user_id', '')
    # user = User.query.filter_by(id=user_id).first()
    # if user is None:
    #     return failure_response('User not given')
    new_outfit = Outfit(title=body.get('title', 'unnamed'),
                        text=body.get('text', ''),
                        public=body.get('public', False),
                        clean=body.get('clean', False),
                        image_url=body.get('image_url', ''),
                        user_id=user_id)
    db.session.add(new_outfit)
    db.session.commit()
    return success_response(new_outfit.partial_serialize(), 201)


@app.route("/outfits/<int:outfit_id>/", methods=["POST"])
def update_outfit(outfit_id):
    outfit = Outfit.query.filter_by(id=outfit_id).first()
    if outfit is None:
        return failure_response('Outfit not found')
    body = json.loads(request.data)
    outfit.title = body.get('title', outfit.title)
    outfit.text = body.get('text', outfit.text)
    outfit.public = body.get('public', outfit.public)
    outfit.clean = body.get('clean', outfit.clean)
    outfit.image_url = body.get('image_url', outfit.image_url)
    outfit.user_id = body.get('user_id', outfit.user_id)
    db.session.commit()
    return success_response(outfit.partial_serialize())


@app.route("/outfits/<int:outfit_id>/", methods=["DELETE"])
def delete(outfit_id):
    outfit = Outfit.query.filter_by(id=outfit_id).first()
    if outfit is None:
        return failure_response('Outfit not found')
    db.session.delete(outfit)
    db.session.commit()
    return success_response(outfit.partial_serialize())


# -- COMMENT ROUTES -----------------------------------------------------------


@app.route("/comment/<int:outfit_id>/", methods=["POST"])
def comment(outfit_id):
    body = json.loads(request.data)
    text = body.get("text")
    user_id = body.get('user_id', '')
    outfit = Outfit.query.filter_by(id=outfit_id).first()
    if outfit is None:
        return failure_response("Outfit not found")
    new_comment = Comment(text=text, outfit=outfit_id, user=user_id)
    db.session.add(new_comment)
    outfit.comments.append(new_comment)
    db.session.commit()
    return success_response(new_comment.serialize())


@app.route("/comment/<int:comment_id>/", methods=["DELETE"])
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if comment is None:
        return failure_response("Comment not found")
    db.session.delete(comment)
    db.session.commit()
    return success_response(comment.serialize())


# -- TAG ROUTES ------------------------------------------------------


@app.route("/outfits/<int:outfit_id>/tag/", methods=["POST"])
def assign_tag(outfit_id):
    outfit = Outfit.query.filter_by(id=outfit_id).first()
    if outfit is None:
        return failure_response('Outfit not found')
    body = json.loads(request.data)
    tag_name = body.get('tag_name')
    if tag_name is None:
        return failure_response('No tag name')
    tag = Tag.query.filter_by(name=tag_name).first()
    if tag is None:
        tag = Tag(
            name=tag_name
        )
    outfit.tags.append(tag)
    db.session.commit()
    return success_response(outfit.partial_serialize())


@app.route("/outfits/<int:outfit_id>/tag/", methods=["DELETE"])
def remove_tag(outfit_id):
    outfit = Outfit.query.filter_by(id=outfit_id).first()
    if outfit is None:
        return failure_response('Outfit not found')
    body = json.loads(request.data)
    tag_name = body.get('tag_name')
    if tag_name is None:
        return failure_response('No tag name')
    tag = Tag.query.filter_by(name=tag_name).first()
    if tag is not None:
        outfit.tags.remove(tag)
    db.session.commit()
    return success_response(outfit.partial_serialize())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
