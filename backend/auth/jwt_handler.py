from auth.utils import create_access_token, decode_access_token


def verify_token(token: str):
    return decode_access_token(token)


__all__ = ["create_access_token", "decode_access_token", "verify_token"]
