## Info
FastApi blogpost project. <br>
Servers both api and frontend.

### API documentation
view at: https://blogpost.fastapicloud.dev/docs

### Frontend Deployment
Deployed in fastapi cloud. <br>
live at https://blogpost.fastapicloud.dev

### Create a user
curl -X POST https://blogpost.fastapicloud.dev/api/users \
  -H "Content-Type: application/json" \
  -d '{"username": "you", "email": "you@example.com", "password": "secret"}'

### Get access token
curl -X POST https://blogpost.fastapicloud.dev/api/users/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=you&password=secret"

### Create a post
curl -X POST https://blogpost.fastapicloud.dev/api/posts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Hello", "content": "My first post!"}'