"""
Agents for the backend.
"""

from typing import List, Dict, Tuple, Literal, TypedDict, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
import os

from backend.utils.config import OPENAI_MODEL
from backend.utils.spoonacular import get_recipe
from backend.utils.spoonacular.interfaces import Recipe, Ingredient
from backend.utils.kroger import authenticate_kroger, get_product_price
from backend.utils.kroger.interfaces import KrogerProductSearchResponse
from backend.utils.logging import StructuredLogger


class Message(TypedDict):
    """Type definition for chat message."""

    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str]
    function_call: Optional[Dict]
    tool_calls: Optional[List]
    tool_call_id: Optional[str]


class GeneralAssistant:
    """
    A general assistant that can answer questions and help with tasks.
    """

    def __init__(self) -> None:
        """Initialize the OpenAI client and logger."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.logger = StructuredLogger(__name__)

    def get_completion(self, messages: List[Message]) -> str:
        """
        Get completion from OpenAI API.

        Args:
            messages: List of message dictionaries with role and content.

        Returns:
            str: The assistant's response.
        """
        self.logger.info(
            "Requesting completion from OpenAI",
            model=OPENAI_MODEL,
            message_count=len(messages),
        )

        chat_messages: List[ChatCompletionMessageParam] = [
            {
                "role": msg["role"],
                "content": msg["content"],
            }  # type: ignore[dict-item]
            for msg in messages
        ]

        try:
            response: ChatCompletion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=chat_messages,
                temperature=0.7,
            )

            content = response.choices[0].message.content
            if content is None:
                self.logger.error("Received empty response from OpenAI")
                raise ValueError("Received empty response from OpenAI")

            self.logger.info(
                "Successfully received completion from OpenAI",
                response_length=len(content),
            )
            return content

        except Exception as e:
            self.logger.error(
                "Error getting completion from OpenAI",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class IngredientExtractor:
    """
    Extract ingredients from a user input.
    """

    def __init__(self) -> None:
        """Initialize the OpenAI client and logger."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.logger = StructuredLogger(__name__)

    def extract_ingredients(self, user_input: str) -> List[str]:
        """
        Extract ingredients from user input.

        Args:
            user_input: Raw user input describing their ingredients.

        Returns:
            List[str]: List of extracted ingredients.
        """
        self.logger.info("Extracting ingredients from user input")

        chat_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "Extract ingredients from the user's input and return them as a comma-separated list. Only include the ingredient names, no quantities.",
            },
            {
                "role": "user",
                "content": user_input,
            },
        ]

        try:
            response: ChatCompletion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=chat_messages,
                temperature=0.3,
            )

            content = response.choices[0].message.content
            if content is None:
                self.logger.error("Received empty response from OpenAI")
                raise ValueError("Received empty response from OpenAI")

            self.logger.info(
                "Successfully extracted ingredients from user input",
                ingredient_count=len(content.split(",")),
            )
            return [ing.strip() for ing in content.split(",")]

        except Exception as e:
            self.logger.error(
                "Error extracting ingredients from user input",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class RecipeFinder:
    """
    Find recipes based on ingredients.
    """

    def __init__(self) -> None:
        """Initialize the logger."""
        self.logger = StructuredLogger(__name__)

    def find_recipe(self, ingredients: List[str]) -> Recipe:
        """
        Find a recipe based on available ingredients.

        Args:
            ingredients: List of available ingredients.

        Returns:
            Recipe: A recipe that can be made with the given ingredients.
        """
        self.logger.info("Searching for recipe")

        recipes = get_recipe(ingredients, number=1, ranking=2)
        if not recipes:
            self.logger.error("No recipes found for the given ingredients")
            raise ValueError("No recipes found for the given ingredients")
        return recipes[0]


class RecipeAdjuster:
    """
    Adjust the recipe based on the missing ingredients.
    """

    def get_missing_ingredients(
        self, recipe: Recipe, available_ingredients: List[str]
    ) -> List[Ingredient]:
        """
        Identify missing ingredients from a recipe.

        Args:
            recipe: Recipe object containing all required ingredients.
            available_ingredients: List of ingredients the user has.

        Returns:
            List[Ingredient]: List of missing ingredients.
        """
        # Convert available ingredients to lowercase for case-insensitive comparison
        available_ingredients_lower = [ing.lower() for ing in available_ingredients]

        # Get missing ingredients from the recipe
        missing_ingredients = recipe.get("missedIngredients", [])

        # Additional check to ensure the ingredient is actually missing
        return [
            ing
            for ing in missing_ingredients
            if ing["name"].lower() not in available_ingredients_lower
        ]


class PriceFetcher:
    """
    Fetch the price of ingredients from a grocery store.
    """

    def get_prices(
        self, ingredients: List[Ingredient]
    ) -> List[Tuple[str, KrogerProductSearchResponse]]:
        """
        Get prices for a list of ingredients.

        Args:
            ingredients: List of ingredients to price.

        Returns:
            List[Tuple[str, KrogerProductSearchResponse]]: List of ingredient names and their price data.
        """
        auth_data = authenticate_kroger()

        prices = []
        for ingredient in ingredients:
            price_data = get_product_price(
                ingredient["name"], authentication_data=auth_data
            )
            prices.append((ingredient["name"], price_data))

        return prices


class CostCalculator:
    """
    Calculate the total cost of a recipe.
    """

    def calculate_total_cost(
        self, price_data: List[Tuple[str, KrogerProductSearchResponse]]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate the total cost of ingredients.

        Args:
            price_data: List of tuples containing ingredient names and their price data.

        Returns:
            Tuple[float, Dict[str, float]]: Total cost and individual ingredient costs.
        """
        ingredient_costs = {}
        total_cost = 0.0

        for ingredient_name, price_info in price_data:
            if price_info["data"]:
                # Get the first product's price
                product = price_info["data"][0]
                if product["items"]:
                    # You might want to add more sophisticated price extraction logic here
                    price = float(
                        product["items"][0].get("price", {}).get("regular", 0)
                    )
                    ingredient_costs[ingredient_name] = price
                    total_cost += price

        return total_cost, ingredient_costs


class RecipeSummarizer:
    """
    Summarize a recipe.
    """

    def __init__(self) -> None:
        """Initialize the OpenAI client and logger."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.logger = StructuredLogger(__name__)

    def summarize(
        self,
        recipe: Recipe,
        missing_ingredients: List[Ingredient],
        total_cost: float,
        ingredient_costs: Dict[str, float],
    ) -> str:
        """
        Create a user-friendly summary of the recipe and costs.

        Args:
            recipe: The recipe to summarize.
            missing_ingredients: List of missing ingredients.
            total_cost: Total cost of missing ingredients.
            ingredient_costs: Dictionary of ingredient costs.

        Returns:
            str: A formatted summary of the recipe and costs.
        """
        self.logger.info("Generating recipe summary")

        chat_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "Create a friendly summary of the recipe, including the title, missing ingredients, and their costs.",
            },
            {
                "role": "user",
                "content": f"""
                Recipe: {recipe['title']}
                Missing Ingredients: {', '.join(ing['name'] for ing in missing_ingredients)}
                Individual Costs: {ingredient_costs}
                Total Cost: ${total_cost:.2f}
                """,
            },
        ]

        try:
            response: ChatCompletion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=chat_messages,
                temperature=0.7,
            )

            content = response.choices[0].message.content
            if content is None:
                self.logger.error("Received empty response from OpenAI")
                raise ValueError("Received empty response from OpenAI")

            self.logger.info(
                "Successfully generated recipe summary", response_length=len(content)
            )
            return content

        except Exception as e:
            self.logger.error(
                "Error generating recipe summary",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class IntentionDetector:
    """
    Detect the user's intention.
    """

    def __init__(self) -> None:
        """Initialize the OpenAI client and logger."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.logger = StructuredLogger(__name__)

    def detect_intention(self, user_input: str) -> str:
        """
        Detect the user's intention from their input.

        Args:
            user_input: The user's input message.

        Returns:
            str: The detected intention.
        """
        self.logger.info("Detecting user intention")

        chat_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "Detect if the user is listing ingredients or asking for something else. Return either 'ingredients' or 'other'.",
            },
            {
                "role": "user",
                "content": user_input,
            },
        ]

        try:
            response: ChatCompletion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=chat_messages,
                temperature=0.3,
            )

            content = response.choices[0].message.content
            if content is None:
                self.logger.error("Received empty response from OpenAI")
                raise ValueError("Received empty response from OpenAI")

            self.logger.info(
                "Successfully detected user intention", intention=content.lower()
            )
            return content.lower()

        except Exception as e:
            self.logger.error(
                "Error detecting user intention",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
