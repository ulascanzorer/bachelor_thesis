# Find top [num] ORCID urls given a list of concepts

import requests
import os
from utils import eprint

def find_top_orcids(name: str, concepts: list[str], num_of_ids: int, how_many_results: int = 50, match_needed: int = 2) -> list[str]:
    top_orcids = []
    access_token = os.environ.get("ORCID_ACCESS_TOKEN")

    headers = {
        "Content-Type": "application/vnd.orcid+json",
        "Authorization type and Access token": "Bearer " + access_token,
    }

    url = "https://pub.orcid.org/v3.0/expanded-search/?q=" + name
    response = requests.get(url, headers=headers)
    response_dict = response.json()
    expanded_results = response_dict["expanded-result"]

    if not expanded_results:
        eprint(f"No results found for {name}")
        return top_orcids
    expanded_results = expanded_results[:how_many_results]

    number_of_results = len(expanded_results)

    result_counter = 1

    found_orcid_urls = []
    for result in expanded_results:
        # print(f"We are at {result_counter} of {number_of_results}")
        if (name_in_result(name, result, match_needed)):
            found_orcid_urls.append("https://orcid.org/" + result["orcid-id"])
            if len(found_orcid_urls) == num_of_ids:
                return found_orcid_urls

        """ orcid = result["orcid-identifier"]["path"]
        url = f'https://pub.orcid.org/v3.0/{orcid}/works'
        response = requests.get(url, headers=headers)
        for concept in concepts:
            if concept in response.text:
                print("found")
                found_orcid_urls.append(result["orcid-identifier"]["uri"])
                if len(found_orcid_urls) == num_of_ids:
                    return found_orcid_urls
                break """
        result_counter += 1
    return found_orcid_urls

def name_in_result(name: str, result: dict[str, any], match_needed: int = 2) -> bool:
    name_splitted = name.split()

    # Remove abbreviated names like "A.".

    for name in name_splitted:
        if name.endswith("."):
            name_splitted.remove(name)

    # Only return true if there are at least two matches.

    match_count = 0

    for name in name_splitted:
        given_names = result["given-names"]
        if given_names:
            if name in given_names.lower().split():
                match_count += 1
                if match_count >= match_needed:
                    return True

        family_names = result["family-names"]
        if family_names:
            if name in family_names.lower().split():
                match_count += 1
                if match_count >= match_needed:
                    return True

    return False