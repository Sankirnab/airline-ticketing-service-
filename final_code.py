
from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
from datetime import datetime

app = FastAPI()

# Function to establish database connection
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        dbname="airline_db",
        user="postgres",
        password="Sbhave@2003",
        port=5432
    )

#User Registration model
class UserInput(BaseModel):
    name: str
    email: str

# API 1: Register user
@app.post("/user")
def register_user(user: UserInput):
    conn = get_db_connection()
    cur1 = conn.cursor()
    
    query = "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING user_id;"
    cur1.execute(query, (user.name,user.email))
    user_id = cur1.fetchone()[0]  # Get the generated user_id

    conn.commit()
    cur1.close()
    conn.close()
    return {"message": "Welcome! User registered successfully!", "user_id": user_id}


# Define data model for Travel Details
class TravelInput(BaseModel):
    user_id: int  # Linking to user_id
    travel_source: str
    travel_destination: str
    travel_date: str

# API 2: Store Travel Details
@app.post("/user/travel_info")
def travel_details(t: TravelInput):
    conn = get_db_connection()
    cur2 = conn.cursor()

    #check if the user exists in the user table
    cur2.execute("Select * from users where user_id =%s;",(t.user_id,))
    user=cur2.fetchone()

    if not user:
        cur2.close()
        conn.close()
        return {"message": "User ID not found!!Please register first. "}

        # Insert into travel_info table
    query = """
        INSERT INTO travel_info (user_id, travel_source, travel_destination, travel_date)
        VALUES (%s, %s, %s, %s) RETURNING travel_id;
        """
    cur2.execute(query, (t.user_id, t.travel_source, t.travel_destination, t.travel_date))
    travel_id = cur2.fetchone()[0]  # Get the generated travel_id
    
    
    conn.commit()
    cur2.close()
    conn.close()
    return {"message": "Congratulations!! Travel details entered successfully!!!", "travel_id": travel_id}


#api 3 : display available flights
@app.get("/user/get_flight_details/{user_id}")
def display_flight_details(user_id: int):
    conn = get_db_connection()
    cur3 = conn.cursor()
        # Retrieve user's travel details
    cur3.execute("SELECT travel_source, travel_destination FROM travel_info WHERE user_id = %s;", (user_id,))
    travel = cur3.fetchone()

    if not travel:
       cur3.close()
       conn.close()
       return {"message": "No travel details found for the given user ID."}

    travel_source, travel_destination = travel
     # Fetch flight details based on source and destination
    query = """
        SELECT flight_id, flight_source, flight_destination, available_seats, flight_departure_time, fare
        FROM flights_info
        WHERE flight_source = %s AND flight_destination = %s;
        """
    cur3.execute(query, (travel_source, travel_destination))
    flights = cur3.fetchall()

    if not flights:
            cur3.close()
            conn.close()
            return {"message": "No flights found for the given route"}

    flight_list = [
            {
                "flight_id": flight[0],
                "flight_source": flight[1],
                "flight_destination": flight[2],
                "available_seats": flight[3],
                "flight_departure_time": str(flight[4]),  # Convert time to string
                "fare": flight[5]
            }
            for flight in flights
        ]
    cur3.close()
    conn.close()
    return {"message": "Available flights found!", "flights": flight_list}

#api to get which flight the user want to choose and number of seats they want to book and total fare

class FlightBookingInput(BaseModel):
    user_id: int
    flight_id: int
    number_of_seats: int

