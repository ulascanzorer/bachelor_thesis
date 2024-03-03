import os
from openai import OpenAI

client = OpenAI()

MODEL = "gpt-3.5-turbo"
response = client.chat.completions.create(model=MODEL,
messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Knock knock."},
    {"role": "assistant", "content": "Who's there?"},
    {"role": "user", "content": "Orange."},
],
temperature=0)

print(response)
