from pathlib import Path
from pymongo import MongoClient
import pickle
import xmltodict
import sys
import ray

summary_path = Path("./ORCID_2023_10_activities_0")

# Create a mongodb connection.

client = MongoClient("localhost", 27017)
db = client.orcid

# An entry buffer, when we fill it up to ENTRY_LIMIT, we will process everything in it.

ENTRY_LIMIT = 2000
entry_buffer = []

# A variable to save already inserted put_codes.

already_inserted_put_codes = []


def get_author_role(combined_name, contributors):
    # Decide which one of the contributors' name corresponds to our combined name the most.

    # e.g. combined_name = "Ulaş Can Zorer"
    # e.g. contributors = ["U. C. Zorer", "Erkan Özyer"]

    if not contributors:
        return "first_author"

    num_contributors = len(contributors)

    if num_contributors == 0:
        # We are the only author here.

        return "only_author"

    # Transform name_parts to lowercase.

    name_parts = combined_name.split()
    name_parts_lowercase = []
    for name_part in name_parts:
        name_part = "".join(filter(str.isalpha, name_part))
        name_parts_lowercase.append(name_part.lower())



    if num_contributors == 1:
        # Check if our name matches with the single contributor

        contributor = contributors[0]

        contributor_parts = contributor.split()
        contributor_parts_lowercase = []

        for contributor_part in contributor_parts:
            contributor_part = "".join(filter(str.isalpha, contributor_part))
            contributor_parts_lowercase.append(contributor_part.lower())

        for name_part in name_parts_lowercase:
            for contributor_part in contributor_parts_lowercase:
                if name_part in contributor_part or contributor_part in name_part:
                    return "only_author"

        return "unknown"

    contributor_to_match_count = {}

    for index, contributor in enumerate(contributors):
        contributor_parts = contributor.split()
        contributor_parts_lowercase = []

        for contributor_part in contributor_parts:
            contributor_part = "".join(filter(str.isalpha, contributor_part))
            contributor_parts_lowercase.append(contributor_part.lower())

        for name_part in name_parts_lowercase:
            for contributor_part in contributor_parts_lowercase:
                if name_part in contributor_part or contributor_part in name_part:
                    if index in contributor_to_match_count:
                        contributor_to_match_count[index] += 1
                    else:
                        contributor_to_match_count[index] = 1
                    break
            
    if contributor_to_match_count:
        max_index = max(contributor_to_match_count, key=contributor_to_match_count.get)

        if max_index == 0:
            # We are first author here.

            return "first_author"
        elif max_index == num_contributors - 1:
            # We are last author here.

            return "last_author"
        else:
            # We are a co-author here.

            return "co-author"
    else:
        # Author role is unknown.

        return "unknown"
    

def process_entries():
    print("Processing and saving a batch of entries.")

    adding_client = MongoClient("localhost", 27017)
    adding_db = adding_client.final_orcid_database

    authors_to_add = []
    works_to_add = []

    all_orcids = []

    for entry in entry_buffer:
        all_orcids.append(entry["orcid"])

    orcid_to_names = {} # e.g. { "0000-0003-4496-9510": ["Chao", "Tao"], ... }

    found_authors_cursor = db.authors.find({ "orcid": { "$in": all_orcids } })

    for found_author in found_authors_cursor:
        orcid = found_author["orcid"]
        given_names = ""
        family_name = ""

        if "given names" in found_author:
            given_names = found_author["given names"]
        if "family name" in found_author:
            family_name = found_author["family name"]

        orcid_to_names[orcid] = [given_names, family_name]

    # Now we can go through all the entries.

    for entry in entry_buffer:

        author = {
            "orcid": entry["orcid"], 
            "works": [], 
            "given_names": orcid_to_names[entry["orcid"]][0], 
            "family_name": orcid_to_names[entry["orcid"]][1], 
            "num_only_author": 0, 
            "num_first_author": 0, 
            "num_co-author": 0, 
            "num_last_author": 0, 
            "num_unknown": 0, 
        }

        combined_name = author["given_names"] + " " + author["family_name"]

        for work in entry["works"]:
            work_entry = [work["put_code"]]

            contributors = work["contributors"]

            author_role = get_author_role(combined_name, contributors)

            if author_role == "only_author":
                author["num_only_author"] += 1
                # -1 symbolizes only_author.

                work_entry.append("-1")
            elif author_role == "first_author":
                author["num_first_author"] += 1
                # -2 symbolizes first_author.

                work_entry.append("-2")
            elif author_role == "co-author":
                author["num_co-author"] += 1
                # -3 symbolizes co-author.

                work_entry.append("-3")
            elif author_role == "last_author":
                author["num_last_author"] += 1
                # -4 symbolizes last_author.

                work_entry.append("-4")
            else:
                author["num_unknown"] += 1
                # -5 symbolizes unknown.

                work_entry.append("-5")

            author["works"].append(work_entry)

            work_to_add = {
                "put_code": work["put_code"], 
                "title": work["title"], 
                "publication_year": work["publication_year"], 
                "url": work["url"], 
                "contributors": work["contributors"],
            }

            # Only add the work to the database if we haven't inserted it yet. This is necessary, 
            # since different authors will likely have the same work multiple times.

            if work_to_add["put_code"] not in already_inserted_put_codes:
                already_inserted_put_codes.append(work_to_add["put_code"])
                works_to_add.append(work_to_add)
            
        authors_to_add.append(author)

    # Let us add the authors to the database.

    adding_db.authors.insert_many(authors_to_add)

    # Before inserting the works, let us filter out the ones whose put codes are already in the
    # already_inserted_put_codes list.

    adding_db.works.insert_many(works_to_add)

    print("Done processing and saving a batch of entries.")


