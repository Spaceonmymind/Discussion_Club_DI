# Discussion Club App

MVP веб-приложения для сопровождения выступлений и дискуссий.

## Стек

- Backend: FastAPI
- Frontend: Jinja2, HTML, CSS, JavaScript
- Database: SQLite
- ORM: SQLAlchemy
- Auth: email/password для администратора и модератора
- Участники: вход по имени или анонимно без пароля

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

## База данных и seed-данные

SQLite-база `discussion_club.db` создаётся автоматически при первом запуске приложения.

При старте создаются:

- администратор: `admin@club.ru` / `admin123`
- модератор: `moderator@club.ru` / `moderator123`
- тестовое мероприятие: `Дискуссионный клуб`
- публичная ссылка: `http://127.0.0.1:8000/event/club-15july`
- подготовленные вопросы для участников

## Основные сценарии

Администратор:

1. Откройте `/login`.
2. Войдите как `admin@club.ru`.
3. Создавайте, редактируйте и удаляйте мероприятия.
4. Создавайте модераторов.
5. Открывайте статистику и страницу модерации мероприятия.

Модератор:

1. Откройте `/login`.
2. Войдите как `moderator@club.ru`.
3. Управляйте подготовленными вопросами.
4. Одобряйте, отклоняйте, закрепляйте и переводите вопросы в обсуждение.
5. Экспортируйте вопросы и ответы в CSV.

Участник:

1. Откройте `/event/club-15july`.
2. Укажите имя или выберите анонимное участие.
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
