from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import CustomUser
from geopy.geocoders import Nominatim

@receiver(pre_save, sender=CustomUser)
def generate_lat_long(sender, instance, **kwargs):
    if instance.user_type == "Barber" and instance.address:
        # Check if address changed or lat/long is missing
        try:
            old_instance = CustomUser.objects.get(pk=instance.pk)
            if old_instance.address == instance.address and instance.latitude:
                return # Address hasn't changed, skip api call
        except CustomUser.DoesNotExist:
            pass # New user

        # Convert Address to Lat/Long using free OSM API
        geolocator = Nominatim(user_agent="barber_app_queue_system")
        try:
            location = geolocator.geocode(instance.address)
            if location:
                instance.latitude = location.latitude
                instance.longitude = location.longitude
        except Exception as e:
            print(f"Geocoding error: {e}")