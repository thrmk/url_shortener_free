from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from hashids import Hashids
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
db = SQLAlchemy(app)
hashids = Hashids(min_length=8, salt='your_salt')

# Models
class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(2048), nullable=False)
    short_url = db.Column(db.String(150), unique=True, nullable=False)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    clicks = db.Column(db.Integer, default=0)
    expiry = db.Column(db.DateTime)

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        original_url = request.form['url']
        short_url = hashids.encode(len(URL.query.all()) + 1)
        new_url = URL(original_url=original_url, short_url=short_url)
        db.session.add(new_url)
        db.session.commit()
        return render_template('index.html', short_url=url_for('redirect_url', short_url=short_url))
    return render_template('index.html')

@app.route('/redirect/<short_url>')
def redirect_url(short_url):
    url = URL.query.filter_by(short_url=short_url).first_or_404()
    url.clicks += 1
    db.session.commit()
    return redirect(url.original_url)

@app.route('/stats')
def stats():
    urls = URL.query.all()
    return render_template('stats.html', urls=urls)

@app.route('/sitemap')
def sitemap():
    urls = [
        {'loc': url_for('home', _external=True)},
        {'loc': url_for('index', _external=True)},
        {'loc': url_for('stats', _external=True)},
        {'loc': url_for('sitemap', _external=True)},
        {'loc': url_for('privacy_policy', _external=True)},
    ]
    return render_template('sitemap.html', urls=urls)

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/delete_url/<id>', methods=['POST'])
def delete_url(id):
    url_id = hashids.decode(id)[0]
    url = URL.query.get_or_404(url_id)
    db.session.delete(url)
    db.session.commit()
    flash('URL deleted successfully.')
    return redirect(url_for('stats'))

if __name__ == '__main__':
    app.run(debug=True)
