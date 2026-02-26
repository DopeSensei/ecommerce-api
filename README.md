# Ecommerce API

Backend portfolio project built with Django, Django REST Framework, PostgreSQL, and Docker Compose.

## Current Scope

- Custom user model (`api.User`)
- Core ecommerce entities:
  - `Product`
  - `Address`
  - `Order`
  - `OrderItem`
- Django admin setup for manual testing
- Development seed command: `populate_db`

## Tech Stack

- Python 3.12
- Django
- Django REST Framework
- PostgreSQL 16
- Docker / Docker Compose

## Run Locally (Docker)

1. Create `.env` in the project root.
2. Start containers:
   ```bash
   docker compose up -d
   ```
3. Run migrations:
   ```bash
   docker compose exec --user "$(id -u):$(id -g)" web python manage.py migrate
   ```
4. Create superuser:
   ```bash
   docker compose exec --user "$(id -u):$(id -g)" web python manage.py createsuperuser
   ```
5. Open admin:
   - `http://localhost:8000/admin/`

## Environment Variables

Use these keys in `.env`:

```env
DEBUG=1
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=ecommerce
DB_USER=ecommerce_user
DB_PASSWORD=ecommerce_pass
DB_HOST=db
DB_PORT=5432
```

## Seed Sample Data

```bash
docker compose exec --user "$(id -u):$(id -g)" web python manage.py populate_db
```

This creates:

- an `admin` user if missing
- one sample address
- several sample products
- sample orders and order items

## Key Design Decisions (Current)

- `settings.AUTH_USER_MODEL` is used for user relations to keep the app compatible with a custom user model.
- `Order.user` uses `SET_NULL` to preserve order history if the account is deleted.
- `shipping_address` and `billing_address` use `PROTECT` so referenced addresses cannot be deleted.
- `OrderItem.product` uses `PROTECT` to keep historical accounting data consistent.

## Next Planned Steps

- Add more necessary models and methods
- Add serializers and DRF views/viewsets
- Add authentication and permissions
- Add inventory/variant/payment/shipment models
- Add automated tests
