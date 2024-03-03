from pymongo import MongoClient
import pymongo

def aggregate_duplicate_authors() -> None:
    client: pymongo.mongo_client.MongoClient = MongoClient("localhost", 27017)
    client.drop_database("test")

    db = client.results

    db.authors.aggregate([
        {
            "$unwind": "$release_ids"
        },
        {
            "$group": { "_id": {"name": "$name", "gender": "$gender", "multiple_authors": "$multiple_authors" }, "release_ids": { "$addToSet": "$release_ids" } }
        },
        {
            "$project": { "_id": 0, "name": "$_id.name", "gender": "$_id.gender", "release_ids": "$release_ids", "multiple_authors": "$_id.multiple_authors" }
        },
        {
            "$merge": { "into": "authors_result", "on": "_id", "whenMatched": "replace", "whenNotMatched": "insert" }
        }
    ])

    db.drop_collection("authors")
    db.authors_result.rename("authors")