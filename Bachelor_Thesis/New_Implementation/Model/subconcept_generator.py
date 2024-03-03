import os
from openai import OpenAI


def generate_subconcepts(concepts, num_subconcepts_per_concept):

    client = OpenAI()
    MODEL = "gpt-3.5-turbo"
    temperature = 0.2

    all_subconcepts = []

    # Go through all concepts and append the generated subconcepts to all_subconcepts.

    for concept in concepts:
        system_prompt = "You are an assistant who responds with the answer, nothing more. Your main " \
                        "task is to get a concept name as input and generate related concepts, which would " \
                        "come up in academic release titles."
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
        
        subconcepts_list = response.choices[0].message.content.split(", ")
        for subconcept in subconcepts_list:
            subconcept = subconcept.lower()
            for subconcept_part in subconcept.split():
                if subconcept_part not in all_subconcepts:
                    all_subconcepts.append(subconcept_part)

    return all_subconcepts