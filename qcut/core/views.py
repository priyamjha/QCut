from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from .serializers import CustomerSignupSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from .models import CustomUser, QueueSession
import json
import math


@csrf_exempt
def mark_served_api(request):
    if request.method != "POST":
        return JsonResponse({'error': 'POST method required'}, status=400)
        
    if not request.user.is_authenticated or request.user.user_type != "Barber":
        return JsonResponse({'error': 'Barber login required'}, status=403)

    # Find the customer currently marked as 'Serving'
    serving_session = QueueSession.objects.filter(
        barber=request.user, 
        is_active=True,
        status="Serving"
    ).order_by('joined_at').first() # Get the oldest one just in case

    if not serving_session:
        return JsonResponse({'success': False, 'message': 'No customer is currently being served.'})

    # Mark the session as inactive (served/completed)
    served_name = serving_session.customer.full_name or "Customer"
    serving_session.is_active = False
    serving_session.status = "Completed" # Use completed status (optional: depends on future features)
    serving_session.save()
    
    return JsonResponse({'success': True, 'message': f'{served_name} marked as served!'})


@csrf_exempt
def start_serving_api(request):
    if request.method != "POST":
        return JsonResponse({'error': 'POST method required'}, status=400)
        
    if not request.user.is_authenticated or request.user.user_type != "Barber":
        return JsonResponse({'error': 'Barber login required'}, status=403)

    # Check if a customer is already being served
    currently_serving = QueueSession.objects.filter(
        barber=request.user, 
        is_active=True, 
        status="Serving"
    ).exists()

    if currently_serving:
         return JsonResponse({'success': False, 'message': 'You are already serving a customer.'})

    # Find the first 'Waiting' customer
    next_customer = QueueSession.objects.filter(
        barber=request.user, 
        is_active=True, 
        status="Waiting"
    ).order_by('joined_at').first()

    if not next_customer:
        return JsonResponse({'success': False, 'message': 'No customer waiting to be served.'})

    # Mark as Serving
    next_customer.status = "Serving"
    next_customer.save()
    
    return JsonResponse({
        'success': True, 
        'message': f'Started serving: {next_customer.customer.full_name or "Customer"}',
        'customer_id': next_customer.customer.id
    })

@csrf_exempt
def get_barber_queue(request):
    """
    API for barber dashboard to fetch their current active queue.
    """
    if not request.user.is_authenticated or request.user.user_type != "Barber":
        return JsonResponse({'error': 'Barber login required'}, status=403)
        
    queue_sessions = QueueSession.objects.filter(
        barber=request.user, 
        is_active=True
    ).select_related('customer').order_by('joined_at')
    
    queue_data = []
    avg_service_time = 25 # minutes per customer

    # Find the serving customer (if any)
    serving_customer_count = QueueSession.objects.filter(
        barber=request.user, 
        is_active=True,
        status="Serving"
    ).count()

    waiting_sessions = queue_sessions.filter(status="Waiting")
    
    # If no one is serving, the wait time is based on all sessions.
    # If someone IS serving, the wait time starts counting from the next person.
    base_wait_count = serving_customer_count # Should be 0 or 1
    
    for session in queue_sessions:
        customer = session.customer
        
        # Calculate estimated wait time based on their position relative to the serving person
        if session.status == "Waiting":
            # Position in the waiting list (after the serving customer)
            position_in_waiting = list(waiting_sessions).index(session)
            wait_time = (base_wait_count + position_in_waiting) * avg_service_time
        else: # Serving
            wait_time = 0

        queue_data.append({
            'id': customer.id,
            'session_id': session.id, # Send session ID for actions
            'name': customer.full_name or customer.username,
            'joined_at': session.joined_at.strftime('%I:%M %p'),
            'status': session.status.lower(), # 'waiting' or 'serving'
            'waitTime': wait_time
        })

    return JsonResponse({'success': True, 'queue_data': queue_data})

# --- HELPER FUNCTION FOR DISTANCE (Haversine Formula) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- API VIEWS ---

