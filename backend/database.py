import yaml
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  # Use one database for both
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Avoids overhead warning
db = SQLAlchemy(app)

# Define a User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    mfa = db.Column(db.String(10), nullable=False)  # Multi-factor authentication

# Define a Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(100), nullable=True)

# Function to initialize the database and insert users and transactions from YAML
def build_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        db_insert_users_from_config()
        db_insert_transactions_from_config()

# Load users from users.yaml
def load_users_from_config():
    with open('users.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config.get('users', {})

# Insert users from users.yaml into the database
def db_insert_users_from_config():
    users = load_users_from_config()
    if User.query.count() == 0:  # Only insert if there are no users
        for username, user_data in users.items():
            user = User(
                username=username,
                password=user_data['password'],
                mfa=user_data['mfa']
            )
            db.session.add(user)
        db.session.commit()

# Load transactions from transactions.yaml
def load_transactions_from_config():
    with open('transactions.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config.get('transactions', [])

# Insert transactions from transactions.yaml into the database
def db_insert_transactions_from_config():
    transactions = load_transactions_from_config()

    for transaction_data in transactions:
        # Check if the transaction already exists
        existing_transaction = Transaction.query.filter_by(transaction_id=transaction_data['transaction_id']).first()

        if existing_transaction:
            # If the transaction already exists, skip the insertion
            print(f"Transaction {transaction_data['transaction_id']} already exists. Skipping.")
            continue

        # Insert the new transaction if it doesn't exist
        transaction = Transaction(
            transaction_id=transaction_data['transaction_id'],
            date=transaction_data['date'],
            time=transaction_data['time'],
            amount=transaction_data['amount'],
            currency=transaction_data['currency'],
            type=transaction_data['type'],
            status=transaction_data['status'],
            account_name=transaction_data['account']['name'],
            account_number=transaction_data['account']['account_number'],
            description=transaction_data['description'],
            location=transaction_data['location']
        )
        db.session.add(transaction)
        print(f"Inserted transaction: {transaction.transaction_id}")

    db.session.commit()





# Function to print all users (for debugging or confirmation)
def print_all_users():
    users = User.query.all()
    print("\n--- Users in Database ---")
    for user in users:
        print(f"User: {user.username}, MFA: {user.mfa}")

# Function to print all transactions (for debugging or confirmation)
def print_all_transactions():
    transactions = Transaction.query.all()
    print("\n--- Transactions in Database ---")
    for transaction in transactions:
        print(f"Transaction ID: {transaction.transaction_id}, Amount: {transaction.amount}, Type: {transaction.type}, Status: {transaction.status}")

# Initialize and build the database
if __name__ == '__main__':
    build_db(app)  # Call build_db with the app instance
    print("Database with users and transactions created successfully.")

    # Print users and transactions
    print_all_users()        # Print all users
    print_all_transactions() # Print all transactions
