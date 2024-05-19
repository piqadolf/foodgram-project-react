# Foodgram

### Описание проекта:
Foodgram — это сервис для публикации рецептов с возможностью подписываться на авторов, добавлять рецепты в избранное, список покупок и скачивать его в удобном формате.

### Стек технологий:
- Python 3.9.10
- Django 3.2.16
- Django REST framework 3.12.4
- Nginx
- Docker
- Postgres 13.0
- Djoser 2.1.0

  
## Деплой приложения на сервере
1. На сервере создайте директорию для приложения:
    ```bash
    mkdir foodgram/infra
    ```
2. В папку _infra_ скопируйте файл `docker-compose.production.yml`.
3. Там же создайте файл `.env` со следующими переменными:
   ```
   SECRET_KEY=
   ALLOWED_HOSTS=
   ENGINE=django.db.backends.postgresql
   DB_NAME=
   POSTGRES_USER=
   POSTGRES_PASSWORD=
   POSTGRES_DB=
   DB_PORT=5432
   ```
4. Теперь соберем и запустим контейнер:
   ```bash
   sudo docker compose up --build
   ```
5. В новом окне терминала создадим супер пользователя:
   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```
6. Контейнер _nginx_ настроен на порт 7000.


### Примеры нескольких запросов и ответов к API:

1. Получение списка рецептов: \
   **GET** `/api/recipes/` \
   REQUEST
   ```json
   {
     "count": 123,
     "next": "http://127.0.0.1:8000/api/recipes/?page=2",
     "previous": "http://127.0.0.1:8000/api/recipes/?page=1",
     "results": [
       {
         "id": 0,
         "tags": [
           {
             "id": 0,
             "name": "Завтрак",
             "color": "green",
             "slug": "breakfast"
           }
         ],
         "author": {
           "email": "ya@ya.ru",
           "id": 0,
           "username": "user",
           "first_name": "Ivan",
           "last_name": "Zivan",
           "is_subscribed": false
         },
         "ingredients": [
           {
             "id": 0,
             "name": "Курица",
             "measurement_unit": "г",
             "amount": 100
           }
         ],
         "is_favorited": false,
         "is_in_shopping_cart": false,
         "name": "string",
         "image": "https://backend:8080/media/image.jpeg",
         "text": "string",
         "cooking_time": 10
       }
     ]
   }
   ```
2. Регистрация пользователя: \
   **POST** `/api/users/` \
   RESPONSE
   ```json
   {
     "email": "ya@ya.ru",
     "username": "user",
     "first_name": "Ivan",
     "last_name": "Zivan",
     "password": "password"
   }
   ```
   REQUEST
   ```json
   {
   "email": "ya@ya.ru",
   "id": 0,
   "username": "user",
   "first_name": "Ivan",
   "last_name": "Zivan"
   }
   ```
3. Подписаться на пользователя: \
   **POST** `/api/users/{id}/subscribe/`
   REQUEST
   ```json
   {
     "email": "user@example.com",
     "id": 0,
     "username": "user",
     "first_name": "Ivan",
     "last_name": "Zivan",
     "is_subscribed": true,
     "recipes": [
       {
         "id": 0,
         "name": "string",
         "image": "https://backend:8080/media/image.jpeg",
         "cooking_time": 10
       }
     ],
     "recipes_count": 1
   }
   ```

### Автор и проект:

https://foodoodoo.hopto.org

[piqadolf](https://github.com/piqadolf)