from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),

    path("customer/signup/", views.customer_signup, name="customer_signup"),
    path("customer/login/", views.customer_login, name="customer_login"),
    path("customer/dashboard/", views.customer_dashboard, name="customer_dashboard"),

    path("barber/login/", views.barber_login, name="barber_login"),
    path("barber/dashboard/", views.barber_dashboard, name="barber_dashboard"),
    path("barber/set_password/", views.barber_set_password, name="barber_set_password"),

    path("logout/", views.user_logout, name="logout"),
    
    path("get-nearby-barbers/", views.get_nearby_barbers, name="get_nearby_barbers"),
    path("join-queue/", views.join_queue_api, name="join_queue_api"),
    
    path("barber-queue/", views.get_barber_queue, name="get_barber_queue"),
    # NEW PATH TO START SERVING
    path("start-serving/", views.start_serving_api, name="start_serving_api"),
    # NEW PATH FOR SERVING CUSTOMER
    path("mark-served/", views.mark_served_api, name="mark_served_api"),
]
