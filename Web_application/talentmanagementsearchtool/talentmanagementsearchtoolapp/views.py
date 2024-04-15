from django.shortcuts import render, redirect
from pymongo import MongoClient
import django_tables2 as tables
from django_tables2 import RequestConfig, LazyPaginator
from django.http import JsonResponse
from django.utils.html import format_html
from .forms import QueryForm, EmailForm
from .model.main import main_flow
from email_validator import validate_email, EmailNotValidError
from .email_sender import send_email
from django_tables2.export.export import TableExport
from django.core.cache import cache
import uuid
import threading
import time

# Connecting to the local (relative to the server code) mongodb database.

client = MongoClient("localhost", 27017)
db = client.final_orcid_database

########################################### Custom functions and data structures.

# Dictionary to store the status of each processing task.

processing_status = {}

# Table to render the results in the result page.

class DictionaryTable(tables.Table):
    given_names = tables.Column(attrs={ "th": { "title": "Given names of the author" } })
    family_name = tables.Column(attrs={ "th": { "title": "Family name of the author" } })
    gender = tables.Column(attrs={ "th": { "title": "Gender of the author" } })
    orcid_url = tables.Column(attrs={ "th": { "title": "ORCID url of the author" } })
    works = tables.Column(attrs={ "th": { "title": "Works of the author" } })
    relevant_work_count = tables.Column(attrs={ "th": { "title": "Number of works of the author, which are relevant to the given query and published before or in the given year" } })
    relevant_work_ratio = tables.Column(attrs={ "th": { "title": "Ratio of the number of relevant works to the total number of works of the author" } })
    only_author_count = tables.Column(attrs={ "th": { "title": "Number of relevant works of the author where they were the only author (no other contributors)" } })
    first_author_count = tables.Column(attrs={ "th": { "title": "Number of relevant works of the author where they were the first author" } })
    last_author_count = tables.Column(attrs={ "th": { "title": "Number of relevant works of the author where they were the last author" } })
    co_author_count = tables.Column(attrs={ "th": { "title": "Number of relevant works of the author where they were a co-author (somewhere in the middle of the contributors list of the work)" } })
    unknown_count = tables.Column(attrs={ "th": { "title": "Number of relevant works of the author where their role cannot be deducted" } })

    # Custom function to render the orcid_url as a link.

    def render_orcid_url(self, value):
        if value:
            return format_html(f'<a href="{value}" target="_blank">{value}</a>')
        else:
            return ""

    # Custom function to render the works, so that we see the urls in there as actual links.

    def render_works(self, value):
        works_html = ""
        counter = 1
        for work in value:
            # Escape curly braces ({}) in the title so that we don't try to replace them with variables in the f-string.

            escaped_title = work[0].replace("{", "{{").replace("}", "}}")

            work_html = f"{counter}) {escaped_title}, {work[1]}, "
            if work[2] != "":
                work_html += f'<a href="{work[2]}" target="_blank">URL</a>'
            else:
                work_html += "No URL"
            
            work_html += "<br><br>"
            works_html += work_html
            counter += 1
        
        return format_html(works_html)


    # Order the table by descending relevant work ratio by default.

    class Meta:
        order_by = ("-relevant_work_ratio",)

# A function which filters the found author results using the given filters from the users. 

