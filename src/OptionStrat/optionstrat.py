import json
import logging
import aiohttp
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from urllib.parse import quote
import boto3
from botocore.exceptions import ClientError
from enum import Enum
from tastytrade.utils import PriceEffect
from tastytrade.order import NewOrder, OrderAction
from tastytrade.dxfeed import Greeks

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
OPTIONSTRAT_PARAM_PATH = '/optionstrat'
URL = "https://optionstrat.com/api/strategy"

class TradeType(Enum):
    NAKED_PUT = "Naked Put"
    NAKED_CALL = "Naked Call"
    PUT_SPREAD = "Put Spread"
    CALL_SPREAD = "Call Spread"
    IRON_CONDOR = "Iron Condor"
    DOUBLE_CALENDAR = "Double Calendar"

def determine_strategy_name(trade_type: TradeType, symbol: str, legs: List[Dict[str, Any]]) -> str:
    # TODO legs don't have expiration
    expirations = sorted(set(leg["expiration"] for leg in legs))
    expiration_short = datetime.fromisoformat(expirations[0]).strftime("%b %d")
    strikes = sorted(int(leg["strike"]) for leg in legs)

    # Use a dictionary to map trade types to their respective naming functions
    naming_functions = {
        TradeType.NAKED_PUT: lambda: f"{symbol} {expiration_short} {strikes[0]} {'Long' if legs[0]['action'] == 'buy' else 'Short'} Put",
        TradeType.NAKED_CALL: lambda: f"{symbol} {expiration_short} {strikes[0]} {'Long' if legs[0]['action'] == 'buy' else 'Short'} Call",
        TradeType.PUT_SPREAD: lambda: f"{symbol} {expiration_short} {strikes[0]}/{strikes[1]} {'Bull' if legs[0]['action'] == 'buy' else 'Bear'} Put Spread",
        TradeType.CALL_SPREAD: lambda: f"{symbol} {expiration_short} {strikes[0]}/{strikes[1]} {'Bull' if legs[0]['action'] == 'buy' else 'Bear'} Call Spread",
        TradeType.IRON_CONDOR: lambda: f"{symbol} {expiration_short} {strikes[0]}/{strikes[1]}/{strikes[2]}/{strikes[3]} Iron Condor",
        TradeType.DOUBLE_CALENDAR: lambda: f"{symbol} {expiration_short}/{datetime.fromisoformat(expirations[1]).strftime('%b %d')} {strikes[0]}/{strikes[1]} Double Calendar",
    }

    return naming_functions.get(trade_type, lambda: f"{symbol} {expiration_short} {'/'.join(map(str, strikes))} Custom Strategy")()

def generate_headers() -> Dict[str, str]:
    ssm = boto3.client('ssm')
    try:
        parameter = ssm.get_parameter(Name=OPTIONSTRAT_PARAM_PATH, WithDecryption=True)
        ssm_params = json.loads(parameter['Parameter']['Value'])
    except (ssm.exceptions.ParameterNotFound, ClientError) as e:
        logger.error(f"Error retrieving parameter from SSM: {e}")
        raise ValueError(f"Failed to retrieve parameter from SSM: {OPTIONSTRAT_PARAM_PATH}")

    expiration_time = datetime.utcnow() + timedelta(hours=24)
    expiration_str = expiration_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
    cookie = f"sid={quote(ssm_params['sid'])}; Path=/; Expires={expiration_str};"
    return { "Cookie": cookie, "Content-Type": "application/json" }

async def post_to_optionstrat(
    trade_type: TradeType,
    symbol: str,
    order: NewOrder,
) -> str:
    legs = [
        {
            # "symbol": float(Decimal(leg.symbol[-7:-3])),
            # "expiration": datetime.strptime(leg.symbol[6:12], "%y%m%d").date().isoformat(),
            # "type": "call" if "C" in leg.symbol else "put",
            # "action": "sell" if leg.action == OrderAction.SELL_TO_OPEN else "buy",
            "revision": 0,
            "enabled": True,
            "symbol": leg.symbol,
            "basis": float(order.price),
            "quantity": int(leg.quantity)
        }
        for leg in order.legs
    ]

    payload = {
        "name": determine_strategy_name(trade_type, symbol, legs),
        "isCustomName": True,
        "description": "All your base are belong to us",
        "basis": float(order.price),
        "strategy": {
            "isCashSecured": False,
            "symbol": symbol,
            "items": legs
        }
    }

    headers = generate_headers()
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, json=payload, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                strategy_id = result.get('id')
                if strategy_id:
                    logger.info(f"Strategy successfully saved with ID: {strategy_id}")
                    return strategy_id
                logger.error("Strategy saved but no ID was returned")
            else:
                logger.error(f"Error saving strategy: {response.status} - {await response.text()}")
            return None

    
