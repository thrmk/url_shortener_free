from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..database import get_db_connection
from ..utils import get_location_from_ip, get_urls, hashids
from datetime import datetime, timedelta
import sqlite3

url_shortener_bp = Blueprint('url_shortener', __name__)

@url_shortener_bp.route('/url_shortener', methods=['GET', 'POST'])
def url_shortener():
    default_expiry = datetime.now() + timedelta(hours=24)
    default_expiry_str = default_expiry.strftime('%Y-%m-%d %H:%M')

    if request.method == 'POST':
        original_url = request.form['url']
        expiry = request.form.get('expiry', default_expiry_str)

        if not original_url:
            flash('Please enter a URL.')
            return redirect(url_for('url_shortener.url_shortener'))

        short_url_code = hashids.encode(len(get_urls()) + 1)
        short_url = url_for('redirect_url.redirect_url', short_url=short_url_code, _external=True)
        
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