def author_results_with_filters(found_authors_cursor,
                                        # Here comes the filters...
                                        integer_filters,
                                        float_filters,
                                        selected_genders):

    filtered_results = []
    all_put_codes = []

    # Convert the integer filters into a usable state.

    converted_integer_filters = ()

    for filter_count in integer_filters:
        if filter_count is None or filter_count == "":
            converted_integer_filters += (-1, )
        else:
            converted_integer_filters += (int(filter_count), )

    min_relevant_work_count, max_relevant_work_count, min_only_author_count, max_only_author_count, min_first_author_count, max_first_author_count, min_last_author_count, max_last_author_count, min_co_author_count, max_co_author_count, min_unknown_count, max_unknown_count = converted_integer_filters

    # Convert the float filters into a usable state.

    converted_float_filters = ()

    for filter_count in float_filters:
        if filter_count is None or filter_count == "":
            converted_float_filters += (-1, )
        else:
            converted_float_filters += (float(filter_count), )

    min_relevant_work_ratio, max_relevant_work_ratio = converted_float_filters


    for found_author in found_authors_cursor:
        relevant_work_count = found_author["relevant_work_count"]
        relevant_work_ratio = found_author["relevant_work_ratio"]
        only_author_count = found_author["only_author_count"]
        first_author_count = found_author["first_author_count"]
        last_author_count = found_author["last_author_count"]
        co_author_count = found_author["co-author_count"]
        unknown_count = found_author["unknown_count"]
        author_works = found_author["works"]

        # Check for the filters.

        ### Numerical filters. ###

        # relevant_work_count filter.

        if (min_relevant_work_count != -1 and relevant_work_count < min_relevant_work_count) or (max_relevant_work_count != -1 and relevant_work_count > max_relevant_work_count):
            continue

        # relevant_work_ratio filter.

        if (min_relevant_work_ratio != -1 and relevant_work_ratio < min_relevant_work_ratio) or (max_relevant_work_ratio != -1 and relevant_work_ratio > max_relevant_work_ratio):
            continue

        # only_author_count filter.

        if (min_only_author_count != -1 and only_author_count < min_only_author_count) or (max_only_author_count != -1 and only_author_count > max_only_author_count):
            continue

        # first_author_count filter.

        if (min_first_author_count != -1 and first_author_count < min_first_author_count) or (max_first_author_count != -1 and first_author_count > max_first_author_count):
            continue

        # last_author_count filter.

        if (min_last_author_count != -1 and last_author_count < min_last_author_count) or (max_last_author_count != -1 and last_author_count > max_last_author_count):
            continue

        # co_author_count filter.

        if (min_co_author_count != -1 and co_author_count < min_co_author_count) or (max_co_author_count != -1 and co_author_count > max_co_author_count):
            continue

        # unknown_count filter.

        if (min_unknown_count != -1 and unknown_count < min_unknown_count) or (max_unknown_count != -1 and unknown_count > max_unknown_count):
            continue
        
        ### End of numerical filters. ###

        # gender filter.

        if "gender" not in found_author:
            found_author["gender"] = "unknown"

        if len(selected_genders) > 0 and found_author["gender"] not in selected_genders:
            continue

        orcid_id = found_author["orcid_id"]
        given_names = found_author["given_names"]
        family_name = found_author["family_name"]

        # Get the actual works with their information from the "works" collection.
        
        for work in author_works:
            all_put_codes.append(work[0])

        author_entry = found_author
        author_entry["orcid_url"] = f"https://orcid.org/{ orcid_id }"

        # We have to do this because of inconsistent naming :/.

        del author_entry["co-author_count"]
        author_entry["co_author_count"] = co_author_count

        filtered_results.append(author_entry)

    # Query for all the works only once at the end.

    all_works_and_information = {}

    works_cursor = db.works.find( { "put_code": { "$in": all_put_codes } })

    for work in works_cursor:
        all_works_and_information[work["put_code"]] = [work["title"], work["publication_year"], work["url"]]

    # Go through all the author entries and replace their "works" field with the detailed version.

    final_filtered_results = []

    for author_entry in filtered_results:
        new_works = []
        for work in author_entry["works"]:
            new_works.append(all_works_and_information[work[0]])
    
        author_entry["works"] = new_works
        final_filtered_results.append(author_entry)

    return final_filtered_results

# A generator specific for the tutorial, also allows filtering and yields filtered results.

