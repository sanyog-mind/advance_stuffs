import logging
import os
import secrets
import urllib
from datetime import datetime
from datetime import timedelta
from http.client import responses
import pandas as pd
from fastapi import HTTPException

import httpx
import pyotp
from fastapi import HTTPException
from sqlalchemy.future import select
from starlette.requests import Request

from src.app.user.models import User
from src.app.user.utils import generate_otp, send_otp, generate_tokens, setup_totp

# Initialize logger
logger = logging.getLogger(__name__)


async def initiate_oauth(request: Request):
    """Handles the logic of redirecting user to Google OAuth login page"""
    try:
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        redirect_uri = os.getenv('REDIRECT_URI', 'http://localhost:8000/auth/callback')

        state = secrets.token_urlsafe(32)

        request.session['oauth_state'] = state
        logger.info(f"Generated OAuth state: {state}")

        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join([
                'openid',
                'email',
                'profile',
                'https://www.googleapis.com/auth/userinfo.profile',
                'https://www.googleapis.com/auth/userinfo.email'
            ]),
            'state': state,
            'access_type': 'offline',
            'include_granted_scopes': 'true',
            'prompt': 'consent',
            'hd': 'mindinventory.com'
        }

        query_string = urllib.parse.urlencode(params)
        authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"

        logger.info(f"Generated authorization URL: {authorization_url}")
        return authorization_url

    except Exception as e:
        logger.error(f"OAuth initiation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth initialization failed: {str(e)}")


async def handle_oauth_callback(request: Request):
    """Handles the logic for the OAuth callback from Google"""
    code = request.query_params.get('code')
    received_state = request.query_params.get('state')

    stored_state = request.session.get('oauth_state')
    print("stored_state", stored_state)
    if not stored_state or stored_state != received_state:
        logger.warning(f"State mismatch. Stored: {stored_state}, Received: {received_state}")
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    del request.session['oauth_state']

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': os.getenv('REDIRECT_URI', 'http://localhost:8000/auth/callback')
            }
        )

        if token_response.status_code != 200:
            logger.error(f"Error exchanging code for token: {token_response.text}")
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")

        token_data = token_response.json()

        user_response = await client.get(
            'https://openidconnect.googleapis.com/v1/userinfo',
            headers={'Authorization': f'Bearer {token_data["access_token"]}'}
        )

        if user_response.status_code != 200:
            logger.error(f"Error fetching user info: {user_response.text}")
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        user_info = user_response.json()

    request.session['user'] = {
        "email": user_info.get('email'),
        "name": user_info.get('name'),
        "picture": user_info.get('picture'),
        "domain": user_info.get('hd')
    }

    return request.session.get('user')


async def create_and_send_otp(mobile_number, db_session):
    query = select(User).where(User.mobile_number == mobile_number)
    result = await db_session.execute(query)
    user = result.scalars().first()
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
    await db_session.commit()
    send_otp(user.mobile_number, otp)
    return {"message": "OTP sent successfully"}

async def verify_otp(mobile_number: str, otp: str, db_session):
    query = select(User).where(User.mobile_number == mobile_number)
    result = await db_session.execute(query)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.otp != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if user.otp_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired")

    user.is_verified = True
    user.otp = None
    user.otp_expires_at = None
    await db_session.commit()
    tokens = await generate_tokens(user)
    return tokens


async def login_with_totp_service(mobile_number: str, password: str, db_session):
    query = select(User).where(User.mobile_number == mobile_number)
    result = await db_session.execute(query)
    user = result.scalars().first()

    if user.password != password:
        return {"message": "Invalid password"}

    totp_qr = await setup_totp(user, db_session)

    return totp_qr

async def verify_totp_service(mobile_number: str, totp_code: str, db_session):
    query = select(User).where(User.mobile_number == mobile_number)
    result = await db_session.execute(query)
    user = result.scalars().first()

    if not user or not user.is_totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP is not enabled for this user")

    totp = pyotp.TOTP(user.totp_secret)

    if not totp.verify(totp_code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    tokens = await generate_tokens(user)

    return {
        "message": "TOTP verified successfully", **tokens
    }


def read_and_compute_sum(csv_path: str, no1: float, no2: float) -> float:
    df = pd.read_csv(csv_path)

    new_row = pd.DataFrame({"no1": [no1], "no2": [no2]})

    df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv(csv_path, index=False)

    return df['sum'].iloc[-1]