"""Pydantic-модели для валидации данных."""

from enum import Enum
from pydantic import BaseModel, Field, EmailStr


# === Задание 6.2: Модели пользователей ===

class UserBase(BaseModel):
    """Базовая модель пользователя."""
    username: str = Field(..., min_length=3, max_length=50)


class User(UserBase):
    """Модель для регистрации (с паролем)."""
    password: str = Field(..., min_length=6)


class UserInDB(UserBase):
    """Модель для хранения в БД (с хешем)."""
    hashed_password: str


class UserResponse(BaseModel):
    """Модель ответа при регистрации/логине."""
    message: str
    username: str | None = None


# === Задание 6.4-6.5: Модели для JWT ===

class Token(BaseModel):
    """Модель токена доступа."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Модель запроса на логин."""
    username: str
    password: str


# === Задание 7.1: Модели для RBAC ===

class UserRole(str, Enum):
    """Перечисление ролей."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserWithRole(UserBase):
    """Пользователь с ролью."""
    role: UserRole = UserRole.GUEST


# === Задание 8.2: Модель Todo ===

class TodoCreate(BaseModel):
    """Создание новой задачи."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class TodoUpdate(BaseModel):
    """Обновление задачи."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    completed: bool | None = None


class TodoResponse(BaseModel):
    """Ответ с задачей."""
    id: int
    title: str
    description: str | None
    completed: bool
    owner_username: str

    class Config:
        from_attributes = True