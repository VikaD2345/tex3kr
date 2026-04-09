# Контрольная работа №3 — Безопасность FastAPI

Реализация системы аутентификации и авторизации в FastAPI с поддержкой JWT, ролевого доступа (RBAC) и защиты документации.


## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <https://github.com/AGUGIs/TRSP_kr3_chelyshev>
```
### 2. Создание виртуального окружения

```bash
python -m venv venv
.\venv\Scripts\activate
```
### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```
### 4. Настройка переменных окружения

```bash
copy .env.example .env
```
5. Запуск приложения

```bash
uvicorn main:app --reload
```


## Тестирование эндпоинтов

### 1. Базовая аутентификация (Задание 6.1)

```bash
# Успешный вход
curl -u admin:secret http://localhost:8000/login-basic

# Неверные данные (вернёт 401)
curl -u wrong:wrong http://localhost:8000/login-basic
```
### 2. Регистрация и вход с хешированием (Задание 6.2)

```bash
# Регистрация нового пользователя
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"alice\",\"password\":\"securepass123\"}"

# Вход с проверкой пароля
curl -u alice:securepass123 http://localhost:8000/login
```
### 3. JWT аутентификация (Задание 6.4-6.5)

```bash
# Получение JWT токена
curl -X POST http://localhost:8000/login-jwt \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"alice\",\"password\":\"securepass123\"}"

# Доступ к защищённому ресурсу (замените YOUR_TOKEN)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/protected_resource
```
### 4. CRUD операции с Todo (Задание 8.2)

```bash
# Создание задачи
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Купить молоко\",\"description\":\"2 литра\"}"

# Получить все задачи
curl http://localhost:8000/todos

# Получить задачу по ID
curl http://localhost:8000/todos/1

# Обновить задачу
curl -X PUT http://localhost:8000/todos/1 \
  -H "Content-Type: application/json" \
  -d "{\"completed\":true}"

# Удалить задачу
curl -X DELETE http://localhost:8000/todos/1
```
### 5. Ролевой доступ (RBAC) (Задание 7.1)

```bash
# Доступ к пользовательской зоне
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/user-area

# Доступ к админ-панели (требуется роль admin)
curl -H "Authorization: Bearer ADMIN_TOKEN" http://localhost:8000/admin-panel
```

## Документация API
В режиме DEV документация доступна по адресам:
Swagger UI: http://127.0.0.1:8000/docs
(требуется базовая аутентификация: admin / secure_docs_pass)
ReDoc: отключён

## Переменные окружения
```bash
# Режим работы: DEV или PROD
MODE=DEV

# Данные для защиты документации (только DEV)
DOCS_USER=admin
DOCS_PASSWORD=secure_docs_pass

# Секретный ключ для JWT
JWT_SECRET=change_this_in_production_please
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# База данных
DATABASE_URL=sqlite:///./control_work.db
```
