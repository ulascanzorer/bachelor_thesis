from .subconcept_generator import generate_subconcepts
from .query_and_storer import query_and_store


def main_flow(concepts, earliest_publication_year, num_subconcepts_per_concept, result_id):
    print("Beginning the main flow.")
    print(f"Generating {num_subconcepts_per_concept} subconcepts for every concept.")

    subconcepts = generate_subconcepts(concepts, num_subconcepts_per_concept)

    print("Here are the subconcepts:")
    for subconcept in subconcepts:
        print(subconcept)
    print("\n")
    print("Querying the work titles for subconcepts, retrieving authors of these works and "
    "storing them in the database under the collections 'releases_result' and 'authors_result'.")

    query_and_store(concepts, subconcepts, earliest_publication_year, result_id)

    print("Done with all the tasks!")

if __name__ == "__main__":
    # Our parameters, which will later come from the user using the web application.
    concepts = ["deep learning", "bioinformatics"]
    earliest_publication_year = 2018
    num_subconcepts_per_concept = 5

    # Call the main flow with given parameters.
    main_flow(concepts, earliest_publication_year, num_subconcepts_per_concept)