import requests
import json
import os
import shutil
import time
import math
from pymongo import MongoClient, InsertOne
from multiprocessing import Lock, Process
import gender_guesser.detector as gender
from gender_from_name import gender_from_name
from dict_to_chunk import chunks
from keyword_to_concepts import get_concepts

# Global release id counter, total hits, page_number and number_of_inner_processes variables.
release_id = 0
number_of_inner_processes = 30

def author_dict_to_database(author_dict: dict):
    client = MongoClient("localhost", 27017)
    db = client.results

    # Initialize the gender detector.
    gender_detector = gender.Detector(case_sensitive=False)

    author_list = []

    for name, release_ids in author_dict.items():
        guessed_gender = gender_from_name(name, gender_detector.get_gender)
        author_list.append({ "name": name, "gender": guessed_gender, "release_ids": release_ids })

    db.authors.insert_many(author_list)


def hits_to_database(hits: list):
    """
    Extracts the releases (their title and doi) and the authors to the respective
    collections in the local mongodb database.

    :param hits: a list containing hits (releases).
    """
    global release_id
    global number_of_inner_processes

    # Make the connection to the mongodb database.
    client = MongoClient("localhost", 27017)
    db = client.results

    # Add all the releases from this response to the local mongodb database in one go.
    releases = []
    author_dict = {}
    number_of_duplicates = 0
    release_count = release_id
    release_names = [release["_source"]["title"] for release in hits]

    # Find which releases are already in the database.
    existing_documents = db.releases.find({ "title": { "$in": release_names }})
    found_names = [document["title"] for document in existing_documents]

    for release in hits:
        if release["_source"]["title"] in found_names:
            number_of_duplicates += 1
            continue
        releases.append({ "release_id": release_count,
                            "title": release["_source"]["title"],
                            "doi": release["_source"]["doi"] })
        
        authors = release["_source"]["contrib_names"]
        for author in authors:
            if author in author_dict:
                author_dict[author].append(release_count)
            else:
                author_dict[author] = [release_count]

        release_count += 1

    processes = []

    print(len(author_dict))

    for chunk in chunks(author_dict, number_of_inner_processes):
        # For every chunk create a thread / process to deal with it.
        print("Here!")
        print(f"Chunk size: {len(chunk)}")
        p = Process(target=author_dict_to_database, args=(chunk,))
        processes.append(p)
        p.start()
    
    # Wait for the threads / processes to end.
    for p in processes:
        p.join()

    #author_list = [{ "name": name, "release_ids": release_ids } for name, release_ids in author_dict.items()]

    db.releases.insert_many(releases)

    release_id += len(hits) - number_of_duplicates
    
    client.close()

def make_request_and_save_response(scroll_id: str = None, things_to_look_for: list = None, second_step: bool = False, page_number: int = 0):
    """
    Makes a request and saves the response in the local mongodb database using the
    'hits_to_database' function.

    :param scroll_id: used for subsequent requests
    :param topics: list of topics, used in the first request
    """
    current_page_number = 0

    if scroll_id is None:
        # We are making the first request.

        # Create a data_template that we will fill in further with the topics.

        data_template = {
            "query": {
                "bool": {
                    "should": []
                }
            },
            "size": 10000
        }

        # Fill in the data_template with match-phrases of topics, so that we can get all the 
        # releases about any one of the given topics.

        for thing in things_to_look_for:
            if thing == "":
                data_template["query"]["bool"]["should"].append({ "match_all": {} } )
            else:
                if not second_step:
                    data_template["query"]["bool"]["should"].append({ "match_phrase": { "title": thing }})
                else:
                    print("HERE!")
                    data_template["query"]["bool"]["should"].append({ "match_phrase": { "contrib_names": thing }})

        # Get the first page of releases using the scroll api.
    
        response = requests.post("https://search.fatcat.wiki/fatcat_release/_search?scroll=3m", json=data_template)
        results = response.json()   # Turn the results into a Python dictionary.

        if "hits" not in results:
            print("We got an unexpected response")
            with open("tempresponse.json", "w") as f:
                json.dump(results, f)
            return -1

        # Print the total amount of things found.
        print("Total amount of releases found: ", results["hits"]["total"]["value"])

        hits = results["hits"]["hits"]
        number_of_hits = len(hits)   # Get the number of actual hits in this response, stop if this is 0.
        if number_of_hits == 0:
            print("Nothing could be found with these topics.")
            return -1

        page_number += 1
        print(f"Processing page number: {page_number}")
        
        current_page_number = page_number
        
        scroll_id = results["_scroll_id"]   # Get the scroll_id to be able to use it later in the loop.
        print(type(hits))

        hits_to_database(hits)
        print(f"Finished processing page number:{current_page_number}")

        return scroll_id
    else:
        # We are making a subsequent request
        data = {
            "scroll": "3m",
            "scroll_id": scroll_id,
        }

        response = requests.post("https://search.fatcat.wiki/_search/scroll", json=data)
        results = response.json()

        if "hits" not in results:
            print("We got an unexpected response")
            with open("tempresponse.json", "w") as f:
                json.dump(results, f)
            return -1

        hits = results["hits"]["hits"]
        number_of_hits = len(hits)
        if number_of_hits == 0:
            return -1
        
        page_number += 1
        print(f"Processing page number: {page_number}")

        current_page_number = page_number
        
        scroll_id = results["_scroll_id"]

        hits_to_database(hits)
        print(f"Finished processing page number: {current_page_number}")

        return scroll_id        

