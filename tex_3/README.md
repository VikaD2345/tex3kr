# FastAPI Security — КР №3

> Система аутентификации и авторизации на FastAPI: JWT-токены, ролевая модель доступа (RBAC) и защита Swagger-документации.

---

## Быстрый старт

**Клонировать репозиторий**
```bash
git clone https://github.com/AGUGIs/TRSP_kr3_chelyshev
```
**Создать и активировать виртуальное окружение**
```bash
python -m venv venv
.\venv\Scripts\activate
```
**Поставить зависимости**
```bash
pip install -r requirements.txt
```
**Скопировать файл с переменными окружения**
```bash
copy .env.example .env
```
**Запустить сервер**
```bash
uvicorn main:app --reload
```

---

## Примеры запросов

#### Базовая аутентификация *(Задание 6.1)*
```bash
curl -u admin:secret http://localhost:8000/login-basic        # 200 OK
curl -u wrong:wrong  http://localhost:8000/login-basic        # 401 Unauthorized
```
#### Регистрация и вход с хешированием *(Задание 6.2)*
```bash
# Регистрация
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"alice\",\"password\":\"securepass123\"}"
# Вход
curl -u alice:securepass123 http://localhost:8000/login
```
#### JWT-аутентификация *(Задания 6.4–6.5)*
```bash
# Получить токен
curl -X POST http://localhost:8000/login-jwt \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"alice\",\"password\":\"securepass123\"}"
# Обратиться к защищённому ресурсу
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/protected_resource
```
#### CRUD — задачи Todo *(Задание 8.2)*
```bash
# Создать
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Купить молоко\",\"description\":\"2 литра\"}"
# Все задачи
curl http://localhost:8000/todos
# По ID
curl http://localhost:8000/todos/1
# Обновить
curl -X PUT http://localhost:8000/todos/1 \
  -H "Content-Type: application/json" \
  -d "{\"completed\":true}"
# Удалить
curl -X DELETE http://localhost:8000/todos/1
```
#### Ролевой доступ RBAC *(Задание 7.1)*
```bash
curl -H "Authorization: Bearer YOUR_TOKEN"  http://localhost:8000/user-area    # для всех
curl -H "Authorization: Bearer ADMIN_TOKEN" http://localhost:8000/admin-panel  # только admin
```

---

## Документация API

Доступна **только в режиме DEV**:

| Интерфейс  | URL                        | Доступ                                   |
|------------|----------------------------|------------------------------------------|
| Swagger UI | http://127.0.0.1:8000/docs | Basic Auth: `admin` / `secure_docs_pass` |
| ReDoc      | —                          | отключён                                 |

---

## Переменные окружения

| Переменная                        | Значение по умолчанию              | Описание                          |
|-----------------------------------|------------------------------------|-----------------------------------|
| `MODE`                            | `DEV`                              | Режим запуска (`DEV` / `PROD`)    |
| `DOCS_USER`                       | `admin`                            | Логин для доступа к документации  |
| `DOCS_PASSWORD`                   | `secure_docs_pass`                 | Пароль для доступа к документации |
| `JWT_SECRET`                      | `change_this_in_production_please` | Секретный ключ JWT                |
| `JWT_ALGORITHM`                   | `HS256`                            | Алгоритм подписи токена           |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                               | Время жизни токена (минуты)       |
| `DATABASE_URL`                    | `sqlite:///./control_work.db`      | Строка подключения к БД           |
