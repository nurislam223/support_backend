import json
import logging
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import SessionLocal, engine
from auth import get_current_user, create_access_token, authenticate_user
from logger import setup_logger
from fastapi.middleware.cors import CORSMiddleware
from middleware import log_requests_middleware
from prometheus_fastapi_instrumentator import Instrumentator

# === 1. Настройка логгера ===
setup_logger()

# === 2. Создание таблиц ===
models.Base.metadata.create_all(bind=engine)

# === 3. Создание приложения ===
app = FastAPI(
    title="Support Backend API",
    description="API for user management and support system",
    version="1.0.0"
)

# === 4. ПОДКЛЮЧАЕМ MIDDLEWARE В ПРАВИЛЬНОМ ПОРЯДКЕ ===

# ВАЖНО: логирующий middleware — первым!
app.middleware("http")(log_requests_middleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 5. Подключаем Prometheus ПОСЛЕ middleware ===
# Это добавит /metrics, но мы хотим, чтобы он тоже логировался
instrumentator = Instrumentator()
instrumentator.instrument(app)
# Вместо .expose(app), мы используем обычный маршрут, чтобы он прошёл через middleware
@app.get("/metrics")
def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# === 6. Зависимость для БД ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === 7. Маршруты ===
@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
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
async def login(request: Request, username: str, password: str):
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}


### USERS ###
@app.post("/users/", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db),
                      current_user: dict = Depends(get_current_user)):
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/")
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                     current_user: dict = Depends(get_current_user)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


@app.get("/users/{user_id}", response_model=schemas.UserResponse)
async def read_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=schemas.UserResponse)
async def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db),
                      current_user: dict = Depends(get_current_user)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user.dict().items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user

@app.patch("/users/{user_id}", response_model=schemas.UserResponse)
async def partial_update_user(
        user_id: int,
        user: schemas.UserUpdate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
    # Находим пользователя
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем только переданные поля (исключаем None значения)
    update_data = user.dict(exclude_unset=True)

    # Обновляем только переданные поля
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"detail": "User deleted"}


### PROFILES ###
@app.post("/profiles/", response_model=schemas.ProfileResponse)
async def create_profile(profile: schemas.ProfileCreate, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    db_profile = models.Profile(**profile.dict())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@app.get("/profiles/{profile_id}", response_model=schemas.ProfileResponse)
async def read_profile(profile_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.put("/profiles/{profile_id}", response_model=schemas.ProfileResponse)
async def update_profile(profile_id: int, profile: schemas.ProfileUpdate, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    db_profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for key, value in profile.dict().items():
        setattr(db_profile, key, value)

    db.commit()
    db.refresh(db_profile)
    return db_profile


@app.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: int, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    db_profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(db_profile)
    db.commit()
    return {"detail": "Profile deleted"}


### ORDERS ###
@app.post("/orders/", response_model=schemas.OrderResponse)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db),
                       current_user: dict = Depends(get_current_user)):
    db_order = models.Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


@app.get("/orders/{order_id}", response_model=schemas.OrderResponse)
async def read_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/users/{user_id}/orders", response_model=List[schemas.OrderResponse])
async def read_orders_by_user(user_id: int, db: Session = Depends(get_db),
                              current_user: dict = Depends(get_current_user)):
    orders = db.query(models.Order).filter(models.Order.user_id == user_id).all()
    return orders


@app.put("/orders/{order_id}", response_model=schemas.OrderResponse)
async def update_order(order_id: int, order: schemas.OrderUpdate, db: Session = Depends(get_db),
                       current_user: dict = Depends(get_current_user)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    for key, value in order.dict().items():
        setattr(db_order, key, value)

    db.commit()
    db.refresh(db_order)
    return db_order


@app.delete("/orders/{order_id}")
async def delete_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(db_order)
    db.commit()
    return {"detail": "Order deleted"}