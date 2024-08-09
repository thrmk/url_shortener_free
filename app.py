import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_from_directory, after_this_request, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from hashids import Hashids
from datetime import datetime, timedelta
import random
import string
import re
import requests
from dateutil.relativedelta import relativedelta
from PIL import Image
import os

def get_location_from_ip(ip_address):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}')
        data = response.json()
        return data.get('city', '') + ', ' + data.get('country', '')
    except requests.RequestException:
        return ''

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure key
hashids = Hashids(min_length=8, salt='your_salt')


UPLOAD_FOLDER = 'static/uploads'
COMPRESSED_FOLDER = 'static/compressed'

# Ensure the upload and compressed folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['COMPRESSED_FOLDER'] = COMPRESSED_FOLDER

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

def init_db():
    with sqlite3.connect('database.db') as connection:
        cursor = connection.cursor()
        cursor.executescript('''
        DROP TABLE IF EXISTS urls;
        DROP TABLE IF EXISTS users;

        CREATE TABLE urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            original_url TEXT NOT NULL,
            short_url TEXT UNIQUE NOT NULL,
            clicks INTEGER NOT NULL DEFAULT 0,
            expiry TEXT NOT NULL,
            ip_address TEXT,
            location TEXT
        );

        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        ''')
        connection.commit()

init_db()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/url_shortener', methods=['GET', 'POST'])
def url_shortener():
    default_expiry = datetime.now() + timedelta(hours=24)
    default_expiry_str = default_expiry.strftime('%Y-%m-%d %H:%M')

    if request.method == 'POST':
        original_url = request.form['url']
        expiry = request.form.get('expiry', default_expiry_str)

        if not original_url:
            flash('Please enter a URL.')
            return redirect(url_for('url_shortener'))

        short_url_code = hashids.encode(len(get_urls()) + 1)
        short_url = url_for('redirect_url', short_url=short_url_code, _external=True)
        
        # Retrieve the real IP address
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        location = get_location_from_ip(ip_address.split(',')[0].strip())  # Get location from IP address

        conn = get_db_connection()

        try:
            conn.execute('INSERT INTO urls (original_url, short_url, expiry, ip_address, location) VALUES (?, ?, ?, ?, ?)', 
                         (original_url, short_url_code, expiry, ip_address, location))
            conn.commit()
            flash('URL shortened successfully!')
        except sqlite3.IntegrityError:
            flash('Short URL already exists.')
        finally:
            conn.close()

        return render_template('url_shortener.html', short_url=short_url, expiry=expiry)

    return render_template('url_shortener.html', expiry=default_expiry_str)

@app.route('/<short_url>')
def redirect_url(short_url):
    conn = get_db_connection()
    url = conn.execute('SELECT * FROM urls WHERE short_url = ?', (short_url,)).fetchone()
    if url is None:
        return 'URL not found', 404
    
    expiry = datetime.strptime(url['expiry'], '%Y-%m-%d %H:%M')
    if datetime.now() > expiry:
        conn.execute('DELETE FROM urls WHERE short_url = ?', (short_url,))
        conn.commit()
        conn.close()
        return 'URL has expired', 410

    # Update click count only
    conn.execute('UPDATE urls SET clicks = clicks + 1 WHERE short_url = ?', (short_url,))
    conn.commit()
    conn.close()

    return redirect(url['original_url'])

@app.route('/stats')
def stats():
    urls = get_urls()
    print(urls)  # Debugging line
    return render_template('stats.html', urls=urls, hashids=hashids)

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/delete_url/<int:id>', methods=['POST'])
def delete_url(id):
    # Directly use the integer ID without decoding since it's coming as an integer
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM urls WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        flash('Failed to delete URL. It may not exist.')
    else:
        flash('URL deleted successfully.')

    return redirect(url_for('stats'))

