"""
Orchestrator for the recipe chatbot workflow.
"""

from typing import Dict, Any, List, cast
from dataclasses import dataclass

from backend.agents import (
    GeneralAssistant,
    IngredientExtractor,
    RecipeFinder,
    RecipeAdjuster,
    PriceFetcher,
    CostCalculator,
    RecipeSummarizer,
    IntentionDetector,
    Message,
)


@dataclass
class ChatbotResponse:
    """Container for chatbot response data."""

    message: str
    data: Dict[str, Any]


class RecipeChatbot:
    """
    Orchestrates the recipe chatbot workflow.
    """

    def __init__(self) -> None:
        """Initialize all required agents."""
        self.general_assistant = GeneralAssistant()
        self.ingredient_extractor = IngredientExtractor()
        self.recipe_finder = RecipeFinder()
        self.recipe_adjuster = RecipeAdjuster()
        self.price_fetcher = PriceFetcher()
        self.cost_calculator = CostCalculator()
        self.recipe_summarizer = RecipeSummarizer()
        self.intention_detector = IntentionDetector()
        self.conversation_state: Dict[str, Any] = {}

    def process_message(self, user_input: str) -> ChatbotResponse:
        """
        Process user input and return appropriate response.

        Args:
            user_input: The user's input message.

        Returns:
            ChatbotResponse: Containing the response message and any relevant data.
        """
        intention = self.intention_detector.detect_intention(user_input)

        if intention == "ingredients":
            # Extract ingredients from user input
            ingredients = self.ingredient_extractor.extract_ingredients(user_input)
            self.conversation_state["available_ingredients"] = ingredients

            # Find recipe based on ingredients
            recipe = self.recipe_finder.find_recipe(ingredients)
            self.conversation_state["recipe"] = recipe

            # Get missing ingredients
            missing_ingredients = self.recipe_adjuster.get_missing_ingredients(
                recipe, ingredients
            )
            self.conversation_state["missing_ingredients"] = missing_ingredients

            # Get prices for missing ingredients
            price_data = self.price_fetcher.get_prices(missing_ingredients)

            # Calculate total cost
            total_cost, ingredient_costs = self.cost_calculator.calculate_total_cost(
                price_data
            )

            # Create summary
            summary = self.recipe_summarizer.summarize(
                recipe, missing_ingredients, total_cost, ingredient_costs
            )

            return ChatbotResponse(
                message=summary,
                data={
                    "recipe": recipe,
                    "missing_ingredients": missing_ingredients,
                    "total_cost": total_cost,
                    "ingredient_costs": ingredient_costs,
                },
            )
        else:
            # Handle general conversation
            messages: List[Message] = [
                cast(
                    Message,
                    {
                        "role": "user",
                        "content": user_input,
                        "name": None,
                        "function_call": None,
                        "tool_calls": None,
                        "tool_call_id": None,
                    },
                )
            ]
            response = self.general_assistant.get_completion(messages)
            return ChatbotResponse(message=response, data={})


if __name__ == "__main__":
    chatbot = RecipeChatbot()
    print(chatbot.process_message("I have some chicken and onions. What can I make?"))
