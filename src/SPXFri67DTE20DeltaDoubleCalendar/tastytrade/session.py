import httpx
from typing import Any, Dict, List, Optional, Union
import json
import boto3
import logging

from tastytrade import API_URL
from tastytrade.utils import validate_response

logger = logging.getLogger(__name__)

class Session:
    SSM_SESSION_PARAM_NAME = '/tastytrade/session_data'
    SSM_CREDENTIALS_PARAM_NAME = '/tastytrade/credentials'

    def __init__(self):
        logger.debug("Initializing session")
        self.ssm = boto3.client('ssm')
        credentials = json.loads(self.ssm.get_parameter(Name=self.SSM_CREDENTIALS_PARAM_NAME, WithDecryption=True)['Parameter']['Value'])
        
        logger.debug("Attempting to retrieve cached session data")
        try:
            session_data_str = self.ssm.get_parameter(Name=self.SSM_SESSION_PARAM_NAME, WithDecryption=True)['Parameter']['Value']
            session_data = json.loads(session_data_str)
            logger.debug("cached session data found")
        except self.ssm.exceptions.ParameterNotFound:
            logger.debug("no cached session data found")
            session_data = {}

        # try to initialize from session data
        self.session_token = session_data.get('session_token')
        self.streamer_token = session_data.get('streamer_token')
        self.dxlink_url = session_data.get('dxlink_url')

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        if self.session_token:
            headers["authorization"] = self.session_token
        self.sync_client = httpx.Client(base_url=API_URL, headers=headers)

        if not self.session_token:
            logger.info("no session token found, performing full initialization")
            self._full_init(credentials)
        elif not self.validate():
            logger.info("session token invalid, performing full initialization")
            self._full_init(credentials)
        else:
            logger.info("using cached session data")

    def _full_init(self, credentials):
        logger.debug("starting full initialization")
        body = {
            "login": credentials['username'],
            "password": credentials['password']
        }
        response = self.sync_client.post("/sessions", json=body)
        validate_response(response)

        json_data = response.json()
        # self.user = user(**json_data["data"]["user"])
        self.session_token = json_data["data"]["session-token"]
        self.sync_client.headers.update({"authorization": self.session_token})

        logger.debug("session created, retrieving streamer token")
        data = self._get("/quote-streamer-tokens")
        self.streamer_token = data["token"]
        self.dxlink_url = data["dxlink-url"]

        logger.debug("caching session data")
        session_data_str = json.dumps({
            'session_token': self.session_token,
            'streamer_token': self.streamer_token,
            'dxlink_url': self.dxlink_url,
            # 'user': self.user.dict() if self.user else none,
        })
        self.ssm.put_parameter(Name=self.SSM_SESSION_PARAM_NAME, Value=session_data_str, Type='SecureString', Overwrite=True)
        logger.debug("full initialization complete")

    def validate(self):
        logger.debug("validating session")
        response = self.sync_client.post("/sessions/validate")
        is_valid = response.status_code == 200 or response.status_code == 201 # gets 201 for some reason
        logger.debug(f"session is {'valid' if is_valid else 'invalid'}")
        return is_valid

    def _get(self, url, **kwargs):
        logger.info(f"making get request to {url}")
        response = self.sync_client.get(url, timeout=30, **kwargs)
        validate_response(response)
        return response.json()["data"]

    def _delete(self, url, **kwargs) -> None:
        response = self.sync_client.delete(url, **kwargs)
        validate_response(response)

    def _post(self, url, **kwargs) -> Dict[str, Any]:
        response = self.sync_client.post(url, **kwargs)
        return self._validate_and_parse(response)

    def _validate_and_parse(self, response: httpx._models.Response) -> Dict[str, Any]:
        validate_response(response)
        return response.json()["data"]