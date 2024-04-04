from django.shortcuts import render, redirect
from django.core.cache import cache
from pymongo import MongoClient
from django.views.generic import ListView
import django_tables2 as tables
from django_tables2 import RequestConfig, LazyPaginator
import django_filters
from django.http import JsonResponse
from django.utils.html import format_html
from .forms import NameForm, QueryForm, UserResultForm, EmailForm
from .model.main import main_flow
from email_validator import validate_email, EmailNotValidError
from .email_sender import send_email
from django.db.models import Model
from django.db.models.options import Options
from django_tables2.export.export import TableExport
import uuid
import threading
import time

client = MongoClient("localhost", 27017)
db = client.final_orcid_database

########################################### Custom functions and data structures.

# Dictionary to store the status of each processing task.

processing_status = {}

class DictionaryTable(tables.Table):
    given_names = tables.Column(attrs={ "th": { "title": "Given names of the author" } })
    family_name = tables.Column(attrs={ "th": { "title": "Family name of the author" } })
    gender = tables.Column(attrs={ "th": { "title": "Gender of the author" } })
    # orcid = tables.Column(attrs={ "th": { "title": "ORCID iD of the author" } })
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


    class Meta:
        order_by = ("-relevant_work_ratio",)

def author_with_custom_counts_generator(only_author_counts,
                                        first_author_counts,
                                        co_author_counts,
                                        last_author_counts,
                                        unknown_counts,
                                        relevant_work_counts,
                                        relevant_work_ratios,
                                        found_author_works,
                                        found_authors_cursor,
                                        # Here comes the filters...
                                        integer_filters,
                                        float_filters,
                                        selected_genders):

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


    for (only_author_count, first_author_count, co_author_count, last_author_count, unknown_count, relevant_work_count, relevant_work_ratio, author_works, found_author) in zip(only_author_counts, first_author_counts, co_author_counts, last_author_counts, unknown_counts, relevant_work_counts, relevant_work_ratios, found_author_works, found_authors_cursor):

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

        # Get the actual works from the "works" collection.
        
        resulting_works = []
        put_codes = []

        for work in author_works:
            put_codes.append(work[0])

        work_information = db.works.find( { "put_code": { "$in": put_codes } })

        for single_work_information in work_information:
            resulting_works.append([single_work_information["title"], single_work_information["publication_year"], single_work_information["url"]]) 

        author_entry = {
            "orcid_id": orcid_id,
            "orcid_url": f"https://orcid.org/{ orcid_id }", 
            "given_names": found_author["given_names"],
            "family_name": found_author["family_name"],
            "gender": found_author["gender"],
            "works": resulting_works,
            "only_author_count": only_author_count,
            "first_author_count": first_author_count,
            "co_author_count": co_author_count,
            "last_author_count": last_author_count,
            "unknown_count": unknown_count,
            "relevant_work_count": relevant_work_count,
            "relevant_work_ratio": relevant_work_ratio,
        }

        yield author_entry

def custom_cursor_generator(cursor_list):
    for cursor in cursor_list:
        for element in cursor:
            yield element

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


def concepts_string_to_list_of_strings(concepts_string):
    results = concepts_string.split(",")
    final_results = [" ".join(result.strip().split()) for result in results]
    return final_results

def query_and_store(request, concepts, publication_year, task_id):
    # TODO Maybe add a mutex before accessing request.session.

    concepts_list = concepts_string_to_list_of_strings(concepts)
    num_subconcepts_per_concept = 2 # Hardcoded for now.

    main_flow(concepts_list, publication_year, num_subconcepts_per_concept, task_id)

    processing_status[task_id] = "complete"
    print("Done processing.")
    return

def wait_for_task_and_send_email(email, task_id):
    while True:
        if task_id in processing_status:
            status = processing_status[task_id]
            if status == "complete":
                del processing_status[task_id]

                email_content = f'The results are in! You can access them using the following link: <a href="http://127.0.0.1:8000/result_page?task_id={task_id}">Results</a>'

                send_email(email, email_content)
                break
            else:
                time.sleep(10)
        else:
            print("THIS SHOULD NOT HAPPEN.")

def list_to_smaller_lists(list_to_divide, smaller_list_size):
    smaller_lists = []
    for i in range(0, len(list_to_divide), smaller_list_size):
        smaller_lists.append(list_to_divide[i:i+smaller_list_size])
    return smaller_lists

########################################### End of custom functions.

########################################### My views.

def home_page(request):
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

            # Set the publication year to -1 if we are in tutorial mode. This will be used later on to determine if we should continue on with displaying the example results.

            if tutorial == "true":
                publication_year = -1

            request.session["concepts"] = query
            request.session["publication_year"] = publication_year

            return redirect("loading_page")
        
    else:
        form = QueryForm()

    return render(request, "talentsearchtoolapp/home_page.html", { "form": form })

