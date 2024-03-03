import requests
import json
from pymongo import MongoClient
import pymongo
from multiprocessing import Process
import gender_guesser.detector as gender
from gender_from_name import gender_from_name
from dict_to_chunk import chunks
from utils import eprint, robust_request, annoying_notification
import time
import sys
import math
from concept_core import relevant_release

### THIS IS AN IMPLEMENTATION FOR api_to_database for save_data_to_mongodb_from_query ###

NUMBER_OF_INNER_PROCESSES = 30
RELEVANCE_QUOTA = 0.1
total_page_number = 0
main_concepts_list: list[str] = []

def author_dict_to_database(author_dict: dict[str, dict[str, any]]):
    client: pymongo.mongo_client.MongoClient = MongoClient("localhost", 27017)
    db = client.results

    gender_detector = gender.Detector(case_sensitive=False)

    author_list = []
    for name, attributes in author_dict.items():
        guessed_gender = gender_from_name(name, gender_detector.get_gender)
        author_list.append({ "name": name, "gender": guessed_gender, "release_ids": attributes["release_ids"] })

    if len(author_list) > 0:
        db.authors.insert_many(author_list)

def releases_to_database(releases: list[dict[str, any]], release_id: int):
    global main_concepts_list

    client: pymongo.mongo_client.MongoClient = MongoClient("localhost", 27017)
    db = client.results

    final_releases = []
    author_dict: dict[str, dict[str, any]] = {}
    author_dict_releases: dict[str, dict[str, int]] = {}
    release_count = release_id
    release_names = [release["_source"]["title"] for release in releases]

    author_names_with_possible_duplicates = []
    for release in releases:
        author_names_with_possible_duplicates.extend(release["_source"]["contrib_names"])

    author_names = list(set(author_names_with_possible_duplicates))

    existing_release_name_documents = db.releases.find({ "title": { "$in": release_names } })
    existing_release_names = [document["title"] for document in existing_release_name_documents]
    already_added_release_names = []

    existing_author_name_documents = db.authors.find({ "name": { "$in": author_names } })
    existing_author_names = [document["name"] for document in existing_author_name_documents]

    # TODO
    # Below, we usually make 10_000 * 1024 = 10_240_000 chatgpt API calls!
    # We have to fix this!

    for release in releases:
        release_name = release["_source"]["title"]
        release_is_relevant = relevant_release(release_name, main_concepts_list)

        # Update the information about how many relevant and irrelevant releases the
        # authors have.

        authors = release["_source"]["contrib_names"]
        for author in authors:
            # For every author count the number of relevant and irrelevant
            # releases.

            if author in author_dict_releases:
                if release_is_relevant:
                    author_dict_releases[author]["relevant"] += 1
                else:
                    author_dict_releases[author]["irrelevant"] += 1
            else:
                if release_is_relevant:
                    author_dict_releases[author] = { "relevant": 1, "irrelevant": 0 }
                else:
                    author_dict_releases[author] = { "relevant": 0, "irrelevant": 1 }


        if release_name in existing_release_names or release_name in already_added_release_names:
            continue

        final_releases.append({ "release_id": release_count,
                            "title": release_name,
                            "doi": release["_source"]["doi"] })
        
        already_added_release_names.append(release_name)
        authors = release["_source"]["contrib_names"]
        last_author_order = len(authors)
        
        for author_order, author in enumerate(authors, start=1):
            if author_order == 1:
                qualifier = " (first) author"
            elif author_order == last_author_order:
                qualifier = " (last) author"
            else:
                qualifier = " (coauthor) author"

            if author in author_dict:
                author_dict[author] = { "release_ids": author_dict[author]["release_ids"] + [(release_count, f"{author_order}.{qualifier}")] }
            else:
                author_dict[author] = { "release_ids": [(release_count, f"{author_order}.{qualifier}")] }

        release_count += 1

    # Cut out the authors whose ratio of relevant releases is less than RELEVANCE_QUOTA
    for author in author_dict_releases:
        if author_dict_releases[author]["irrelevant"] != 0:
            if author_dict_releases[author]["relevant"] / author_dict_releases[author]["irrelevant"] < RELEVANCE_QUOTA:
                if author in author_dict:
                    del author_dict[author]

    processes = []
    print(f"LEN OF AUTHOR DICT: {len(author_dict)}")

    # save the author dict properly in chunks
    for chunk in chunks(author_dict, NUMBER_OF_INNER_PROCESSES):
        p = Process(target=author_dict_to_database, args=(chunk,))
        processes.append(p)
        p.start()

    # wait for the processes to end
    for p in processes:
        p.join()

    db.releases.insert_many(final_releases)
    client.close()
    return release_count


