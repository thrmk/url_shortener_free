import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from hashids import Hashids
from datetime import datetime, timedelta
import random
import string
import re
import requests

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
    result = None
    if request.method == 'POST':
        value = float(request.form['value'])
        from_unit = request.form['from_unit']
        to_unit = request.form['to_unit']

        result = convert_units(value, from_unit, to_unit)

    return render_template('unit_converter.html', result=result)

def convert_units(value, from_unit, to_unit):
    # Add conversion logic here
    conversion_rates = {
        ('meters', 'kilometers'): 0.001,
        ('kilometers', 'meters'): 1000,
        ('grams', 'kilograms'): 0.001,
        ('kilograms', 'grams'): 1000,
        # Add more conversions as needed
    }

    if (from_unit, to_unit) in conversion_rates:
        return value * conversion_rates[(from_unit, to_unit)]
    else:
        return "Conversion not supported."

@app.route('/sitemap.xml')
def sitemap():
    urls = [
        {'loc': url_for('home', _external=True)},
        {'loc': url_for('url_shortener', _external=True)},
        {'loc': url_for('bmi', _external=True)},
        {'loc': url_for('password_generator', _external=True)},
        {'loc': url_for('unit_converter', _external=True)},
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

if __name__ == '__main__':
    app.run(debug=True)
