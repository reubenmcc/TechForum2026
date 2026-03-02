import os
import anthropic
from dotenv import load_dotenv
from  filereadAgent import find_file_by_description

if __name__ == "__main__":
    load_dotenv("keys.env")

    client = anthropic.Anthropic()

    result = find_file_by_description(
        client=client,
        description="What is the IRR for Wholelife?",
        file_directory="agentDocs"
    )
    print(result)