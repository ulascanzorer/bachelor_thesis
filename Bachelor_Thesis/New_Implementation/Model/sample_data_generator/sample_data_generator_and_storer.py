from pymongo import MongoClient

client = MongoClient("localhost", 27017)
db = client.sample_data

def generate_and_save_sample_data():
    db.drop_collection("releases")
    db.drop_collection("authors")

    releases_to_insert = [
        { "put_code": 0, "title": "A revolutionary convolutional neural net: bla bla", 
          "publication_year": 2024, "external_url": "www.revconv.com" },

        { "put_code": 1, "title": "bla bla alignment bla bla", 
          "publication_year": 2020, "external_url": "www.bazinga.com" },

        { "put_code": 2, "title": "new embeddings bla bla", 
          "publication_year": 2010, "external_url": "www.doinnng.com" },

        { "put_code": 3, "title": "this work sucks", 
          "publication_year": 1990, "external_url": "www.rararara.com" },

        { "put_code": 4, "title": "geography is so important", 
          "publication_year": 2001, "external_url": "www.yeahh.com" },

        { "put_code": 5, "title": "revolutionary gene therapy", 
          "publication_year": 2005, "external_url": "www.nope.com" },

        { "put_code": 6, "title": "mining is so difficult, it is crazy", 
          "publication_year": 2010, "external_url": "www.crazy.com" },

        { "put_code": 7, "title": " autoencoder is a thing of the past now", 
          "publication_year": 2011, "external_url": "www.baby.com" },

        { "put_code": 8, "title": "sports are so important", 
          "publication_year": 1980, "external_url": "www.cars2bestmovie.com" },   
        
        { "put_code": 9, "title": "never stretch before a workout", 
          "publication_year": 1977, "external_url": "www.darksouls.com" },
        
        { "put_code": 10, "title": "protein structure is very weird (I don't know)", 
          "publication_year": 2013, "external_url": "www.books.com" },
        
        { "put_code": 11, "title": "image recognition technologies", 
          "publication_year": 2002, "external_url": "www.saxophone.com" },
        
        { "put_code": 12, "title": "big data is back babyyyy", 
          "publication_year": 1999, "external_url": "www.dot.com" },
        
        { "put_code": 13, "title": "I like watching movies", 
          "publication_year": 2018, "external_url": "www.nothing.com" },
    ]

    # 0: first_author
    # 1: co-author
    # 2: last_author


    authors_to_insert = [
        { "orcid": 0, "given names": "Ulaş Can", "family name": "Zorer", 
          "works": [(0, "-1"), (5, "-3")], 
          "num_first_author": 1, "num_last_author": 1, "num_co_author": 0 },
        
        { "orcid": 1, "given names": "Ela", "family name": "Zorer", 
          "works": [(1, "-1"), (2, "-2")], 
          "num_first_author": 1, "num_last_author": 0, "num_co_author": 1 },
        
        { "orcid": 2, "given names": "Duygu", "family name": "Zorer", 
          "works": [(8, "-2"), (9, "-3")], 
          "num_first_author": 0, "num_last_author": 1, "num_co_author": 1 },
        
        { "orcid": 3, "given names": "Gürol", "family name": "Zorer", 
          "works": [(11, "-1"), (12, "-2")], 
          "num_first_author": 1, "num_last_author": 0, "num_co_author": 1 },
    ]

    db.releases.insert_many(releases_to_insert)
    db.authors.insert_many(authors_to_insert)


if __name__ == "__main__":
    generate_and_save_sample_data()
    print("DONE")