"""
Streamlit interface for the recipe chatbot with execution logging.
"""

import streamlit as st
from typing import Dict, Any, List
from datetime import datetime
import logging
from logging.handlers import QueueHandler
import queue
from dataclasses import dataclass
from typing import Optional

from backend.orchestrator import RecipeChatbot, ChatbotResponse
from backend.utils.logging import setup_logging


@dataclass
class LogRecord:
    """Container for formatted log records."""

    timestamp: str
    level: str
    message: str
    context: Optional[Dict[str, Any]] = None


def initialize_session_state() -> None:
    """Initialize the session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = RecipeChatbot()
    if "log_queue" not in st.session_state:
        st.session_state.log_queue = queue.Queue()

        # Set up queue handler for logging
        queue_handler = QueueHandler(st.session_state.log_queue)
        queue_handler.setLevel(logging.INFO)

        # Remove all existing handlers from all loggers
        logging.getLogger().handlers = []
        logging.getLogger("backend").handlers = []

        # Initialize structured logging with our queue handler
        setup_logging(level=logging.INFO)

        # Add queue handler only to the backend logger
        structured_logger = logging.getLogger("backend")
        structured_logger.addHandler(queue_handler)


def get_log_color(level: str) -> str:
    """Get color for log level."""
    colors = {
        "INFO": "gray",
        "DEBUG": "blue",
        "WARNING": "orange",
        "ERROR": "red",
        "CRITICAL": "red",
    }
    return colors.get(level, "gray")


def display_logs() -> None:
    """Display logs from the queue in the sidebar."""
    st.sidebar.title("Execution Logs")

    if "displayed_logs" not in st.session_state:
        st.session_state.displayed_logs = set()
    if "logs" not in st.session_state:
        st.session_state.logs = []

    # Process new logs
    while True:
        try:
            record = st.session_state.log_queue.get_nowait()

            # Create unique identifier for the log
            log_id = f"{record.created}_{record.getMessage()}"

            # Skip if already displayed
            if log_id in st.session_state.displayed_logs:
                continue

            # Extract context from both standard and structured logs
            context = None
            if hasattr(record, "context"):
                context = record.context
            elif hasattr(record, "extra"):
                context = record.extra

            if context and not isinstance(context, dict):
                context = None

            log_record = LogRecord(
                timestamp=datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                level=record.levelname,
                message=record.getMessage(),
                context=context,
            )

            st.session_state.logs.append(log_record)
            st.session_state.displayed_logs.add(log_id)

        except queue.Empty:
            break

    # Display logs with formatting
    for log in st.session_state.logs:
        color = get_log_color(log.level)

        # Format the log message
        log_html = (
            f"<small>{log.timestamp}</small> "
            f"<span style='color: {color};'><b>{log.level}</b></span><br/>"
            f"{log.message}<br/>"
        )

        # Add context if available and is a dictionary
        if log.context and isinstance(log.context, dict):
            context_str = "<br/>".join(
                f"<small><b>{k}</b>: {v}</small>" for k, v in log.context.items()
            )
            log_html += (
                f"<div style='margin-left: 10px; font-size: 0.8em;'>{context_str}</div>"
            )

        st.sidebar.markdown(log_html, unsafe_allow_html=True)


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
    st.set_page_config(
        page_title="Recipe Chatbot",
        page_icon="🍳",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session_state()

    # Main chat interface
    st.title("🍳 Recipe Chatbot")
    st.markdown("""
    Welcome to your AI-powered cooking assistant! I can help you:
    - Find recipes based on ingredients you have
    - Calculate costs for missing ingredients
    - Answer general cooking questions
    """)

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
        # Clear previous logs when starting new conversation
        st.session_state.logs = []
        st.session_state.displayed_logs = set()

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
            {
                "role": "assistant",
                "content": response.message,
                "data": response.data,
            }
        )
        # Force a rerun to update logs
        st.rerun()

    display_logs()


if __name__ == "__main__":
    main()
