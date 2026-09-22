from django.utils.timezone import now
from datetime import timedelta, datetime, date
from .openaistuff.recommender_prompt import get_recommendations
from .googleplaces.google_places_api import get_image
from django.shortcuts import render, redirect, get_object_or_404
from datetime import time as dt_time
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import time as dt_time
from decimal import Decimal
from django.http import JsonResponse, HttpResponse
import requests
import logging
import re
import os

logger = logging.getLogger(__name__)
from .forms import FullSurveyForm
import json
from django.db.models import Prefetch
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.contrib.auth.forms import PasswordResetForm


def survey_page(request):
    if request.method == "POST":
        form = SurveyResponseForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            response = form.save(commit=False)
            if request.user.is_authenticated:
                response.username = request.user
            response.save()
            request.session['survey_data'] = {
                "trip_title": data['trip_title'],
                "stay_length": data['stay_length'],
                "stay_location": data['stay_location'].name,
                "preferred_cuisine": data['preferred_cuisine'].name,
                "activity_level": data['activity_level'].name,
                "activity_duration_hours": data['activity_duration_hours'],
                "budget": str(data.get('budget', '')),
                "social_context": data['social_context'].name,
                "radius": data['radius'],
                "dislikes": data.get('dislikes', '')
            }
            return redirect("planner:activity")

# @login_required  #needs to be uncommented later
def dashboard(request):
    user = request.user
    if not request.user.is_authenticated:
        return redirect("planner:survey")
    if user.is_authenticated:
        user_display = user.first_name or user.username or "[User]"
    else:
        user_display = "[User]"

    # Pre-made trip templates
    premade_trips = [
        {
            "title": "Classic Chicago Experience",
            "duration": "3 Days",
            "description": "Perfect for first-timers! Explore iconic landmarks, deep-dish pizza, and stunning architecture.",
            "highlights": [
                "Millennium Park & Cloud Gate (The Bean)",
                "Navy Pier & Lakefront Trail",
                "Lou Malnati's Deep Dish Pizza",
                "Architecture River Cruise",
                "Museum of Science & Industry"
            ]
        },
        {
            "title": "Foodie's Paradise",
            "duration": "2 Days",
            "description": "A culinary journey through Chicago's diverse neighborhoods and award-winning restaurants.",
            "highlights": [
                "Chicago-style hot dogs at Portillo's",
                "Italian beef at Al's Beef",
                "Brunch in West Loop",
                "Chicago French Market",
                "Rooftop dining with skyline views"
            ]
        },
        {
            "title": "Art & Culture Tour",
            "duration": "2 Days",
            "description": "Immerse yourself in Chicago's world-class museums and vibrant arts scene.",
            "highlights": [
                "Art Institute of Chicago",
                "Chicago Theatre District",
                "Millennium Park concerts",
                "Museum Campus (Field, Shedd, Adler)",
                "Street art in Pilsen & Logan Square"
            ]
        }
    ]

    return render(request, "planner/dashboard.html", {
        "user_display": user_display,
        "premade_trips": premade_trips,
    })



def favorites_page(request):
    if request.user.is_authenticated:
        favorited_itinerary_ids = FavoriteItinerary.objects.filter(user=request.user).values_list('itinerary_id', flat=True)
        favorited_itineraries = Itinerary.objects.filter(id__in=favorited_itinerary_ids).prefetch_related(
            Prefetch(
                'itineraryactivity_set',
                queryset=ItineraryActivity.objects.order_by('day', 'order'),
                to_attr='ordered_activities'  # This lets you access .ordered_activities in the template
            )
        )
    else:
        favorited_itineraries = []  

    return render(request, 'planner/favorites.html', {
        'favorites': favorited_itineraries,
    })

def favorite_itinerary(request, itinerary_id):
    if request.method == 'POST':
        itinerary = get_object_or_404(Itinerary, id=itinerary_id)
        FavoriteItinerary.objects.get_or_create(user=request.user, itinerary=itinerary)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)
    

def logout_now(request):
    logout(request)
    return redirect('planner:login')

def login_page(request):
    return render(request, "planner/login.html")

def landing_redirect(request):
    if request.user.is_authenticated:
        return redirect('planner:dashboard')
    else:
        return redirect("planner:survey")

