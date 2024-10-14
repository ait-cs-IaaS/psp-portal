import yaml
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Define a User model with MFA support
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    mfa = db.Column(db.String(10), nullable=False)  # Add the MFA field

# Function to initialize the database and insert users from config.yaml
def build_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        db_insert_users_from_config()

# Load users from the config.yaml file
def load_users_from_config():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config.get('users', {})

# Insert users from the config.yaml into the database
def db_insert_users_from_config():
    users = load_users_from_config()

    if User.query.count() == 0:  # Only insert if there are no users in the database
        for username, user_data in users.items():
            user = User(
                username=username,
                password=user_data['password'],
                mfa=user_data['mfa']  # Insert the MFA from the config
            )
            db.session.add(user)
        db.session.commit()
