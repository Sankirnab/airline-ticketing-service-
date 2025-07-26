from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
import psycopg2
from datetime import datetime

app = FastAPI()

def get_db_connection():
    return psycopg2.connect(
       host="localhost",
        dbname="airline_db",
        user="postgres",
        password="Sbhave@2003",
        port=5432
    )
#API 1 :to delete the user from the system available in the user_logs



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
   
          # Delete from user_logs
        cur6.execute("DELETE FROM user_logs WHERE user_id = %s", (user_id,))

        # Delete from flight_book_details first (to avoid foreign key error)
        cur6.execute("DELETE FROM flight_book_details WHERE user_id = %s", (user_id,))

        # Delete from travel_info
        cur6.execute("DELETE FROM travel_info WHERE user_id = %s", (user_id,))

        # Finally, delete from users
        cur6.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

        conn.commit()
        return {"response": "User deleted successfully!"}
    
    finally:
        cur6.close()
        conn.close()


# updating flight info
class FlightUpdateRequest(BaseModel):
    flight_departure_time: str  # Format: "HH:MM:SS"

@app.post("/admin/flight_update/{flight_id}")
def update_flights_info(flight_id: int, flight_data: FlightUpdateRequest):
    con = get_db_connection()
    cur8 = con.cursor()

    # Convert string to time format
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



