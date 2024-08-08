from flask import Blueprint, redirect
from ..database import get_db_connection
from datetime import datetime

redirect_url_bp = Blueprint('redirect_url', __name__)

@redirect_url_bp.route('/<short_url>')
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