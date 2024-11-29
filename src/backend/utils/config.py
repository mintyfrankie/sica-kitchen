"""
Configuration settings for the backend.
"""

import os
from typing import Final

# OpenAI Configuration
OPENAI_MODEL: Final[str] = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
