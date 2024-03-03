from typing_extensions import Callable
from pymongo import MongoClient
from utils import eprint
from send_email import send_email
from detect_multiple_authors_and_add_orcid_urls import detect_multiple_authors_and_add_orcid_urls
from get_author_names_from_database import get_author_names_from_database
from list_to_chunk import get_chunks_from_list_chunk_size
from concept_core import related_concepts_from_concepts
from aggregate_duplicate_authors import aggregate_duplicate_authors
import pymongo

MAIN_CONCEPT_LIMIT = 10
FATCAT_QUERY_LIMIT = 1024

def save_data_to_mongodb_from_query(main_concepts: list[str],
                                    num_concepts: int,
                                    api_to_database: Callable[[list[str], bool, int], int],
                                    name_chunk_len: int):
    # Before doing anything, create a pymongo client and drop the designated database.

    print("DELETING EXISTING DATABASE, STARTING FROM SCRATCH")

    client: pymongo.mongo_client.MongoClient = MongoClient("localhost", 27017)
    client.drop_database("results")

    print("DELETE OPERATION COMPLETED")

    # Save the release_ids here.

    release_id = 0

    # Print error if we want more than MAIN_CONCEPT_LIMIT main concepts.

    if len(main_concepts) > MAIN_CONCEPT_LIMIT:
        eprint(f"Please provide a number of main concepts which is less than {MAIN_CONCEPT_LIMIT}.")
        return -1

    # Get the concepts from the main concepts.

    concepts = related_concepts_from_concepts(main_concepts, num_concepts)

    # Print error if we can't find concepts for some reason.

    if not concepts:
        eprint("There has been a problem generating concepts from keyword.")
        return -1

    # Print error if the amount of concepts is greater than FATCAT_QUERY_LIMIT.

    if len(concepts) > FATCAT_QUERY_LIMIT:
        eprint(f"We can only search for {FATCAT_QUERY_LIMIT} concepts at a time, consider using a lower value of 'num_concepts'")
        return -1

    # Print the final concepts to search for.

    print("THESE ARE THE CONCEPTS THAT WE WILL SEARCH FOR:")
    print(concepts)

    # Search for releases with titles containing any or more than one of the concepts,
    # save the releases and the authors in the database.

    print("BEGINNING WITH STEP ONE, SEARCHING FOR RELEASES ABOUT GIVEN CONCEPTS")

    release_id = api_to_database(things_to_look_for=concepts,
                                 second_step=False,
                                 release_id=release_id,
                                 main_concepts=main_concepts)

    # Aggregate duplicate authors and create one author with multiple release_ids.

    print("AGGREGATING THE RESULTS")
    aggregate_duplicate_authors()

    # Get all the author names from the database as a list.

    names = get_author_names_from_database()

    # Get chunks of names of a specified size and for every one of them look for
    # even more releases and save them in the database and update the authors.

    # FATCAT_QUERY_LIMIT (1024) is again the limit of number of different parameters in our
    # elasticsearch query

    if name_chunk_len > FATCAT_QUERY_LIMIT:
        eprint(f"Can at most divide the author names in chunks of size {FATCAT_QUERY_LIMIT}.")
        return -1

    chunks = get_chunks_from_list_chunk_size(names, name_chunk_len)

    print("CONTINUING WITH STEP TWO, SEARCHING FOR RELEASES FROM ALL FOUND AUTHORS")
    print(f"WE HAVE {len(chunks)} CHUNK(S) TO WORK WITH")

    chunk_number = 1
    for chunk in chunks:
        print(f"GETTING CHUNK NUMBER {chunk_number}!")
        release_id = api_to_database(things_to_look_for=chunk,
                                     second_step=True,
                                     release_id=release_id,
                                     main_concepts=main_concepts)
        print("AGGREGATE SOME RESULTS")
        aggregate_duplicate_authors()
        chunk_number += 1

    """ print("AGGREGATING THE RESULTS")
    aggregate_duplicate_authors() """

    # Go through all the authors and mark them as "multiple_authors": True if we
    # find more than one orcid for them. If that is the case also add the orcid
    # urls.

    # UNCOMMENT THIS WHEN YOU ARE DONE TESTING

    # detect_multiple_authors_and_add_orcid_urls(process_num=30)  # Process number 30 for now.

    # close the pymongo client
    client.close()

def send_email(email_receiver: str):
    send_email(email_receiver)
