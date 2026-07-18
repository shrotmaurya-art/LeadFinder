"""Phone, website, and address normalization utilities for LeadFinder."""

def normalize_phone(phone: str | None) -> str | None:
    """Normalizes phone numbers to standard E.164 formats, defaulting to India (+91) for local numbers."""
    if not phone:
        return None
    cleaned = phone.strip()
    if not cleaned:
        return None
    
    has_plus = cleaned.startswith("+")
    digits = "".join(c for c in cleaned if c.isdigit())
    if not digits:
        return None
    
    if has_plus:
        return "+" + digits
        
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
        
    if digits.startswith("0") and len(digits) == 11:
        return "+91" + digits[1:]
        
    if len(digits) == 10:
        return "+91" + digits

    if len(digits) < 10:
        return None
    
    return digits

def normalize_website(url: str | None) -> str | None:
    """Reduces a URL down to a bare domain, removing scheme, www, and any paths/parameters."""
    if not url:
        return None
    cleaned = url.strip().lower()
    if not cleaned:
        return None
        
    if cleaned.startswith("https://"):
        cleaned = cleaned[8:]
    elif cleaned.startswith("http://"):
        cleaned = cleaned[7:]
        
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
        
    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0]
        
    return cleaned if cleaned else None

def normalize_address(address: str | None) -> str | None:
    """Cleans up whitespace and formatting in addresses."""
    if not address:
        return None
    cleaned = " ".join(address.strip().lower().split())
    return cleaned if cleaned else None
