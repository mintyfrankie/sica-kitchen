"""
Functions to interact with Kroger API.
"""

import httpx
import os
from base64 import b64encode

from time import time

from backend.utils.interfaces import (
    KrogerAuthenticationResponse,
    KrogerProductSearchResponse,
)


def authenticate_kroger() -> KrogerAuthenticationResponse:
    """
    Authenticate with Kroger API.
    """

    ENDPOINT = "https://api.kroger.com/v1/connect/oauth2/token"
    CLIENT_ID = os.getenv("KROGER_CLIENT_ID")
    CLIENT_SECRET = os.getenv("KROGER_CLIENT_SECRET")

    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("KROGER_CLIENT_ID and KROGER_CLIENT_SECRET must be set")

    credentials = b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "product.compact",
    }

    response = httpx.post(ENDPOINT, headers=headers, data=data)
    response.raise_for_status()
    response_data: KrogerAuthenticationResponse = response.json()
    response_data["expired_at"] = time() + response_data["expires_in"]
    return response_data


def get_product_price(
    ingredient: str,
    authentication_data: KrogerAuthenticationResponse,
    location_id: str = "01400722",
    limit: int = 1,
) -> KrogerProductSearchResponse:
    """
    Get the price of a product from Kroger API.
    """

    ENDPOINT = "https://api.kroger.com/v1/products"
    ACCESS_TOKEN = authentication_data["access_token"]

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    params = {
        "filter.term": ingredient,
        "filter.limit": limit,
        "filter.locationId": location_id,
    }

    response = httpx.get(ENDPOINT, headers=headers, params=params)
    response.raise_for_status()
    return response.json()
