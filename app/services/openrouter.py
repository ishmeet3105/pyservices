import requests
from app.config import OPENROUTER_API_KEY,AZURE_OPENAI_KEY
import os
import openai

def convert_prospect_language(name: str, language: str) -> str:

    prompt = f"""
    You are a helpful assistant which helps in converting names to {language} script i want to use phenomes to convert name. Donot give out any other gibberish data except for only name.
    Name: {name}
    """

    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f"Bearer {OPENROUTER_API_KEY}",
        'Content-Type': 'application/json'
    }

    payload = {
        "model": "openai/gpt-4.1-nano",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 20
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error converting {name}: {e}")
        return None



def evaluate_prompt(prompt_text: str) -> str:
  
    url = f"https://vocallabsllmtest2.openai.azure.com/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview"
    print("url is", url)
    headers = {
        "Content-Type": "application/json",
        "api-key": "apikey"
    }
    print("prompt we are sending to llm right",prompt_text)
    payload = {
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "You are a strict evaluator. Return only TRUE or FALSE."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    }
                ]
            }
        ],
        "temperature": 0.0,
        "top_p": 1,
        "max_tokens": 256
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Azure OpenAI Error: {e}")
        return "FALSE"
