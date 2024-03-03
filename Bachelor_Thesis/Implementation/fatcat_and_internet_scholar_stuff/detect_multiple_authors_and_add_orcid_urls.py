from top_orcids import find_top_orcids
from pymongo import MongoClient
import pymongo
from list_to_chunk import get_chunks_from_list_chunk_num
from multiprocessing import Process

def detect_multiple_authors_and_add_orcid_urls_from_chunk(db: pymongo.database.Database, chunk: list[any], process_count: int, match_needed: int = 2):
    all_author_names_chunk = [document["name"] for document in chunk]
    author_to_orcid_urls = {}

    author_names_number = len(all_author_names_chunk)
    author_name_counter = 1
    for author in all_author_names_chunk:
        if author_name_counter % 10:
            print(f"Process {process_count}: We are at author name number {author_name_counter} out of {author_names_number}")
        
        orcid_urls = find_top_orcids(name=author, concepts=[], num_of_ids=3, how_many_results=30, match_needed=match_needed)
        if len(orcid_urls) > 1:
            author_to_orcid_urls[author] = orcid_urls
        
        author_name_counter += 1
    
    modified_author_documents = []

    for document in chunk:
        if document["name"] in author_to_orcid_urls:
            modified_author_documents.append({ "name": document["name"],
                                               "gender": document["gender"], 
                                               "release_ids": document["release_ids"],
                                               "multiple_authors": True,
                                               "orcid_urls": author_to_orcid_urls[document["name"]] })

    multiple_author_names = list(author_to_orcid_urls.keys())

    if len(multiple_author_names) > 0 and len(modified_author_documents) > 0:
        db.authors.delete_many({ "name": { "$in": multiple_author_names } })
        db.authors.insert_many(modified_author_documents)

def detect_multiple_authors_and_add_orcid_urls(db_name: str, process_num: int = 1, match_needed: int = 2):
    print(f"DETECTING MULTIPLE AUTHORS AND ADDING ORCID URLS USING {process_num} PROCESSES")

    client = MongoClient("localhost", 27017)
    db = client[db_name]

    all_author_documents = db.authors.find({})
    actual_all_author_documents = [document for document in all_author_documents]

    chunks = get_chunks_from_list_chunk_num(actual_all_author_documents, process_num)
    processes = []
    process_count = 0

    for chunk in chunks:
        p = Process(target=detect_multiple_authors_and_add_orcid_urls_from_chunk,
                    args=(db, chunk, process_count, match_needed))
        processes.append(p)
        p.start()
        process_count += 1
    
    # wait for the processes to end
    for p in processes:
        p.join()