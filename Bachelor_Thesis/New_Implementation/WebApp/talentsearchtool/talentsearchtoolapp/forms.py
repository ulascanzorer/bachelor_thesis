from django import forms

class NameForm(forms.Form):
    your_name = forms.CharField(label="Your name", max_length=100)

class QueryForm(forms.Form):
    query = forms.CharField(max_length=300)
    choices = (
        ("1", "Male"),
        ("2", "Female"),
    )
    choice = forms.MultipleChoiceField(label="", choices=choices)

class UserResultForm(forms.Form):
    user_id = forms.CharField(max_length=300)
    user_result_id = forms.CharField(max_length=300)