@app.route('/bmi', methods=['GET', 'POST'])
def bmi():
    bmi = None
    category = ''
    
    if request.method == 'POST':
        try:
            weight = float(request.form.get('weight', 0))
            weight_unit = request.form.get('weight_unit', 'kg')
            height = float(request.form.get('height', 0))
            height_unit = request.form.get('height_unit', 'cm')
            
            bmi = calculate_bmi(weight, weight_unit, height, height_unit)

            if bmi is not None:
                if bmi < 18.5:
                    category = 'Underweight'
                elif 18.5 <= bmi < 24.9:
                    category = 'Normal weight'
                elif 25 <= bmi < 29.9:
                    category = 'Overweight'
                else:
                    category = 'Obesity'
            else:
                flash('Invalid input. Please enter valid numbers for weight and height.')
        except ValueError:
            flash('Please enter valid numeric values for weight and height.')

    return render_template('bmi.html', bmi=bmi, category=category)

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

@app.route('/password_generator', methods=['GET', 'POST'])
def password_generator():
    password = None
    strength = None
    color = "red"

    # Default settings
    include_uppercase = False
    include_digits = False
    include_special = False
    length = 12

    if request.method == 'POST':
        length = int(request.form.get('length', 12))
        include_uppercase = 'uppercase' in request.form
        include_digits = 'digits' in request.form
        include_special = 'special' in request.form

        password = generate_password(length, include_uppercase, include_digits, include_special)
        strength, color = assess_password_strength(password)

    return render_template(
        'password_generator.html',
        password=password,
        strength=strength,
        color=color,
        length=length,
        include_uppercase=include_uppercase,
        include_digits=include_digits,
        include_special=include_special
    )

@app.route('/unit_converter', methods=['GET', 'POST'])
def unit_converter():
    value = ''
    from_unit = ''
    to_unit = ''
    category = ''
    result = None

    units = {
        'distance': ['meters', 'kilometers', 'miles', 'yards', 'feet', 'inches', 'centimeters', 'millimeters', 'nautical miles'],
        'weight': ['grams', 'kilograms', 'pounds', 'ounces', 'milligrams', 'micrograms', 'stones', 'tons', 'carats'],
        'temperature': ['celsius', 'fahrenheit', 'kelvin', 'rankine'],
        'volume': ['liters', 'milliliters', 'gallons', 'cups', 'pints', 'quarts', 'cubic meters', 'cubic centimeters', 'cubic inches'],
        'data': ['bytes', 'kilobytes', 'megabytes', 'gigabytes', 'terabytes', 'petabytes', 'exabytes', 'zettabytes', 'yottabytes'],
        # Add more categories and units as needed
    }

    if request.method == 'POST':
        try:
            value = float(request.form['value'])
            category = request.form['category']
            from_unit = request.form['from_unit']
            to_unit = request.form['to_unit']

            result = convert_units(value, from_unit, to_unit, category)
        except ValueError:
            flash('Please enter a valid number.')

    return render_template('unit_converter.html', result=result, value=value, from_unit=from_unit, to_unit=to_unit, category=category, units=units)

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

