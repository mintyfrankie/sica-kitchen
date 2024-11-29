"""
Streamlit interface for the recipe chatbot.
"""

import streamlit as st
from typing import Dict, Any

from backend.orchestrator import RecipeChatbot, ChatbotResponse


def initialize_session_state() -> None:
    """Initialize the session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = RecipeChatbot()


def display_recipe_data(data: Dict[str, Any]) -> None:
    """
    Display recipe data in a structured format.

    Args:
        data: Recipe data dictionary from chatbot response.
    """
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


def main() -> None:
    """Main Streamlit application."""
    st.set_page_config(page_title="Recipe Chatbot", page_icon="🍳", layout="wide")

    st.title("🍳 Recipe Chatbot")
    st.markdown("""
    Welcome to your AI-powered cooking assistant! I can help you:
    - Find recipes based on ingredients you have
    - Calculate costs for missing ingredients
    - Answer general cooking questions
    """)

    initialize_session_state()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "data" in message and message["data"]:
                display_recipe_data(message["data"])

    # Chat input
    if prompt := st.chat_input(
        "What ingredients do you have? Or ask me anything about cooking!"
    ):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get chatbot response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response: ChatbotResponse = st.session_state.chatbot.process_message(
                    prompt
                )
                st.write(response.message)
                if response.data:
                    display_recipe_data(response.data)

        # Store assistant response
        st.session_state.messages.append(
            {"role": "assistant", "content": response.message, "data": response.data}
        )


if __name__ == "__main__":
    main()