def survey_full_page(request):
    session_key = 'survey_data'

    # ✅ Clear stale session data on GET
    if request.method == 'GET':
        for key in [
            "survey_data",
            "activity_index",
            "activity_recommendations",
            "restaurant_recommendations",
            "temp_activities",
            "current_itinerary"
        ]:
            request.session.pop(key, None)
        print("[DEBUG] Cleared session data at start")

    data = request.session.get(session_key, {})

    if request.method == 'POST':
        form = FullSurveyForm(request.POST)

        if form.is_valid():
            # ✅ Store cleaned data into session
            for key, val in form.cleaned_data.items():
                if hasattr(val, "pk") and hasattr(val, "name"):
                    data[key] = val.name
                elif isinstance(val, dt_time):
                    data[key] = val.strftime("%H:%M")
                elif isinstance(val, Decimal):
                    data[key] = float(val)  # convert Decimal to float
                else:
                    data[key] = val


            request.session[session_key] = data
            print("[SURVEY SUBMIT] Preferred Cuisine:", data.get("preferred_cuisine"))
            # print(f"[DEBUG] Session survey data now: {json.dumps(data, indent=4)}")

            # ✅ Save to model if authenticated
            if request.user.is_authenticated:
                model_data = data.copy()
                model_data["stay_location"] = Neighborhood.objects.get(name=data["stay_location"])
                model_data["preferred_cuisine"] = PreferredCuisine.objects.get(name=data["preferred_cuisine"])
                model_data["activity_level"] = ActivityLevel.objects.get(name=data["activity_level"])
                model_data["social_context"] = SocialContext.objects.get(name=data["social_context"])
                model_data["user"] = request.user
                # activity_duration_hours is already an integer, no conversion needed
                model_data.pop("trip_location", None)

                SurveyResponse.objects.create(**model_data)

            # Clean up partial recommendation data
            for key in [
                "activity_index",
                "activity_recommendations",
                "restaurant_recommendations",
                "temp_activities"
            ]:
                request.session.pop(key, None)

            return redirect("planner:activity")
        else:
            print("[DEBUG] Form errors:", form.errors.as_json())
    else:
        form = FullSurveyForm(initial=data)
    
    return render(request, "planner/survey.html", {
        "form": form
        
    })

def activity_page(request):
    print("original_activity_id:", request.POST.get("original_activity_id", "<not found>"))


    day = int(request.GET.get("day", 1))

    if request.method == "POST" and "original_activity_id" in request.POST:
        try:
            original_id = int(request.POST["original_activity_id"])
        except (ValueError, KeyError):
            messages.error(request, "Something went wrong. Please try again.")
            return redirect("planner:activity")

        replacement_name = request.POST["replacement_name"]
        replacement_description = request.POST["replacement_description"]
        replacement_neighborhood = request.POST["replacement_neighborhood"]
        replacement_latitude = request.POST["replacement_latitude"]
        replacement_longitude = request.POST["replacement_longitude"]
        replacement_category = request.POST["replacement_category"]
        replacement_photo_name = request.POST["replacement_photo_name"]
        replacement_address = request.POST["replacement_address"]

        activity = ItineraryActivity.objects.get(id=original_id)

        recommendations = request.session["recommendations"]
        recommendations.append({
            "name": activity.activity_name,
            "explanation": activity.activity_description,
            "neighborhood": activity.activity_neighborhood.name,
            "category": activity.category,
            "latitude": activity.latitude,
            "longitude": activity.longitude,
            "photo_name": activity.photo_name,
            "address": activity.address
        })

        new_recommendations_list = []
        for recommendation in recommendations:
            if recommendation["name"] == replacement_name:
                continue
            new_recommendations_list.append(recommendation)

        request.session["recommendations"] = new_recommendations_list

        
        
        neighborhood, _ = Neighborhood.objects.get_or_create(name=replacement_neighborhood)

        activity.activity_name = replacement_name
        activity.activity_description = replacement_description
        activity.activity_neighborhood = neighborhood
        activity.latitude = replacement_latitude
        activity.longitude = replacement_longitude
        activity.category = replacement_category
        activity.photo_name = replacement_photo_name
        activity.address = replacement_address
        activity.save()

        return redirect("planner:activity")


    activity_cards = []
    survey_data = request.session["survey_data"]

    if "current_itinerary" not in request.session:
        create_new_itinerary(request, survey_data["stay_length"]) # itinerary created, also don't need to use current_day, we'll change to pagination
        try:
            fetch_and_store_recommendations(survey_data, request)
        except ValueError as e:
            print(f"[ERROR] Survey data validation failed: {e}")
            messages.error(request, f"Could not generate itinerary: {e}")
            return redirect("planner:survey")
        current_itinerary = Itinerary.objects.get(id=request.session["current_itinerary"]) # get the itinerary with the id passed from other function
        make_activity_cards((request.session["itinerary"]), current_itinerary)
    else:
        current_itinerary = Itinerary.objects.get(id=request.session["current_itinerary"])
    activity_cards = get_activities(current_itinerary, day)

    # print(json.dumps(recommendations, indent=4))
    # return JsonResponse(survey_data, safe=False)
    return render(request, "planner/activity.html", {
        "activities": activity_cards,
        "recommendations": request.session["recommendations"],
        "day": day,
        "total_days": current_itinerary.total_duration
    })

