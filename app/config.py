import os
from dotenv import load_dotenv

# Load the config.env file explicitly
load_dotenv(dotenv_path="app/config.env")

# Fetch the environment variables
HASURA_URL = "https://db.vocallabs.ai/v1/graphql"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HASURA_HEADERS = {
    "Content-Type": "application/json",
    "x-hasura-admin-secret": os.getenv("HASURA_SECRET")
}

config = {
    "auth_server_url": "https://example.com",
    "env": os.getenv("ENV", "prod")
}



AZURE_OPENAI_ENDPOINT= "https://vocallabsllmtest2"
AZURE_OPENAI_KEY= os.getenv("AZURE_OPENAI_KEY")