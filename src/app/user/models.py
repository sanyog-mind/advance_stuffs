from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    password = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False)
    is_verified = Column(Boolean, default=False)
    mobile_number = Column(String, nullable=False, unique=True)
    otp = Column(String(6))
    otp_expires_at = Column(DateTime)
    last_login = Column(DateTime)
    totp_secret = Column(String, nullable=True)
    is_totp_enabled = Column(Boolean, default=False)
