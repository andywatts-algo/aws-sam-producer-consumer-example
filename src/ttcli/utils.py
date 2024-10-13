import getpass
import logging
import os
import pickle
import shutil
from configparser import ConfigParser
from datetime import date
from decimal import Decimal
from importlib.resources import as_file, files
from typing import Optional

from rich import print as rich_print
from tastytrade import Account, NestedFutureOptionChain, NestedOptionChain, Session, get_tasty_monthly
from tastytrade.instruments import NestedOptionChainExpiration, NestedFutureOptionChainExpiration
from tastytrade.order import NewOrder, PlacedOrderResponse

logger = logging.getLogger(__name__)
VERSION = '0.2'
ZERO = Decimal(0)

CONTEXT_SETTINGS = {'help_option_names': ['-h', '--help']}

CUSTOM_CONFIG_PATH = '.config/ttcli/ttcli.cfg'
TOKEN_PATH = '.config/ttcli/.session'


def print_error(msg: str):
    rich_print(f'[bold red]Error: {msg}[/bold red]')


def print_warning(msg: str):
    rich_print(f'[light_coral]Warning: {msg}[/light_coral]')


def test_order_handle_errors(
    account: Account,
    session: 'RenewableSession',
    order: NewOrder
) -> Optional[PlacedOrderResponse]:
    url = f'{session.base_url}/accounts/{account.account_number}/orders/dry-run'
    json = order.model_dump_json(exclude_none=True, by_alias=True)
    response = session.client.post(url, data=json)
    # modified to use our error handling
    if response.status_code // 100 != 2:
        content = response.json()['error']
        print_error(f"{content['message']}")
        errors = content.get('errors')
        if errors is not None:
            for error in errors:
                if "code" in error:
                    print_error(f"{error['message']}")
                else:
                    print_error(f"{error['reason']}")
        return None
    else:
        data = response.json()['data']
        return PlacedOrderResponse(**data)


class RenewableSession(Session):
    def __init__(self):
        custom_path = os.path.join(os.path.expanduser('~'), CUSTOM_CONFIG_PATH)
        data_file = files('ttcli.data').joinpath('ttcli.cfg')
        token_path = os.path.join(os.path.expanduser('~'), TOKEN_PATH)

        logged_in = False
        # try to load token
        if os.path.exists(token_path):
            with open(token_path, 'rb') as f:
                self.__dict__ = pickle.load(f)

            # make sure token hasn't expired
            logged_in = self.validate()

        # load config
        self.config = ConfigParser()
        if not os.path.exists(custom_path):
            with as_file(data_file) as path:
                # copy default config to user home dir
                os.makedirs(os.path.dirname(custom_path), exist_ok=True)
                shutil.copyfile(path, custom_path)
                self.config.read(path)
        self.config.read(custom_path)

        if not logged_in:
            # either the token expired or doesn't exist
            username, password = self._get_credentials()
            Session.__init__(self, username, password)

            accounts = Account.get_accounts(self)
            self.accounts = [acc for acc in accounts if not acc.is_closed]
            # write session token to cache
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'wb') as f:
                pickle.dump(self.__dict__, f)
            logger.debug('Logged in with new session, cached for next login.')
        else:
            logger.debug('Logged in with cached session.')

    def _get_credentials(self):
        username = os.getenv('TT_USERNAME')
        password = os.getenv('TT_PASSWORD')
        if self.config.has_section('general'):
            username = username or self.config['general'].get('username')
            password = password or self.config['general'].get('password')

        if not username or not password:
            raise ValueError("TT_USERNAME and TT_PASSWORD environment variables or config values must be set")

        return username, password

    def get_account(self) -> Account:
        return self.accounts[0]


def is_monthly(day: date) -> bool:
    return day.weekday() == 4 and 15 <= day.day <= 21


def round_to_width(x, base=Decimal(1)):
    return base * round(x / base)


def choose_expiration(
    chain: NestedOptionChain,
    include_weeklies: bool = False
) -> NestedOptionChainExpiration:
    exps = [e for e in chain.expirations]
    if not include_weeklies:
        exps = [e for e in exps if is_monthly(e.expiration_date)]
    exps.sort(key=lambda e: e.expiration_date)
    default = get_tasty_monthly()
    default_option = None
    for i, exp in enumerate(exps):
        if exp.expiration_date == default:
            default_option = exp
            print(f'{i + 1}) {exp.expiration_date} (default)')
        else:
            print(f'{i + 1}) {exp.expiration_date}')
    choice = 0
    while choice not in range(1, len(exps) + 1):
        try:
            raw = input('Please choose an expiration: ')
            choice = int(raw)
        except ValueError:
            return default_option

    return exps[choice - 1]


def choose_futures_expiration(
    chain: NestedFutureOptionChain,
    include_weeklies: bool = False
) -> NestedFutureOptionChainExpiration:
    chain = chain.option_chains[0]
    if include_weeklies:
        exps = [e for e in chain.expirations]
    else:
        exps = [e for e in chain.expirations if e.expiration_type != 'Weekly']
    exps.sort(key=lambda e: e.expiration_date)
    # find closest to 45 DTE
    default = min(exps, key=lambda e: abs(e.days_to_expiration - 45))
    for i, exp in enumerate(exps):
        if exp == default:
            print(f'{i + 1}) {exp.expiration_date} [{exp.underlying_symbol}] (default)')
        else:
            print(f'{i + 1}) {exp.expiration_date} [{exp.underlying_symbol}]')
    choice = 0
    while choice not in range(1, len(exps) + 1):
        try:
            raw = input('Please choose an expiration: ')
            choice = int(raw)
        except ValueError:
            return default

    return exps[choice - 1]








