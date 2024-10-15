from execution import Execution, Spread
import logging
import asyncio
from tastytrade import Account
from tastytrade.session import Session
import boto3
from bull_put_spread_order import BullPutSpreadOrder
from tastytrade.order import NewOrder, OrderTimeInForce, OrderType, Leg, OrderAction

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
DRY_RUN = False
PORTFOLIO = "PAPER"
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

    order, quote_data = await BullPutSpreadOrder.new(session, SYMBOL, DTE, DELTA, WIDTH, QUANTITY)
    order_data = await order.validate(session, account)
    order_response = account.place_order(session, order, dry_run=DRY_RUN)
    order = order_response.order
    logger.info(f"Placed order: {order.id}. Status: {order.status}.  Leg count: {len(order.legs)}")
    
    return { "order_id": order.id }


def dry_run(new_order, quote_data):
    for leg in new_order.legs:
        tradersync_execution = Execution.from_option_leg(
            underlying_symbol=SYMBOL,
            leg=leg,
            quote_data=quote_data,
            spread=Spread.BULL_PUT
        )

        tradersync_execution.save_to_ddb()
