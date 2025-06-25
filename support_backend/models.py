from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    name = Column(String, index=True)
    password = Column(String, index=True)

    profile = relationship("Profile", back_populates="user")
    orders = relationship("Order", back_populates="user")
    roles = relationship("UserRole", secondary="user_user_roles", back_populates="users")
    
class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    bio = Column(Text)
    avatar_url = Column(String(255))

    user = relationship("User", back_populates="profile")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    total_amount = Column(Numeric(10, 2))
    status = Column(String(50))

    user = relationship("User", back_populates="orders")

class UserRole(Base):
    __tablename__ = 'user_roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)

    users = relationship("User", secondary="user_user_roles", back_populates="roles")

class UserUserRole(Base):
    __tablename__ = 'user_user_roles'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('user_roles.id'), primary_key=True)