from django.shortcuts import render
from map.models import Place

def map_view(request):
    places = Place.objects.filter(geocoded=True)
    return render(request, "map/map.html", {"places": places})