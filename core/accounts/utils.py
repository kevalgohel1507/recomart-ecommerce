import random
from django.core.mail import send_mail

OTP_STORE = {}

def generate_otp(key):
    otp = str(random.randint(100000,999999))
    OTP_STORE[key] = otp
    return otp

def verify_otp(key,otp):
    return OTP_STORE.get(key) == otp