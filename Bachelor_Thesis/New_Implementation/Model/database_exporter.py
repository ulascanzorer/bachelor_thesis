from pymongo import MongoClient
import subprocess

def export_database():
    subprocess.run(["mongoexport", "--db=sample_data", "--collection=releases_result", "--type=csv",
                   "--fields=put_code,title,publication_year,external_url",
                   "--out=found_releases.csv"])

    subprocess.run(["mongoexport", "--db=sample_data", "--collection=authors_result", "--type=csv",
                   "--fields=orcid,given names,family name,works,num_first_author,num_last_author,num_co_author",
                   "--out=found_authors.csv"])