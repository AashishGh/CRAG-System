# config.py


import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
def get_environment_config(key):
    return os.environ[key]




