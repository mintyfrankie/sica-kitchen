"""
Streamlit interface for the recipe chatbot with execution logging.
"""

import streamlit as st
from typing import Dict, Any
import queue

from backend.orchestrator import RecipeChatbot, ChatbotResponse
from frontend.utils.log_displayer import setup_logging_handler, display_logs


def initialize_session_state() -> None:
    """Initialize the session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = RecipeChatbot()
    if "log_queue" not in st.session_state:
        st.session_state.log_queue = queue.Queue()
        setup_logging_handler()


def display_recipe_data(data: Dict[str, Any]) -> None:
    """Display recipe data in a structured format."""
    if not data:
        return

    if "recipe" in data:
        recipe = data["recipe"]
        with st.expander("Recipe Details", expanded=True):
            if "image" in recipe:
                st.image(recipe["image"], caption=recipe["title"])
            if "missedIngredients" in recipe:
                st.subheader("Required Ingredients")
                for ing in recipe["missedIngredients"]:
                    st.write(f"- {ing['name']}")

    if "total_cost" in data:
        with st.expander("Cost Breakdown", expanded=True):
            st.subheader("Shopping List")
            st.write(f"Total Cost: ${data['total_cost']:.2f}")
            if "ingredient_costs" in data:
                for ing, cost in data["ingredient_costs"].items():
                    st.write(f"- {ing}: ${cost:.2f}")


def handle_user_input(prompt: str) -> None:
    """Process user input and display the chatbot response."""
    st.session_state.logs = []
    st.session_state.displayed_logs = set()

    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response: ChatbotResponse = st.session_state.chatbot.process_message(prompt)
            st.write(response.message)
            if response.data:
                display_recipe_data(response.data)

    st.session_state.messages.append(
        {"role": "assistant", "content": response.message, "data": response.data}
    )
    st.rerun()


def display_chat_interface() -> None:
    """Display the chat interface and handle messages."""
    st.title("🧑‍🍳 SiCa Kitchen")
    st.markdown(
        """
    Welcome to your AI-powered cooking assistant! I can help you:
    - Find recipes based on ingredients you have
    - Calculate costs for missing ingredients
    - Answer general cooking questions
    """
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "data" in message and message["data"]:
                display_recipe_data(message["data"])

    if prompt := st.chat_input(
        "What ingredients do you have? Or ask me anything about cooking!"
    ):
        handle_user_input(prompt)


def main() -> None:
    """Main Streamlit application."""
    st.set_page_config(
        page_title="SiCa Kitchen",
        page_icon="🧑‍🍳",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session_state()
    display_chat_interface()
    display_logs()


if __name__ == "__main__":
    main()
