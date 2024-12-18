from pydantic import BaseModel

class OTPVerificationRequest(BaseModel):
    mobile_number: str
    otp: str

class loginwithemailandpassword(BaseModel):
    mobile_number: str
    password: str

class TOTPVerificationRequest(BaseModel):
    mobile_number: str
    totp: str

class NumbersInput(BaseModel):
    no1: float
    no2: float