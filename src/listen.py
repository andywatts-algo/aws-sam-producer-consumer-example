
from tastytrade import DXLinkStreamer
from tastytrade.dxfeed import EventType, Greeks, Quote



async def listen_quotes(
    n_quotes: int,
    streamer: DXLinkStreamer,
    skip: str | None = None
) -> dict[str, Quote]:
    quote_dict = {}
    async for quote in streamer.listen(EventType.QUOTE):
        if quote.eventSymbol != skip:
            quote_dict[quote.eventSymbol] = quote
        if len(quote_dict) == n_quotes:
            return quote_dict


async def listen_greeks(
    n_greeks: int,
    streamer: DXLinkStreamer
) -> dict[str, Greeks]:
    greeks_dict = {}
    async for greeks in streamer.listen(EventType.GREEKS):
        greeks_dict[greeks.eventSymbol] = greeks
        if len(greeks_dict) == n_greeks:
            return greeks_dict


async def listen_summaries(
    n_summaries: int,
    streamer: DXLinkStreamer
) -> dict[str, Quote]:
    summary_dict = {}
    async for summary in streamer.listen(EventType.SUMMARY):
        summary_dict[summary.eventSymbol] = summary
        if len(summary_dict) == n_summaries:
            return summary_dict


async def listen_trades(
    n_trades: int,
    streamer: DXLinkStreamer
) -> dict[str, Quote]:
    trade_dict = {}
    async for trade in streamer.listen(EventType.TRADE):
        trade_dict[trade.eventSymbol] = trade
        if len(trade_dict) == n_trades:
            return trade_dict


