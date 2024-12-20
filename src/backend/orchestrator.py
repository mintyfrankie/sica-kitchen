"""
Orchestrator for the recipe chatbot workflow.
"""

from typing import Dict, Any, List, cast, Callable
from dataclasses import dataclass
import time
import logging
from functools import wraps

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
from backend.utils.logging import StructuredLogger


@dataclass
class ChatbotResponse:
    """Container for chatbot response data."""

    message: str
    data: Dict[str, Any]


def log_execution(log_type: str, message: str) -> None:
    """
    Log execution details to Streamlit's session state if available.

    Args:
        log_type: Type of log entry (agent, api, info)
        message: Log message to display
    """
    logger = StructuredLogger(__name__)
    logger.info(message, context={"log_type": log_type})


def log_step(step_type: str) -> Callable:
    """
    Decorator to log execution steps.

    Args:
        step_type: Type of step being logged
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StructuredLogger(__name__)
            logger.info(
                f"Starting {func.__name__}",
                context={"step_type": step_type, "action": "start"},
            )
            result = func(*args, **kwargs)
            logger.info(
                f"Completed {func.__name__}",
                context={"step_type": step_type, "action": "complete"},
            )
            return result

        return wrapper

    return decorator


class RecipeChatbot:
    """
    Orchestrates the recipe chatbot workflow.
    """

    def __init__(self) -> None:
        """Initialize all required agents and logger."""
        # Initialize logger
        self.logger = StructuredLogger(__name__)

        # Initialize agents
        self.logger.info("Initializing chatbot agents")
        self.general_assistant = GeneralAssistant()
        self.ingredient_extractor = IngredientExtractor()
        self.recipe_finder = RecipeFinder()
        self.recipe_adjuster = RecipeAdjuster()
        self.price_fetcher = PriceFetcher()
        self.cost_calculator = CostCalculator()
        self.recipe_summarizer = RecipeSummarizer()
        self.intention_detector = IntentionDetector()
        self.conversation_state: Dict[str, Any] = {}
        self.logger.info("Chatbot initialization complete")

    @log_step("agent")
    def process_message(self, user_input: str) -> ChatbotResponse:
        """
        Process user input and return appropriate response.

        Args:
            user_input: The user's input message.

        Returns:
            ChatbotResponse: Containing the response message and any relevant data.
        """
        start_time = time.time()

        # Detect intention
        intention = self.intention_detector.detect_intention(user_input)
        self.logger.info("Detected intention", intention=intention)

        if intention in ["ingredients", "recipe_search"]:
            self.logger.set_context(workflow="recipe_search")

            # Extract ingredients
            ingredients = self.ingredient_extractor.extract_ingredients(user_input)
            self.conversation_state["available_ingredients"] = ingredients

            # Find recipe
            recipe = self.recipe_finder.find_recipe(ingredients)
            self.conversation_state["recipe"] = recipe

            # Get missing ingredients
            missing_ingredients = self.recipe_adjuster.get_missing_ingredients(
                recipe, ingredients
            )
            self.conversation_state["missing_ingredients"] = missing_ingredients

            # Get prices
            price_data = self.price_fetcher.get_prices(missing_ingredients)

            # Calculate costs
            total_cost, ingredient_costs = self.cost_calculator.calculate_total_cost(
                price_data
            )

            # Create summary
            summary = self.recipe_summarizer.summarize(
                recipe, missing_ingredients, total_cost, ingredient_costs
            )

            processing_time = time.time() - start_time
            self.logger.info(
                "Recipe workflow complete",
                processing_time=f"{processing_time:.2f}s",
                recipe_title=recipe["title"],
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
            self.logger.set_context(workflow="general_conversation")
            self.logger.info("Handling general conversation")

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

            processing_time = time.time() - start_time
            self.logger.info(
                "Message processing complete", processing_time=f"{processing_time:.2f}s"
            )

            return ChatbotResponse(message=response, data={})


if __name__ == "__main__":
    from backend.utils.logging import setup_logging

    setup_logging(level=logging.INFO)

    chatbot = RecipeChatbot()
    print(chatbot.process_message("I have some chicken and onions. What can I make?"))
