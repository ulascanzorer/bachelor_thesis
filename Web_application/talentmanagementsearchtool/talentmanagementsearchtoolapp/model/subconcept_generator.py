import os
from openai import OpenAI

# The main function used for generating the subconcepts using the ChatGPT API.
def generate_subconcepts(concepts, num_subconcepts_per_concept):

    client = OpenAI()
    MODEL = "gpt-3.5-turbo"
    temperature = 0.2   # An internals setting for the ChatGPT model.

    all_subconcepts = []

    # Go through all concepts and append the generated subconcepts to all_subconcepts.

    for concept in concepts:
        system_prompt = "You are an assistant who responds with the answer, nothing more. Your main " \
                        "task is to get a concept name as input and generate related concepts, which would " \
                        "come up in academic release titles. I will then split the output that you give me to " \
                        "individual words in order to query from a database, so please try to avoid using words " \
                        "that are commonly used such as 'in', 'of', etc. and try using more specific words where " \
                        "possible."
        user_prompt = f"Tell me {num_subconcepts_per_concept} most important concepts related to " \
                      f"{concept} separated by commas and without numbering please."

        response = client.chat.completions.create(model=MODEL,
                                                  messages=[
                                                    { 
                                                        "role": "system", 
                                                        "content": system_prompt 
                                                    },
                                                    {
                                                        "role": "user", 
                                                        "content": user_prompt
                                                    },
                                                  ],
                                                  temperature=0.2)
        
        # Get the resulting subconcepts, parse and format them, and save them.

        subconcepts_list = response.choices[0].message.content.split(", ")
        for subconcept in subconcepts_list:
            subconcept = subconcept.lower()
            for subconcept_part in subconcept.split():
                if subconcept_part not in all_subconcepts:
                    all_subconcepts.append(subconcept_part)

    return all_subconcepts