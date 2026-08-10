# Digest Session App

MVP веб-приложения для проведения дайджест-сессий: фокус-вопросы, живой поток сообщений, голосование и модерация.

## Стек

- Backend: FastAPI
- Frontend: Jinja2, HTML, CSS, JavaScript
- Database: SQLite
- ORM: SQLAlchemy
- Auth: email/password для администратора и модератора
- Участники: вход по email без пароля

## Установка

```bash
cd discussion_club_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

```bash
python run.py
```

Приложение будет доступно по адресу:

```text
http://127.0.0.1:8000
```

## Запуск в Docker

```bash
docker compose up -d --build
```

Приложение будет доступно по адресу:

```text
http://127.0.0.1:8000
```

SQLite-база хранится в Docker volume `digest_session_data`, поэтому данные переживают пересборку контейнера.

Остановить контейнер:

```bash
docker compose down
```

## База данных и seed-данные

SQLite-база `discussion_club.db` создаётся автоматически при первом запуске приложения.

При старте создаются:

- администратор: `admin@club.ru` / `admin123`
- модератор: `moderator@club.ru` / `moderator123`
- тестовая сессия: `Пульс финтех-инноваций`
- публичная ссылка: `http://127.0.0.1:8000/event/club-15july`
- подготовленные вопросы для участников

## Основные сценарии

Администратор:

1. Откройте `/login`.
2. Войдите как `admin@club.ru`.
3. Создавайте, редактируйте и удаляйте сессии.
4. Создавайте модераторов.
5. Открывайте статистику и страницу модерации мероприятия.

Модератор:

1. Откройте `/login`.
2. Войдите как `moderator@club.ru`.
3. Управляйте фокус-вопросами.
4. Проверяйте, отклоняйте, закрепляйте и переводите сообщения в фокус.
5. Экспортируйте вопросы и ответы в CSV.

Участник:

1. Откройте `/event/club-15july`.
2. Укажите email.
3. Ответьте на подготовленные вопросы.
4. Отправьте вопрос спикеру.
5. Голосуйте за вопросы других участников.

## API

Участник:

- `POST /api/events/{event_id}/participants`
- `GET /api/events/{event_id}/prepared-questions`
- `POST /api/prepared-questions/{question_id}/answers`
- `POST /api/events/{event_id}/live-questions`
- `GET /api/events/{event_id}/live-questions`
- `POST /api/live-questions/{question_id}/vote`

Модератор:

- `POST /api/events/{event_id}/prepared-questions`
- `PATCH /api/prepared-questions/{question_id}`
- `DELETE /api/prepared-questions/{question_id}`
- `GET /api/events/{event_id}/moderation/live-questions`
- `PATCH /api/live-questions/{question_id}/status`
- `PATCH /api/live-questions/{question_id}/pin`
- `PATCH /api/live-questions/{question_id}/comment`

Администратор:

- `POST /api/events`
- `PATCH /api/events/{event_id}`
- `DELETE /api/events/{event_id}`
- `GET /api/events/{event_id}/stats`

## Примечания для MVP

- Авторизация простая и хранит идентификатор пользователя в cookie.
- Для продакшена нужно добавить CSRF-защиту, HTTPS, полноценные миграции и настройку секретного ключа.
- Живые списки обновляются polling-запросами каждые 5 секунд.
