import base64
import os
import random
from datetime import datetime
from datetime import timedelta
import asyncio
from io import BytesIO

import jwt
import pyotp
import qrcode
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.future import select
from starlette.responses import JSONResponse, StreamingResponse
from twilio.rest import Client

from src.app.user.models import User

load_dotenv()

TWILIO_ACCOUNT_SID=os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN=os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER=os.environ.get("TWILIO_NUMBER")

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(mobile_number, otp):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=f"Your OTP is {otp}. It will expire in 5 minutes.",
        from_=TWILIO_NUMBER,
        to=mobile_number
    )
    return message.sid

SECRET_KEY = "sanyog"
ALGORITHM = "HS256"

# Asynchronous JWT token creation
async def create_jwt_token(data: dict, expires_delta: timedelta):
    """Asynchronously create a JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})

    await asyncio.sleep(0)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Asynchronous token generation
async def generate_tokens(user):
    """Asynchronously generate access and refresh tokens for a user."""
    access_token = await create_jwt_token({"sub": user.email}, timedelta(minutes=15))
    refresh_token = await create_jwt_token({"sub": user.email}, timedelta(days=7))
    return {"access_token": access_token, "refresh_token": refresh_token}




async def setup_totp(user: User, db_session):
    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        user.is_totp_enabled = True

        db_session.add(user)
        await db_session.commit()

    totp = pyotp.TOTP(user.totp_secret)
    issuer_name = "fastapi"
    provisioning_uri = totp.provisioning_uri(user.email, issuer_name=issuer_name)

    qr_img = qrcode.make(provisioning_uri)

    img_buffer = BytesIO()
    qr_img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    return StreamingResponse(img_buffer, media_type="image/png")

