from typing import Optional, List
from pydantic import BaseModel

# ==== USER ====
class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None  # Пароль необязателен при обновлении

class UserResponse(UserBase):
    id: int
    profiles: List['ProfileResponse'] = []
    orders: List['OrderResponse'] = []
    roles: List['RoleResponse'] = []
    logs: List['ActivityLogResponse'] = []

    class Config:
        from_attributes = True  # Для совместимости с SQLAlchemy ORM


# ==== PROFILE ====
class ProfileBase(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class ProfileCreate(ProfileBase):
    user_id: int

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ==== ORDER ====
class OrderBase(BaseModel):
    total_amount: float
    status: str

class OrderCreate(OrderBase):
    user_id: int

class OrderUpdate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ==== ROLE ====
class RoleBase(BaseModel):
    name: str

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: int

    class Config:
        from_attributes = True


# ==== USER ROLES (Many-to-Many) ====
class UserRoleLink(BaseModel):
    user_id: int
    role_id: int

    class Config:
        from_attributes = True


# ==== ACTIVITY LOGS ====
class ActivityLogBase(BaseModel):
    action: str
    ip_address: str

class ActivityLogCreate(ActivityLogBase):
    user_id: int

class ActivityLogUpdate(ActivityLogBase):
    pass

class ActivityLogResponse(ActivityLogBase):
    id: int
    user_id: int
    created_at: str

    class Config:
        from_attributes = True


# ==== Обновляем "UserResponse" после определения всех зависимых моделей ====
UserResponse.model_rebuild()