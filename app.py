import logging
from flask import Flask
from flask_cors import CORS
from backend.database import build_db, db, User  # Ensure User is imported

# Set up logging
logging.basicConfig(level=logging.DEBUG)



# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Using SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable Cross-Origin Resource Sharing (CORS)
CORS(app)

# Build the database and insert initial users from the config file
build_db(app)

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
