import logging

from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer

from src.app.user.schema import OTPVerificationRequest, loginwithemailandpassword, TOTPVerificationRequest
from src.app.user.service import initiate_oauth, handle_oauth_callback, create_and_send_otp, verify_otp, \
    login_with_totp_service, verify_totp_service
from src.connection.connection import ConnectionHandler, get_connection_handler_for_app
from fastapi import APIRouter, HTTPException, Depends


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize logger
logger = logging.getLogger(__name__)

load_dotenv()
user_router = APIRouter()


@user_router.get("/login")
async def login(request: Request):
    """Redirect user to Google OAuth login page"""
    try:
        authorization_url = await initiate_oauth(request)

        return RedirectResponse(url=authorization_url)

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth initialization failed: {str(e)}")


@user_router.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback from Google"""
    try:
        user = await handle_oauth_callback(request=request)
        return {
            "message": "Login successful",
            "user": user
        }

    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@user_router.post("/login_otp")
async def login_with_otp(
        mobile_number: str,
        connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
):
    session = connection_handler.session

    # Await the async function and get the result
    result = await create_and_send_otp(mobile_number, session)

    if isinstance(result, dict):
        return result
    else:
        return {"message": "Internal server error", "status": "error"}


@user_router.post("/verify_otp")
async def login_with_otp(
        request: OTPVerificationRequest,
        connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
):
    session = connection_handler.session
    tokens = await verify_otp(request.mobile_number, request.otp, session)
    response={"message": "OTP verified successfully", **tokens}
    return response
@user_router.post("/login_totp")
async def login_with_totp(
    request:loginwithemailandpassword,
    connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
):
    session = connection_handler.session
    result = await login_with_totp_service(request.mobile_number, request.password, session)
    return result

@user_router.post("/verify_totp")
async def verify_totp(
    request: TOTPVerificationRequest,
    connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
):
    session = connection_handler.session

    result = await verify_totp_service(request.mobile_number, request.totp, session)

    return result