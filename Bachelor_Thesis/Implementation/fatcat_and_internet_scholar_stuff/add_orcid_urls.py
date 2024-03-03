from pymongo import MongoClient
from top_orcids import find_top_orcids

# Get all documents with "multiple_authors": true and add the orcid urls.

# CURRENTLY I DON'T USE THIS!   

def add_orcid_urls(concepts: list[str], number_of_urls: int = 3, how_many_results: int = 3):
    client = MongoClient("localhost", 27017)
    db = client.results

    multiple_authors_documents = list(db.authors.find({ "multiple_authors": True }))
    multiple_authors_names = [document["name"] for document in multiple_authors_documents]
    modified_multiple_author_documents = []
    num_documents_to_modify = len(multiple_authors_documents)
    current_index = 1

    for document in multiple_authors_documents:
        print(f"Modifying document number {current_index} of {num_documents_to_modify}.")
        modified_multiple_author_documents.append(
            {
                "name": document["name"],
                "release_ids": document["release_ids"],
                "multiple_authors": document["multiple_authors"],
                "orcid_urls": find_top_orcids(document["name"], concepts, number_of_urls, how_many_results),
            }
        )
        current_index += 1

    db.authors.delete_many({ "name": { "$in": multiple_authors_names } })
    db.authors.insert_many(modified_multiple_author_documents)
