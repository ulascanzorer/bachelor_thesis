# Find top [num] ORCID urls given a list of concepts

import requests
from utils import eprint

def find_top_ORCIDs(name: str, concepts: list[str], num_of_ids: int, how_many_results: int = 200) -> list[str]:
    top_orcids = []

    with open("orchid_credentials.txt", "r") as f:
        contents = f.readlines()
        access_token = contents[7].strip()

    headers = {
        "Content-Type": "application/vnd.orcid+json",
        "Authorization type and Access token": "Bearer " + access_token,
    }

    url = "https://pub.orcid.org/v3.0/search/?q=" + name
    response = requests.get(url, headers=headers)
    response_dict = response.json()
    results = response_dict["result"]
    # Use first 200 results
    results = results[:200]

    number_of_results = len(results)

    result_counter = 1

    found_orcid_urls = []
    for result in results:
        orcid = result["orcid-identifier"]["path"]
        url = f'https://pub.orcid.org/v3.0/{orcid}/works'
        response = requests.get(url, headers=headers)
        for concept in concepts:
            if concept in response.text:
                found_orcid_urls.append(result["orcid-identifier"]["uri"])
                if len(found_orcid_urls) == num_of_ids:
                    return found_orcid_urls
                break
        result_counter += 1
    return found_orcid_urls