from chatgptapi import get_similarity_ranking_from_gpt, get_related_concepts_from_gpt
import math

THINGS_TO_MATCH_RATIO = 0.3
SIMILARITY_LOWER_LIMIT = 5

def relevant_release(release_name: str, things_to_look_for: list[str]) -> bool:
    num_things_to_match = len(things_to_look_for) * THINGS_TO_MATCH_RATIO
    things_that_actually_match = 0
    relevant = False

    for thing in things_to_look_for:
        if int(get_similarity_ranking_from_gpt(release_name=release_name, main_topic=thing)) > SIMILARITY_LOWER_LIMIT:
            things_that_actually_match += 1
            if things_that_actually_match >= num_things_to_match:
                relevant = True
                break
            
    return relevant

def related_concepts_from_concepts(main_concepts: list[str], num_concepts: int) -> list[str]:
    num_concepts_per_main_concept = math.floor(num_concepts / len(main_concepts))

    final_concepts = []

    for main_concept in main_concepts:
        found_concepts = get_related_concepts_from_gpt(concept=main_concept, num_concepts=num_concepts_per_main_concept)
        final_concepts.extend(found_concepts)

    return final_concepts