FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# proje tamamlaninca prdocution compose yaz;
# CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
# gunicorn + nginx
# static file handling
