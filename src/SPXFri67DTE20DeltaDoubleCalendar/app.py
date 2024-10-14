from tradersync.execution import Execution, Spread
import logging
import asyncio
from tastytrade import Account
from tastytrade.session import Session
import boto3
from extended_new_order import ExtendedNewOrder

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
DRY_RUN = False
DTE = 1
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


    if DRY_RUN:
        # Build Order
        new_order, quote_data = await ExtendedNewOrder.create(session, SYMBOL, DTE, DELTA, WIDTH, QUANTITY)
        data = await new_order.validate(session, account)
        
        # Save each leg
        for leg in new_order.legs:
            tradersync_execution = Execution.from_option_leg(
                underlying_symbol=SYMBOL,
                leg=leg,
                quote_data=quote_data,
                spread=Spread.BULL_PUT
            )

            tradersync_execution.save_to_ddb()


    else:
        extended_new_order, quote_data = await ExtendedNewOrder.create(session, SYMBOL, DTE, DELTA, WIDTH, QUANTITY)
        placed_order_response = account.place_order(session, extended_new_order, dry_run=DRY_RUN)
        print("asdf")

        # save order.id, legs to orders table
        # Subscribe to status updates

        # placed_order = ExtendedPlacedOrder.from_response(placed_order_response)
        # placed_order.save_to_dynamodb()
    


    return { "statusCode": 200 }
