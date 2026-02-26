docker compose exec --user "$(id -u):$(id -g)" web python manage.py <komut>


docker compose up -d
docker compose ps (web Up olmali)

docker compose exec --user "$(id -u):$(id -g)" web python manage.py createsuperuser