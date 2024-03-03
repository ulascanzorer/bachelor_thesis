import os
from openai import OpenAI

def get_related_concepts_from_gpt(concept: str, num_concepts: int = 30, temperature: float = 0.2):
    client = OpenAI()
    MODEL = "gpt-3.5-turbo"
    system_prompt = """You are an assistant who responds with the answer, nothing more. Your main task is to
                   get a concept name as input and generate related concepts."""

    user_prompt = f"Tell me {num_concepts} most important concepts related to {concept} separated by commas please."

    response = client.chat.completions.create(model=MODEL,
    messages=[
        { "role": "system", "content": system_prompt },
        { "role": "user", "content": user_prompt },
    ],
    temperature=temperature)

    related_concepts_list = response.choices[0].message.content.split(", ")
    print("This is the related concepts list:", related_concepts_list)
    final_concepts_list = []

    for related_concept in related_concepts_list:
        related_concept = related_concept.lower()
        for concept in related_concept.split():
            if concept not in final_concepts_list:
                final_concepts_list.append(concept)

    return final_concepts_list

def get_similarity_ranking_from_gpt(release_name: str, main_topic: str, temperature: float = 0.2):
    client = OpenAI()
    MODEL = "gpt-3.5-turbo"

    system_prompt = f"""Given an academic release title, rate its relevance to the main topic: {main_topic} on a scale from 0 to 10. 
                        Provide a brief explanation for your rating. The format of the answer should be: ranking: (the ranking you give) 
                        newline explanation"""
    
    user_prompt = release_name

    response = client.chat.completions.create(model=MODEL,
    messages=[
        { "role": "system", "content": system_prompt },
        { "role": "user", "content": user_prompt },
    ],
    temperature=temperature)

    actual_ranking = response.choices[0].message.content.split()[1]

    return actual_ranking


if __name__ == "__main__":
    concept = "deep learning"
    subconcepts = get_related_concepts_from_gpt(concept)
    print("And these are the subconcepts:", subconcepts)