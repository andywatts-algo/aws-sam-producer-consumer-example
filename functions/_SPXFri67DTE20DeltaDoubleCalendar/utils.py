import re
from datetime import date

def convert_option_symbol_to_quote_format(symbol: str) -> str:
    """
    Convert an option symbol from the source format to the quote data format.
    
    Example:
    'SPXW  241014P05850000' -> '.SPXW241014P5850'
    """
    # Remove spaces and last two zeros
    cleaned = symbol.replace(' ', '')[:-3]
    
    # Split into parts
    ticker, date, option_type, strike = cleaned[:4], cleaned[4:10], cleaned[10], cleaned[11:]
    
    # Remove leading zeros from strike
    strike = strike.lstrip('0')

    # Reconstruct the symbol
    return f".{ticker}{date}{option_type}{strike}"

def extract_expiration_date(symbol: str) -> date:
    """
    Extract the expiration date from the option symbol.
    
    Example:
    'SPXW  241014P05850000' -> date(2024, 10, 14)
    """
    match = re.search(r'(\d{6})', symbol)
    if match:
        date_str = match.group(1)
        year = int('20' + date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        return date(year, month, day)
    else:
        raise ValueError(f"Unable to extract expiration date from symbol: {symbol}")
        
def extract_strike_price(option_symbol):
    """
    Extract the strike price from an option symbol.
    
    :param option_symbol: The option symbol (e.g., 'SPX230616P04125000')
    :return: The strike price as a float
    """
    strike_str = option_symbol[-8:]  # Last 8 characters represent the strike price
    return float(strike_str) / 1000  # Convert to actual strike price (e.g., 4125.00)