@app.route('/age_calculator', methods=['GET', 'POST'])
def age_calculator():
    age_details = None
    total_days = None
    total_hours = None
    total_minutes = None
    total_seconds = None
    total_months = None
    format_type = request.form.get('format_type', 'full')

    if request.method == 'POST':
        try:
            dob_str = request.form.get('dob')
            dob = datetime.strptime(dob_str, '%Y-%m-%d')
            today = datetime.today()

            # Calculate the age
            age = relativedelta(today, dob)
            age_details = {
                'years': age.years,
                'months': age.months,
                'days': age.days,
                'total_days': (today - dob).days,
                'total_months': age.years * 12 + age.months,
                'time': today - dob
            }

            # Calculate total number of days, hours, minutes, seconds, and months
            total_days = (today - dob).days
            total_hours = total_days * 24
            total_minutes = total_hours * 60
            total_seconds = (today - dob).total_seconds()
            total_months = age.years * 12 + age.months

            if format_type == 'days':
                age_details = {
                    'days': total_days
                }
            elif format_type == 'months':
                age_details = {
                    'months': total_months
                }
            elif format_type == 'time':
                age_details = {
                    'time': str(age.years) + " years, " + str(age.months) + " months, " + str(age.days) + " days"
                }
            elif format_type == 'hours':
                age_details = {
                    'hours': total_hours
                }
            elif format_type == 'minutes':
                age_details = {
                    'minutes': total_minutes
                }
            elif format_type == 'seconds':
                age_details = {
                    'seconds': total_seconds
                }
            elif format_type == 'full':
                pass  # Use the full detailed age

        except ValueError:
            age_details = 'Invalid date format. Please enter a valid date.'

    return render_template('age_calculator.html', age_details=age_details, total_days=total_days, total_hours=total_hours, total_minutes=total_minutes, total_seconds=total_seconds, total_months=total_months, format_type=format_type)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(filepath, output_filename):
    try:
        with Image.open(filepath) as img:
            original_size = os.path.getsize(filepath)
            original_format = img.format

            # Compress the image
            compressed_image_path = os.path.join(app.config['COMPRESSED_FOLDER'], output_filename)
            img.save(compressed_image_path, format=original_format, optimize=True, quality=75)

            # Calculate compression details
            compressed_size = os.path.getsize(compressed_image_path)
            compression_percentage = ((original_size - compressed_size) / original_size) * 100
            original_dimensions = img.size
            compressed_dimensions = Image.open(compressed_image_path).size

            return compressed_image_path, compression_percentage, original_dimensions, compressed_dimensions
    except Exception as e:
        print(f"Error compressing image: {e}")
        return None, None, None, None

@app.route('/image_compressor', methods=['GET', 'POST'])
def image_compressor():
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            compressed_filepath, compression_percentage, original_dimensions, compressed_dimensions = compress_image(filepath, file.filename)

            if compressed_filepath:
                flash('Image successfully compressed and saved!')
                return render_template('image_compressor.html',
                                       compressed_image=os.path.basename(compressed_filepath),
                                       compression_percentage=compression_percentage,
                                       original_dimensions=original_dimensions,
                                       compressed_dimensions=compressed_dimensions)

    return render_template('image_compressor.html')

@app.route('/download/<filename>')
def download_file(filename):
    compressed_path = os.path.join(app.config['COMPRESSED_FOLDER'], filename)
    if os.path.isfile(compressed_path):
        os.remove(compressed_path)
        return send_file(compressed_path, as_attachment=True)
    else:
        flash('File not found.')
        return redirect(url_for('image_compressor'))

@app.route('/delete/<filename>')
def delete_file(filename):
    uploaded_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.isfile(uploaded_path):
        os.remove(uploaded_path)
    compressed_path = os.path.join(app.config['COMPRESSED_FOLDER'], filename)
    if os.path.isfile(compressed_path):
        os.remove(compressed_path)
    return redirect(url_for('image_compressor'))

@app.route('/sitemap.xml')
def sitemap():
    urls = [
        {'loc': url_for('home', _external=True)},
        {'loc': url_for('url_shortener', _external=True)},
        {'loc': url_for('bmi', _external=True)},
        {'loc': url_for('password_generator', _external=True)},
        {'loc': url_for('unit_converter', _external=True)},
        {'loc': url_for('age_calculator', _external=True)},
        {'loc': url_for('privacy_policy', _external=True)},
        {'loc': url_for('robots_txt', _external=True)},
        {'loc': url_for('sitemap', _external=True)},
    ]
    xml = render_template('sitemap.xml', urls=urls, now=datetime.now())
    return Response(xml, mimetype='application/xml')


def get_urls():
    conn = get_db_connection()
    urls = conn.execute('SELECT * FROM urls').fetchall()
    conn.close()
    return urls

@app.route('/robots.txt', methods=['GET','POST'])
def robots_txt():
    return send_from_directory(app.root_path, 'robots.txt')

@app.route('/all_urls', methods=['GET','POST'])
def all_urls():
    urls = get_urls()
    return render_template('all_urls.html', urls=urls, hashids=hashids)

@app.route('/routes')
def show_routes():
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    return '<br>'.join(routes)

if __name__ == '__main__':
    app.run(debug=True)
