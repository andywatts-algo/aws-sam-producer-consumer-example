from tastytrade.order import NewOrder, OrderAction, OrderTimeInForce, OrderType
from tastytrade.instruments import NestedOptionChain, Option
from tastytrade import DXLinkStreamer
from tastytrade.dxfeed import Greeks, Quote
from tastytrade.listen import listen_greeks, listen_quotes
from tastytrade.utils import PriceEffect
from ttcli.utils import round_to_width, test_order_handle_errors
from decimal import Decimal
from datetime import date
import logging

logger = logging.getLogger(__name__)

class ExtendedNewOrder(NewOrder):

    def to_dict(self):
        return self.dict()

    def to_json(self):
        return self.json(indent=2)

    async def validate(self, session, account):
        data = test_order_handle_errors(account, session, self)
        if data.warnings:
            for warning in data.warnings:
                logger.warning(warning.message)
        if data is None:
            raise ValueError("Order validation failed")
        return data

    @classmethod
    async def create(cls, session, SYMBOL, DTE, DELTA, WIDTH, QUANTITY):
        chain = NestedOptionChain.get_chain(session, SYMBOL)
        subchain = min(chain.expirations, key=lambda e: abs((e.expiration_date - date.today()).days - DTE))
        tick_size = chain.tick_sizes[0].value

        async with DXLinkStreamer(session) as streamer:
            # Select strikes
            mid = len(subchain.strikes) // 2
            quarter = mid // 2
            dxfeeds = [s.put_streamer_symbol for s in subchain.strikes[mid-quarter:mid+quarter]]
            
            # Get greeks
            await streamer.subscribe(Greeks, dxfeeds)
            greeks_dict = await listen_greeks(len(dxfeeds), streamer)
            greeks = list(greeks_dict.values())
            
            # Select strikes using delta
            selected = min(greeks, key=lambda g: abs(g.delta * Decimal(100) + DELTA))
            selected_strike = next(s for s in subchain.strikes if s.put_streamer_symbol == selected.eventSymbol)
            spread_strike = next(s for s in subchain.strikes if s.strike_price == selected_strike.strike_price - WIDTH)

            # Get quotes
            await streamer.subscribe(Quote, [selected_strike.put_streamer_symbol, spread_strike.put_streamer_symbol])
            quote_dict = await listen_quotes(2, streamer)

            # Calculate mid price
            bid = quote_dict[selected_strike.put_streamer_symbol].bidPrice - quote_dict[spread_strike.put_streamer_symbol].askPrice
            ask = quote_dict[selected_strike.put_streamer_symbol].askPrice - quote_dict[spread_strike.put_streamer_symbol].bidPrice
            mid_price = round_to_width((bid + ask) / Decimal(2), tick_size)

            # Get options and create order
            short_symbol = selected_strike.put
            spread_symbol = spread_strike.put
            options = Option.get_options(session, [short_symbol, spread_symbol])
            if not options:
                raise ValueError(f"No options found for symbols: {short_symbol}, {spread_symbol}")
            options = sorted(options, key=lambda x: x.strike_price, reverse=True)

            legs = [
                options[0].build_leg(abs(QUANTITY), OrderAction.SELL_TO_OPEN if QUANTITY < 0 else OrderAction.BUY_TO_OPEN),
                options[1].build_leg(abs(QUANTITY), OrderAction.BUY_TO_OPEN if QUANTITY < 0 else OrderAction.SELL_TO_OPEN)
            ]
            
            new_order = cls(
                time_in_force=OrderTimeInForce.DAY,
                order_type=OrderType.LIMIT,
                legs=legs,
                price=mid_price
            )

            return new_order, quote_dict
