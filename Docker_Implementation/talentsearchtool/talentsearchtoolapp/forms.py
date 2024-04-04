from django import forms
import datetime

class NameForm(forms.Form):
    your_name = forms.CharField(label="Your name", max_length=100)

class QueryForm(forms.Form):
    query = forms.CharField(max_length=300, label="", widget=forms.TextInput(attrs={ "placeholder": "Enter academic fields!" }))

    # Show the last 100 years as choices.

    current_year = datetime.datetime.now().year
    choices = [(year, str(year)) for year in range(current_year, current_year - 100, -1)]
    publication_year = forms.ChoiceField(choices=choices)
    tutorial = forms.CharField(label="", required=False)

class EmailForm(forms.Form):
    email = forms.CharField(max_length=300, label="", widget=forms.TextInput(attrs={
    "placeholder": "Enter your email address here!" }))

class UserResultForm(forms.Form):
    user_id = forms.CharField(max_length=300)
    user_result_id = forms.CharField(max_length=300)