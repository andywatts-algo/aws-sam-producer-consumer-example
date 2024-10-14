from tastytrade.order import PlacedOrder, OrderTimeInForce, OrderType, InstrumentType, FillInfo
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'Orders'

class ExtendedPlacedOrder(PlacedOrder):
    def to_dict(self):
        return self.dict()

    def to_json(self):
        return self.json(indent=2)

    def save_to_dynamodb(self):
        table = dynamodb.Table(TABLE_NAME)
        try:
            item = self.to_dict()
            response = table.put_item(Item=item)
            logger.info(f"Order saved to DynamoDB: Order {self.id}")
        except ClientError as e:
            logger.error(f"Error saving order to DynamoDB: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Unexpected error saving order to DynamoDB: {str(e)}")

    def to_csv_row(self):
        csv_data = []
        current_time = datetime.now().isoformat()
        for leg in self.legs:
            # Extract the average fill price from the fills
            total_fill_value = sum(fill.fill_price * fill.quantity for fill in leg.fills)
            total_fill_quantity = sum(fill.quantity for fill in leg.fills)
            average_fill_price = total_fill_value / total_fill_quantity if total_fill_quantity else Decimal('0')

            csv_data.append({
                'Date': current_time,
                'Type': 'Trade',
                'Sub Type': leg.action.value,
                'Action': leg.action.value,
                'Symbol': leg.symbol,
                'Instrument Type': 'Equity Option',
                'Description': f"{leg.action.value} {leg.quantity} {leg.symbol}",
                'Value': average_fill_price * leg.quantity * 100,  # Assuming 100 multiplier
                'Quantity': leg.quantity,
                'Average Price': average_fill_price,
                'Commissions': self.commission / len(self.legs),
                'Fees': self.fees / len(self.legs),
                'Multiplier': 100,
                'Root Symbol': leg.symbol.split()[0],
                'Underlying Symbol': self.underlying_symbol,
                'Expiration Date': leg.symbol.split()[1][:6],
                'Strike Price': leg.strike_price,
                'Call or Put': 'CALL' if leg.symbol[-1] == 'C' else 'PUT',
                'Order #': self.id,
                'Currency': 'USD'
            })
        return csv_data

    @classmethod
    def from_response(cls, response):
        return cls(**response.dict())  # Use dict() method if response is a Pydantic model

def simulate_fill(new_order, price, quote_data):
    current_time = datetime.now()
    
    # Create fill information for each leg
    filled_legs = []
    for leg in new_order.legs:
        # Get the quote for this leg's symbol
        quote = quote_data.get(leg.symbol)
        if quote is None:
            logger.warning(f"No quote data found for symbol {leg.symbol}. Using order price.")
            leg_price = price
        else:
            # Use the midpoint of bid and ask as the fill price
            leg_price = (quote.bidPrice + quote.askPrice) / Decimal(2)

        # Create a FillInfo object for this leg
        fill_info = FillInfo(
            fill_id=f"sim_{current_time.strftime('%Y%m%d%H%M%S')}_{leg.symbol}",
            quantity=abs(leg.quantity),
            fill_price=leg_price,
            filled_at=current_time
        )

        # Create a new leg with the fill information
        filled_leg = leg.copy(update={'fills': [fill_info]})
        filled_legs.append(filled_leg)

    return ExtendedPlacedOrder(
        id=current_time.strftime('%Y%m%d%H%M%S'),
        status='Filled',
        underlying_symbol=new_order.underlying_symbol,
        legs=filled_legs,
        price=price,
        time_in_force=new_order.time_in_force,
        order_type=new_order.order_type,
        commission=0.5 * len(new_order.legs),
        fees=0.1 * len(new_order.legs),
        account_number="SIMULATED",  # Use a placeholder for simulated orders
        cancellable=False,
        editable=False,
        edited=False,
        updated_at=current_time,
        underlying_instrument_type=InstrumentType.EQUITY  # Assuming it's an equity option
    )
