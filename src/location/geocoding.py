
from geopy.geocoders import Nominatim
from geopy.exc import (
    GeocoderTimedOut,
    GeocoderUnavailable,
    GeocoderServiceError,
)
from geopy.extra.rate_limiter import RateLimiter


# Replace with your application identifier.
geolocator = Nominatim(
    user_agent="forestcarbondl_student_project",
    timeout=30,
)

geocode_with_limit = RateLimiter(
    geolocator.geocode,
    min_delay_seconds=1,
    max_retries=1,
)


def search_location(place_name: str):
    """
    Search for a place using OpenStreetMap Nominatim.

    Returns:
        dict containing name, latitude, longitude,
        and bounding box, or None if not found.
    """

    if not place_name or not place_name.strip():
        raise ValueError("Please enter a location name.")

    try:
        result = geocode_with_limit(
            place_name.strip(),
            exactly_one=True,
            addressdetails=True,
)

        if result is None:
            return None

        return {
            "name": result.address,
            "latitude": float(result.latitude),
            "longitude": float(result.longitude),
            "bounding_box": result.raw.get("boundingbox"),
        }

    except GeocoderTimedOut:
        raise RuntimeError("Location search timed out.")

    except GeocoderUnavailable:
        raise RuntimeError("Location service is unavailable.")

    except GeocoderServiceError as error:
        raise RuntimeError(
            f"Location search failed: {error}"
        )
