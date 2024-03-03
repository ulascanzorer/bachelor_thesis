from django.shortcuts import render, redirect
from pymongo import MongoClient
from django.views.generic import ListView
import django_tables2 as tables
from django_tables2 import RequestConfig
from .forms import NameForm, QueryForm, UserResultForm

client = MongoClient("localhost", 27017)
db = client.final_orcid_database

def author_with_custom_counts_generator(only_author_counts,
                                        first_author_counts,
                                        co_author_counts,
                                        last_author_counts,
                                        unknown_counts,
                                        relevant_work_counts,
                                        found_author_works,
                                        found_authors_cursor):
    for (only_author_count, first_author_count, co_author_count, last_author_count, unknown_count, relevant_work_count, author_works, found_author) in zip(only_author_counts, first_author_counts, co_author_counts, last_author_counts, unknown_counts, relevant_work_counts, found_author_works, found_authors_cursor):
        yield {
            "orcid": found_author["orcid"],
            "given_names": found_author["given_names"],
            "family_name": found_author["family_name"],
            "works": author_works,
            "only_author_count": only_author_count,
            "first_author_count": first_author_count,
            "co_author_count": co_author_count,
            "last_author_count": last_author_count,
            "unknown_count": unknown_count,
            "relevant_work_count": relevant_work_count,
        }


# Create your views here.

def homepage(request):
    return render(request, "talentsearchtoolapp/homepage.html")

def result_page(request):
    user_id = int(request.session.get("user_id"))
    user_result_id = int(request.session.get("user_result_id"))

    user_results_cursor = db.user_results.find({ "user_id": user_id, "result_id": user_result_id })


    found_orcids_and_counts = []
    for user_result in user_results_cursor:
        found_orcids_and_counts.extend(user_result["found_results"])

    found_orcids = []

    found_only_author_counts = []
    found_first_author_counts = []
    found_co_author_counts = []
    found_last_author_counts = []
    found_unknown_counts = []
    found_relevant_work_counts = []

    found_author_works = []

    for found in found_orcids_and_counts:
        found_orcids.append(found["orcid"])
        found_only_author_counts.append(found["only_author_count"])
        found_first_author_counts.append(found["first_author_count"])
        found_co_author_counts.append(found["co-author_count"])
        found_last_author_counts.append(found["last_author_count"])
        found_unknown_counts.append(found["unknown_count"])
        found_relevant_work_counts.append(found["relevant_work_count"])
        found_author_works.append(found["works"])

    found_authors_cursor = db.authors.find({ "orcid": { "$in": found_orcids } })
    
    custom_generator = author_with_custom_counts_generator(found_only_author_counts,
                                                           found_first_author_counts,
                                                           found_co_author_counts,
                                                           found_last_author_counts,
                                                           found_unknown_counts,
                                                           found_relevant_work_counts,
                                                           found_author_works,
                                                           found_authors_cursor)


    table = DictionaryTable(custom_generator)
    RequestConfig(request, paginate={ "per_page": 25 }).configure(table)

    context = { "table": table }

    return render(request, "talentsearchtoolapp/result_page.html", context)

def form_example_get_name(request):
    if request.method == "POST":
        form = UserResultForm(request.POST)
        if form.is_valid():
            request.session["user_id"] = form.cleaned_data["user_id"]
            request.session["user_result_id"] = form.cleaned_data["user_result_id"]

            return redirect("sample_result_page")
        
    else:
        form = UserResultForm()

    return render(request, "talentsearchtoolapp/form_example.html", { "form": form })

class DictionaryTable(tables.Table):
    given_names = tables.Column()
    family_name = tables.Column()
    orcid = tables.Column()
    works = tables.Column()
    relevant_work_count = tables.Column()
    only_author_count = tables.Column()
    first_author_count = tables.Column()
    last_author_count = tables.Column()
    co_author_count = tables.Column()
    unknown_count = tables.Column()

