import json
import logging
import asyncio
from datetime import date, datetime
from decimal import Decimal
from ttcli.utils import round_to_width, test_order_handle_errors
from tastytrade import Account, DXLinkStreamer
from tastytrade.dxfeed import Greeks, Quote
from tastytrade.instruments import NestedOptionChain, Option
from tastytrade.listen import listen_greeks, listen_quotes
from tastytrade.order import NewOrder, OrderAction, OrderTimeInForce, OrderType
from tastytrade.session import Session
from tastytrade.streamer import EventType
from tastytrade.utils import PriceEffect

logger = logging.getLogger()
logger.setLevel(logging.INFO)


logger.setLevel(logging.INFO)

SYMBOL = "SPX"
WIDTH = 20

def lambda_handler(event, context):
    session = Session()
    
    try:
        result = asyncio.run(place_trade(event, context, session))
        return { "statusCode": 200, "body": json.dumps("hello world") }
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return { "statusCode": 500, "body": json.dumps(str(e)) }



async def place_trade(event, context, session):
    DTE = 1
    WIDTH = 20
    DELTA = 20
    QUANTITY = -1
    ZERO = Decimal(0)

    chain = NestedOptionChain.get_chain(session, SYMBOL)
    today = date.today()
    subchain = min(chain.expirations, key=lambda e: abs((e.expiration_date - today).days - DTE))
    tick_size = chain.tick_sizes[0].value
    precision = abs(tick_size.as_tuple().exponent) if tick_size.as_tuple().exponent < 0 else ZERO

    async with DXLinkStreamer(session) as streamer:
        logger.info(f"subscribing to {Greeks}")

        # Get strikes around ATM
        mid = len(subchain.strikes) // 2
        quarter = mid // 2
        dxfeeds = [s.put_streamer_symbol for s in subchain.strikes[mid-quarter:mid+quarter]]
        logger.info(f"Subscribing to {len(dxfeeds)} put strike deltas around ATM ({subchain.strikes[mid].strike_price}) for {SYMBOL} {subchain.expiration_date}")

        # Get greeks
        await streamer.subscribe(Greeks, dxfeeds)
        logger.info("subscribed")
        greeks_dict = await listen_greeks(len(dxfeeds), streamer)
        greeks = list(greeks_dict.values())
        logger.info(f"Got {len(greeks)} greeks")

        # Compute strikes
        selected = min(greeks, key=lambda g: abs(g.delta * Decimal(100) + DELTA))
        strike = next(s.strike_price for s in subchain.strikes if s.put_streamer_symbol == selected.eventSymbol)
        spread_strike = next(s for s in subchain.strikes if s.strike_price == strike - WIDTH)

        # Get quotes
        await streamer.subscribe(Quote, [selected.eventSymbol, spread_strike.put_streamer_symbol])
        quote_dict = await listen_quotes(2, streamer)
        bid = quote_dict[selected.eventSymbol].bidPrice - quote_dict[spread_strike.put_streamer_symbol].askPrice
        ask = quote_dict[selected.eventSymbol].askPrice - quote_dict[spread_strike.put_streamer_symbol].bidPrice
        mid = round_to_width((bid + ask) / Decimal(2), tick_size)

        # Get options
        short_symbol = next(s.put for s in subchain.strikes if s.strike_price == strike)
        logger.info(f"Option symbols: short={short_symbol}, spread={spread_strike.put}")
        options = Option.get_options(session, [short_symbol, spread_strike.put])
        logger.debug(f"Retrieved options: {options}")
        if not options:
            raise ValueError(f"No options found for symbols: {short_symbol}, {spread_strike.put}")
        options.sort(key=lambda x: x.strike_price, reverse=True)

        # Build order
        legs = [
            options[0].build_leg(abs(QUANTITY), OrderAction.SELL_TO_OPEN if QUANTITY < 0 else OrderAction.BUY_TO_OPEN),
            options[1].build_leg(abs(QUANTITY), OrderAction.BUY_TO_OPEN if QUANTITY < 0 else OrderAction.SELL_TO_OPEN)
        ]
        order = NewOrder(
            time_in_force=OrderTimeInForce.DAY,
            order_type=OrderType.LIMIT,
            legs=legs,
            price=mid,
            price_effect=PriceEffect.CREDIT if QUANTITY < 0 else PriceEffect.DEBIT
        )

        # Check order
        accounts = Account.get_accounts(session)
        account = accounts[0]
        data = test_order_handle_errors(account, session, order)
        # Log any warnings
        if data.warnings:
            for warning in data.warnings:
                logger.warning(warning.message)
        if data is None:
            return

        log_trade(order, subchain, selected, data, SYMBOL, QUANTITY, WIDTH)

    return 'Success'


def log_trade(order, subchain, selected, data, SYMBOL, QUANTITY, WIDTH):
    # Prepare the order details for serialization
    order_details = order.model_dump()
    
    # Construct the order name
    expiration_date = datetime.strptime(str(subchain.expiration_date), "%Y-%m-%d")
    expiration_str = expiration_date.strftime("%b %d")
    def extract_strike(symbol):
        return symbol[-7:-3]
    lower_strike = min(extract_strike(leg.symbol) for leg in order.legs)
    higher_strike = max(extract_strike(leg.symbol) for leg in order.legs)
    strategy = "Bull Put Spread" if QUANTITY < 0 else "Bear Put Spread"
    name = f"{SYMBOL} {expiration_str} {lower_strike}/{higher_strike} {strategy}"

    # Add additional information
    order_details.update({
        "name": name,
        "symbol": SYMBOL,
        "strategy": "put spread" if WIDTH else "naked put",
        "expiration": str(subchain.expiration_date),
        "delta": selected.delta,
        "buying_power_effect": data.buying_power_effect.change_in_buying_power,
        "fees": data.fee_calculation.total_fees,
        "width": WIDTH
    })

    # Log the JSON output
    logger.info(json.dumps(order_details, indent=2, default=str))
