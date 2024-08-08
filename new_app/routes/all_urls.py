from flask import Blueprint, render_template
from ..utils import get_urls, hashids

all_urls_bp = Blueprint('all_urls', __name__)

@all_urls_bp.route('/all_urls', methods=['GET','POST'])
def all_urls():
    urls = get_urls()
    return render_template('all_urls.html', urls=urls, hashids=hashids)