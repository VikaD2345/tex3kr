"""Главный файл приложения FastAPI."""

import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import init_db, get_db_cursor, get_db_connection
from models import (
    User, UserInDB, UserResponse, Token, LoginRequest,
    TodoCreate, TodoUpdate, TodoResponse, UserRole
)
from auth import (
    settings, auth_user_basic, auth_user, get_current_user,
    create_access_token, verify_password, get_password_hash,
    fake_users_db, require_role, docs_auth, security_basic
)

# === Инициализация приложения ===

app = FastAPI(
    title="Control Work API",
    description="Решение контрольной работы №3 по безопасности FastAPI",
    version="1.0.0",
    # В зависимости от режима настраиваем документацию
    docs_url=None if settings.MODE == "PROD" else "/docs",
    redoc_url=None,  # Скрываем redoc всегда (по ТЗ)
    openapi_url=None if settings.MODE == "PROD" else "/openapi.json",
)

# === Rate Limiter (Задание 6.5) ===

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# === Задание 6.1: Простая базовая аутентификация ===

@app.get("/login-basic", tags=["6.1 Basic Auth"])
@limiter.limit("10/minute")
def login_basic(
        request: Request,
        username: Annotated[str, Depends(auth_user_basic)]
):
    """
    Задание 6.1: Защищённая конечная точка с базовой аутентификацией.

    Тест:
    # Неправильные данные (браузер запросит ввод)
    curl -u wrong:wrong http://localhost:8000/login-basic

    # Правильные данные
    curl -u admin:secret http://localhost:8000/login-basic
    """
    return {"message": "You got my secret, welcome"}


# === Задание 6.2: Регистрация и логин с хешированием ===

@app.post("/register", status_code=status.HTTP_201_CREATED, tags=["6.2 Hash Auth"])
@limiter.limit("1/minute")  # Защита от спама
def register(
        request: Request,
        user: User
):
    """
    Регистрация нового пользователя с хешированием пароля.

    curl -X POST -H "Content-Type: application/json" \
      -d '{"username":"user1","password":"correctpass"}' \
      http://localhost:8000/register
    """
    # Проверка на существование
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )

    # Хеширование и сохранение
    user_in_db = UserInDB(
        username=user.username,
        hashed_password=get_password_hash(user.password)
    )
    fake_users_db[user.username] = user_in_db

    return {"message": "New user created", "username": user.username}


@app.get("/login", tags=["6.2 Hash Auth"])
@limiter.limit("5/minute")  # Ограничение попыток входа
def login(
        request: Request,
        current_user: Annotated[UserInDB, Depends(auth_user)]
):
    """
    Вход с проверкой хеша пароля.

    # Успешный вход
    curl -u user1:correctpass http://localhost:8000/login

    # Неверный пароль
    curl -u user1:wrongpass http://localhost:8000/login
    """
    return {"message": f"Welcome, {current_user.username}!"}


# === Задание 6.3: Защита документации по режиму ===

# Переопределяем стандартные эндпоинты документации
if settings.MODE == "DEV":
    @app.get("/docs", include_in_schema=False, dependencies=[Depends(docs_auth)])
    async def custom_docs():
        """DEV: Документация с базовой аутентификацией."""
        # Перенаправляем на стандартную документацию
        # (FastAPI сам обрабатывает /docs, мы только защищаем доступ)
        raise HTTPException(status_code=307, headers={"Location": "/docs"})


    @app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(docs_auth)])
    async def custom_openapi():
        """DEV: Схема OpenAPI с защитой."""
        # Возвращаем стандартную схему
        return app.openapi()


# В PROD-режиме эндпоинты документации уже отключены через FastAPI(..., docs_url=None)


# === Задание 6.4-6.5: JWT аутентификация ===

@app.post("/login-jwt", response_model=Token, tags=["6.4-6.5 JWT"])
@limiter.limit("5/minute")
def login_jwt(request: Request, credentials: LoginRequest):
    """
    JWT-аутентификация: выдача токена при успешном входе.

    Пример запроса:
    curl -X POST -H "Content-Type: application/json" \
      -d '{"username":"alice","password":"qwerty123"}' \
      http://localhost:8000/login-jwt
    """
    # Поиск пользователя (защита от тайминг-атак)
    username_bytes = credentials.username.encode("utf-8")
    user = None

    for stored_username in fake_users_db:
        if secrets.compare_digest(username_bytes, stored_username.encode("utf-8")):
            user = fake_users_db[stored_username]
            break

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Проверка пароля
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization failed"
        )

    # Генерация токена
    access_token = create_access_token(
        data={"sub": user.username, "role": getattr(user, "role", UserRole.USER)},
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/protected_resource", tags=["6.4-6.5 JWT"])
def protected_resource(current_user: dict = Depends(get_current_user)):
    """
    Защищённый ресурс, доступный только с валидным JWT.

    curl -H "Authorization: Bearer <token>" http://localhost:8000/protected_resource
    """
    return {"message": f"Access granted, {current_user.get('sub')}!"}


# === Задание 7.1: Ролевой доступ (RBAC) ===

@app.get("/admin-panel", tags=["7.1 RBAC"], dependencies=[Depends(require_role(UserRole.ADMIN))])
def admin_panel(current_user: dict = Depends(get_current_user)):
    """Доступно только администраторам."""
    return {"message": f"Welcome to admin panel, {current_user.get('sub')}!"}


@app.get("/user-area", tags=["7.1 RBAC"], dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.USER))])
def user_area(current_user: dict = Depends(get_current_user)):
    """Доступно администраторам и обычным пользователям."""
    return {"message": f"Hello, {current_user.get('sub')} (role: {current_user.get('role')})!"}


