from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, username=None, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")

        user = self.model(
            phone_number=phone_number,
            username=username,
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, username, phone_number, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", "Barber")

        return self.create_user(
            phone_number=phone_number,
            username=username,
            password=password,
            **extra_fields
        )


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ("Customer", "Customer"),
        ("Barber", "Barber"),
    )

    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=15, unique=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    address = models.TextField(blank=True) # Text address (e.g., "Sector 18, Noida")
    google_map_url = models.URLField(blank=True, max_length=500) # The redirection link
    
    # Hidden fields for distance calculation (Auto-filled)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["phone_number"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.username} - {self.user_type}"
    
class QueueSession(models.Model):
    STATUS_CHOICES = (
        ("Waiting", "Waiting"),
        ("Serving", "Serving"),
    )
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="queue_history")
    barber = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="active_queue")
    joined_at = models.DateTimeField(auto_now_add=True)
    # NEW FIELD: Status to track who is currently being served
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Waiting")
    is_active = models.BooleanField(default=True) # True = In Queue (Waiting/Serving), False = Completed/Cancelled

    class Meta:
        ordering = ['joined_at']