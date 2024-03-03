import wikipedia

def get_concepts(keyword: str, num_concepts: int = 10) -> list[str]:
    try:
        page = wikipedia.page(keyword, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as e:
        page = wikipedia.page(e.options[0], auto_suggest=False)
    except Exception as e:
        print(e)
        return []
    
    result = page.links

    # replace the concepts that comprise of multiple words with their individual words
    for concept in list(result):
        modified_concept = concept.replace("(", " ")
        modified_concept = modified_concept.replace(")", " ")
        individual_concepts = modified_concept.split()
        result.remove(concept)
        for individual_concept in individual_concepts:
            result.append(individual_concept)

    result.insert(0, keyword)   # Also add the keyword itself.

    result = list(dict.fromkeys(result))  # Turn it into a set to remove duplicates and then turn it back into a list.

    return result[0:num_concepts]

if __name__ == "__main__":
    keyword = "deep learning"
    num_concepts = 1000
    concepts = get_concepts(keyword, num_concepts)
    print(concepts)