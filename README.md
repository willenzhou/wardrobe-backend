# Wardrobe
## An Outfit Manager

### ROUTES

/users/ 
GET 
returns all users

/outfits/
GET
returns all outfits

/outfits/<int:outfit_id>/
GET
returns specific outfit

/outfits/
POST
add a new outfit
{
  "title": string,
  "text": string,
  "public": bool,
  "clean": bool,
  "image_url": string,
  "user_id": int
}

/outfits/<int:outfit_id>/
POST
updates an existing outfit
{
  "title": string,
  "text": string,
  "public": bool,
  "clean": bool,
  "image_url": string,
  "user_id": int
}

/outfits/<int:outfit_id>/
DELETE
deletes an outfit

/outfits/<int:outfit_id>/tag/
POST
adds a tag to an outfit
{
  "tag_name": string
}

/outfits/<int:outfit_id>/tag/
DELETE
removes a tag from an outfit
{
  "tag_name": string
}

/comment/<int:outfit_id>/
POST
adds a comment to an outfit
{
  "text": string, 
  "user_id": int
}

/comment/<int:comment_id>/
DELETE
deletes comment