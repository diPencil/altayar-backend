import hashlib
import hmac
import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
import bcrypt

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # return pwd_context.hash(password)
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    # return pwd_context.verify(plain_password, hashed_password)
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False


def generate_verification_token(length: int = 32) -> str:
    """Generate a random verification token"""
    return secrets.token_urlsafe(length)


def generate_code(length: int = 8, uppercase: bool = True) -> str:
    """Generate a random alphanumeric code"""
    characters = string.ascii_uppercase + string.digits if uppercase else string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature using HMAC-SHA256"""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def generate_unique_number(prefix: str, sequence: int) -> str:
    """Generate unique number with prefix (e.g., BKG-2025-001234)"""
    from datetime import datetime
    year = datetime.now().year
    return f"{prefix}-{year}-{sequence:06d}"


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    """Validate phone format (basic)"""
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, phone) is not None


def calculate_tax(amount: float, tax_rate: float) -> float:
    """Calculate tax amount"""
    return round(amount * (tax_rate / 100), 2)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount"""
    return f"{amount:,.2f} {currency}"


def get_date_range(start_date: Optional[datetime], end_date: Optional[datetime]):
    """Get date range or default to last 30 days"""
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    return start_date, end_date


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')