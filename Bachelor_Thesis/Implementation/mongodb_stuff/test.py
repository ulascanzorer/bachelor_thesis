from pymongo import MongoClient
import json

# Connect to mongodb database

client = MongoClient("localhost", 27017)

db = client.testjsondb

# Load the test json file

with open("./test.json", "r") as f:
    test_dict = json.load(f)

# Drop the authors table at the start.
db.drop_collection("authors")

# Go through the names in test_dict, if name exists in database append the new values,
# if not add the new name and values.
for name in test_dict:
    result = db.authors.find_one({ "name": { "$in": [name] } })

    if not result:
        # Name is not in database.
        db.authors.insert_one({ "name": name, "releases": test_dict[name] })
    else:
        # Name is in database, add the new values to existing document.
        print(f"This name is already in the database: {name}")
        for release in test_dict[name]:
            db.authors.update_one(
                { "name": name },
                { "$push": { "releases": release } }
            )


""" # Add one document as an example
db.authors.insert_one({ "name": "ulas", "age": 22 })

document = db.authors.find_one({ "name": { "$in": ["ulas"] } })
print(document) """
    