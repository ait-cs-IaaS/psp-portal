import yaml
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import time
from datetime import datetime
import random
from threading import Thread

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

# Load transactions from transactions.yaml
def load_transactions_from_yaml():
    if os.path.exists('transactions.yaml'):
        with open('transactions.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config.get('transactions', [])
    return []

# Save transactions to transactions.yaml
def save_transactions_to_yaml(transactions):
    try:
        with open('transactions.yaml', 'w') as f:
            yaml.dump({'transactions': transactions}, f)
        print("Successfully saved transactions to YAML.")
    except Exception as e:
        print(f"Failed to write to YAML: {e}")

def add_transaction_periodically():
    """Function to add a new transaction to the YAML file every 20 seconds."""
    while True:
        with app.app_context():  # Ensure the app context is available in the thread
            # Get current date and time
            current_datetime = datetime.now()
            current_date = current_datetime.strftime("%Y-%m-%d")
            current_time = current_datetime.strftime("%H:%M:%S")

            # Create a random amount and transaction type
            amount = round(random.uniform(10.00, 10000.00), 2)
            transaction_type = random.choice(['debit', 'credit'])
            status = "completed"
            currency = "EUR"

            # Generate a random transaction ID
            transaction_id = f"TXN{random.randint(10000000, 99999999)}"

            # Sample account information
            account_name = "Sample Account"
            account_number = f"LU{random.randint(100000000000000000, 999999999999999999)}"
            description = f"Sample transaction of {transaction_type}"
            location = "Sample Location"

            # Create a new transaction object
            new_transaction = {
                'transaction_id': transaction_id,
                'date': current_date,
                'time': current_time,
                'amount': amount,
                'currency': currency,
                'type': transaction_type,
                'status': status,
                'account': {
                    'name': account_name,
                    'account_number': account_number
                },
                'description': description,
                'location': location
            }

            # Print the newly generated transaction
            print("\nNew Transaction Generated:")
            print(f"Transaction ID: {transaction_id}")
            print(f"Date: {current_date}")
            print(f"Time: {current_time}")
            print(f"Amount: {amount} {currency}")
            print(f"Type: {transaction_type}")
            print(f"Status: {status}")
            print(f"Account Name: {account_name}")
            print(f"Account Number: {account_number}")
            print(f"Description: {description}")
            print(f"Location: {location}")

            # Load existing transactions from the YAML file
            transactions = load_transactions_from_yaml()

            # Append the new transaction to the list
            transactions.append(new_transaction)

            # Save the updated transactions back to the YAML file
            save_transactions_to_yaml(transactions)

            print(f"New transaction added to YAML: {transaction_id} at {current_date} {current_time}")

            # Wait for 20 seconds before adding another transaction
            time.sleep(20)

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

# Insert transactions from transactions.yaml into the database
def db_insert_transactions_from_config():
    transactions = load_transactions_from_yaml()

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

if __name__ == '__main__':
    build_db(app)  # Initialize the database
    print("Database with users and transactions created successfully.")

    # Start the background thread to add transactions to YAML every 20 seconds
    transaction_thread = Thread(target=add_transaction_periodically)
    transaction_thread.daemon = True  # Ensure the thread exits when the main program exits
    transaction_thread.start()

    print("Transaction generation thread started.")

    # Print users and transactions
    print_all_users()        # Print all users
    print_all_transactions() # Print all transactions

    # Run the Flask application
    app.run(debug=True)