def tutorial_custom_generator(integer_filters, float_filters, selected_genders):
    # Convert the integer filters into a usable state.

    converted_integer_filters = ()

    for filter_count in integer_filters:
        if filter_count is None or filter_count == "":
            converted_integer_filters += (-1, )
        else:
            converted_integer_filters += (int(filter_count), )

    min_relevant_work_count, max_relevant_work_count, min_only_author_count, max_only_author_count, min_first_author_count, max_first_author_count, min_last_author_count, max_last_author_count, min_co_author_count, max_co_author_count, min_unknown_count, max_unknown_count = converted_integer_filters

    # Convert the float filters into a usable state.

    converted_float_filters = ()

    for filter_count in float_filters:
        if filter_count is None or filter_count == "":
            converted_float_filters += (-1, )
        else:
            converted_float_filters += (float(filter_count), )

    min_relevant_work_ratio, max_relevant_work_ratio = converted_float_filters

    # Get the tutorial results.

    tutorial_results_cursor = db.tutorial_result.find()

    for result in tutorial_results_cursor:
        # Check for the filters.

        ### Numerical filters. ###

        # relevant_work_count filter.

        if (min_relevant_work_count != -1 and result["relevant_work_count"] < min_relevant_work_count) or (max_relevant_work_count != -1 and result["relevant_work_count"] > max_relevant_work_count):
            continue

        # relevant_work_ratio filter.

        if (min_relevant_work_ratio != -1 and result["relevant_work_ratio"] < min_relevant_work_ratio) or (max_relevant_work_ratio != -1 and result["relevant_work_ratio"] > max_relevant_work_ratio):
            continue

        # only_author_count filter.

        if (min_only_author_count != -1 and result["only_author_count"] < min_only_author_count) or (max_only_author_count != -1 and result["only_author_count"] > max_only_author_count):
            continue

        # first_author_count filter.

        if (min_first_author_count != -1 and result["first_author_count"] < min_first_author_count) or (max_first_author_count != -1 and result["first_author_count"] > max_first_author_count):
            continue

        # last_author_count filter.

        if (min_last_author_count != -1 and result["last_author_count"] < min_last_author_count) or (max_last_author_count != -1 and result["last_author_count"] > max_last_author_count):
            continue

        # co_author_count filter.

        if (min_co_author_count != -1 and result["co_author_count"] < min_co_author_count) or (max_co_author_count != -1 and result["co_author_count"] > max_co_author_count):
            continue

        # unknown_count filter.

        if (min_unknown_count != -1 and result["unknown_count"] < min_unknown_count) or (max_unknown_count != -1 and result["unknown_count"] > max_unknown_count):
            continue
        
        ### End of numerical filters. ###

        # gender filter.

        if len(selected_genders) > 0 and result["gender"] not in selected_genders:
            continue

        yield result

# A function that transformas a string of concepts to a list.

def concepts_string_to_list_of_strings(concepts_string):
    results = concepts_string.split(",")
    final_results = [" ".join(result.strip().split()) for result in results]
    return final_results

# A function that does the querying and the storing, which is executed in seperate threads for each query.

def query_and_store(concepts, publication_year, task_id):
    concepts_list = concepts_string_to_list_of_strings(concepts)
    num_subconcepts_per_concept = 10 # Hardcoded in the current implementation, could be made a parameter for the user later on.

    # Call the main functionality.

    main_flow(concepts_list, publication_year, num_subconcepts_per_concept, task_id)

    # Set the status of the task to "complete", so that we can check for that in the loading page in order to redirect accordingly or to send the email when the results are ready.

    processing_status[task_id] = "complete"
    print("Done processing.")
    return

# A function that periodically checks if the given task is completed and sends an email to the user when it is.

def wait_for_task_and_send_email(email, task_id):
    while True:
        if task_id in processing_status:
            status = processing_status[task_id]
            if status == "complete":
                del processing_status[task_id]

                email_content = f'The results are in! You can access them using the following link: <a href="http://10.152.16.10:8000/result_page?task_id={task_id}">Results</a>'

                send_email(email, email_content)
                break
            else:
                time.sleep(10)
        else:
            print("THIS SHOULD NOT HAPPEN.")

# A function which divides a list to smaller lists, given the smaller list size.

def list_to_smaller_lists(list_to_divide, smaller_list_size):
    smaller_lists = []
    for i in range(0, len(list_to_divide), smaller_list_size):
        smaller_lists.append(list_to_divide[i:i+smaller_list_size])
    return smaller_lists

########################################### End of custom functions.

########################################### My views.

# A function that is executed when a user acceses the home page.

