import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GPT_API_KEY = os.getenv('GPT_API_KEY')
    