def get_and_save_releases_from_fatcat_release_search(things_to_look_for: list, second_step: bool = False):
    print("HERE!")
    page_number = 0

    while True:
        if page_number == 0:
            # We are making the first request.
            scroll_id = make_request_and_save_response(None, things_to_look_for, second_step=second_step, page_number=page_number)
            if scroll_id == -1:
                break
        else:
            # We are making a subsequent request.
            scroll_id = make_request_and_save_response(scroll_id, None, second_step=second_step, page_number=page_number)
            if scroll_id == -1:
                break
        page_number += 1



def save_authors_and_releases_by_keyword(keyword: str, num_concepts: int):
    if num_concepts > 1024:
        print("Can at most search for 1024 concepts.")
        return -1

    concepts = get_concepts(keyword, num_concepts)

    if not concepts:
        print("There has been a problem generating concepts from keyword.")
        return -1

    print("These are the concepts which will be used for the query: ", concepts)

    # Connect to the database, delete results database and start from scratch.
    client = MongoClient("localhost", 27017)
    client.drop_database("results")
    db = client.results

    get_and_save_releases_from_fatcat_release_search(concepts, second_step=False)
    
    # Make one last aggregation query on the authors.

    db.authors.aggregate([
            {
                "$unwind": "$release_ids",
            },

            {
                "$group": {
                    "_id": {
                        "name": { "$trim": { "input": "$name" } },
                        "gender": "$gender",
                    },
                    "release_ids": { "$addToSet": "$release_ids" },
                }
            },

            {
                "$project": {
                    "_id": 0,
                    "name": "$_id.name",
                    "gender": "$_id.gender",
                    "release_ids": 1,
                }
            },

            {
                "$out": "authors"
            }
        ]
    )

def authors_to_more_releases(author_names: list):
    print("HERE")
    get_and_save_releases_from_fatcat_release_search(author_names, second_step=True)


if __name__ == "__main__":
    keyword = "optimisation"
    num_concepts = 1

    # Step 1: Save the authors and releases in the database.
    save_authors_and_releases_by_keyword(keyword, num_concepts)

    # Step 2: Get all the author names and search for their other releases in fatcat search api.

    names = get_author_names_from_database()
    names_set = set()

    # Sanity check
    for name in names:
        if name in names_set:
            print("This is a duplicate name -> ", name)
        else:
            names_set.add(name)
    
    if len(names) == len(names_set):
        print("No duplicates, number of elements -> ", len(names))

    names = list(names_set)

    names_len = len(names)
    # Divide the names into 1000 name chunks so that we can make the queries correctly.

    number_of_chunks = math.floor(names_len / 1000)
    last_chunk_len = names_len % 1000
    
    for i in range(0, number_of_chunks):
        authors_to_more_releases(names[i * 1000: ((i * 1000) + 1000)])

    authors_to_more_releases(names[number_of_chunks * 1000: ((number_of_chunks * 1000) + last_chunk_len)])