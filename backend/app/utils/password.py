from passlib.context import CryptContext

_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return bcrypt hash of the plain password."""
    return _context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain password matches the hash."""
    return _context.verify(plain, hashed)
