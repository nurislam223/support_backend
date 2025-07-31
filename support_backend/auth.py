from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials

# Схема для Bearer токена
bearer_scheme = HTTPBearer()

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 3600

fake_users_db = {
    "admin": {
        "username": "admin",
        "password": "secret",
        "role": "admin"
    }
}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    request: Request,  # Добавляем request, чтобы сохранить юзера в state
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = fake_users_db.get(username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # 💡 Сохраняем пользователя в request.state для последующего логирования
        request.state.user = user
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user or user["password"] != password:
        return False
    return user