import os
import logging
from dotenv import load_dotenv

# Load environment variables once
load_dotenv()

# Safely expose API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def setup_logging():
    """Initializes standard logging for all modules."""
    logging.basicConfig(
        level=logging.INFO, 
        # We added %(module)s so you know EXACTLY which file generated the log
        format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s' 
    )