# API 3: Book a Flight
@app.post("/user/book_flight")
def book_flight(booking: FlightBookingInput):
    conn = get_db_connection()
    cur4 = conn.cursor()

        # Check if the flight exists
    cur4.execute("SELECT available_seats, fare FROM flights_info WHERE flight_id = %s;", (booking.flight_id,))
    flight = cur4.fetchone()

    if not flight:
            cur4.close()
            conn.close()
            return {"message":"Flight id not found!"}
    available_seats, fare_per_seat = flight  # Extract flight details

        # Check if enough seats are available
    if booking.number_of_seats > available_seats:
            cur4.close()
            conn.close()
            return {"message":"Not enough seats available!"}

        # Calculate total fare
    total_fare = booking.number_of_seats * fare_per_seat

        # Insert booking details into flight_book_details table
    query = """
        INSERT INTO flight_book_details (user_id, flight_id, number_of_seats, total_fare)
        VALUES (%s, %s, %s, %s) RETURNING booking_id;
        """
    cur4.execute(query, (booking.user_id, booking.flight_id, booking.number_of_seats, total_fare))
    booking_id = cur4.fetchone()[0]  # Get the generated booking ID

        # Update available seats in flights_info table
    new_available_seats = available_seats - booking.number_of_seats
    cur4.execute("UPDATE flights_info SET available_seats = %s WHERE flight_id = %s;", (new_available_seats, booking.flight_id))

    conn.commit()  
    cur4.close()
    conn.close()

    return {
            "message": "Flight booked successfully!",
            "booking_id": booking_id,
            "total_fare": total_fare
        }

# API 4: Retrieve Ticket Details
@app.get("/user/ticket_details/{booking_id}")
def get_ticket_details(booking_id: int):
    conn = get_db_connection()
    cur5 = conn.cursor()


    query = """
            SELECT 
                fb.booking_id, u.user_id, u.name, u.email,
                f.flight_id, f.flight_source, f.flight_destination,t.travel_id,t.travel_date,
                f.flight_departure_time, f.fare, fb.number_of_seats, fb.total_fare
            FROM flight_book_details fb
            JOIN users u ON fb.user_id = u.user_id
            JOIN flights_info f ON fb.flight_id = f.flight_id
            JOIN travel_info t  ON t.user_id = u.user_id
            WHERE fb.booking_id = %s;
        """
        
    cur5.execute(query, (booking_id,))
    ticket = cur5.fetchone()

    if not ticket:
            cur5.close()
            conn.close()
            return {"message":"No ticket details found for the given booking ID"}

    #Extract values from the query result
    
    (booking_id, user_id, user_name, user_email, flight_id, flight_source, 
     flight_destination,travel_id,travel_date,flight_departure_time, fare_per_seat, number_of_seats, total_fare) = ticket
    travel_date=str(travel_date)
    # Check if log already exists
    cur5.execute("SELECT COUNT(*) FROM user_logs WHERE booking_id = %s;", (booking_id,))
    log_exists = cur5.fetchone()[0] > 0

    # Insert into `user_logs`
    if not log_exists:
        cur5.execute("""
                INSERT INTO user_logs (user_id, name, email, booking_id, flight_id, source, 
                destination,travel_id,travel_date,flight_departure_time, fare, number_of_seats, total_fare) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s);
            """, (user_id, user_name, user_email, booking_id, flight_id, 
                  flight_source, flight_destination,travel_id,travel_date, flight_departure_time, 
                  fare_per_seat, number_of_seats, total_fare))
    conn.commit()
    cur5.close()
    conn.close()
    # Response
    return {
            "message": "Ticket details retrieved successfully! Thank you!! Happy Journey!!",
            "ticket_details": {
                "booking_id": booking_id,
                "user_details": {
                    "user_id": user_id,
                    "name": user_name,
                    "email": user_email
                },
                "flight_details": {
                    "flight_id": flight_id,
                    "source": flight_source,
                    "destination": flight_destination,
                    "departure_time": str(flight_departure_time)
                },
                "fare_details": {
                    "fare_per_seat": fare_per_seat,
                    "number_of_seats": number_of_seats,
                    "total_fare": total_fare
                },
                "travel_info":{
                     "travel_id":travel_id,
                     "travel_date":travel_date
                }
            }
        }

