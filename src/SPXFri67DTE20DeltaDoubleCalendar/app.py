from tradersync.execution import Execution, Market, Action, Spread, OptionType
from datetime import date, datetime, time
from decimal import Decimal
import json
import logging
import asyncio
from tastytrade import Account
from tastytrade.session import Session
import boto3
from extended_new_order import ExtendedNewOrder
from extended_placed_order import ExtendedPlacedOrder, simulate_fill
from utils import convert_option_symbol_to_quote_format, extract_expiration_date, extract_strike_price

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
DRY_RUN = True
DTE = 0
SYMBOL = "SPX"
STRATEGY = "Bull Put Spread"
DELTA = 20
WIDTH = 20
QUANTITY = -1

def lambda_handler(event, context):
    return asyncio.run(main())
    
async def main():
    session = Session()
    account = Account.get_accounts(session)[0]

    # Build Order
    new_order, quote_data = await ExtendedNewOrder.create(session, SYMBOL, DTE, DELTA, WIDTH, QUANTITY)
    data = await new_order.validate(session, account)
    
    # Build TraderSync Execution
    for leg in new_order.legs:
        tradersync_execution = Execution.from_option_leg(
            underlying_symbol=SYMBOL,
            leg=leg,
            quote_data=quote_data,
            spread=Spread.BULL_PUT
        )

        tradersync_execution.save_to_ddb()


    # Place or simulate
    # if not DRY_RUN:
        # placed_order_response = account.place_order(session, new_order, dry_run=DRY_RUN)
        # placed_order = ExtendedPlacedOrder.from_response(placed_order_response)
    # else:
        # For dry run
        # simulated_filled_order = simulate_fill(new_order, new_order.price, quote_data)
        # logger.info(f"Simulated filled order: {simulated_filled_order}")
        # placed_order = simulated_filled_order
    

    

    # placed_order.save_to_dynamodb()
    # csv_rows = placed_order.to_csv_row()
    


    return { "statusCode": 200 }
