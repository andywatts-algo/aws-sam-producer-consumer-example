from pydantic import Bas
from datetime import date as Date, time as Time, datetime
from enum import Enum, auto
from decimal import Decimal
import boto3
from typing import Dict
from tastytrade.dxfeed import Quote
from utils import convert_option_symbol_to_quote_format, extract_expiration_date, extract_strike_price

class Market(Enum):
    OPTIONS = auto()
    STOCKS = auto()
    FUTURES = auto()

class Action(Enum):
    BUY = auto()
    SELL = auto()

class Spread(Enum):
    SINGLE = auto()
    VERTICAL = auto()
    IRON_CONDOR = auto()
    BUTTERFLY = auto()

class OptionType(Enum):
    CALL = auto()
    PUT = auto()

class Portfolio(Enum):
    LIVE = auto()
    PAPER = auto()
    DEV = auto()

class Spread(Enum):
    SINGLE = auto()
    VERTICAL = auto()
    IRON_CONDOR = auto()
    BUTTERFLY = auto()
    BULL_PUT = auto()
    DOUBLE_CALENDAR = auto()


@dataclass
class Execution:
    symbol: str
    action: Action
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

    @classmethod
    def from_option_leg(cls, symbol: str, leg_symbol: str, quantity: int, quote_data: Dict[str, Quote], spread: Spread):
        quote_symbol = convert_option_symbol_to_quote_format(leg_symbol)
        quote = quote_data[quote_symbol]
        price = Decimal(str((quote.bidPrice + quote.askPrice) / 2))
        
        return cls(
            symbol=symbol,
            action=Action.SELL if quantity < 0 else Action.BUY,
            spread=spread,
            option_type=OptionType.CALL if 'C' in leg_symbol else OptionType.PUT,
            date=Date.today(),
            time=datetime.now().time(),
            expiration_date=extract_expiration_date(leg_symbol),
            quantity=abs(quantity),
            price=price,
            strike=Decimal(str(extract_strike_price(leg_symbol))),
            market=Market.OPTIONS,
            portfolio=Portfolio.DEV,
            commission=Decimal('0.5'),
            fees=Decimal('0.1')
        )

    def save_to_ddb(self, table_name: str = 'Executions'):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
        item = asdict(self)
        
        return table.put_item(Item=item)




