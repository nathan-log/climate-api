"""
Sun Data Calculator Module

This module contains functions for calculating sunrise, sunset, and daylight hours
based on geographic coordinates and date.
"""

import math
import datetime
import pytz
from timezonefinder import TimezoneFinder
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global timezone finder instance
tf = TimezoneFinder()

def get_timezone(latitude, longitude):
    """Get the timezone string for a specific latitude and longitude."""
    timezone_str = tf.timezone_at(lat=latitude, lng=longitude)
    if timezone_str is None:
        timezone_str = 'UTC'  # Default to UTC if no timezone found
    return timezone_str

def calculate_sunrise_sunset(latitude, longitude, date=None, local_tz=None):
    """
    Calculate sunrise and sunset times for a given location and date.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        date: Date to calculate for (default: today)
        local_tz: Optional pytz timezone object (to avoid repeated lookups)
    """
    if date is None:
        date = datetime.date.today()
    
    # Get the timezone for this location if not provided
    if local_tz is None:
        timezone_str = get_timezone(latitude, longitude)
        local_tz = pytz.timezone(timezone_str)
    
    # Julian date calculation
    n1 = math.floor(275 * date.month / 9)
    n2 = math.floor((date.month + 9) / 12)
    n3 = (1 + math.floor((date.year - 4 * math.floor(date.year / 4) + 2) / 3))
    n = n1 - (n2 * n3) + date.day - 30
    
    # Convert longitude to hour value
    lngHour = longitude / 15
    
    # Calculate sunrise/sunset times
    t_rise = n + ((6 - lngHour) / 24)
    t_set = n + ((18 - lngHour) / 24)
    
    # Calculate the Sun's mean anomaly
    m_rise = (0.9856 * t_rise) - 3.289
    m_set = (0.9856 * t_set) - 3.289
    
    # Calculate the Sun's true longitude
    l_rise = m_rise + (1.916 * math.sin(math.radians(m_rise))) + (0.020 * math.sin(math.radians(2 * m_rise))) + 282.634
    l_set = m_set + (1.916 * math.sin(math.radians(m_set))) + (0.020 * math.sin(math.radians(2 * m_set))) + 282.634
    
    # Adjust into 0-360 degree range
    l_rise = l_rise % 360
    l_set = l_set % 360
    
    # Calculate the Sun's right ascension
    ra_rise = math.degrees(math.atan(0.91764 * math.tan(math.radians(l_rise))))
    ra_set = math.degrees(math.atan(0.91764 * math.tan(math.radians(l_set))))
    
    # Right ascension value needs to be in the same quadrant as L
    ra_rise = ra_rise + (math.floor(l_rise / 90) * 90 - math.floor(ra_rise / 90) * 90)
    ra_set = ra_set + (math.floor(l_set / 90) * 90 - math.floor(ra_set / 90) * 90)
    
    # Convert to hours
    ra_rise = ra_rise / 15
    ra_set = ra_set / 15
    
    # Calculate the Sun's declination
    sin_dec_rise = 0.39782 * math.sin(math.radians(l_rise))
    cos_dec_rise = math.cos(math.asin(sin_dec_rise))
    sin_dec_set = 0.39782 * math.sin(math.radians(l_set))
    cos_dec_set = math.cos(math.asin(sin_dec_set))
    
    # Calculate the Sun's local hour angle
    cos_h_rise = (math.sin(math.radians(-0.83)) - (math.sin(math.radians(latitude)) * sin_dec_rise)) / (math.cos(math.radians(latitude)) * cos_dec_rise)
    cos_h_set = (math.sin(math.radians(-0.83)) - (math.sin(math.radians(latitude)) * sin_dec_set)) / (math.cos(math.radians(latitude)) * cos_dec_set)
    
    # Check if the Sun never rises/sets
    if cos_h_rise > 1 or cos_h_set > 1:
        return (None, None)  # Sun never rises - polar night
    if cos_h_rise < -1 or cos_h_set < -1:
        return (None, None)  # Sun never sets - polar day
    
    # Convert to hours
    h_rise = (360 - math.degrees(math.acos(cos_h_rise))) / 15
    h_set = math.degrees(math.acos(cos_h_set)) / 15
    
    # Calculate local mean time of rising/setting
    t_rise = h_rise + ra_rise - (0.06571 * t_rise) - 6.622
    t_set = h_set + ra_set - (0.06571 * t_set) - 6.622
    
    # Adjust for UTC
    utc_rise = (t_rise - lngHour) % 24
    utc_set = (t_set - lngHour) % 24
    
    # Convert to datetime objects in UTC, then convert to local time
    utc_tz = pytz.UTC
    
    sunrise_hour = int(utc_rise)
    sunrise_minute = int((utc_rise % 1) * 60)
    sunset_hour = int(utc_set)
    sunset_minute = int((utc_set % 1) * 60)
    
    # Handle day rollovers for sunset
    sunrise_date = date
    sunset_date = date
    
    # Create datetime objects in UTC
    sunrise_time_utc = datetime.datetime.combine(
        sunrise_date, 
        datetime.time(sunrise_hour, sunrise_minute),
        tzinfo=utc_tz
    )
    
    sunset_time_utc = datetime.datetime.combine(
        sunset_date, 
        datetime.time(sunset_hour, sunset_minute),
        tzinfo=utc_tz
    )
    
    # Convert to local timezone
    sunrise_time_local = sunrise_time_utc.astimezone(local_tz)
    sunset_time_local = sunset_time_utc.astimezone(local_tz)
    
    # Ensure sunset is after sunrise - if not, it's probably on the previous/next day
    if sunset_time_local < sunrise_time_local:
        # Try adjusting sunset to the next day
        sunset_time_utc_next = sunset_time_utc + datetime.timedelta(days=1)
        sunset_time_local_next = sunset_time_utc_next.astimezone(local_tz)
        
        # Check if this makes more sense
        if (sunset_time_local_next - sunrise_time_local).total_seconds() < 24 * 3600:
            sunset_time_local = sunset_time_local_next
        else:
            # Otherwise, sunrise might be on the previous day
            sunrise_time_utc_prev = sunrise_time_utc - datetime.timedelta(days=1)
            sunrise_time_local_prev = sunrise_time_utc_prev.astimezone(local_tz)
            if (sunset_time_local - sunrise_time_local_prev).total_seconds() < 24 * 3600:
                sunrise_time_local = sunrise_time_local_prev
    
    return (sunrise_time_local, sunset_time_local)

