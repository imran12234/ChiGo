from django import forms
from .models import SurveyResponse, Neighborhood, PreferredCuisine, ActivityLevel, SocialContext
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class SurveyResponseForm(forms.ModelForm):
    trip_title = forms.CharField(
        required=True,
        label="Trip Title",
        widget=forms.TextInput(attrs={"placeholder": "My Chicago Adventure"})
    )

    stay_length = forms.IntegerField(
        required=True,
        label="How long will you be staying? (Days)",
        min_value=1,
        widget=forms.NumberInput(attrs={'placeholder': '3', 'type': 'number', 'step': '1'})
    )

    radius = forms.IntegerField(
        required=True,
        label="Radius from stay location (Miles)",
        min_value=1,
        widget=forms.NumberInput(attrs={"placeholder": "5", 'type': 'number', 'step': '1'})
    )

    preferred_cuisine = forms.ModelChoiceField(
        queryset=PreferredCuisine.objects.all(),
        label="Preferred Cuisine",
        empty_label="Select a cuisine",
        required=True
    )

    activity_level = forms.ModelChoiceField(
        queryset=ActivityLevel.objects.all(),
        label="Activity Level",
        empty_label="Select activity level",
        required=True
    )

    stay_location = forms.ModelChoiceField(
        queryset=Neighborhood.objects.all(),
        label="Where are you staying?",
        empty_label="Select a neighborhood",
        required=True
    )

    activity_duration_hours = forms.IntegerField(
        required=True,
        label="Activity time frame (Hours)",
        min_value=1,
        max_value=24,
        widget=forms.NumberInput(attrs={
            'placeholder': '4',
            'type': 'number',
            'step': '1'
        }),
        help_text="Hours"
    )

    budget = forms.DecimalField(
        required=True,
        label="Trip Budget",
        min_value=0,
        widget=forms.NumberInput(attrs={"placeholder": "Enter your budget (e.g., 500.00)"})
    )

    social_context = forms.ModelChoiceField(
        queryset=SocialContext.objects.all(),
        empty_label="Select social context",
        required=True
    )

    dislikes = forms.CharField(
        required=False,  # optional
        label="What would you like to avoid?",
        widget=forms.Textarea(attrs={
            "placeholder": "e.g., long walks, spicy food, crowded places",
            "rows": 3
        })
    )

    class Meta:
        model = SurveyResponse
        fields = [
            'trip_title',
            'stay_length',
            'stay_location',
            'preferred_cuisine',
            'activity_level',
            'activity_duration_hours',
            'budget',
            'social_context',
            'radius',
            'dislikes'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["stay_location"]
        # Curated shortcuts, not a ranking derived from usage data.
        suggested_names = (
            "Loop", "River North", "Streeterville", "Magnificent Mile",
            "West Loop", "Lincoln Park", "Gold Coast", "South Loop",
        )
        neighborhoods = list(field.queryset.order_by("name", "pk"))
        suggested = [
            (place.pk, place.name)
            for name in suggested_names
            for place in neighborhoods if place.name == name
        ]
        remaining = [(place.pk, place.name) for place in neighborhoods
                     if place.name not in suggested_names]
        field.choices = [("", field.empty_label)]
        if suggested:
            field.choices += [("Suggested neighborhoods", suggested)]
        if remaining:
            field.choices += [("All other neighborhoods", remaining)]
        field.widget.attrs.update({
            "class": "form-select",
            "aria-describedby": "hint-stay_location error-stay_location",
            "aria-required": "true",
        })

    def clean_stay_length(self):
        stay_length = self.cleaned_data.get('stay_length')
        if stay_length is None or stay_length < 1:
            raise forms.ValidationError("Stay length must be at least 1 day.")
        return stay_length



class FullSurveyForm(SurveyResponseForm):
    # Inherits all fields from SurveyResponseForm
    pass


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))

    
class RegisterUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
