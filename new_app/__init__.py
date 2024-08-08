from flask import Flask
from .database import init_db

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    
    # Initialize database
    with app.app_context():
        init_db()
            
    # Register blueprints
    from .routes.home import home_bp
    from .routes.url_shortener import url_shortener_bp
    from .routes.redirect_url import redirect_url_bp
    from .routes.stats import stats_bp
    from .routes.privacy_policy import privacy_policy_bp
    from .routes.delete_url import delete_url_bp
    from .routes.bmi import bmi_bp
    from .routes.password_generator import password_generator_bp
    from .routes.unit_converter import unit_converter_bp
    from .routes.age_calculator import age_calculator_bp
    from .routes.sitemap import sitemap_bp
    from .routes.all_urls import all_urls_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(url_shortener_bp)
    app.register_blueprint(redirect_url_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(privacy_policy_bp)
    app.register_blueprint(delete_url_bp)
    app.register_blueprint(bmi_bp)
    app.register_blueprint(password_generator_bp)
    app.register_blueprint(unit_converter_bp)
    app.register_blueprint(age_calculator_bp)
    app.register_blueprint(sitemap_bp)
    app.register_blueprint(all_urls_bp)

    @app.route('/routes')
    def show_routes():
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        return '<br>'.join(routes)

    return app
