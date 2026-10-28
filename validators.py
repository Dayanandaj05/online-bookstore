"""Input validation helpers for bookstore domain models."""
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Tuple, Optional

# Standard RFC 5322 compliant email regex pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)


def validate_title(title: Any) -> Tuple[bool, Optional[str]]:
    """Validate that title is non-empty string."""
    if title is None:
        return False, "Title is required and cannot be empty."
    if not isinstance(title, str) or not title.strip():
        return False, "Title must be a non-empty string."
    if len(title.strip()) > 255:
        return False, "Title cannot exceed 255 characters."
    return True, None


def validate_price(price: Any) -> Tuple[bool, Optional[str]]:
    """Validate that price is a positive number (price > 0)."""
    if price is None:
        return False, "Price is required."
    try:
        val = Decimal(str(price).strip())
        if val <= Decimal("0.00"):
            return False, "Price must be strictly greater than 0."
        if val.as_tuple().exponent < -2:
            return False, "Price cannot have more than 2 decimal places."
        return True, None
    except (InvalidOperation, ValueError, TypeError):
        return False, "Price must be a valid numeric amount."


def validate_stock(stock: Any) -> Tuple[bool, Optional[str]]:
    """Validate that stock is an integer >= 0."""
    if stock is None:
        return False, "Stock is required."
    try:
        if isinstance(stock, float) and not stock.is_integer():
            return False, "Stock must be a whole integer."
        val = int(stock)
        if val < 0:
            return False, "Stock must be greater than or equal to 0."
        return True, None
    except (ValueError, TypeError):
        return False, "Stock must be a valid integer."


def validate_email(email: Any) -> Tuple[bool, Optional[str]]:
    """Validate that email has a valid address format."""
    if email is None:
        return False, "Email address is required."
    if not isinstance(email, str) or not email.strip():
        return False, "Email address cannot be empty."
    cleaned = email.strip()
    if len(cleaned) > 150:
        return False, "Email cannot exceed 150 characters."
    if not EMAIL_REGEX.match(cleaned):
        return False, "Please provide a valid email address (e.g. user@example.com)."
    return True, None


def validate_book_payload(data: dict) -> Tuple[bool, dict]:
    """Validate dictionary payload for a book."""
    errors = {}
    
    t_ok, t_err = validate_title(data.get("title"))
    if not t_ok:
        errors["title"] = t_err
        
    p_ok, p_err = validate_price(data.get("price"))
    if not p_ok:
        errors["price"] = p_err
        
    s_ok, s_err = validate_stock(data.get("stock"))
    if not s_ok:
        errors["stock"] = s_err
        
    author = data.get("author")
    if not author or not str(author).strip():
        errors["author"] = "Author is required."

    isbn = data.get("isbn")
    if not isbn or not str(isbn).strip():
        errors["isbn"] = "ISBN is required."

    category = data.get("category")
    if not category or not str(category).strip():
        errors["category"] = "Category is required."

    return len(errors) == 0, errors


def validate_customer_payload(data: dict) -> Tuple[bool, dict]:
    """Validate dictionary payload for a customer."""
    errors = {}

    name = data.get("name")
    if not name or not str(name).strip():
        errors["name"] = "Name is required."

    e_ok, e_err = validate_email(data.get("email"))
    if not e_ok:
        errors["email"] = e_err

    return len(errors) == 0, errors
