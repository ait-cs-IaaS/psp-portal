import yaml
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from datetime import datetime
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define User and Transaction models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    mfa = db.Column(db.String(10), nullable=False)  # Multi-factor authentication

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
            data = yaml.safe_load(f)
            return data.get('transactions', [])
    return []

# Save transactions to transactions.yaml
def save_transactions_to_yaml(transactions):
    with open('transactions.yaml', 'w') as f:
        yaml.dump({'transactions': transactions}, f)
    print("Successfully saved transactions to YAML.")

def add_transaction_to_history(transaction_data):
    # Generate a unique transaction ID
    transaction_id = f"TXN{random.randint(10000000, 99999999)}"
    transaction_data['transaction_id'] = transaction_id

    # Add the transaction to the database
    new_transaction = Transaction(
        transaction_id=transaction_data['transaction_id'],
        date=transaction_data['date'],
        time=transaction_data['time'],
        amount=transaction_data['amount'],
        currency=transaction_data['currency'],
        type=transaction_data['type'],
        status=transaction_data['status'],  # Either "Completed" or "Not Authorized"
        account_name=transaction_data['account_name'],
        account_number=transaction_data['account_number'],
        description=transaction_data['description'],
        location=transaction_data['location']
    )
    db.session.add(new_transaction)
    db.session.commit()

    # Add the transaction to the transactions.yaml file
    transactions = load_transactions_from_yaml()
    transactions.append({
        'transaction_id': transaction_data['transaction_id'],
        'date': transaction_data['date'],
        'time': transaction_data['time'],
        'amount': transaction_data['amount'],
        'currency': transaction_data['currency'],
        'type': transaction_data['type'],
        'status': transaction_data['status'],
        'account_name': transaction_data['account_name'],
        'account_number': transaction_data['account_number'],
        'description': transaction_data['description'],
        'location': transaction_data['location']
    })
    save_transactions_to_yaml(transactions)
    print(f"Transaction {transaction_id} added to history with status: {transaction_data['status']}")


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
            account_name=transaction_data['account_name'],
            account_number=transaction_data['account_number'],
            description=transaction_data['description'],
            location=transaction_data.get('location', '')
        )
        db.session.add(transaction)
        print(f"Inserted transaction: {transaction.transaction_id}")

    db.session.commit()


# Load transactions from transactions.yaml
def load_transactions_from_yaml():
    if os.path.exists('transactions.yaml'):
        with open('transactions.yaml', 'r') as f:
            data = yaml.safe_load(f)
            return data.get('transactions', [])
    return []

# Save transactions to transactions.yaml
def save_transactions_to_yaml(transactions):
    with open('transactions.yaml', 'w') as f:
        yaml.dump({'transactions': transactions}, f)
    print("Successfully saved transactions to YAML.")

    
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

    # For testing or demo purposes, you can start the periodic transaction thread
    # to simulate random transactions every 20 seconds.
    transaction_thread = Thread(target=add_transaction_periodically)
    transaction_thread.daemon = True  # Ensure the thread exits when the main program exits
    transaction_thread.start()

    print("Transaction generation thread started.")

    # Print users and transactions
    print_all_users()        # Print all users
    print_all_transactions() # Print all transactions

    # Run the Flask application
    app.run(debug=True)