def process_works_folder(activity_folder):
    # e.g. activity_folder = ORCID_2023_10_activities_0/510/0000-0003-4496-9510/works

    entry = { 
        "orcid": activity_folder.parent.name, 
        "works": [], 
        "given_names": "", 
        "family_name": "", 
    }

    for work_xml_file in activity_folder.iterdir():
        if not str(work_xml_file).endswith(".xml"):
            continue
        
        with open(work_xml_file, "r") as xml_file:

            xml_string = xml_file.read()
            try:
                python_dict = xmltodict.parse(xml_string)
            except Exception as e:
                print(f"An error occurred while parsing file {work_xml_file}, and here it is: ")
                print(e)

                # Skip if there was an error parsing. Nothing that can be done, the file is
                # probably corrupt.

                continue

            if "work:work" not in python_dict:
                continue

            work_dict = python_dict["work:work"]
            
            if "@put-code" not in work_dict:
                continue

            put_code = work_dict["@put-code"]   # put_code of the current work.

            work = { 
                "put_code": put_code, 
                "title": "", 
                "publication_year": -1,
                "url": "", 
                "contributors": [], 
            }

            if "work:title" in work_dict and work_dict["work:title"] is not None and "common:title" in work_dict["work:title"]:
                work["title"] = work_dict["work:title"]["common:title"]

            if "common:publication-date" in work_dict and work_dict["common:publication-date"] is not None and "common:year" in work_dict["common:publication-date"]:
                work["publication_year"] = work_dict["common:publication-date"]["common:year"]

            if "common:url" in work_dict:
                work["url"] = work_dict["common:url"]


            contributors = []


            if "work:contributors" in work_dict and work_dict["work:contributors"] is not None and "work:contributor" in work_dict["work:contributors"]:
                contributor_entries = work_dict["work:contributors"]["work:contributor"]

                # If we have only one contributor.

                if type(contributor_entries) == dict:
                    if "work:credit-name" in contributor_entries:
                        contributors.append(contributor_entries["work:credit-name"])
                        work["contributors"] = contributors
                
                # If we have more than one contributors.

                else:
                    for contributor_entry in contributor_entries:
                        if "work:credit-name" in contributor_entry:
                            contributors.append(contributor_entry["work:credit-name"])

                    work["contributors"] = contributors

            entry["works"].append(work)

    entry_buffer.append(entry)
    if len(entry_buffer) >= ENTRY_LIMIT:
        process_entries()
        del entry_buffer[:]

if __name__ == "__main__":
    num_of_subfolders = len(list(summary_path.iterdir()))

    for index, subfolder in enumerate(summary_path.iterdir()):
        # e.g. subfolder = ORCID_2023_10_activities_0/510

        print(f"Working on: {subfolder} ({index + 1} out of {num_of_subfolders})")

        for orcid_folder in subfolder.iterdir():
            # e.g. orcid_folder = ORCID_2023_10_activities_0/380/0000-0002-5250-5380

            for activity_folder in orcid_folder.iterdir():
                # e.g. activity_folder = ORCID_2023_10_activities_0/510/0000-0003-4496-9510/works

                if activity_folder.name == "works":
                    process_works_folder(activity_folder)
                    break

            if len(entry_buffer) % 1000 == 0:
                print(f"entry_buffer currently has {len(entry_buffer)} elements.")

    # Process the rest of the entries.


    if len(entry_buffer) > 0:
        process_entries()

    # Save all the inserted put codes to a file, so that we can use them later on as well.

    with open("already_inserted_put_codes", "wb") as fp:
        pickle.dump(already_inserted_put_codes, fp)