import logging
from dotenv import load_dotenv
import os

from flask import Flask
from flask_cors import CORS
from backend.database import build_db, print_all_users
from extensions import mail  # Import mail from extensions

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from a .env file
load_dotenv()

def create_app():
    # Initialize the Flask app
    app = Flask(__name__)
    app.secret_key = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')  # Update with correct SMTP server
    app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')  # Using port 587 for TLS
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False') == 'True'  # Enable TLS
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True' # Do not use SSL, as TLS is enabled
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Get mail username from .env
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Get mail password from .env
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')  # Get sender address from .env


    # Initialize extensions with the app
    mail.init_app(app)
    CORS(app)

    # Build the database and insert initial users from the config file
    with app.app_context():
        build_db(app)
        print_all_users()

    # Import and register blueprints within the create_app function
    from routes import api
    app.register_blueprint(api, url_prefix='/')

    return app

# Create the app instance
app = create_app()

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

