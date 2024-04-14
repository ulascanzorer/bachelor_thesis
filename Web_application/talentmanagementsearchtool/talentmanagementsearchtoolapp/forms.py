from django import forms
import datetime

# Query form to be used in the home page, includes the given academic fields and the given earliest publication year.

class QueryForm(forms.Form):
    query = forms.CharField(max_length=300, label="", widget=forms.TextInput(attrs={ "placeholder": "Enter academic fields!" }))

    # Show the last 100 years as choices.

    current_year = datetime.datetime.now().year
    choices = [(year, str(year)) for year in range(current_year, current_year - 100, -1)]
    publication_year = forms.ChoiceField(choices=choices)
    tutorial = forms.CharField(label="", required=False)

# Email form to be used in the loading page, so that the users can enter their email addresses.

class EmailForm(forms.Form):
    email = forms.CharField(max_length=300, label="", widget=forms.TextInput(attrs={
    "placeholder": "Enter your email address here!" }))