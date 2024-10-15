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

    # Entry order
    entry_order, quote_data = await BullPutSpreadOrder.new(session, SYMBOL, DTE, DELTA, WIDTH, QUANTITY)
    entry_data = await entry_order.validate(session, account)
    entry_order_response = account.place_order(session, entry_order, dry_run=DRY_RUN)
    entry_order = entry_order_response.order
    logger.info(f"Placed order: {entry_order.id}. Status: {entry_order.status}.  Leg count: {len(entry_order.legs)}")


    # Wait for order to be filled
    logger.info("Sleeping for 2 seconds to allow order to be filled")
    await asyncio.sleep(2)
    entry_order = account.get_order(session, entry_order.id)
    if entry_order.status != 'Filled':
        return { "statusCode": 500, "body": "Order not filled" }


    # Enter PT
    PROFIT_TARGET = 0.5  # 50% profit target
    entry_price = sum(leg.price * abs(leg.quantity) for leg in entry_order.legs)
    profit_target_price = entry_price * (1 - PROFIT_TARGET)
    profit_target_order = NewOrder(
        time_in_force=OrderTimeInForce.GTC,
        order_type=OrderType.LIMIT,
        price=profit_target_price,
        legs=[
            Leg(
                instrument_type=leg.instrument_type,
                symbol=leg.symbol,
                action=OrderAction.BUY_TO_CLOSE if leg.action == OrderAction.SELL_TO_OPEN else OrderAction.SELL_TO_CLOSE,
                quantity=abs(leg.quantity)
            )
            for leg in entry_order.legs
        ]
    )
    profit_target_order_response = account.place_order(session, profit_target_order, dry_run=DRY_RUN)
    profit_target_order = profit_target_order_response.order
    logger.info(f"Placed PT order: {profit_target_order.id}. Status: {profit_target_order.status}. Price: {profit_target_order.price}")


    # Post to OS 


    return { "statusCode": 200 }


def dry_run(new_order, quote_data):
    for leg in new_order.legs:
        tradersync_execution = Execution.from_option_leg(
            underlying_symbol=SYMBOL,
            leg=leg,
            quote_data=quote_data,
            spread=Spread.BULL_PUT
        )

        tradersync_execution.save_to_ddb()


def live():
    pass
