from pymongo import MongoClient
import gender_guesser.detector as gender
import re

# A function to divide a list into smaller lists, given the size of the smaller lists.

def list_to_smaller_lists(list_to_divide, smaller_list_size):
    smaller_lists = []
    for i in range(0, len(list_to_divide), smaller_list_size):
        smaller_lists.append(list_to_divide[i:i+smaller_list_size])
    return smaller_lists


# The main function to query for the works and authors and save the results appropriately in the database.

def query_and_store(original_concepts, subconcepts, earliest_publication_year, result_id):
    client = MongoClient("localhost", 27017)
    db = client.final_orcid_database

    batch_size = 100000 # This is the number of documents that will be returned from the database in one go, we set this to a high number in order to have less frequent interaction with the database for the performance.

    
    # We first query the works by dividing the subconcepts list into smaller lists to make multiple queries to avoid errors because of the number of results. We save all of the put codes that we find during these queries in the found_put_codes list.

    number_of_subconcepts_to_query_at_one_time = 20
    smaller_subconcepts_lists = list_to_smaller_lists(subconcepts, number_of_subconcepts_to_query_at_one_time)

    found_put_codes = set()

    number_of_queries = len(smaller_subconcepts_lists)
    counter = 1
    for subconcepts_list in smaller_subconcepts_lists:
        print(subconcepts_list)
        print(f"We are at query number {counter} out of {number_of_queries} queries.")
        counter += 1
        regex_pattern = "|".join(fr"\b{re.escape(subconcept)}\b" for subconcept in subconcepts_list)
        regex = f"({regex_pattern})"

        found_works_cursor = db.works.find({ "$expr": { "$gte": [ { "$toInt": "$publication_year" }, earliest_publication_year] },
                                             "title": { "$regex": regex, "$options": "i" },}).batch_size(batch_size)

        for found_work in found_works_cursor:
            found_put_codes.add(found_work["put_code"])


    print("Number of found put codes: ", len(found_put_codes))


    # Now, we will query the authors using the put codes that we have found in the previous step. We use the same method as before and divide the put codes list into smaller lists to make the queries error-free.

    number_of_put_codes_to_query_at_one_time = 100000
    smaller_put_codes_lists = list_to_smaller_lists(list(found_put_codes), number_of_put_codes_to_query_at_one_time)

    found_orcid_ids = set()    # Set as a set, just to be sure we don't have duplicate orcid ids.
    found_results = []

    number_of_queries = len(smaller_put_codes_lists)
    counter = 1
    for put_codes_list in smaller_put_codes_lists:
        print(f"We are at query number {counter} out of {number_of_queries} queries.")
        counter += 1

        found_authors_cursor = db.authors.find({ "works": { "$elemMatch": { "$elemMatch": { "$in": put_codes_list } } } }).batch_size(batch_size)

        found_authors_list = list(found_authors_cursor)
        num_of_found_authors = len(found_authors_list)

        for found_author in found_authors_list:
            if found_author["orcid_id"] in found_orcid_ids:
                continue
            found_orcid_ids.add(found_author["orcid_id"])

            orcid_id = found_author["orcid_id"]

            # Just in case, if the gender field is non-existent set it to "unknown" as default.

            if "gender" not in found_author:
                found_author["gender"] = "unknown"

            # We create the author entry, whose main purpose is to save information specific to the search.

            author_entry = { 
                "orcid_id": orcid_id,
                "given_names": found_author["given_names"], # These three fields are added for
                "family_name": found_author["family_name"], # performance reasons, to avoid
                "gender": found_author["gender"],   # querying the authors collection again for them.
                "works": [],
                "only_author_count": 0,
                "first_author_count": 0,
                "co-author_count": 0,
                "last_author_count": 0,
                "unknown_count": 0, 
                "relevant_work_count": 0,
                "relevant_work_ratio": 0.0
            }

            works_of_author = found_author["works"]
            all_works_count = len(works_of_author)

            # We only consider the works whose put codes were found before, the relevant works.

            filtered_works_of_author = list(filter(lambda work: work[0] in found_put_codes, works_of_author))
            
            author_entry["relevant_work_count"] = len(filtered_works_of_author)
            if all_works_count > 0:
                author_entry["relevant_work_ratio"] = author_entry["relevant_work_count"] / all_works_count

            # -1: only_author
            # -2: first_author
            # -3: co-author
            # -4: last_author
            # -5: unknown

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

                author_entry["works"].append([put_code, work[1]])

            found_results.append(author_entry)

    print("Number of found orcid ids: ", len(found_results))

    # Finally, we save the resulting authors to the database, again in smaller parts.

    smaller_found_results = list_to_smaller_lists(list(found_results), 20000)

    for smaller_found_results_list in smaller_found_results:
        db.user_results.insert_one({
            "user_id": 1,
            "result_id": result_id,
            "query": original_concepts,
            "found_results": smaller_found_results_list,
        })