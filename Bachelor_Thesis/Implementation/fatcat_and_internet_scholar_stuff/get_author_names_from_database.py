from pymongo import MongoClient
import pymongo

def get_author_names_from_database() -> list[str]:
    client: pymongo.mongo_client.MongoClient = MongoClient("localhost", 27017)
    db = client.results
    collection = db.authors
    cursor = collection.find({})
    names = []
    for document in cursor:
        names.append(document["name"])

    return names