def loading_page(request):
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
                
                context = { "email_error": str(e), "form": form }

                return render(request, "talentsearchtoolapp/loading_page.html", context)

    else:
        concepts = request.session.get("concepts")
        publication_year = request.session.get("publication_year")

        if publication_year == -1:
            # We are in tutorial mode.

            task_id = "tutorial_result"

            form = EmailForm()

            context = { "task_id": task_id, "form": form }

            return render(request, "talentsearchtoolapp/loading_page.html", context)
        else:
            task_id = str(uuid.uuid4())

            request.session["current_task_id"] = task_id

            processing_thread = threading.Thread(target=query_and_store, args=(request, concepts, publication_year, task_id))

            processing_thread.start()

            form = EmailForm()

            context = { "task_id": task_id, "form": form }

            processing_status[task_id] = "in_progress"

            return render(request, "talentsearchtoolapp/loading_page.html", context)


def email_confirmation_page(request):
    return render(request, "talentsearchtoolapp/email_confirmation_page.html")

def result_page(request):
    # Get the concepts and the earliest publication date and make the query using the 
    # function in the model directory. Only do this if we have a different query and
    # publication year than the last time we entered the result page.

    # Now let us display the results.

    user_id = 1 # Harcoded for now.
    user_result_id = request.GET.get("task_id")

    # Get the numerical filter parameters
    
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

    if user_result_id == "tutorial_result":
        tutorial_generator = tutorial_custom_generator(integer_filters, float_filters, selected_genders)

        table = DictionaryTable(tutorial_generator)
        RequestConfig(request, paginate={ "paginator_class": LazyPaginator }).configure(table)
        context = { "table": table, "task_id": user_result_id, "selected_genders": selected_genders, "original_query": ["deep learning", "attention mechanisms"] }

        export_format = request.GET.get("_export", None)
        if TableExport.is_valid_format(export_format):
            exporter = TableExport(export_format, table)
            return exporter.response(f"tutorial_table.{export_format}")

        return render(request, "talentsearchtoolapp/result_page.html", context)


    user_results_cursor = db.user_results.find({ "user_id": user_id, "result_id": user_result_id })


    found_orcids_and_counts = []

    for user_result in user_results_cursor:
        found_orcids_and_counts.extend(user_result["found_results"])
        original_query = user_result["query"]

    found_orcids = []

    found_only_author_counts = []
    found_first_author_counts = []
    found_co_author_counts = []
    found_last_author_counts = []
    found_unknown_counts = []
    found_relevant_work_counts = []
    found_relevant_work_ratios = []

    found_author_works = []

    for found in found_orcids_and_counts:
        found_orcids.append(found["orcid_id"])
        found_only_author_counts.append(found["only_author_count"])
        found_first_author_counts.append(found["first_author_count"])
        found_co_author_counts.append(found["co-author_count"])
        found_last_author_counts.append(found["last_author_count"])
        found_unknown_counts.append(found["unknown_count"])
        found_relevant_work_counts.append(found["relevant_work_count"])
        found_relevant_work_ratios.append(found["relevant_work_ratio"])
        found_author_works.append(found["works"])

    # found_authors_cursor = db.authors.find({ "orcid_id": { "$in": found_orcids } })
    
    # This is done in order to get the results in the order of found_orcids and thus
    # match with the other arrays when we combine them in our custom generator.

    # found_orcids can be really large and then the aggregate command throws an error. Therefore, we shall split it in manageable smaller lists, make the queries and get cursors, and then use a "custom_cursor", which uses all these cursors in order and yields their results.

    smaller_orcid_lists = list_to_smaller_lists(found_orcids, 100000)
    all_cursors = []

    for orcid_list in smaller_orcid_lists:
        cursor = db.authors.aggregate([
            { "$match": { "orcid_id": { "$in": orcid_list } } },
            { "$addFields": { "orcidIndex": { "$indexOfArray": [orcid_list, "$orcid_id"] } } },
            { "$sort": { "orcidIndex": 1 } }
        ])
        all_cursors.append(cursor)

    custom_cursor = custom_cursor_generator(all_cursors)

    custom_generator = author_with_custom_counts_generator(found_only_author_counts,
                                                           found_first_author_counts,
                                                           found_co_author_counts,
                                                           found_last_author_counts,
                                                           found_unknown_counts,
                                                           found_relevant_work_counts,
                                                           found_relevant_work_ratios,
                                                           found_author_works,
                                                           custom_cursor,
                                                           # Here comes the filters...
                                                           integer_filters,
                                                           float_filters,
                                                           selected_genders)


    # Option 2

    table = DictionaryTable(custom_generator)
    RequestConfig(request, paginate={ "paginator_class": LazyPaginator }).configure(table)

    export_format = request.GET.get("_export", None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        export_name = f'query_result_{"".join(original_query)}'
        return exporter.response(f"{export_name}.{export_format}")


    context = { "table": table, "task_id": user_result_id, "selected_genders": selected_genders, "original_query": original_query }


    # Option 1

    #RequestConfig(request, paginate={ "per_page": 25 }).configure(table)
    #context = { "table": table, "task_id": user_result_id, "selected_genders": selected_genders }

    return render(request, "talentsearchtoolapp/result_page.html", context)


def example_page(request):
    task_id = str(uuid.uuid4())

    processing_thread = threading.Thread(target=wait_and_notify, args=(task_id,))

    processing_thread.start()

    context = { "task_id": task_id }

    processing_status[task_id] = "in_progress"

    return render(request, "talentsearchtoolapp/example_page.html", context)

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