@app.get("/public-area", tags=["7.1 RBAC"],
         dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.USER, UserRole.GUEST))])
def public_area(current_user: dict = Depends(get_current_user)):
    """Доступно всем аутентифицированным пользователям."""
    return {"message": "Public area accessed"}


# === Задание 8.1: Регистрация в БД ===

@app.post("/register-db", status_code=status.HTTP_201_CREATED, tags=["8.1 SQLite Users"])
def register_db(user: User):
    """
    Регистрация пользователя в SQLite (пароль пока в открытом виде по ТЗ).

    curl -X POST -H "Content-Type: application/json" \
      -d '{"username":"test_user","password":"12345"}' \
      http://localhost:8000/register-db
    """
    with get_db_cursor() as cursor:
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (user.username, user.password)  # По ТЗ — без шифрования
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists in database"
            )

    return {"message": "User registered successfully!"}


# === Задание 8.2: CRUD для Todo ===

@app.post("/todos", response_model=TodoResponse, status_code=status.HTTP_201_CREATED, tags=["8.2 Todo CRUD"])
def create_todo(todo: TodoCreate, owner: str = "default_user"):
    """Создание новой задачи."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "INSERT INTO todos (title, description, completed, owner_username) VALUES (?, ?, ?, ?)",
            (todo.title, todo.description, False, owner)
        )
        todo_id = cursor.lastrowid

    return TodoResponse(
        id=todo_id,
        title=todo.title,
        description=todo.description,
        completed=False,
        owner_username=owner
    )


@app.get("/todos/{todo_id}", response_model=TodoResponse, tags=["8.2 Todo CRUD"])
def get_todo(todo_id: int):
    """Получение задачи по ID."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM todos WHERE id = ?", (todo_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Todo not found")

    return TodoResponse(**dict(row))


@app.put("/todos/{todo_id}", response_model=TodoResponse, tags=["8.2 Todo CRUD"])
def update_todo(todo_id: int, todo_update: TodoUpdate):
    """Обновление задачи."""
    with get_db_connection() as conn:
        # Проверяем существование
        existing = conn.execute(
            "SELECT * FROM todos WHERE id = ?", (todo_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Todo not found")

        # Формируем динамический UPDATE
        updates = []
        values = []
        if todo_update.title is not None:
            updates.append("title = ?")
            values.append(todo_update.title)
        if todo_update.description is not None:
            updates.append("description = ?")
            values.append(todo_update.description)
        if todo_update.completed is not None:
            updates.append("completed = ?")
            values.append(todo_update.completed)

        if updates:
            values.append(todo_id)
            conn.execute(
                f"UPDATE todos SET {', '.join(updates)} WHERE id = ?",
                values
            )
            conn.commit()

        # Возвращаем обновлённую запись
        row = conn.execute(
            "SELECT * FROM todos WHERE id = ?", (todo_id,)
        ).fetchone()
        return TodoResponse(**dict(row))


@app.delete("/todos/{todo_id}", tags=["8.2 Todo CRUD"])
def delete_todo(todo_id: int):
    """Удаление задачи."""
    with get_db_cursor() as cursor:
        result = cursor.execute(
            "DELETE FROM todos WHERE id = ?", (todo_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Todo not found")

    return {"message": "Todo deleted successfully"}


@app.get("/todos", response_model=list[TodoResponse], tags=["8.2 Todo CRUD"])
def list_todos(owner: str | None = None):
    """Список задач (опционально с фильтрацией по владельцу)."""
    with get_db_connection() as conn:
        if owner:
            rows = conn.execute(
                "SELECT * FROM todos WHERE owner_username = ?", (owner,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM todos").fetchall()

    return [TodoResponse(**dict(row)) for row in rows]


# === Health check ===

@app.get("/health", tags=["System"])
def health_check():
    """Проверка работоспособности приложения."""
    return {
        "status": "ok",
        "mode": settings.MODE,
        "docs_protected": settings.MODE == "DEV"
    }


# === Инициализация при старте ===

@app.on_event("startup")
def on_startup():
    """Инициализация БД при запуске."""
    init_db()
    print(f"🚀 App started in {settings.MODE} mode")
    if settings.MODE == "DEV":
        print(f"🔐 Docs protected: /docs, /openapi.json (user: {settings.DOCS_USER})")
    else:
        print("🔒 Docs disabled in PROD mode")


# === Обработчик ошибок (опционально) ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Кастомный обработчик для добавления WWW-Authenticate при 401."""
    if exc.status_code == 401 and "WWW-Authenticate" not in exc.headers:
        exc.headers["WWW-Authenticate"] = "Basic"
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )