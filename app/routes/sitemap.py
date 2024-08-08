from flask import Blueprint, render_template, url_for, Response
from datetime import datetime

sitemap_bp = Blueprint('sitemap', __name__)

@sitemap_bp.route('/sitemap', methods=['GET', 'POST'])
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

