"""
Interfaces for external APIs and services.
"""

from typing import List, Optional, TypedDict, Literal


class KrogerAuthenticationResponse(TypedDict):
    """
    Response from Kroger API authentication.
    Endpoint: https://api.kroger.com/v1/connect/oauth2/token
    """

    access_token: str
    expires_in: int
    expired_at: float
    token_type: str


class ImageSize(TypedDict):
    size: str
    url: str


class Image(TypedDict):
    perspective: str
    featured: Optional[bool]
    sizes: List[ImageSize]


class Fulfillment(TypedDict):
    curbside: bool
    delivery: bool
    inStore: bool
    shipToHome: bool


class Item(TypedDict):
    itemId: str
    favorite: bool
    fulfillment: Fulfillment
    size: str


class Temperature(TypedDict):
    indicator: Literal["Ambient"]
    heatSensitive: bool


class Product(TypedDict):
    productId: str
    upc: str
    productPageURI: str
    aisleLocations: List[str]
    brand: Optional[str]
    categories: List[str]
    countryOrigin: str
    description: str
    images: List[Image]
    items: List[Item]
    itemInformation: dict
    temperature: Temperature


class Pagination(TypedDict):
    start: int
    limit: int
    total: int


class Meta(TypedDict):
    pagination: Pagination


class KrogerProductSearchResponse(TypedDict):
    """
    Response from Kroger API.
    """

    data: List[Product]
    meta: Meta