def make_activity_cards(activities: list, current_itinerary):
    """
    Adds the activities to the database
    """
    print(f"Neighborhood: {json.dumps(activities, indent=4)}")
    for activity in activities:
        try:
            neighborhood = Neighborhood.objects.get(name=activity["neighborhood"])
        except Neighborhood.DoesNotExist:
            neighborhood, _ = Neighborhood.objects.get_or_create(name=activity["neighborhood"])
        ItineraryActivity.objects.create(
            itinerary = current_itinerary,
            activity_name = activity["name"],
            day = activity["day"],
            activity_neighborhood = neighborhood,
            activity_description = activity["explanation"],
            order = activity["order"],
            latitude = activity.get("latitude", 0),
            longitude = activity.get("longitude", 0),
            category = activity.get("category", "activity"),
            photo_name = activity.get("photo_name", ""),
            address = activity.get("address", "")
        )

def get_activities(current_itinerary, day):
    # print(f"***********IN GET_ACTIVITIES()")
    current_itinerary_activities = ItineraryActivity.objects.filter(itinerary=current_itinerary, day=day).order_by("order")
    activities = []

    for i in range(len(current_itinerary_activities)):
        activity = current_itinerary_activities[i]
        activities.append({
            "id": activity.id,
            "index": i,
            "neighborhood": activity.activity_neighborhood.name,
            "place": activity.activity_name,
            "description": activity.activity_description,
            "latitude": activity.latitude,
            "longitude": activity.longitude,
            "category": activity.category,
            "photo_name": activity.photo_name,
            "address": activity.address
    })

    # print(f"activity cards: {json.dumps(activities,indent=4)}")
    return activities

def create_new_itinerary(request, stay_length):

    itinerary = Itinerary.objects.create(
        name=request.session["survey_data"]["trip_title"],
        username=request.user if request.user.is_authenticated else None,
        total_duration=stay_length,
        current_day=1
    )

    request.session["current_itinerary"] = itinerary.id # store the current itinerary in the user's session so we can keep "building it"


def get_transit_time(orig_lat, orig_lng, dest_lat, dest_lng, api_key):
    """Return estimated walk and drive times using Google Routes API, with Haversine fallback."""
    import math

    def haversine_miles(lat1, lng1, lat2, lng2):
        R = 3958.8
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    def query_route(mode):
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration",
        }
        body = {
            "origin": {"location": {"latLng": {"latitude": orig_lat, "longitude": orig_lng}}},
            "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
            "travelMode": mode,
        }
        resp = requests.post(url, json=body, headers=headers, timeout=5)
        if resp.status_code == 200:
            routes = resp.json().get("routes", [])
            if routes:
                seconds = int(routes[0].get("duration", "0s").rstrip("s"))
                return max(1, round(seconds / 60))
        return None

    walk_min = drive_min = None
    try:
        walk_min = query_route("WALK")
    except Exception as e:
        print(f"[ERROR] Routes API (WALK) failed: {e}")
    try:
        drive_min = query_route("DRIVE")
    except Exception as e:
        print(f"[ERROR] Routes API (DRIVE) failed: {e}")

    # Haversine fallback for any missing mode
    if walk_min is None or drive_min is None:
        miles = haversine_miles(orig_lat, orig_lng, dest_lat, dest_lng)
        if walk_min is None:
            walk_min = max(5, round((miles / 2.5 * 60) / 5) * 5)
        if drive_min is None:
            drive_min = max(1, round((miles / 20 * 60) / 5) * 5)  # ~20 mph city driving

    return {"walk": walk_min, "drive": drive_min}


