import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
GROUP_ID = int(os.getenv("GROUP_ID")) 
