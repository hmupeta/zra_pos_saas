"""Symmetric encryption for credential fields."""
import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _key():
    return base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())


def encrypt(value):
    if not value:
        return ""
    return Fernet(_key()).encrypt(str(value).encode()).decode()


def decrypt(value):
    if not value:
        return ""
    try:
        return Fernet(_key()).decrypt(value.encode()).decode()
    except Exception:
        return ""


class EncryptedCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 600)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value else value

    def get_prep_value(self, value):
        if not value:
            return value
        try:
            return encrypt(value)
        except Exception:
            return value