def get_nearby_barbers(request):
    """
    API called by JS. Receives lat/long from browser.
    Returns barbers under 5km.
    """
    try:
        cust_lat = float(request.GET.get('lat', 0))
        cust_long = float(request.GET.get('long', 0))
    except ValueError:
        return JsonResponse({'error': 'Invalid coordinates'}, status=400)

    barbers = CustomUser.objects.filter(user_type="Barber").exclude(latitude__isnull=True)
    
    nearby_barbers = []
    
    for barber in barbers:
        dist = calculate_distance(cust_lat, cust_long, barber.latitude, barber.longitude)
        
        if dist <= 5.0: # Filter under 5km
            # Get real queue count
            queue_count = QueueSession.objects.filter(barber=barber, is_active=True).count()
            
            # Determine status
            status = "available"
            if queue_count > 2:
                status = "busy"
            
            # Estimate wait time (15 mins per person)
            wait_time = queue_count * 15

            nearby_barbers.append({
                'id': barber.id,
                'name': barber.full_name or barber.username,
                'status': status,
                'distance': round(dist, 1),
                'queue': queue_count,
                'waitTime': wait_time,
                'address': barber.address,
                'map_url': barber.google_map_url,
                'phone_number': barber.phone_number,
            })

    # Sort by distance
    nearby_barbers.sort(key=lambda x: x['distance'])
    
    return JsonResponse({'barbers': nearby_barbers})

@csrf_exempt
def join_queue_api(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
            
        data = json.loads(request.body)
        barber_id = data.get('barber_id')
        
        try:
            barber = CustomUser.objects.get(id=barber_id, user_type="Barber")
            
            # Check if already in queue
            existing = QueueSession.objects.filter(customer=request.user, is_active=True).exists()
            if existing:
                return JsonResponse({'success': False, 'message': 'You are already in a queue!'})

            # Add to queue
            QueueSession.objects.create(customer=request.user, barber=barber)
            
            new_queue_count = QueueSession.objects.filter(barber=barber, is_active=True).count()
            
            return JsonResponse({
                'success': True, 
                'queue_count': new_queue_count,
                'barber_name': barber.full_name
            })
            
        except CustomUser.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Barber not found'})

    return JsonResponse({'error': 'POST method required'}, status=400)

def customer_dashboard(request):
    return render(request, "core/customer_dashboard.html")

def barber_dashboard(request):
    return render(request, "core/barber_dashboard.html")


def home(request):
    if request.user.is_authenticated:
        if request.user.user_type == "Customer":
            return redirect("core:customer_dashboard")
        elif request.user.user_type == "Barber":
            return redirect("core:barber_dashboard")
    return render(request, "core/home.html")


def customer_signup(request):
    if request.method == "POST":
        # use your serializer you already wrote
        serializer = CustomerSignupSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            messages.success(request, "Signup successful. Please proceed to login with your phone number.")
            return redirect("core:customer_login")
        else:
            messages.error(request, "Signup failed. " + str(serializer.errors))
            # pass serializer back for showing previous values if needed
            return render(request, "core/customer_signup.html", {"form": serializer})
    return render(request, "core/customer_signup.html", {"form": None})

def customer_login(request):
    if request.method == "POST":
        phone_number = request.POST.get("phone_number")
        try:
            user = CustomUser.objects.get(phone_number=phone_number, user_type="Customer")
            login(request, user)
            return redirect("core:customer_dashboard")
        except CustomUser.DoesNotExist:
            messages.error(request, "No customer with this phone number.")
            return redirect("core:customer_signup")
    return render(request, "core/customer_login.html")

def barber_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user and user.user_type == "Barber":
            login(request, user)
            return redirect("core:barber_dashboard")

        messages.error(request, "Invalid barber credentials.")
    return render(request, "core/barber_login.html")


def barber_set_password(request):
    # This view assumes admin already created a CustomUser row for the barber (with user_type="Barber")
    # You will need some token or identification to let the barber find their record (phone or id).
    # For demo we accept username or phone query param to prefill.
    if request.method == "POST":
        username = request.POST.get("username")
        p1 = request.POST.get("password1")
        p2 = request.POST.get("password2")
        if p1 != p2:
            messages.error(request, "Passwords do not match.")
            return render(request, "core/barber_set_password.html", {"username": username})
        try:
            user = CustomUser.objects.get(username=username, user_type="Barber")
            user.set_password(p1)
            user.save()
            messages.success(request, "Password set. You may login now.")
            return redirect("core:barber_login")
        except CustomUser.DoesNotExist:
            messages.error(request, "No barber found with that username (admin must create account first).")
            return render(request, "core/barber_set_password.html", {"username": username})
    # GET
    return render(request, "core/barber_set_password.html", {"username": request.GET.get("username", "")})

def user_logout(request):
    logout(request)
    messages.success(request, "Logged out.")
    return redirect("core:home")
