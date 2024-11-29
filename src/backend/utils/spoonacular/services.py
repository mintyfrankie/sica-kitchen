"""
Functions to interact with Spoonacular API.

This module provides functions to interact with the Spoonacular API,
including recipe search and detailed recipe information retrieval.
"""

import httpx
import os
from typing import Optional, List

from backend.utils.spoonacular.interfaces import (
    RecipeInformation,
    Recipe,
)


def get_recipe(
    ingredients: List[str], number: int = 1, ranking: int = 1
) -> List[Recipe]:
    """
    Get recipes from Spoonacular API based on available ingredients.

    Args:
        ingredients: List of ingredient names to search with
        number: Number of recipes to return (default: 1)
        ranking: Sort mode for recipes:
                1 = maximize used ingredients
                2 = minimize missing ingredients

    Returns:
        List[Recipe]: List of recipes matching the ingredients

    Raises:
        ValueError: If SPOONACULAR_API_KEY is not set
        httpx.HTTPError: If the API request fails
    """
    ENDPOINT = "https://api.spoonacular.com/recipes/findByIngredients"
    API_KEY = os.getenv("SPOONACULAR_API_KEY")
    if not API_KEY:
        raise ValueError("SPOONACULAR_API_KEY is not set")

    params = {
        "ingredients": ingredients,
        "number": number,
        "ranking": ranking,
        "apiKey": API_KEY,
    }

    response = httpx.get(ENDPOINT, params=params)
    response.raise_for_status()
    return response.json()


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
