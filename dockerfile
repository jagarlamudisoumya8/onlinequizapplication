FROM python:3.14.5

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

RUN python manage.py collectstatic --noinput

EXPOSE 10000

CMD ["gunicorn","quizplatform.wsgi:application","--bind","0.0.0.0:10000"]