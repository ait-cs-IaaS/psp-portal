import logging
from flask import Flask
from flask_cors import CORS
from flask_mail import Mail, Message
from flask_migrate import Migrate

from backend.database import build_db, db, User  # Ensure User is imported

# Set up logging
logging.basicConfig(level=logging.DEBUG)



# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Using SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your-email-password'   # Replace with your app-specific password if using Gmail
app.config['MAIL_DEFAULT_SENDER'] = ('Your App', 'your-email@gmail.com')

# Enable Cross-Origin Resource Sharing (CORS)
CORS(app)

# Build the database and insert initial users from the config file
build_db(app)

mail = Mail(app)

# --- TEMPORARY DATABASE CHECK ---

# Run this code to inspect your database and check if the MFA is properly inserted
with app.app_context():
    users = User.query.all()
    for user in users:
        print(f"User: {user.username}, MFA: {user.mfa}")

# --- END OF TEMPORARY DATABASE CHECK ---

# Import the routes and register them
from routes import api
app.register_blueprint(api)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
