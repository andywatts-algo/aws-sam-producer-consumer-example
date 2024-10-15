from dataclasses import asdict, dataclass
from pydantic import BaseModel, Field
from datetime import date as Date, time as Time, datetime
from enum import Enum, auto
from decimal import Decimal
import boto3
from typing import Dict
from tastytrade.dxfeed import Quote
from tastytrade.order import Leg, OrderAction
from tastytrade.instruments import OptionType
from utils import convert_option_symbol_to_quote_format, extract_expiration_date, extract_strike_price

class Market(str, Enum):
    OPTIONS = "OPTIONS"
    STOCKS = "STOCKS"
    FUTURES = "FUTURES"

class Spread(str, Enum):
    SINGLE = "SINGLE"
    VERTICAL = "VERTICAL"
    IRON_CONDOR = "IRON_CONDOR"
    BUTTERFLY = "BUTTERFLY"
    BULL_PUT = "BULL_PUT"
    DOUBLE_CALENDAR = "DOUBLE_CALENDAR"

class Portfolio(str, Enum):
    LIVE = "LIVE"
    PAPER = "PAPER"
    DEV = "DEV"

class Execution(BaseModel):
    symbol: str
    action: OrderAction
    spread: Spread
    option_type: OptionType
    date: Date
    time: Time
    expiration_date: Date
    quantity: int
    price: Decimal
    strike: Decimal
    market: Market = Market.OPTIONS
    portfolio: Portfolio = Portfolio.DEV
    commission: Decimal = Decimal('0.5')
    fees: Decimal = Decimal('0.1')
    leg_number: int = None
    id: str

    @classmethod
    def from_option_leg(cls, underlying_symbol: str, leg: Leg, quote_data: Dict[str, Quote], spread: Spread):
        quote_symbol = convert_option_symbol_to_quote_format(leg.symbol)
        quote = quote_data[quote_symbol]
        price = Decimal(str((quote.bidPrice + quote.askPrice) / 2))
        
        return cls(
            id=f"{leg.action}__{leg.symbol}__{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            symbol=leg.symbol,
            underlying_symbol=underlying_symbol,
            action=leg.action,
            spread=spread,
            option_type=OptionType.CALL if 'C' in leg.symbol else OptionType.PUT,
            date=Date.today(),
            time=datetime.now().time(),
            expiration_date=extract_expiration_date(leg.symbol),
            quantity=abs(leg.quantity),
            price=price,
            strike=Decimal(str(extract_strike_price(leg.symbol))),
            market=Market.OPTIONS,
            portfolio=Portfolio.DEV,
            commission=Decimal('0.5'),
            fees=Decimal('0.1')
        )

    def save_to_ddb(self, table_name: str = 'Executions'):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        item = self.model_dump(mode='json')
        return table.put_item(Item=item)

    class Config:
        json_encoders = {
            Date: lambda v: v.isoformat(),
            Time: lambda v: v.isoformat(),
            Decimal: str  
        }
