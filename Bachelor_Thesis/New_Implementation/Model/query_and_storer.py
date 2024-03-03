from pymongo import MongoClient
import re

def list_to_smaller_lists(list_to_divide, smaller_list_size):
    smaller_lists = []
    for i in range(0, len(list_to_divide), smaller_list_size):
        smaller_lists.append(list_to_divide[i:i+smaller_list_size])
    return smaller_lists


def query_and_store(subconcepts):
    client = MongoClient("localhost", 27017)
    # db = client.sample_data
    db = client.final_orcid_database

    batch_size = 100000

    # Let us first query the releases and authors.

    number_of_subconcepts_to_query_at_one_time = 20
    smaller_lists = list_to_smaller_lists(subconcepts, number_of_subconcepts_to_query_at_one_time)

    found_put_codes = set()

    number_of_queries = len(smaller_lists)
    counter = 1
    for subconcepts_list in smaller_lists:
        print(subconcepts_list)
        print(f"We are at query number {counter} out of {number_of_queries} queries.")
        counter += 1
        regex_pattern = "|".join(fr"\b{re.escape(subconcept)}\b" for subconcept in subconcepts_list)
        regex = f"({regex_pattern})"

        found_works_cursor = db.works.find({ "title": { "$regex": regex, "$options": "i" } }).batch_size(batch_size)

        for found_work in found_works_cursor:
            found_put_codes.add(found_work["put_code"])


    print("Number of found put codes: ", len(found_put_codes))


    # Example found_orcids entry:
    # {
        # "orcid": 0009-0007-8042-2543,
        # "first_author_count": 1,
        # "co-author_count": 2,
        # "last_author_count": 3,
    # }

    number_of_put_codes_to_query_at_one_time = 100000
    smaller_lists = list_to_smaller_lists(list(found_put_codes), number_of_put_codes_to_query_at_one_time)

    found_orcids = set()
    found_results = []

    number_of_queries = len(smaller_lists)
    counter = 1
    for put_codes_list in smaller_lists:
        print(f"We are at query number {counter} out of {number_of_queries} queries.")
        counter += 1

        found_authors_cursor = db.authors.find({ "works": { "$elemMatch": { "$elemMatch": { "$in": put_codes_list } } } }).batch_size(batch_size)

        found_authors_list = list(found_authors_cursor)
        num_of_found_authors = len(found_authors_list)
        author_counter = 1

        for found_author in found_authors_list:
            if found_author["orcid"] in found_orcids:
                continue
            found_orcids.add(found_author["orcid"])

            # print(f"Processing author number {author_counter} out of {num_of_found_authors}.")
            author_counter += 1
            author_entry = { 
                "orcid": found_author["orcid"],
                "works": [],
                "only_author_count": 0,
                "first_author_count": 0,
                "co-author_count": 0,
                "last_author_count": 0,
                "unknown_count": 0, 
                "relevant_work_count": 0,
            }
            works_of_author = found_author["works"]
            filtered_works_of_author = list(filter(lambda work: work[0] in found_put_codes, works_of_author))
            author_entry["relevant_work_count"] = len(filtered_works_of_author)
            if author_entry["relevant_work_count"] > 500:
                print("How?!")
                print("The length of the original works list: ", len(works_of_author))
                print("The length of the filtered list: ", len(filtered_works_of_author))
                return
            found_results.append(author_entry)

    print("Number of found orcids: ", len(found_results))

    # -1: first_author
    # -2: co-author
    # -3: last_author
    # -4: unknown
    

    # We are not adding the relevant works to the entry anymore, we will allow the user
    # to click on a link to get these kind of information, it takes ridiculously long.
    """ works_of_author = found_author["works"]
    filtered_works_of_author = list(filter(lambda work: work[0] in found_put_codes, works_of_author))

    print("Number of filtered works of author: ", len(filtered_works_of_author))

    for work in filtered_works_of_author:
        put_code = work[0]
        
        if work[1] == "-1":
            author_entry["only_author_count"] += 1
        elif work[1] == "-2":
            author_entry["first_author_count"] += 1
        elif work[1] == "-3":
            author_entry["co-author_count"] += 1
        elif work[1] == "-4":
            author_entry["last_author_count"] += 1
        else:
            author_entry["unknown_count"] += 1

        author_entry["works"].append([put_code, work[1]]) """

    # Now let us save them in a result collection.

    db.drop_collection("user_results")

    smaller_found_results = list_to_smaller_lists(list(found_results), 50000)

    for smaller_found_results_list in smaller_found_results:
        db.user_results.insert_one({
            "user_id": 1,
            "result_id": 1,
            "found_results": smaller_found_results_list,
        })