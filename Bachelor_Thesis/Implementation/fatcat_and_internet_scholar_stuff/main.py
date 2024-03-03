from save_data_to_mongodb_from_query import save_data_to_mongodb_from_query, send_email
from get_and_save_releases_from_fatcat_release_search import get_and_save_releases_from_fatcat_release_search
from utils import eprint

if __name__ == "__main__":
    operation_result = save_data_to_mongodb_from_query(main_concepts=["deep learning"],
                                     num_concepts=10,
                                     api_to_database=get_and_save_releases_from_fatcat_release_search,
                                     name_chunk_len=1024)
    
    if operation_result != -1:
        send_email("ulascanzorer@gmail.com")
    else:
        eprint("There has been an error.")
        
    print("DONE")
