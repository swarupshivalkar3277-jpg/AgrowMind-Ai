from auth.utils import create_access_token, decode_access_token


def verify_token(token: str):
    try:
        return decode_access_token(token)
    except ValueError:
        return None


__all__ = ["create_access_token", "decode_access_token", "verify_token"]
