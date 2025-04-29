from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta

# Function to release expired bookings
def release_expired_bookings(theater):
    expired_bookings = Booking.objects.filter(
        theater=theater,
        is_confirmed=False,
        reserved_until__lt=timezone.now()
    )
    for booking in expired_bookings:
        seat = booking.seat
        seat.is_booked = False
        seat.save()
        booking.delete()

def movie_list(request):
    search_query = request.GET.get('search')
    if search_query:
        movies = Movie.objects.filter(name__icontains=search_query)
    else:
        movies = Movie.objects.all()
    return render(request, 'movies/movie_list.html', {'movies': movies})

def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, 'movies/theater_list.html', {'movie': movie, 'theaters': theaters})

@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theater).order_by('seat_number')  # maintain order

    # Release expired bookings
    release_expired_bookings(theater)

    is_housefull = all(seat.is_booked for seat in seats)

    if request.method == 'POST' and not is_housefull:
        selected_seats = request.POST.getlist('seats')
        error_seats = []
        booked_seat_numbers = []

        if not selected_seats:
            return render(request, "movies/seat_selection.html", {
                'theater': theater,
                "seats": seats,
                'error': "No seats selected",
                'is_housefull': is_housefull
            })

        for seat_id in selected_seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theater)
            if seat.is_booked:
                error_seats.append(seat.seat_number)
                continue
            try:
                Booking.objects.create(
                    user=request.user,
                    seat=seat,
                    movie=theater.movie,
                    theater=theater,
                    reserved_until=timezone.now() + timedelta(seconds=15),  # 15 seconds reservation
                    is_confirmed=False
                )
                seat.is_booked = True
                seat.save()
                booked_seat_numbers.append(seat.seat_number)
            except IntegrityError:
                error_seats.append(seat.seat_number)

        if error_seats:
            error_message = f"The following seats are already booked: {', '.join(error_seats)}"
            return render(request, 'movies/seat_selection.html', {
                'theater': theater,
                "seats": seats,
                'error': error_message,
                'is_housefull': all(seat.is_booked for seat in seats)
            })

        return redirect('confirm_booking')

    return render(request, 'movies/seat_selection.html', {
        'theater': theater,
        "seats": seats,
        'is_housefull': is_housefull
    })

@login_required(login_url='/login/')
def confirm_booking(request):
    pending_bookings = Booking.objects.filter(
        user=request.user,
        is_confirmed=False,
        reserved_until__gte=timezone.now()
    )

    if not pending_bookings:
        return redirect('profile')  # No pending bookings

    timeout = 15  # seconds

    if request.method == 'POST':
        for booking in pending_bookings:
            booking.is_confirmed = True
            booking.save()

        # Send confirmation email
        user_email = request.user.email
        subject = "Booking Confirmed - Movie Tickets"
        seat_list = ', '.join([booking.seat.seat_number for booking in pending_bookings])
        movie_name = pending_bookings[0].movie.name
        theater_name = pending_bookings[0].theater.name
        time = pending_bookings[0].theater.time.strftime("%d-%m-%Y %I:%M %p")

        message = f"""Hello {request.user.username},

Your booking is confirmed!

Movie: {movie_name}
Theater: {theater_name}
Time: {time}
Seats: {seat_list}

Thank you for booking with us.
Enjoy your movie!

Regards,
BookMySeat
"""

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user_email],
            fail_silently=False,
        )

        return redirect('profile')

    return render(request, 'movies/confirm_booking.html', {
        'pending_bookings': pending_bookings,
        'timeout': timeout
    })
