Run the docker container
```
docker compose up -d --build
docker compose logs -f app 
```

To check the database
```
docker compose exec db psql -U minerva -d minerva -c "SELECT id, username, password_hash FROM users;"
```