def lookup_place_details(name, api_key):
    """Look up a Chicago place by name via Google Places API and return photo_name, lat, lng, address."""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.formattedAddress,places.location,places.photos"
    }
    # Bias results toward Chicago — prefers local results but won't return
    # empty if no exact match, avoiding (0,0) fallback on valid Chicago places
    chicago_bias = {
        "circle": {
            "center": {"latitude": 41.8781, "longitude": -87.6298},
            "radius": 30000.0
        }
    }
    try:
        response = requests.post(url, headers=headers, json={
            "textQuery": f"{name} Chicago",
            "locationBias": chicago_bias
        }, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("places"):
                place = data["places"][0]
                return {
                    "photo_name": place["photos"][0]["name"] if place.get("photos") else "",
                    "latitude": place.get("location", {}).get("latitude", 0),
                    "longitude": place.get("location", {}).get("longitude", 0),
                    "address": place.get("formattedAddress", "")
                }
        else:
            logger.warning("Places lookup failed with HTTP %s", response.status_code)
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        logger.warning("Places lookup failed (%s)", type(exc).__name__)
    return {"photo_name": "", "latitude": 0, "longitude": 0, "address": ""}


def fetch_and_store_recommendations(data, request):
    try:
        stay_length = int(data["stay_length"])
        if stay_length < 1:
            raise ValueError(f"stay_length must be >= 1, got {stay_length}")
    except (TypeError, ValueError, KeyError) as e:
        raise ValueError(f"Invalid stay_length: {e}")

    location = str(data.get("stay_location", "")).strip()
    if not location:
        raise ValueError("stay_location is missing or empty")

    favorite_cuisine = str(data.get("preferred_cuisine", "")).strip()
    if not favorite_cuisine:
        raise ValueError("preferred_cuisine is missing or empty")

    activity_level = str(data.get("activity_level", "")).strip()
    if not activity_level:
        raise ValueError("activity_level is missing or empty")

    try:
        budget = float(data.get("budget") or 0)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid budget: {e}")

    social_context = str(data.get("social_context", "")).strip()
    if not social_context:
        raise ValueError("social_context is missing or empty")

    dislikes = str(data.get("dislikes", "")).strip()

    try:
        radius = int(data.get("radius") or 5)
        if radius < 1:
            radius = 1
    except (TypeError, ValueError):
        radius = 5

    result = get_recommendations(
        stay_length,
        location,
        favorite_cuisine,
        activity_level,
        budget,
        social_context,
        dislikes,
        radius
    )

    api_key = os.getenv("PLACES_API_KEY")

    # Enrich every item with real coords and photo from Google Places
    for item in result["itinerary"] + result["recommendations"]:
        item.setdefault("photo_name", "")
        item.setdefault("latitude", 0)
        item.setdefault("longitude", 0)
        item.setdefault("address", "")
        if api_key:
            details = lookup_place_details(item["name"], api_key)
            item.update(details)

    print(f"[DEBUG] Photo URLs in itinerary:")
    for item in result["itinerary"]:
        print(f"  {item['name']}: {item.get('photo_name', 'NO PHOTO')}")

    request.session["itinerary"] = result["itinerary"]
    request.session["recommendations"] = result["recommendations"]

def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        print("Trying to login with:", username, password)
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('planner:dashboard')
        else:
            form.add_error(None, "Invalid credentials.")
    return render(request, 'planner/login.html', {'form': form})


@login_required
def summary_page(request):

    itineraries = Itinerary.objects.filter(username=request.user).order_by('id')
    itinerary = None
    activities = []
    activities_for_coords = []

    itineraryID = request.GET.get('itinerary_id') or request.session.get("current_itinerary")

# @login_required
# def summary_page(request):
#     itineraries = Itinerary.objects.filter(username=request.user).order_by('id')
#     itinerary = None
#     activities = []
    
#     itineraryID = request.GET.get('itinerary_id')

    if itineraryID:
        try:
            itinerary = get_object_or_404(Itinerary, id=itineraryID)
        except Itinerary.DoesNotExist:
            itinerary = None

    if itinerary:
        raw_activities = list(ItineraryActivity.objects.filter(itinerary=itinerary).order_by('day', 'order'))
        places_api_key = os.getenv("PLACES_API_KEY")
        prev_by_day = {}
        activities = []
        activities_for_coords = []

        for i, activity in enumerate(raw_activities):
            day = activity.day
            if day not in prev_by_day:
                transit_time = "Start of day"
            elif places_api_key and not (activity.latitude == 0 and activity.longitude == 0):
                prev = prev_by_day[day]
                transit_time = get_transit_time(
                    prev.latitude, prev.longitude,
                    activity.latitude, activity.longitude,
                    places_api_key
                )
            else:
                transit_time = "N/A"

            prev_by_day[day] = activity

            activities.append({
                "id": activity.id,
                "activity_name": activity.activity_name,
                "day": activity.day,
                "order": activity.order,
                "category": activity.category,
                "photo_name": activity.photo_name,
                "address": activity.address,
                "activity_neighborhood": activity.activity_neighborhood,
                "activity_description": activity.activity_description,
                "latitude": activity.latitude,
                "longitude": activity.longitude,
                "transit_time": transit_time,
            })

            activities_for_coords.append({
                "id": activity.id,
                "index": i,
                "neighborhood": activity.activity_neighborhood.name,
                "place": activity.activity_name,
                "description": activity.activity_description,
                "latitude": activity.latitude,
                "longitude": activity.longitude,
                "category": activity.category,
                "photo_name": activity.photo_name,
                "address": activity.address,
                "day": activity.day,
            })
        # for activity in activities:
        #     start = datetime.combine(datetime.today(), activity.start_time)
        #     end = datetime.combine(datetime.today(), activity.end_time)
        #     if start > end:
        #         end += timedelta(days=1)
        #     duration = (end - start).seconds // 60
        #     activity.duration_minutes = duration


        # activities = ItineraryActivity.objects.filter(itinerary=itinerary).order_by('start_time')
        # for activity in activities:
        #     start = datetime.combine(datetime.today(), activity.start_time)
        #     end = datetime.combine(datetime.today(), activity.end_time)
        #     if start > end:
        #         end += timedelta(days=1)
        #     duration = (end - start).seconds // 60
        #     activity.duration_minutes = duration

    return render(request, "planner/summary.html", {
        'selected_itinerary': itinerary,
        'activities': activities,
        'itineraries': itineraries,
        'activities_for_coords': activities_for_coords
    })
    

def register(request):
    if request.method == "POST":
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Registration successful.")
            return redirect("planner:login")
    else:
        form = RegisterUserForm()
    return render(request, "planner/register.html", {"form": form})



class emailValidationForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No user is associated with this email address.")
        return email

class CustomPasswordResetView(PasswordResetView):
    template_name = 'password_reset/form.html'
    success_url = reverse_lazy('password_reset_done')
    form_class = emailValidationForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'email'
        })
        return form
    def form_valid(self, form):
        print("Form is valid, attempting to send reset email...")
        return super().form_valid(form)
    
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'password_reset/confirm.html'
    success_url = reverse_lazy('password_reset_complete')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['new_password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'New password'})
        form.fields['new_password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})
        return form

def photo_proxy(request):
    """Proxy photo requests to Google Places API to avoid CORS and authentication issues"""
    photo_name = request.GET.get('photo_name', '')

    if not re.fullmatch(r"places/[A-Za-z0-9_-]+/photos/[A-Za-z0-9_-]+", photo_name):
        return HttpResponse(status=400)

    api_key = os.getenv("PLACES_API_KEY")
    if not api_key:
        return HttpResponse(status=503)
    url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=400&key={api_key}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return HttpResponse(response.content, content_type=response.headers.get('Content-Type', 'image/jpeg'))
        elif response.status_code == 400:
            # Photo reference may be expired — refresh by fetching the place directly
            # photo_name format: places/{place_id}/photos/{photo_reference}
            parts = photo_name.split('/')
            if len(parts) >= 2:
                place_id = parts[1]
                details_response = requests.get(
                    f"https://places.googleapis.com/v1/places/{place_id}",
                    headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": "photos"},
                    timeout=10
                )
                if details_response.status_code == 200:
                    details_data = details_response.json()
                    if 'photos' in details_data and details_data['photos']:
                        fresh_photo_name = details_data['photos'][0]['name']
                        fresh_url = f"https://places.googleapis.com/v1/{fresh_photo_name}/media?maxHeightPx=400&key={api_key}"
                        fresh_response = requests.get(fresh_url, timeout=10)
                        if fresh_response.status_code == 200:
                            return HttpResponse(fresh_response.content, content_type=fresh_response.headers.get('Content-Type', 'image/jpeg'))
            print(f"[ERROR] Failed to fetch photo (stale ref): {response.status_code}")
            return HttpResponse(status=404)
        else:
            logger.warning("Places photo request failed with HTTP %s", response.status_code)
            return HttpResponse(status=response.status_code)
    except Exception as e:
        logger.warning("Places photo request failed (%s)", type(e).__name__)
        return HttpResponse(status=500)