@app.post("/user/delete_booking/{booking_id}")
def delete_ticket(booking_id: int):
    conn = get_db_connection()
    cur6 = conn.cursor()
    
    try:
        # Check if the booking exists before deleting
        cur6.execute("SELECT * FROM flight_book_details WHERE booking_id = %s;", (booking_id,))
        booking = cur6.fetchone()

        if not booking:
            return {"message": "Booking ID does not exist"}

        #Update user_logs f
        cur6.execute("UPDATE user_logs SET status = 'cancelled' WHERE booking_id = %s;", (booking_id,))

        # update flight_book_details status
        cur6.execute("UPDATE flight_book_details SET status = 'cancelled' WHERE booking_id = %s;", (booking_id,))

        conn.commit()  # Commit both updates together

        return {
            "message": "Booking cancelled successfully! Do visit again!",
            "cancelled_booking_id": booking_id
        }
    
    except Exception as e:
        conn.rollback()  
        return {"error": str(e)}
    
    finally:
        cur6.close()
        conn.close()
#------------------------------------------------------------------------------------------
# admin page
@app.get("/admin/get_user_info/{user_id}")
def get_user_info(user_id: int):
    conn = get_db_connection()
    cur9 = conn.cursor()

    try:
        # Fetch user details
        cur9.execute(
            "SELECT travel_id, flight_id, booking_id, name, email, source, destination, travel_date, flight_departure_time, fare, number_of_seats, total_fare FROM user_logs WHERE user_id = %s",
            (user_id,),
        )
        user_details = cur9.fetchone()

        if not user_details:
            return {"response": "User not found!"} 
        
        (
            travel_id, flight_id, booking_id, name, email, source, 
            destination, travel_date, flight_departure_time, fare, 
            number_of_seats, total_fare
        ) = user_details

        return {
            "message": "User details retrieved successfully!",
            "user_logs": {
                "user_id": user_id,
                "travel_id": travel_id,
                "flight_id": flight_id,
                "booking_id": booking_id,
                "name": name,
                "email": email,
                "source": source,
                "destination": destination,
                "travel_date": travel_date,
                "flight_departure_time": flight_departure_time,
                "fare": fare,
                "number_of_seats": number_of_seats,
                "total_fare": total_fare,
            }
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        cur9.close()
        conn.close()


# updating flight info
class FlightUpdateRequest(BaseModel):
    flight_departure_time: str  # Format: "HH:MM:SS"

@app.post("/admin/flight_update/{flight_id}")
def update_flights_info(flight_id: int, flight_data: FlightUpdateRequest):
    con = get_db_connection()
    cur8 = con.cursor()

    try:
        flight_time = datetime.strptime(flight_data.flight_departure_time, "%H:%M:%S").time()
    except ValueError:
        cur8.close()
        con.close()
        return{ "detail":"Invalid time format. Use 'HH:MM:SS'."}

    # Check if the flight exists
    cur8.execute("SELECT * FROM flights_info WHERE flight_id = %s;", (flight_id,))
    flight_exists = cur8.fetchone()

    if not flight_exists:
        cur8.close()
        con.close()
        return{ "detail":"The flight doesn't exist"}
        
    # Update flight departure time
    cur8.execute(
        "UPDATE flights_info SET flight_departure_time = %s WHERE flight_id = %s;",
        (flight_time, flight_id)
    )

    con.commit()  
    cur8.close()
    con.close()

    return {"response": "Flight timings updated successfully!!"}

#delete user
@app.post("/admin/delete_user_info/{user_id}")
def delete_info(user_id: int):
    conn = get_db_connection()
    cur6 = conn.cursor()

    try:
        # Check if the user exists
        cur6.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user_exists = cur6.fetchone()
        
        if not user_exists:
            return {"response": "The user_id does not exist!"}
   
         #  update all bookings as "cancelled"
        cur6.execute("UPDATE flight_book_details SET status = 'cancelled' WHERE user_id = %s;", (user_id,))

        #  Delete from travel_info
        cur6.execute("DELETE FROM travel_info WHERE user_id = %s;", (user_id,))

        # delete from users
        cur6.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))

        conn.commit()
        return {"response": "User deleted successfully!"}
    
    finally:
        cur6.close()
        conn.close()

