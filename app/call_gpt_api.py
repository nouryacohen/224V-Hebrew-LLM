from .config import Config
from openai import OpenAI

client = OpenAI(
  api_key=Config.GPT_API_KEY
)

def call_gpt_api(messages):
    
    response = client.chat.completions.create(
        model="gpt-4o", 
        temperature=0.1, 
        messages=messages
    )
    return response.choices[0].message.content
