from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import JWTError

# Инициализируем схему Bearer токена
bearer_scheme = HTTPBearer()

# Пример БД (заменить на реальную)
fake_users_db = {
    "admin": {"username": "admin", "password": "secret"}
}

# Секретный ключ и алгоритм
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

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