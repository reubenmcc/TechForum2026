import anthropic
import os
from dotenv import load_dotenv

load_dotenv("keys.env")

def create():

    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],  # This is the default and can be omitted
    )

    return client