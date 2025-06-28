from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import SessionLocal, engine
from auth import get_current_user, create_access_token, authenticate_user
import logger  
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from middleware import log_requests_middleware
from prometheus_fastapi_instrumentator import Instrumentator

# Создаем таблицы в БД
models.Base.metadata.create_all(bind=engine)

log_request = logger.log_request

logger = logger.setup_logger()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрируем middleware для логирования
app.middleware("http")(log_requests_middleware)

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
    log_request(user["username"], "POST", "/token", status=200, details="Login successful")
    return {"access_token": token, "token_type": "bearer"}


### USERS ###


@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "POST", "/users/", body=user.dict())
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/", response_model=List[schemas.UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "GET", "/users/", details=f"Skip: {skip}, Limit: {limit}")
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "GET", f"/users/{user_id}", details=f"ID: {user_id}")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "PUT", f"/users/{user_id}", body=user.dict())
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
    log_request(current_user["username"], "DELETE", f"/users/{user_id}", details=f"ID: {user_id}")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"detail": "User deleted"}


### PROFILES ###

@app.post("/profiles/", response_model=schemas.ProfileResponse)
def create_profile(profile: schemas.ProfileCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "POST", "/profiles/", body=profile.dict())
    db_profile = models.Profile(**profile.dict())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

@app.get("/profiles/{profile_id}", response_model=schemas.ProfileResponse)
def read_profile(profile_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "GET", f"/profiles/{profile_id}", details=f"ID: {profile_id}")
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.put("/profiles/{profile_id}", response_model=schemas.ProfileResponse)
def update_profile(profile_id: int, profile: schemas.ProfileUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "PUT", f"/profiles/{profile_id}", body=profile.dict())
    db_profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for key, value in profile.dict().items():
        setattr(db_profile, key, value)

    db.commit()
    db.refresh(db_profile)
    return db_profile

@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "DELETE", f"/profiles/{profile_id}", details=f"ID: {profile_id}")
    db_profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(db_profile)
    db.commit()
    return {"detail": "Profile deleted"}


### ORDERS ###

@app.post("/orders/", response_model=schemas.OrderResponse)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "POST", "/orders/", body=order.dict())
    db_order = models.Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders/{order_id}", response_model=schemas.OrderResponse)
def read_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "GET", f"/orders/{order_id}", details=f"ID: {order_id}")
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/users/{user_id}/orders", response_model=List[schemas.OrderResponse])
def read_orders_by_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "GET", f"/users/{user_id}/orders", details=f"User ID: {user_id}")
    orders = db.query(models.Order).filter(models.Order.user_id == user_id).all()
    return orders

@app.put("/orders/{order_id}", response_model=schemas.OrderResponse)
def update_order(order_id: int, order: schemas.OrderUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "PUT", f"/orders/{order_id}", body=order.dict())
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    for key, value in order.dict().items():
        setattr(db_order, key, value)

    db.commit()
    db.refresh(db_order)
    return db_order

@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_request(current_user["username"], "DELETE", f"/orders/{order_id}", details=f"ID: {order_id}")
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(db_order)
    db.commit()
    return {"detail": "Order deleted"}