def calculate_daylight_hours(sunrise, sunset):
    """
    Calculate the number of daylight hours between sunrise and sunset.
    
    Args:
        sunrise: Sunrise datetime (or None for polar day/night)
        sunset: Sunset datetime (or None for polar day/night)
        
    Returns:
        float: Hours of daylight, or None if not calculable
    """
    if sunrise is None and sunset is None:
        return None  # Will be determined later based on date
    
    if sunrise is None or sunset is None:
        return None
    
    delta = sunset - sunrise
    return delta.total_seconds() / 3600

def is_polar_day(latitude, date):
    """
    Simple check for polar day (midnight sun) based on latitude and date
    
    Args:
        latitude: Latitude in decimal degrees
        date: Date to check
        
    Returns:
        bool: True if polar day
    """
    # Northern hemisphere summer (April-August)
    if latitude > 0 and date.month >= 4 and date.month <= 8:
        return True
    
    # Southern hemisphere summer (November-February)
    if latitude < 0 and (date.month >= 11 or date.month <= 2):
        return True
    
    return False

def is_polar_night(latitude, date):
    """
    Simple check for polar night based on latitude and date
    
    Args:
        latitude: Latitude in decimal degrees
        date: Date to check
        
    Returns:
        bool: True if polar night
    """
    # Northern hemisphere winter (November-February)
    if latitude > 0 and (date.month >= 11 or date.month <= 2):
        return True
    
    # Southern hemisphere winter (May-August)
    if latitude < 0 and date.month >= 5 and date.month <= 8:
        return True
    
    return False

def get_sun_data_for_date_range(latitude, longitude, start_date, end_date, format_times_simple=True):
    """
    Calculate sun data for a range of dates
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        start_date: Start date (datetime.date object or ISO string)
        end_date: End date (datetime.date object or ISO string)
        format_times_simple: If True, return times in simple 24hr format. If False, return full ISO format.
        
    Returns:
        dict: Sun data for the date range
    """
    # Convert string dates to datetime if needed
    if isinstance(start_date, str):
        start_date = datetime.date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = datetime.date.fromisoformat(end_date)
    
    # Get timezone once for efficiency
    timezone_str = get_timezone(latitude, longitude)
    local_tz = pytz.timezone(timezone_str)
    
    # Calculate number of days in range
    delta = end_date - start_date
    num_days = delta.days + 1  # +1 to include the end date
    
    # Initialize results
    results = {
        "coordinates": {
            "lat": latitude,
            "lon": longitude
        },
        "timezone": timezone_str,
        "dateRange": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": num_days
        },
        "data": []
    }
    
    # Calculate for each day
    current_date = start_date
    while current_date <= end_date:
        # Get sunrise/sunset times
        sunrise, sunset = calculate_sunrise_sunset(latitude, longitude, current_date, local_tz=local_tz)
        
        # If both sunrise and sunset are None, determine if it's polar day or polar night
        if sunrise is None and sunset is None:
            # Look at the season to determine if it's day or night
            if is_polar_day(latitude, current_date):
                polar_day = True
                polar_night = False
                daylight_hours = 24.0
            else:
                polar_day = False
                polar_night = True
                daylight_hours = 0.0
        else:
            # Regular day with sunrise and sunset
            polar_day = False
            polar_night = False
            daylight_hours = calculate_daylight_hours(sunrise, sunset)
        
        if format_times_simple:
            # Format times as simple 24hr format (HH:MM)
            sunrise_str = sunrise.strftime("%H:%M") if sunrise else None
            sunset_str = sunset.strftime("%H:%M") if sunset else None
        else:
            # Use full ISO format
            sunrise_str = sunrise.isoformat() if sunrise else None
            sunset_str = sunset.isoformat() if sunset else None
        
        day_data = {
            "date": current_date.isoformat(),
            "sunrise": sunrise_str,
            "sunset": sunset_str,
            "daylightHours": round(daylight_hours, 2) if daylight_hours is not None else None,
            "polarDay": polar_day,
            "polarNight": polar_night
        }
        
        results["data"].append(day_data)
        current_date += datetime.timedelta(days=1)
    
    return results