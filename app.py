from flask import Flask, jsonify, render_template, request
from flask_cors import CORS  
import sqlite3
import requests
import logging

app = Flask(__name__)
CORS(app)  #

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# SQLite database setup
DATABASE = 'ganaza.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    return conn

# Initialize the database
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ganaza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mosque_name TEXT NOT NULL,
            prayer_time TEXT NOT NULL,
            time TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            message TEXT,
            deceased_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Home route to serve the HTML page
@app.route('/')
def home():
    return render_template('map.html')

# API endpoint to fetch all ganazas
@app.route('/get-all-ganazas', methods=['GET'])
def get_all_ganazas():
    conn = get_db_connection()
    try:
        ganazas = conn.execute('SELECT * FROM ganaza').fetchall()
        return jsonify([dict(ganaza) for ganaza in ganazas])
    except sqlite3.OperationalError as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

# API endpoint to search for mosques using Nominatim
@app.route('/search-mosque', methods=['GET'])
def search_mosque():
    query = request.args.get('query', '').strip()
    logging.debug(f"Search query: {query}")

    if not query:
        return jsonify([])

    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&addressdetails=1&limit=10"
    headers = {
        'User-Agent': 'GanazaMapApp (joekhalid2002@gmail.com)'  
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        logging.debug(f"Nominatim results: {results}")

        mosques = [
            {
                'name': result.get('name', 'Unnamed Mosque'),
                'latitude': float(result['lat']),
                'longitude': float(result['lon']),
                'address': result.get('display_name', 'Address not available'),
                'country': result['address'].get('country', 'Unknown'),
            }
            for result in results
            if result.get('class') == 'amenity'  # Ensure it's an amenity
            and result.get('type') == 'place_of_worship'  # Ensure it's a place of worship
            and (query.lower() in result.get('name', '').lower() or query.lower() in result.get('display_name', '').lower())  # Flexible search
        ]
        logging.debug(f"Filtered mosques: {mosques}")
        return jsonify(mosques)

    except requests.exceptions.RequestException as e:
        logging.error(f"Error connecting to Nominatim: {e}")
        return jsonify({"error": "Failed to connect to Nominatim API"}), 500

# API endpoint to fetch nearby mosques using reverse geocoding
@app.route('/nearby-mosques', methods=['GET'])
def nearby_mosques():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    logging.debug(f"Fetching mosques near: {lat}, {lng}")

    if not lat or not lng:
        return jsonify({"error": "Latitude and longitude are required"}), 400

    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&addressdetails=1"
    headers = {
        'User-Agent': 'GanazaMapApp (joekhalid2002@gmail.com)'  
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        logging.debug(f"Nominatim reverse geocoding result: {result}")

        if result.get('class') == 'amenity' and result.get('type') == 'place_of_worship':
            mosque = {
                'name': result.get('name', 'Unnamed Mosque'),
                'latitude': lat,
                'longitude': lng,
                'address': result.get('display_name', 'Address not available'),
                'country': result['address'].get('country', 'Unknown'),
            }
            return jsonify([mosque])
        else:
            return jsonify([])

    except requests.exceptions.RequestException as e:
        logging.error(f"Error connecting to Nominatim: {e}")
        return jsonify({"error": "Failed to connect to Nominatim API"}), 500

# API endpoint to post ganaza location
@app.route('/post-ganaza', methods=['POST'])
def post_ganaza():
    data = request.json
    logging.debug(f"Received data: {data}")

    mosque_name = data.get('mosque_name')
    prayer_time = data.get('prayer_time')
    time = data.get('time')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    message = data.get('message')
    deceased_name = data.get('deceased_name')

    if not all([mosque_name, prayer_time, time, latitude, longitude]):
        return jsonify({"error": "Missing required fields"}), 400

    # Validate latitude and longitude
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude"}), 400

    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO ganaza (mosque_name, prayer_time, time, latitude, longitude, message, deceased_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (mosque_name, prayer_time, time, latitude, longitude, message, deceased_name))
        conn.commit()
        return jsonify({"message": "Ganaza posted successfully"}), 201
    except sqlite3.OperationalError as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)