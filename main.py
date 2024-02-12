# Load config

import configuration
config = configuration.load_config('config.yml')

# Start with TogetherAI as a base

from langchain_together import Together

llm = Together(
    model="mistralai/Mixtral-8x7B-Instruct-v0.1",

    temperature=0.71,
    top_p=0.8,
    top_k=50,
    repetition_penalty=1.11,

    together_api_key=config['backend']['together_ai']['api_key']
)

print(llm.invoke("Hey! How are you doing?"))