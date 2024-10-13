from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from rich.console import Console
from rich.table import Table
from tastytrade import DXLinkStreamer
from tastytrade.streamer import EventType
from tastytrade.instruments import NestedOptionChain, Option
from tastytrade.order import NewOrder, OrderAction, OrderTimeInForce, OrderType, PriceEffect
import logging
import json
import os

from src.tastytrade.listen import listen_greeks, listen_quotes
from ttcli.utils import ZERO, RenewableSession, round_to_width, test_order_handle_errors


logger = logging.getLogger()

async def put(symbol: str, quantity: int, delta: int, dte: int, width: Optional[int] = None):
    sesh = RenewableSession()
    chain = NestedOptionChain.get_chain(sesh, symbol)
    today = date.today()
    subchain = min(chain.expirations, key=lambda e: abs((e.expiration_date - today).days - dte))
    tick_size = chain.tick_sizes[0].value
    precision = abs(tick_size.as_tuple().exponent) if tick_size.as_tuple().exponent < 0 else ZERO

    async with DXLinkStreamer(sesh) as streamer:
        dxfeeds = [s.put_streamer_symbol for s in subchain.strikes]
        await streamer.subscribe(EventType.GREEKS, dxfeeds)
        greeks_dict = await listen_greeks(len(dxfeeds), streamer)
        greeks = list(greeks_dict.values())

        selected = min(greeks, key=lambda g: abs(g.delta * Decimal(100) + delta))
        strike = next(s.strike_price for s in subchain.strikes if s.put_streamer_symbol == selected.eventSymbol)

        if width:
            spread_strike = next(s for s in subchain.strikes if s.strike_price == strike - width)
            await streamer.subscribe(EventType.QUOTE, [selected.eventSymbol, spread_strike.put_streamer_symbol])
            quote_dict = await listen_quotes(2, streamer)
            bid = quote_dict[selected.eventSymbol].bidPrice - quote_dict[spread_strike.put_streamer_symbol].askPrice
            ask = quote_dict[selected.eventSymbol].askPrice - quote_dict[spread_strike.put_streamer_symbol].bidPrice
        else:
            await streamer.subscribe(EventType.QUOTE, [selected.eventSymbol])
            quote = await streamer.get_event(EventType.QUOTE)
            bid, ask = quote.bidPrice, quote.askPrice
        mid = round_to_width((bid + ask) / Decimal(2), tick_size)

        short_symbol = next(s.put for s in subchain.strikes if s.strike_price == strike)
        logger.debug("Option symbols", short_symbol=short_symbol, spread_strike_put=spread_strike.put if width else None)

        if width:
            options = Option.get_options(sesh, [short_symbol, spread_strike.put])
            logger.debug("Retrieved options", options=options)
            if not options:
                raise ValueError(f"No options found for symbols: {short_symbol}, {spread_strike.put}")
            options.sort(key=lambda x: x.strike_price, reverse=True)
            legs = [
                options[0].build_leg(abs(quantity), OrderAction.SELL_TO_OPEN if quantity < 0 else OrderAction.BUY_TO_OPEN),
                options[1].build_leg(abs(quantity), OrderAction.BUY_TO_OPEN if quantity < 0 else OrderAction.SELL_TO_OPEN)
            ]
        else:
            put_option = Option.get_option(sesh, short_symbol)
            if put_option is None:
                raise ValueError(f"No option found for symbol: {short_symbol}")
            legs = [put_option.build_leg(abs(quantity), OrderAction.SELL_TO_OPEN if quantity < 0 else OrderAction.BUY_TO_OPEN)]


        order = NewOrder(
            time_in_force=OrderTimeInForce.DAY,
            order_type=OrderType.LIMIT,
            legs=legs,
            price=mid,
            price_effect=PriceEffect.CREDIT if quantity < 0 else PriceEffect.DEBIT
        )
        acc = sesh.get_account()

        data = test_order_handle_errors(acc, sesh, order)
        if data is None:
            return


        # Prepare the order details for serialization
        order_details = order.model_dump()
        
        # Construct the order name
        expiration_date = datetime.strptime(str(subchain.expiration_date), "%Y-%m-%d")
        expiration_str = expiration_date.strftime("%b %d")
        
        def extract_strike(symbol):
            return symbol[-7:-3]
        
        if width:
            lower_strike = min(extract_strike(leg.symbol) for leg in legs)
            higher_strike = max(extract_strike(leg.symbol) for leg in legs)
            strategy = "Bull Put Spread" if quantity < 0 else "Bear Put Spread"
            name = f"{symbol} {expiration_str} {lower_strike}/{higher_strike} {strategy}"
        else:
            strike = extract_strike(legs[0].symbol)
            strategy = "Short Put" if quantity < 0 else "Long Put"
            name = f"{symbol} {expiration_str} {strike} {strategy}"

        # Add additional information
        order_details.update({
            "name": name,
            "symbol": symbol,
            "strategy": "put spread" if width else "naked put",
            "expiration": str(subchain.expiration_date),
            "delta": selected.delta,
            "buying_power_effect": data.buying_power_effect.change_in_buying_power,
            "fees": data.fee_calculation.total_fees,
        })

        if width:
            order_details["spread_width"] = width


        # Print the JSON output
        logger.debug(json.dumps(order_details, indent=2, default=str))

        if data.warnings:
            for warning in data.warnings:
                logger.warning(warning.message)
