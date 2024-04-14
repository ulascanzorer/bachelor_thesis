import xmltodict
import os
import math
from multiprocessing import Process
from multiprocessing import set_start_method
from pymongo import MongoClient

# Set a number of processes.

NUMBER_OF_PROCESSES = 20

# Create a limit for the buffer where we write the contents to the database and empty it.

AUTHORS_TO_ADD_LIMIT = 10000

current_orcid = ""  # variable to store the current orcid

# A function to divide a list of names into chunks.

def divide_list_into_chunks(list_to_divide, number_of_chunks):
    chunk_size = math.ceil(len(list_to_divide) // number_of_chunks)

    return [list_to_divide[i:i + chunk_size] for i in range(0, len(list_to_divide), chunk_size)]

# A function to parse all the xml files in a first_level_directory and save the necessary 
# information in the respective buffer.

def process_first_level_directories(process_id, first_level_directory_paths):

    # Create an author buffer that we will write to the database when it has certain amounts of elements.
    # When we reach that state, we will also clear it and start filling it again.

    authors_to_add = []

    # Initialize MongoDB connection to the local database.

    client = MongoClient("localhost", 27017)
    db = client.orcid

    # The main loop.

    for first_level_directory_path in first_level_directory_paths:
        print("Process", process_id, "currently processing files in:", first_level_directory_path)

        # e.g. first_level_directory_path = "./ORCID_2023_10_summaries/000"

        xml_file_names = os.listdir(first_level_directory_path)
        number_of_names = len(xml_file_names)

        for index, xml_file_name in enumerate(xml_file_names):
            # e.g. xml_file_name = "0000-0003-1622-0000.xml"

            if index % 1000 == 0:
                print(index, "out of", number_of_names)

            # Skip non xml files.

            if not xml_file_name.endswith(".xml"):
                continue

            author = { "orcid": xml_file_name.split(".")[0] }

            xml_file_path = os.path.join(first_level_directory_path, xml_file_name)

            # e.g. xml_file_path = "./ORCID_2023_10_summaries/000/0000-0003-1622-0000.xml"

            with open(xml_file_path, "r") as xml_file:
                xml_string = xml_file.read()
                python_dict = xmltodict.parse(xml_string)

                if "record:record" in python_dict:
                    record_dict = python_dict["record:record"]
                    if "person:person" in record_dict:
                        person_dict = record_dict["person:person"]
                        if "person:name" in person_dict:
                            person_name_dict = person_dict["person:name"]
                            if "personal-details:given-names" in person_name_dict:
                                given_names = person_name_dict["personal-details:given-names"]
                                author["given names"] = given_names
                            
                            if "personal-details:family-name" in person_name_dict:
                                family_name = person_name_dict["personal-details:family-name"]
                                author["family name"] = family_name

            authors_to_add.append(author)

            if len(authors_to_add) >= AUTHORS_TO_ADD_LIMIT:
                db.authors.insert_many(authors_to_add)
                del authors_to_add[:]
            elif index == number_of_names - 1 and len(authors_to_add) > 0:
                db.authors.insert_many(authors_to_add)
                del authors_to_add[:]


def process_orcid_summaries():
    path = "./ORCID_2023_10_summaries"
    first_level_directories = os.listdir(path)
    first_level_directory_paths = []

    for first_level_directory in first_level_directories:
        first_level_directory_path = os.path.join(path, first_level_directory)
        first_level_directory_paths.append(first_level_directory_path)

    processes = []

    # Divide the first level directories into chunks and create enough processes to handle them.

    process_id = 0

    for chunk in divide_list_into_chunks(first_level_directory_paths, NUMBER_OF_PROCESSES):
        p = Process(target=process_first_level_directories, args=(process_id, chunk,))
        process_id += 1
        processes.append(p)
        p.start()

    # Wait for the processes to end.

    for p in processes:
        p.join()

    print("All files processed.")


if __name__ == "__main__":
    # Do this configuration to (hopefully) stop the slowdown of processes over time.

    set_start_method("spawn")

    process_orcid_summaries()
