from fastapi import HTTPException
from config.settings import settings

def validate_currency(currency: str) -> str:
    """
    Validates that the provided currency is supported.
    Returns the currency if valid, otherwise raises HTTPException(400).
    If currency is None/Empty, returns the default currency.
    """
    if not currency:
        return settings.DEFAULT_CURRENCY
        
    if currency not in settings.supported_currencies_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported currency: {currency}. Supported currencies: {', '.join(settings.supported_currencies_list)}"
        )
    
    return currency
