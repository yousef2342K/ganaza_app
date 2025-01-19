from geopy.distance import geodesic

def is_within_radius(user_location, ganaza_location, radius):
    """
    Check if a ganaza location is within a given radius of the user's location.
    """
    distance = geodesic(user_location, ganaza_location).kilometers
    return distance <= radius
