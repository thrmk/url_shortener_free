import requests
import re
import string
import random
from hashids import Hashids
import sqlite3

hashids = Hashids(salt='your_salt', min_length=6)

def get_location_from_ip(ip_address):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}')
        data = response.json()
        return data.get('city', '') + ', ' + data.get('country', '')
    except requests.RequestException:
        return ''

def calculate_bmi(weight, weight_unit, height, height_unit):
    try:
        # Convert weight to kilograms
        if weight_unit == 'lbs':
            weight_kg = weight * 0.453592  # pounds to kg
        elif weight_unit == 'oz':
            weight_kg = weight * 0.0283495  # ounces to kg
        else:  # kg
            weight_kg = weight

        # Convert height to meters
        if height_unit == 'inches':
            height_m = height * 0.0254  # inches to meters
        else:  # cm
            height_m = height / 100  # cm to meters

        bmi = weight_kg / (height_m * height_m)
        return round(bmi, 2)
    except (ZeroDivisionError, ValueError):
        return None

def assess_password_strength(password):
    strength = "Weak"
    score = 0
    color = "red"

    # Basic length check
    if len(password) >= 8:
        score += 1

    # Check for upper case letters
    if re.search(r'[A-Z]', password):
        score += 1

    # Check for digits
    if re.search(r'\d', password):
        score += 1

    # Check for special characters
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1

    # Additional score for very strong passwords
    if len(password) >= 12 and score == 4:
        strength = "Very Strong"
        color = "green"
    elif len(password) >= 10 and score == 4:
        strength = "Strong"
        color = "blue"
    elif score >= 2:
        strength = "Moderate"
        color = "orange"
    
    return strength, color

def generate_password(length, include_uppercase, include_digits, include_special):
    chars = string.ascii_lowercase
    if include_uppercase:
        chars += string.ascii_uppercase
    if include_digits:
        chars += string.digits
    if include_special:
        chars += string.punctuation

    return ''.join(random.choice(chars) for _ in range(length))

def get_urls():
    conn = sqlite3.connect('app/database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT short_url FROM urls')
    urls = cursor.fetchall()
    conn.close()
    print(urls)
    return [url[0] for url in urls]

def convert_units(value, from_unit, to_unit, category):
    base_conversions = {
        'distance': {
            'meters': 1,
            'kilometers': 1000,
            'miles': 1609.34,
            'yards': 0.9144,
            'feet': 0.3048,
            'inches': 0.0254,
            'centimeters': 0.01,
            'millimeters': 0.001,
            'decimeters': 0.1,
            'hectometers': 100,
            'nautical miles': 1852,
            'light-years': 9.461e15,  # 1 light-year = 9.461 trillion kilometers
            'astronomical units': 1.496e11,  # 1 astronomical unit = 149.6 million kilometers
            'parsecs': 3.086e16,  # 1 parsec = 3.086 trillion kilometers
        },
        'weight': {
            'grams': 1,
            'kilograms': 1000,
            'pounds': 453.592,
            'ounces': 28.3495,
            'milligrams': 0.001,
            'micrograms': 1e-6,
            'decigrams': 0.1,
            'hectograms': 100,
            'stones': 6350.29,
            'tons': 1e6,
            'carats': 0.2,  # 1 carat = 0.2 grams
            'troy ounces': 31.1035,  # 1 troy ounce = 31.1035 grams
            'grains': 0.0647989,  # 1 grain = 0.0647989 grams
            'pennyweights': 1.55517,  # 1 pennyweight = 1.55517 grams
        },
        'temperature': {
            # Temperature conversions are special cases handled separately
            'celsius': ('kelvin', lambda c: c + 273.15, lambda k: k - 273.15),
            'fahrenheit': ('kelvin', lambda f: (f + 459.67) * 5/9, lambda k: (k * 9/5) - 459.67),
            'kelvin': ('kelvin', lambda k: k, lambda k: k),  # No conversion needed
            'rankine': ('kelvin', lambda r: r * 5/9, lambda k: k * 9/5),
        },
        'volume': {
            'liters': 1,
            'milliliters': 0.001,
            'gallons': 3.78541,
            'cups': 0.236588,
            'pints': 0.473176,
            'quarts': 0.946353,
            'cubic meters': 1000,
            'cubic centimeters': 0.001,
            'cubic inches': 0.0163871,
            'deciliters': 0.1,
            'hectoliters': 100,
        },
        'data': {
            'bytes': 1,
            'kilobytes': 1e3,
            'megabytes': 1e6,
            'gigabytes': 1e9,
            'terabytes': 1e12,
            'petabytes': 1e15,
            'exabytes': 1e18,
            'zettabytes': 1e21,
            'yottabytes': 1e24,
            'gigabits': 1.25e8,  # 1 gigabit = 125 million bytes
        },
        'area': {
            'square meters': 1,
            'square kilometers': 1e6,
            'square miles': 2.59e6,
            'acres': 4046.86,
            'hectares': 10000,
            'square yards': 0.836127,
            'square feet': 0.092903,
            'square inches': 0.00064516,
            'square centimeters': 1e-4,
            'square millimeters': 1e-6,
            'square decimeters': 0.01,
            'square hectometers': 1e4,
        },
        'perimeter': {
            'meters': 1,
            'kilometers': 1000,
            'miles': 1609.34,
            'yards': 0.9144,
            'feet': 0.3048,
            'inches': 0.0254,
            'centimeters': 0.01,
            'millimeters': 0.001,
            'decimeters': 0.1,
            'hectometers': 100,
        },
        'logarithmic': {
            'decibels': 1,
            'bels': 10,
            'nepers': 8.68589,  # 1 neper = 8.68589 dB
            # More logarithmic units can be added here
        },
        'sound': {
            'decibels': 1,
            'bels': 10,
            'nepers': 8.68589,  # 1 neper = 8.68589 dB
            # More sound-related units can be added
        },
        'light': {
            'lumens': 1,
            'candela': 1 / (4 * 3.14159),  # 1 candela = 1 lumen/sr (steradian)
            'lux': 1,  # Note: 1 lux = 1 lumen/m^2, but the conversion needs context (surface area)
            # More light-related units can be added
        }
    }

    if category not in base_conversions:
        return "Invalid category."

    if category == 'temperature':
        from_base = base_conversions[category][from_unit]
        to_base = base_conversions[category][to_unit]
        # Convert to base (kelvin) then to the target unit
        return round(to_base[2](from_base[1](value)), 2)

    try:
        # Convert from the input unit to the base unit (SI)
        base_value = value * base_conversions[category][from_unit]
        # Convert from the base unit to the target unit
        converted_value = base_value / base_conversions[category][to_unit]
        return round(converted_value, 2)
    except KeyError:
        return "Conversion not supported."