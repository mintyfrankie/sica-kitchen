from typing import List, TypedDict


class Ingredient(TypedDict):
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


SpoonacularSearchResponse = List[Recipe]
