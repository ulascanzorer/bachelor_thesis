from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient("localhost", 27017)

db = client.neuraldb

people = db.people

mike_id = people.insert_one({"name": "Mike", "age": 30}).inserted_id
people.insert_one({"name": "Lisa", "age": 20, "interests": ["C++", "Python", "Piano"]})

for person in people.find():
    print(person)


print([p for p in people.find({"_id": ObjectId("6572efc53d6e2d2bd2bbfa43")})])

print([p for p in people.find({"age": {"$lt": 25}})])

people.update_one({"_id": ObjectId("6572f81221415378ef2d9fa7")}, {"$set": {"age": 27}})

people.delete_many({"age": {"$lt": 25}})

client.drop_database("neuraldb")