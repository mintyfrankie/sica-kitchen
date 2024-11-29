"""
Type definitions for Spoonacular API responses.

This module defines the type interfaces for the Spoonacular API responses,
making it easier to work with the API data in a type-safe manner.
"""

from typing import List, TypedDict, Optional

__all__ = [
    "Ingredient",
    "Recipe",
    "RecipeStep",
    "RecipeInformation",
    "SpoonacularSearchResponse",
]


class Ingredient(TypedDict):
    """
    Type definition for ingredient information from Spoonacular API.

    Attributes:
        id: Unique identifier for the ingredient
        amount: Quantity of the ingredient
        unit: Unit of measurement
        unitLong: Full name of the unit
        unitShort: Abbreviated unit name
        aisle: Grocery store aisle
        name: Ingredient name
        original: Original ingredient text
        originalName: Original ingredient name
        meta: Additional ingredient metadata
        image: URL to ingredient image
    """

    id: int
    amount: float
    unit: str
    unitLong: str
    unitShort: str
    aisle: str
    name: str
    original: str
    originalName: str
    meta: List[str]
    image: str


class Recipe(TypedDict):
    """
    Type definition for recipe information from findByIngredients endpoint.

    Attributes:
        id: Unique recipe identifier
        title: Recipe title
        image: URL to recipe image
        imageType: Image file type
        usedIngredientCount: Number of user's ingredients used
        missedIngredientCount: Number of missing ingredients
        missedIngredients: List of missing ingredients
        usedIngredients: List of user's ingredients used
        unusedIngredients: List of user's ingredients not used
        likes: Number of recipe likes
    """

    id: int
    title: str
    image: str
    imageType: str
    usedIngredientCount: int
    missedIngredientCount: int
    missedIngredients: List[Ingredient]
    usedIngredients: List[Ingredient]
    unusedIngredients: List[Ingredient]
    likes: int


class RecipeStep(TypedDict):
    """
    Type definition for a single step in recipe instructions.

    Attributes:
        number: Step number
        step: Step instructions
        ingredients: List of ingredients used in this step
        equipment: List of equipment needed for this step
        length: Optional timing information for this step
    """

    number: int
    step: str
    ingredients: List[Ingredient]
    equipment: List[dict]
    length: Optional[dict]


class RecipeInformation(TypedDict):
    """
    Type definition for detailed recipe information.

    Attributes:
        id: Unique recipe identifier
        title: Recipe title
        summary: Recipe description and summary
        instructions: Full cooking instructions
        analyzedInstructions: Structured step-by-step instructions
        readyInMinutes: Total preparation time
        servings: Number of servings
        sourceUrl: Original recipe source URL
    """

    id: int
    title: str
    summary: str
    instructions: str
    analyzedInstructions: List[dict]
    readyInMinutes: int
    servings: int
    sourceUrl: Optional[str]


# Type alias for the response from findByIngredients endpoint
SpoonacularSearchResponse = List[Recipe]
