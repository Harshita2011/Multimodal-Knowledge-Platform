from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return str(_pwd.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    return bool(_pwd.verify(password, password_hash))