def home_page(request):
    # If the user has submitted data (academic fields, earliest publication year), store them in the user's session to be accessed later during the query.

    if request.method == "POST":
        form = QueryForm(request.POST)
        if form.is_valid():
            # Do something with the data.

            query = form.cleaned_data["query"]
            publication_year = form.cleaned_data["publication_year"]
            tutorial = form.cleaned_data["tutorial"]

            print(f"This is the value of the tutorial input sent by the client: {tutorial}.")

            # Convert publication year to an integer.

            publication_year = int(publication_year)

            print(f"This is the query: {query} and this is its type: {type(query)}")
            print(f"This is the publication year: {publication_year} and this is its type: {type(publication_year)}")

            # Set the publication year to -1 if we are in tutorial. This will be used later on to determine if we should continue on with displaying the example results.

            if tutorial == "true":
                publication_year = -1

            request.session["concepts"] = query
            request.session["publication_year"] = publication_year

            return redirect("loading_page")

    # If the user has just visited the home page without submitting something, we display the home page with the empty QueryForm.

    else:
        form = QueryForm()

    return render(request, "talentsearchtoolapp/home_page.html", { "form": form , "title": "Home Page" })

# A function that is executed when a user accesses the loading page.

def loading_page(request):
    # If an email address was submitted by the user, we sanitize it and start the thread which waits for the query to finish and send an email.

    if request.method == "POST":
        form = EmailForm(request.POST)
        if form.is_valid():
            # Do something with the data.

            email = form.cleaned_data["email"]

            # Validate the email input.
            
            try:
                validated = validate_email(email)

                email = validated.normalized
                
                # Email address is valid.

                # Create a thread to send the email when we are done and redirect to a success page.

                task_id = request.session.get("current_task_id")

                del request.session["current_task_id"]

                email_sending_thread = threading.Thread(target=wait_for_task_and_send_email, args=(email, task_id, ))

                email_sending_thread.start()

                return redirect("email_confirmation_page")

 
            except EmailNotValidError as e:
                # Render the same page with an error in the context.

                print("EMAIL ERROR")

                form = EmailForm()
                
                context = { "email_error": str(e), "form": form, "title": "Loading Page" }

                return render(request, "talentsearchtoolapp/loading_page.html", context)

    # This part will run before submitting the email address.

    else:
        concepts = request.session.get("concepts")
        publication_year = request.session.get("publication_year")

        # If we are in the tutorial, we show the user the necessary message.

        if publication_year == -1:
            # We are in the tutorial.

            task_id = "tutorial_result"

            form = EmailForm()

            context = { "task_id": task_id, "form": form, "title": "Loading Page" }

            return render(request, "talentsearchtoolapp/loading_page.html", context)
        else:
            # If we are not in the tutorial, we create a unique task_id and start a querying task in a seperate thread.

            task_id = str(uuid.uuid4())

            request.session["current_task_id"] = task_id

            processing_thread = threading.Thread(target=query_and_store, args=(concepts, publication_year, task_id))

            processing_thread.start()

            form = EmailForm()

            context = { "task_id": task_id, "form": form, "title": "Loading Page" }

            processing_status[task_id] = "in_progress"

            return render(request, "talentsearchtoolapp/loading_page.html", context)

# A function that is executed when a user accesses the email_confirmation_page, ideally by being redirected from the loading page.

def email_confirmation_page(request):
    return render(request, "talentsearchtoolapp/email_confirmation_page.html", context={ "title": "Email Confirmation Page" })

# A function that is executed when a user accesses the result page.

