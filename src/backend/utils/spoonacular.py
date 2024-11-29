"""
Functions to interact with Spoonacular API.
"""

import httpx
import os


def get_recipe(ingredients: list[str], number: int = 1, ranking: int = 1) -> dict:
    """
    Get a recipe from Spoonacular API.
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
