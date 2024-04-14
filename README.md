# Installation and Usage Guide
In the Web_application directory you can find the main django project folder, the requirements.txt file for the Python requirements, and a Dockerfile. You can use the application using two methods:
### 1. Without Docker
#### Installing Python requirements
From the root directory of the repository, run the following commands to change your directory, create and enable a virtual environment and install the necessary Python packages:
```
cd Web_application/talentmanagementsearchtool
python -m venv ./.venv
source .venv/bin/activate
pip install -r ../requirements.txt
```
#### Installing and starting mongod
Then, you must install and start the mongod service. This part could be different based on your operating system, but you can find the instructions for your operating system quite easily online.
#### Populating the MongoDB database
If you only want a taste of the application, you can use the following command from the root directory in order to put the tutorial data in your database and use only the tutorial:
```
mongorestore -d final_orcid_database ./tutorial_database
```
If you want the full functionality, proceed with the remaining instructions. **Caution**: If you want the tutorial and the full functionalities, run the command above before extracting the ORCID files below.
 
You must first download the individual ORCID Public Data Files from here: [ORCID Public Data Files](https://orcid.figshare.com/articles/dataset/ORCID_Public_Data_File_2023/24204912)

Then, you must use the extraction scripts provided in the Extraction_scripts directory. The workflow is as follows:
1. Get the ORCID summaries folder in the same directory with "orcid_summaries_extractor.py" and execute it in order to retrieve general information about all the ORCID users, which shall be used by "orcid_activities_file_extractor.py".
2. One by one, get the ORCID activity folders in the same directory with "orcid_activities_file_extractor.py", for each folder change the name in the script accordingly, the scripts are documented so you will find it easily.
3. When every folder has been processed, use the functions in the "database_manager.ipynb" in order to remove possible duplicates, and add indices to the database collections.
4. At the end, use the "adding_genders.ipynb" in order to add the genders to all the authors.

#### Setting environment variables
Finally, for full functionality you must provide some environment variables for the application to use. These are:
1. EMAIL_SENDER_ADDRESS: Set this to a gmail account that will be used to send the notifications of the application per email.
2. EMAIL_SENDER_PASSWORD: Set this to be the app password of the gmail account.
3. OPENAI_API_KEY: Set this to your private openai key, which you can receive by their website.
You can restart your shell in order for these to come into effect.

#### Running the web application
After finishing the previous steps, run the following commands from the root of the repository in order to run a local server. You can access the web application on [localhost:8000](localhost:8000) on your browser and use its full functionalities.
```
cd Web_application/talentmanagementsearchtool
source .venv/bin/activate
python manage.py runserver
```
## 2. With Docker
If you want to run the local server inside a Docker container, you can follow the steps below:
1. Go into the Web_application directory from the root directory of the repository and build the Docker image:
```
cd Web_application
docker build -t talentmanagementsearchtool .
```
2. Run the container with the following command, which also does the port mappings so that you can view the application on your host machine when it runs:
```
docker run -d -p 8000:8000 --name talentmanagementsearchtool -it talentmanagementsearchtool
```
3. In the Docker container, the Python requirements are installed and mongod is running. You can now copy the extraction scripts and the final_orcid_database folder from the root of the repository into the container using a command like "docker cp".
4. You can now enter your Docker container and follow the steps from the first part starting from the "Populate the MongoDB Database":
```
docker exec -it talentmanagementsearchtool bash
```
5. You must modify the final command to run the server as follows, so that the server accepts requests from your host machine:
```
python manage.py runserver 0.0.0.0:8000
```