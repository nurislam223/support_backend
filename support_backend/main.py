import json
import logging
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, Response
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
import time

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Создаем таблицы в БД
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для логирования тела запроса и ответа
@app.middleware("http")
async def log_request_response_middleware(request: Request, call_next):
    # Логирование запроса
    start_time = time.time()

    # Получаем тело запроса
    body = await request.body()
    request_body = None
    if body:
        try:
            request_body = json.loads(body.decode())
        except:
            request_body = body.decode()

    # Логируем информацию о запросе
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request body: {request_body}")

    # Восстанавливаем тело запроса для дальнейшей обработки
    async def receive():
        return {'type': 'http.request', 'body': body}

    request._receive = receive

    # Обрабатываем запрос
    response = await call_next(request)

    # Логирование ответа
    process_time = time.time() - start_time

    # Получаем тело ответа
    response_body = b""
    if hasattr(response, 'body_iterator'):
        async for chunk in response.body_iterator:
            response_body += chunk

        # Восстанавливаем тело ответа
        response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

    # Парсим тело ответа
    response_body_parsed = None
    if response_body:
        try:
            response_body_parsed = json.loads(response_body.decode())
        except:
            response_body_parsed = response_body.decode()

    # Логируем информацию о ответе
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response body: {response_body_parsed}")
    logger.info(f"Process time: {process_time:.4f}s")
    logger.info("-" * 50)

    return response


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
async def read_home(request: Request):
    # Логируем запрос к корневому endpoint'у
    logger.info(f"Home page accessed from {request.client.host}")

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
    logger.info(f"Login attempt for username: {username}")

    user = authenticate_user(username, password)
    if not user:
        logger.warning(f"Failed login attempt for username: {username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = create_access_token(data={"sub": user["username"]})
    logger.info(f"Successful login for username: {username}")

    return {"access_token": token, "token_type": "bearer"}


### USERS ###
@app.post("/users/", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db),
                      current_user: dict = Depends(get_current_user)):
    logger.info(f"Creating new user: {user.name}")

    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"User created successfully: {db_user.id}")
    return db_user


@app.get("/users/", response_model=List[schemas.UserResponse])
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                     current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching users, skip: {skip}, limit: {limit}")

    users = db.query(models.User).offset(skip).limit(limit).all()
    logger.info(f"Found {len(users)} users")

    return users


@app.get("/users/{user_id}", response_model=schemas.UserResponse)
async def read_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching user with ID: {user_id}")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"User found: {user_id}")
    return user


@app.put("/users/{user_id}", response_model=schemas.UserResponse)
async def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db),
                      current_user: dict = Depends(get_current_user)):
    logger.info(f"Updating user with ID: {user_id}")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        logger.warning(f"User not found for update: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user.dict().items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)

    logger.info(f"User updated successfully: {user_id}")
    return db_user


@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"Deleting user with ID: {user_id}")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        logger.warning(f"User not found for deletion: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()

    logger.info(f"User deleted successfully: {user_id}")
    return {"detail": "User deleted"}


### PROFILES ###
@app.post("/profiles/", response_model=schemas.ProfileResponse)
async def create_profile(profile: schemas.ProfileCreate, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    logger.info(f"Creating profile for user: {profile.user_id}")

    db_profile = models.Profile(**profile.dict())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)

    logger.info(f"Profile created successfully: {db_profile.id}")
    return db_profile


@app.get("/profiles/{profile_id}", response_model=schemas.ProfileResponse)
async def read_profile(profile_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching profile with ID: {profile_id}")

    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile:
        logger.warning(f"Profile not found: {profile_id}")
        raise HTTPException(status_code=404, detail="Profile not found")

    logger.info(f"Profile found: {profile_id}")
    return profile


@app.put("/profiles/{profile_id}", response_model=schemas.ProfileResponse)
async def update_profile(profile_id: int, profile: schemas.ProfileUpdate, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    logger.info(f"Updating profile with ID: {profile_id}")

    db_profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not db_profile:
        logger.warning(f"Profile not found for update: {profile_id}")
        raise HTTPException(status_code=404, detail="Profile not found")

    for key, value in profile.dict().items():
        setattr(db_profile, key, value)

    db.commit()
    db.refresh(db_profile)

    logger.info(f"Profile updated successfully: {profile_id}")
    return db_profile


@app.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: int, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    logger.info(f"Deleting profile with ID: {profile_id}")

    db_profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not db_profile:
        logger.warning(f"Profile not found for deletion: {profile_id}")
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(db_profile)
    db.commit()

    logger.info(f"Profile deleted successfully: {profile_id}")
    return {"detail": "Profile deleted"}


### ORDERS ###
@app.post("/orders/", response_model=schemas.OrderResponse)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db),
                       current_user: dict = Depends(get_current_user)):
    logger.info(f"Creating order for user: {order.user_id}")

    db_order = models.Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    logger.info(f"Order created successfully: {db_order.id}")
    return db_order


@app.get("/orders/{order_id}", response_model=schemas.OrderResponse)
async def read_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching order with ID: {order_id}")

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        logger.warning(f"Order not found: {order_id}")
        raise HTTPException(status_code=404, detail="Order not found")

    logger.info(f"Order found: {order_id}")
    return order


@app.get("/users/{user_id}/orders", response_model=List[schemas.OrderResponse])
async def read_orders_by_user(user_id: int, db: Session = Depends(get_db),
                              current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching orders for user: {user_id}")

    orders = db.query(models.Order).filter(models.Order.user_id == user_id).all()
    logger.info(f"Found {len(orders)} orders for user: {user_id}")

    return orders


@app.put("/orders/{order_id}", response_model=schemas.OrderResponse)
async def update_order(order_id: int, order: schemas.OrderUpdate, db: Session = Depends(get_db),
                       current_user: dict = Depends(get_current_user)):
    logger.info(f"Updating order with ID: {order_id}")

    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        logger.warning(f"Order not found for update: {order_id}")
        raise HTTPException(status_code=404, detail="Order not found")

    for key, value in order.dict().items():
        setattr(db_order, key, value)

    db.commit()
    db.refresh(db_order)

    logger.info(f"Order updated successfully: {order_id}")
    return db_order


@app.delete("/orders/{order_id}")
async def delete_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"Deleting order with ID: {order_id}")

    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        logger.warning(f"Order not found for deletion: {order_id}")
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(db_order)
    db.commit()

    logger.info(f"Order deleted successfully: {order_id}")
    return {"detail": "Order deleted"}