"""
Diagnostic: lists which Groq models your API key can actually call.

Run this if test_offline.py shows a model-not-found error.

Run with: python list_models.py
"""

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq()

print("Models available to your Groq API key:\n")
for model in client.models.list().data:
    print(f"  {model.id}")
