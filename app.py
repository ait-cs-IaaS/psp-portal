import logging
from dotenv import load_dotenv
import os

from flask import Flask
from flask_mail import Mail
from flask_cors import CORS

from backend.database import build_db, User, print_all_users  # Ensure User and print_all_users are imported

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from a .env file
load_dotenv()

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Using SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Configuration using environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')  # Update with correct SMTP server
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')  # Using port 587 for TLS
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False') == 'True'  # Enable TLS
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True' # Do not use SSL, as TLS is enabled
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Get mail username from .env
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Get mail password from .env
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')  # Get sender address from .env


# Initialize Flask-Mail
mail = Mail(app)

# Enable Cross-Origin Resource Sharing (CORS)
CORS(app)

# Build the database and insert initial users from the config file
build_db(app)

# Ensure the print_all_users is executed within the app context
with app.app_context():
    print_all_users()

# Import the routes and register the blueprint
from routes import api
app.register_blueprint(api, url_prefix='/')  # No need to pass `mail=mail`

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