def response_to_database(response: dict[str, any], page_number: int, release_id: int,
                         first_time: bool):
    global total_page_number

    if "hits" not in response:
        eprint("A PROBLEM OCCURRED WITH MAKING THE REQUEST (SOMEONE WAS TOO SLOW), ABORTING CURRENT CHUNK")
        with open("tempresponse.json", "w") as f:
            json.dump(response, f)
        return (release_id, -1)

    if first_time:
        total_amount = response["hits"]["total"]["value"]
        total_page_number = math.ceil(total_amount / 10000)
        print(f"TOTAL AMOUNT OF RELEASES FOUND: {total_amount:_}")

    releases = response["hits"]["hits"]
    number_of_releases = len(releases)
    if number_of_releases == 0:
        if first_time:
            eprint("Nothing could be found with these topics")
        return (release_id, -1)
    
    print(f"CURRENTLY PROCESSING {number_of_releases:_} Many RELEASES IN PAGE NUMBER: {page_number + 1} OUT OF {total_page_number:_}")

    scroll_id = response["_scroll_id"]

    new_release_id = releases_to_database(
                                releases=releases,
                                release_id=release_id)

    print(f"FINISHED PROCESSING PAGE NUMBER: {page_number + 1} OUT OF {total_page_number:_}")

    # return a tuple with content as such: (new_release_id, scroll_id)
    return (new_release_id, scroll_id)

def make_request_and_save_response(scroll_id: str = "",
                                   things_to_look_for: list = [],
                                   second_step: bool = False,
                                   page_number: int = 0,
                                   scroll_timeout_mins: int = 3,
                                   release_id: int = 0):

    first_time = True
    
    if scroll_id == "":
        # We are making the first request.

        data_template: dict[str, any] = {
            "query": {
                "bool": {
                    "should": []
                }
            },
            "size": 10000,
        }

        for thing in things_to_look_for:
            if thing == "":
                data_template["query"]["bool"]["should"].append({ "match_all": {} })
            else:
                if second_step:
                    data_template["query"]["bool"]["should"].append({ "match_phrase": { "contrib_names": thing } })
                else:
                    data_template["query"]["bool"]["should"].append({ "match_phrase": { "title": thing } })

        response_json = robust_request(url="https://search.fatcat.wiki/fatcat_release/_search?scroll=" + str(scroll_timeout_mins) + "m",
                                       data=data_template,
                                       post_request=True)

    else:
        first_time = False

        # We are making a subsequent request.

        data: dict[str, any] = {
            "scroll": str(scroll_timeout_mins) + "m",
            "scroll_id": scroll_id,
        }

        response_json = robust_request(url="https://search.fatcat.wiki/_search/scroll",
                                       data=data,
                                       post_request=True)

    if "failure" in response_json:
        eprint(response_json["failure"])

        # Terminate the program completely.

        sys.exit(1)

    # Return a tuple with content as such: (new_release_id, scroll_id).

    return response_to_database(
                    response=response_json,
                    page_number=page_number,
                    release_id=release_id,
                    first_time=first_time)

def get_and_save_releases_from_fatcat_release_search(things_to_look_for: list[str], second_step: bool, release_id: int, main_concepts: list[str]) -> int:
    global main_concepts_list
    main_concepts_list = main_concepts

    page_number = 0
    
    while True:
        if page_number == 0:
            # We are making the first request.

            release_id, scroll_id = make_request_and_save_response(
                                                    scroll_id="",
                                                    things_to_look_for=things_to_look_for,
                                                    second_step=second_step,
                                                    page_number=page_number,
                                                    scroll_timeout_mins=3,
                                                    release_id=release_id)
            if scroll_id == -1:
                return release_id
        else:
            # We are making a subsequent request.

            release_id, scroll_id = make_request_and_save_response(
                                                    scroll_id=scroll_id,
                                                    things_to_look_for=things_to_look_for,
                                                    second_step=second_step,
                                                    page_number=page_number,
                                                    scroll_timeout_mins=3,
                                                    release_id=release_id)
            if scroll_id == -1:
                return release_id
        
        page_number += 1