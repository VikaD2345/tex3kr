"""Утилиты аутентификации и безопасности."""

import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic_settings import BaseSettings, SettingsConfigDict

from models import UserInDB, UserRole


# === Настройки ===

class Settings(BaseSettings):
    """Конфигурация приложения."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    MODE: str = "DEV"
    DOCS_USER: str = "admin"
    DOCS_PASSWORD: str = "secure_docs_pass"

    JWT_SECRET: str = "change_this_in_production_please"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()

# === Password Hashing (Задание 6.2) ===

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль против хеша."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Генерирует хеш пароля."""
    return pwd_context.hash(password)


# === In-memory DB для заданий 6.1-6.5 ===

fake_users_db: dict[str, UserInDB] = {}

# === Basic Auth Dependency (Задание 6.1-6.2) ===

security_basic = HTTPBasic()


def auth_user_basic(credentials: Annotated[HTTPBasicCredentials, Depends(security_basic)]) -> str:
    """
    Задание 6.1: Базовая аутентификация.
    Возвращает username при успехе, иначе 401.
    """
    # Для задания 6.1 — простая проверка
    if credentials.username == "admin" and credentials.password == "secret":
        return credentials.username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


def auth_user(credentials: Annotated[HTTPBasicCredentials, Depends(security_basic)]) -> UserInDB:
    """
    Задание 6.2: Аутентификация с хешированием и защитой от тайминг-атак.
    """
    # Защита от тайминг-атак при сравнении username
    username_bytes = credentials.username.encode("utf-8")

    user = None
    for stored_username in fake_users_db:
        stored_bytes = stored_username.encode("utf-8")
        if secrets.compare_digest(username_bytes, stored_bytes):
            user = fake_users_db[stored_username]
            break

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Проверка пароля
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return user


# === JWT Utilities (Задание 6.4-6.5) ===

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Создаёт JWT токен."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Декодирует и проверяет JWT токен."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# === JWT Bearer Dependency ===

security_bearer = HTTPBearer()


async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)],
) -> dict:
    """
    Задание 6.4: Извлекает и проверяет JWT из заголовка Authorization.
    Возвращает payload токена или 401.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


# === RBAC Dependency (Задание 7.1) ===

def require_role(*allowed_roles: UserRole):
    """
    Декоратор-фабрика для проверки роли пользователя.
    Используется как: dependencies=[Depends(require_role(UserRole.ADMIN))]
    """

    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", UserRole.GUEST)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


# === Docs Protection (Задание 6.3) ===

async def docs_auth(credentials: Annotated[HTTPBasicCredentials, Depends(security_basic)]):
    """
    Задание 6.3: Защита документации в DEV-режиме.
    """
    if settings.MODE not in ("DEV", "PROD"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid MODE: {settings.MODE}. Must be DEV or PROD",
        )

    if settings.MODE == "PROD":
        # В PROD документация полностью скрыта (возвращается 404 в main.py)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # DEV-режим: проверка учётных данных
    if not (
            secrets.compare_digest(credentials.username.encode(), settings.DOCS_USER.encode()) and
            secrets.compare_digest(credentials.password.encode(), settings.DOCS_PASSWORD.encode())
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid docs credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True