"""
Agents for the backend.
"""

from typing import List, Dict, Tuple, Literal, TypedDict, Optional, Any
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
from backend.utils.prompts import (
    INTENTION_DETECTOR_PROMPT,
    INGREDIENT_EXTRACTOR_PROMPT,
    RECIPE_FORMATTER_PROMPT,
    SICA_SYSTEM_PROMPT,
)


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
                "role": "system",
                "content": SICA_SYSTEM_PROMPT,
            }
        ]

        chat_messages.extend(
            [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                }  # type: ignore[dict-item]
                for msg in messages
            ]
        )

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
        self.logger.debug("Extracting ingredients from user input")

        chat_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": INGREDIENT_EXTRACTOR_PROMPT,
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

            self.logger.debug(
                "Extracted ingredients",
                ingredient_count=len(content.split(",")),
                model=OPENAI_MODEL,
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

    def _score_recipe(self, recipe: Recipe, main_ingredients: List[str]) -> float:
        """
        Score a recipe based on ingredient usage and relevance.

        Args:
            recipe: Recipe to score.
            main_ingredients: List of main ingredients that should be featured.

        Returns:
            float: Score between 0 and 1, higher is better.
        """
        # Convert everything to lowercase for comparison
        main_ingredients_lower = [ing.lower() for ing in main_ingredients]
        used_ingredients = [
            ing["name"].lower() for ing in recipe.get("usedIngredients", [])
        ]
        missed_ingredients = [
            ing["name"].lower() for ing in recipe.get("missedIngredients", [])
        ]

        # Calculate basic scores
        main_ingredient_usage = sum(
            1
            for ing in used_ingredients
            if any(main in ing for main in main_ingredients_lower)
        )
        total_ingredients = len(used_ingredients) + len(missed_ingredients)
        used_ratio = (
            len(used_ingredients) / total_ingredients if total_ingredients > 0 else 0
        )

        # Penalize if none of the main ingredients are primary ingredients in the recipe title
        title_relevance = any(
            main in recipe["title"].lower() for main in main_ingredients_lower
        )

        # Combine scores with weights
        score = (
            0.4
            * main_ingredient_usage
            / len(main_ingredients)  # How many main ingredients are used
            + 0.3 * used_ratio  # Ratio of available to total ingredients
            + 0.3 * (1.0 if title_relevance else 0.0)  # Title relevance bonus
        )

        return score

    def find_recipe(self, ingredients: List[str]) -> Recipe:
        """
        Find a recipe based on available ingredients.

        Args:
            ingredients: List of available ingredients.

        Returns:
            Recipe: A recipe that can be made with the given ingredients.
        """
        self.logger.info("Searching for recipe")

        # Get more recipes to choose from
        recipes = get_recipe(ingredients, number=5, ranking=1)
        if not recipes:
            self.logger.error("No recipes found for the given ingredients")
            raise ValueError("No recipes found for the given ingredients")

        # Score and sort recipes
        scored_recipes = [
            (recipe, self._score_recipe(recipe, ingredients)) for recipe in recipes
        ]
        scored_recipes.sort(key=lambda x: x[1], reverse=True)

        self.logger.info(
            "Found and scored recipes",
            scores=[
                {"title": recipe["title"], "score": score}
                for recipe, score in scored_recipes
            ],
        )

        return scored_recipes[0][0]  # Return the highest scoring recipe


class RecipeFormatter:
    """
    Format recipe data into a structured format using AI.
    """

    def __init__(self) -> None:
        """Initialize the OpenAI client and logger."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.logger = StructuredLogger(__name__)

    def format_recipe(self, recipe: Recipe) -> Dict[str, Any]:
        """
        Format a recipe into a structured format.

        Args:
            recipe: Raw recipe data from Spoonacular API.

        Returns:
            Dict[str, Any]: Structured recipe data including title, ingredients,
                           instructions, cooking time, difficulty, and servings.
        """
        self.logger.info("Formatting recipe data")

        chat_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": RECIPE_FORMATTER_PROMPT,
            },
            {
                "role": "user",
                "content": str(recipe),  # Convert recipe dict to string
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

            # Parse the response into a dictionary
            formatted_recipe = eval(
                content
            )  # Note: In production, use json.loads with proper error handling

            self.logger.info(
                "Successfully formatted recipe",
                recipe_title=formatted_recipe.get("title"),
            )

            return formatted_recipe

        except Exception as e:
            self.logger.error(
                "Error formatting recipe",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


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

    def _clean_ingredient_name(self, name: str) -> str:
        """
        Clean ingredient name for API search.

        Args:
            name: Raw ingredient name from recipe.

        Returns:
            str: Cleaned ingredient name suitable for search.
        """
        # Remove everything after * or ( or ,
        name = name.split("*")[0].split("(")[0].split(",")[0]

        # Remove common unnecessary words
        unnecessary_words = ["slabs of", "pieces of", "of", "fresh", "whole"]
        for word in unnecessary_words:
            name = name.replace(word, "")

        # Clean up whitespace and strip
        name = " ".join(name.split())
        return name.strip()

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
            clean_name = self._clean_ingredient_name(ingredient["name"])
            price_data = get_product_price(clean_name, authentication_data=auth_data)
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
                product = price_info["data"][0]
                if product["items"]:
                    price = float(
                        product["items"][0].get("price", {}).get("regular", 0)
                    )
                    ingredient_costs[ingredient_name] = price
                    total_cost += price

        return total_cost, ingredient_costs


class RecipeSummarizer:
    """
    Create a dynamic, personality-driven summary of recipes using AI.
    """

    def __init__(self) -> None:
        """Initialize the clients and formatter."""
        self.logger = StructuredLogger(__name__)
        self.formatter = RecipeFormatter()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def summarize(
        self,
        recipe: Recipe,
        missing_ingredients: List[Ingredient],
        total_cost: float,
        ingredient_costs: Dict[str, float],
    ) -> str:
        """
        Create a dynamic, personality-driven summary of the recipe.

        Args:
            recipe: The recipe to summarize
            missing_ingredients: List of ingredients the user needs to buy
            total_cost: Total cost of missing ingredients
            ingredient_costs: Cost breakdown by ingredient

        Returns:
            str: A personalized summary of the recipe matching SiCa's personality
        """
        formatted_recipe = self.formatter.format_recipe(recipe)

        recipe_data = {
            "recipe": formatted_recipe,
            "missing_ingredients": [
                {"name": ing["name"], "cost": ingredient_costs.get(ing["name"], 0)}
                for ing in missing_ingredients
            ],
            "total_cost": total_cost,
        }

        chat_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": SICA_SYSTEM_PROMPT
                + "\nYour task is to create an engaging, personality-driven summary of a recipe. Include all important information like ingredients needed, costs, cooking instructions, but present it in your unique style. Make it fun and engaging while being informative.",
            },
            {
                "role": "user",
                "content": f"Please create a summary for this recipe and its required ingredients: {recipe_data}",
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
                "Successfully generated recipe summary",
                recipe_title=formatted_recipe.get("title"),
                summary_length=len(content),
            )

            return content

        except Exception as e:
            self.logger.error(
                "Error generating recipe summary",
                error=str(e),
                error_type=type(e).__name__,
            )
            return self._create_basic_summary(
                formatted_recipe, missing_ingredients, total_cost, ingredient_costs
            )

    def _create_basic_summary(
        self,
        formatted_recipe: Dict[str, Any],
        missing_ingredients: List[Ingredient],
        total_cost: float,
        ingredient_costs: Dict[str, float],
    ) -> str:
        """
        Create a basic summary as fallback if AI generation fails.

        Args:
            formatted_recipe: The formatted recipe data
            missing_ingredients: List of ingredients the user needs to buy
            total_cost: Total cost of missing ingredients
            ingredient_costs: Cost breakdown by ingredient

        Returns:
            str: A basic formatted summary
        """
        summary = f"**{formatted_recipe['title']} Recipe Summary**\n\n"
        return summary


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
            str: The detected intention, one of:
                - 'ingredients': User is listing ingredients they have
                - 'recipe_search': User is asking what they can make with ingredients
                - 'other': User has a different request
        """
        # self.logger.info("Detecting user intention")

        chat_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": INTENTION_DETECTOR_PROMPT,
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

            # Strip any whitespace and quotes
            intention = content.lower().strip().strip("'\"")

            self.logger.debug(
                "Successfully detected user intention",
                intention=intention,
                model=OPENAI_MODEL,
            )
            return intention

        except Exception as e:
            self.logger.error(
                "Error detecting user intention",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
