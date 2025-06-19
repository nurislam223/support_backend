from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import SessionLocal, engine
from auth import (
    get_current_user,
    create_access_token,
    authenticate_user
)
from logger import log_action
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

# Создаем таблицы в БД
models.Base.metadata.create_all(bind=engine)

# CORS
middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
]

app = FastAPI(middleware=middleware)

# Подключаем мониторинг Prometheus
Instrumentator().instrument(app).expose(app)

# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_home():
    html_content = """
    <html>
        <head>
            <title>Support Backend API</title>
        </head>
        <body>
            <h1>Добро пожаловать в API технической поддержки!</h1>
            <p>Этот сервис позволяет управлять пользователями, аутентифицироваться и логировать действия.</p>

            <h2>Доступные эндпоинты:</h2>
            <ul>
                <li><strong>POST /token</strong> — Получить JWT-токен по логину и паролю</li>
                <li><strong>POST /users/</strong> — Создать нового пользователя (требуется токен)</li>
                <li><strong>GET /users/</strong> — Получить список пользователей (требуется токен)</li>
                <li><strong>GET /users/{user_id}</strong> — Получить пользователя по ID (требуется токен)</li>
                <li><strong>PUT /users/{user_id}</strong> — Обновить данные пользователя (требуется токен)</li>
                <li><strong>DELETE /users/{user_id}</strong> — Удалить пользователя (требуется токен)</li>
                <li><strong>GET /metrics</strong> — Метрики Prometheus для мониторинга</li>
            </ul>

            <h2>Полезные ссылки:</h2>
            <ul>
                <li><a href="/docs">Swagger UI</a> — интерактивная документация API</li>
                <li><a href="/redoc">ReDoc</a> — альтернативная документация</li>
            </ul>

            <p><strong>Аутентификация:</strong> Используйте <code>/token</code> с тестовыми данными:<br>
               username: <code>admin</code>, password: <code>secret</code></p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/token")
def login(username: str, password: str):
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_action(current_user["username"], "create_user", f"Email: {user.email}")
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/", response_model=List[schemas.UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_action(current_user["username"], "read_users", f"Skip: {skip}, Limit: {limit}")
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_action(current_user["username"], "get_user_by_id", f"ID: {user_id}")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_action(current_user["username"], "update_user", f"ID: {user_id}")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user.dict().items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_action(current_user["username"], "delete_user", f"ID: {user_id}")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"detail": "User deleted"}

