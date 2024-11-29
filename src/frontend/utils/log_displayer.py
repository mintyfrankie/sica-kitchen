import logging
from datetime import datetime
from dataclasses import dataclass
from logging.handlers import QueueHandler
from typing import Optional, Dict, Any
import queue

from backend.utils.logging import setup_logging

import streamlit as st


@dataclass
class LogRecord:
    """Container for formatted log records."""

    timestamp: str
    level: str
    message: str
    context: Optional[Dict[str, Any]] = None


def setup_logging_handler() -> None:
    """Configure logging handlers for the application."""
    queue_handler = QueueHandler(st.session_state.log_queue)
    queue_handler.setLevel(logging.INFO)

    logging.getLogger().handlers = []
    logging.getLogger("backend").handlers = []

    setup_logging(level=logging.INFO)
    structured_logger = logging.getLogger("backend")
    structured_logger.addHandler(queue_handler)


def process_log_record(record: logging.LogRecord) -> Optional[LogRecord]:
    """Process a log record and convert it to our custom LogRecord format."""
    log_id = f"{record.created}_{record.getMessage()}"

    if log_id in st.session_state.displayed_logs:
        return None

    context = getattr(record, "context", None) or getattr(record, "extra", None)
    if context and not isinstance(context, dict):
        context = None

    log_record = LogRecord(
        timestamp=datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
        level=record.levelname,
        message=record.getMessage(),
        context=context,
    )

    st.session_state.displayed_logs.add(log_id)
    return log_record


def format_log_html(log: LogRecord) -> str:
    """Format a log record as HTML for display."""
    colors = {
        "INFO": "gray",
        "DEBUG": "blue",
        "WARNING": "orange",
        "ERROR": "red",
        "CRITICAL": "red",
    }
    color = colors.get(log.level, "gray")

    log_html = (
        f"<small>{log.timestamp}</small> "
        f"<span style='color: {color};'><b>{log.level}</b></span><br/>"
        f"{log.message}<br/>"
    )

    if log.context and isinstance(log.context, dict):
        context_str = "<br/>".join(
            f"<small><b>{k}</b>: {v}</small>" for k, v in log.context.items()
        )
        log_html += (
            f"<div style='margin-left: 10px; font-size: 0.8em;'>{context_str}</div>"
        )

    return log_html


def display_logs() -> None:
    """Display logs from the queue in the sidebar."""
    st.sidebar.title("Execution Logs")

    if "displayed_logs" not in st.session_state:
        st.session_state.displayed_logs = set()
    if "logs" not in st.session_state:
        st.session_state.logs = []

    while True:
        try:
            record = st.session_state.log_queue.get_nowait()
            if log_record := process_log_record(record):
                st.session_state.logs.append(log_record)
        except queue.Empty:
            break

    for log in st.session_state.logs:
        st.sidebar.markdown(format_log_html(log), unsafe_allow_html=True)