def result_page(request):
    # We fill in the parameters in order to be able to query the right results from the database.

    user_id = 1 # Harcoded for now, we assume having one user with multiple results but doesn't matter a lot in our case, since every result has its own unique user_result_id.
    user_result_id = request.GET.get("task_id")

    # Get the numerical filter parameters.
    
    # Integer Filters.

    min_relevant_work_count = request.GET.get("min_relevant_work_count")
    max_relevant_work_count = request.GET.get("max_relevant_work_count")

    min_only_author_count = request.GET.get("min_only_author_count")
    max_only_author_count = request.GET.get("max_only_author_count")

    min_first_author_count = request.GET.get("min_first_author_count")
    max_first_author_count = request.GET.get("max_first_author_count")

    min_last_author_count = request.GET.get("min_last_author_count")
    max_last_author_count = request.GET.get("max_last_author_count")

    min_co_author_count = request.GET.get("min_co_author_count")
    max_co_author_count = request.GET.get("max_co_author_count")

    min_unknown_count = request.GET.get("min_unknown_count")
    max_unknown_count = request.GET.get("max_unknown_count")

    integer_filters = (min_relevant_work_count, max_relevant_work_count, min_only_author_count, max_only_author_count, min_first_author_count, max_first_author_count, min_last_author_count, max_last_author_count, min_co_author_count, max_co_author_count, min_unknown_count, max_unknown_count)

    # Float filters.

    min_relevant_work_ratio = request.GET.get("min_relevant_work_ratio")
    max_relevant_work_ratio = request.GET.get("max_relevant_work_ratio")

    float_filters = (min_relevant_work_ratio, max_relevant_work_ratio)

    # Get the gender parameters.

    selected_genders = request.GET.getlist("gender")
    print(selected_genders)

    # Special case if we are in the tutorial.

    if user_result_id == "tutorial_result":
        tutorial_generator = tutorial_custom_generator(integer_filters, float_filters, selected_genders)

        table = DictionaryTable(tutorial_generator) # use a table from django-tables2

        RequestConfig(request, paginate={ "paginator_class": LazyPaginator }).configure(table) # set the pagination so that we don't see all the results on one page.

        context = { "table": table, "task_id": user_result_id, "selected_genders": selected_genders, "original_query": ["deep learning", "attention mechanisms"], "title": "Result Page" }

        export_format = request.GET.get("_export", None)
        if TableExport.is_valid_format(export_format):
            exporter = TableExport(export_format, table)
            return exporter.response(f"tutorial_table.{export_format}")

        return render(request, "talentsearchtoolapp/result_page.html", context)

    # If we are not in the tutorial, we get the resulting author information with their search-specific counts and save them.

    # First check if the results are in the cache or not.

    cached_data = cache.get(user_result_id)

    if cached_data is None:
        user_results_cursor = db.user_results.find({ "user_id": user_id, "result_id": user_result_id })

        found_author_results = []

        for user_result in user_results_cursor:
            found_author_results.extend(user_result["found_results"])
            original_query = user_result["query"]


        filtered_results = author_results_with_filters(found_author_results,
                                                            # Here comes the filters...
                                                            integer_filters,
                                                            float_filters,
                                                            selected_genders)

        cache.set(user_result_id, (filtered_results, original_query, integer_filters, float_filters, selected_genders), timeout=3600)   # Sets the results in the cache for an hour.

    else:
        filtered_results, original_query, latest_integer_filters, latest_float_filters, latest_selected_genders = cached_data

        # Check if the filters are still the same, if not filter the results again.
        print(selected_genders)
        print(latest_selected_genders)

        if integer_filters != latest_integer_filters or float_filters != latest_float_filters or selected_genders != latest_selected_genders:
            user_results_cursor = db.user_results.find({ "user_id": user_id, "result_id": user_result_id })

            found_author_results = []

            for user_result in user_results_cursor:
                found_author_results.extend(user_result["found_results"])
                original_query = user_result["query"]


            filtered_results = author_results_with_filters(found_author_results,
                                                                # Here comes the filters...
                                                                integer_filters,
                                                                float_filters,
                                                                selected_genders)

            cache.set(user_result_id, (filtered_results, original_query, integer_filters, float_filters, selected_genders), timeout=3600)   # Sets the results in the cache for an hour.
            

    page_size = 20

    table = DictionaryTable(filtered_results)
    RequestConfig(request, paginate={ "paginator_class": LazyPaginator, "per_page": page_size }).configure(table)

    export_format = request.GET.get("_export", None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        export_name = f'query_result_{"".join(original_query)}'
        return exporter.response(f"{export_name}.{export_format}")


    context = { "table": table, "task_id": user_result_id, "selected_genders": selected_genders, "original_query": original_query, "title": "Result Page" }

    return render(request, "talentsearchtoolapp/result_page.html", context)

# A function which is called every time the loading page template wants to learn if the task is finished. It does not render anything, returns JsonResponse to indicate if the task is complete, in progress, or if the task does not exist, which should normally not be the case.

def check_processing_status(request):
    task_id = request.GET.get("task_id")
    if task_id in processing_status:
        status = processing_status[task_id]
        if status == "complete":
            del processing_status[task_id]
            return JsonResponse({ "status": "complete" })
        else:
            return JsonResponse({ "status": "in_progress" })
    else:
        return JsonResponse({ "status": "error", "message": "No such task." })

########################################### End of my views.
