from flask import Blueprint, render_template
from ..utils import hashids, get_urls

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/stats')
def stats():
    urls = get_urls()
    print(urls)  # Debugging line
    return render_template('stats.html', urls=urls, hashids=hashids)