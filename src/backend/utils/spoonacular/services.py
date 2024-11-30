"""
Functions to interact with Spoonacular API.

This module provides functions to interact with the Spoonacular API,
including recipe search and detailed recipe information retrieval.
"""

import httpx
import os
from typing import Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.utils.spoonacular.interfaces import (
    RecipeInformation,
    Recipe,
)
from backend.utils.logging import StructuredLogger

logger = StructuredLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True,
)
def get_recipe(
    ingredients: List[str], number: int = 1, ranking: int = 1, timeout: float = 30.0
) -> List[Recipe]:
    """
    Get recipes from Spoonacular API based on available ingredients.

    Args:
        ingredients: List of ingredient names to search with
        number: Number of recipes to return (default: 1)
        ranking: Sort mode for recipes:
                1 = maximize used ingredients
                2 = minimize missing ingredients
        timeout: Timeout in seconds for the API request (default: 30.0)

    Returns:
        List[Recipe]: List of recipes matching the ingredients

    Raises:
        ValueError: If SPOONACULAR_API_KEY is not set
        httpx.HTTPError: If the API request fails
        httpx.TimeoutException: If the request times out
    """
    ENDPOINT = "https://api.spoonacular.com/recipes/findByIngredients"
    API_KEY = os.getenv("SPOONACULAR_API_KEY")
    if not API_KEY:
        raise ValueError("SPOONACULAR_API_KEY is not set")

    params = {
        "ingredients": ",".join(ingredients),  # Join ingredients with commas
        "number": number,
        "ranking": ranking,
        "apiKey": API_KEY,
    }

    try:
        logger.info(
            "Making request to Spoonacular API",
            endpoint=ENDPOINT,
            ingredient_count=len(ingredients),
            number=number,
        )

        with httpx.Client(timeout=timeout) as client:
            response = client.get(ENDPOINT, params=params)
            response.raise_for_status()

        logger.info(
            "Successfully retrieved recipes from Spoonacular",
            recipe_count=len(response.json()),
        )

        return response.json()

    except httpx.TimeoutException as e:
        logger.error(
            "Timeout while fetching recipes from Spoonacular",
            error=str(e),
            timeout=timeout,
        )
        raise

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error while fetching recipes from Spoonacular",
            error=str(e),
            status_code=e.response.status_code,
        )
        raise

    except Exception as e:
        logger.error(
            "Unexpected error while fetching recipes from Spoonacular",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


def get_recipe_information(recipe_id: int) -> Optional[RecipeInformation]:
    """
    Get detailed recipe information including instructions.

    Args:
        recipe_id: The Spoonacular recipe ID

    Returns:
        Optional[RecipeInformation]: Detailed recipe information or None if not found

    Raises:
        ValueError: If SPOONACULAR_API_KEY is not set
        httpx.HTTPError: If the API request fails (except 404)
    """
    ENDPOINT = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    API_KEY = os.getenv("SPOONACULAR_API_KEY")
    if not API_KEY:
        raise ValueError("SPOONACULAR_API_KEY is not set")

    params = {
        "apiKey": API_KEY,
    }

    response = httpx.get(ENDPOINT, params=params)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()
