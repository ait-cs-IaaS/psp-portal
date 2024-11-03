import yaml
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize the Flask app and database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Add the email column to the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    mfa = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Added email column


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
    second_user = db.Column(db.String(80), nullable=True)  # Add this line

# Load transactions from transactions.yaml
def load_transactions_from_yaml():
    if os.path.exists('transactions.yaml'):
        with open('transactions.yaml', 'r') as f:
            data = yaml.safe_load(f)
            return data.get('transactions', [])
    return []

# Save transactions to transactions.yaml
def save_transactions_to_yaml(transactions):
    try:
        logging.info("Attempting to save transactions to YAML.")
        with open('transactions.yaml', 'w') as f:
            yaml.dump({'transactions': transactions}, f, default_flow_style=False)
        logging.info("Successfully saved transactions to YAML.")
    except Exception as e:
        logging.error(f"Error saving transactions to YAML: {e}")

# Generate the next transaction ID by incrementing the last digits
def generate_next_transaction_id():
    last_transaction_id = get_last_transaction_id()

    if last_transaction_id:
        # Extract the numeric part (everything after "TXN")
        numeric_part = int(last_transaction_id[3:])  # Convert the string number part to an integer
        next_numeric_part = numeric_part + 1  # Increment by 1

        # Reassemble the transaction ID by adding "TXN" in front of the incremented number
        next_transaction_id = f"TXN{next_numeric_part:08d}"  # Ensure it's zero-padded to 8 digits
        logging.info(f"Next transaction ID generated: {next_transaction_id}")
        return next_transaction_id
    else:
        # If no transactions exist, start with a default
        logging.info("No previous transaction ID found, starting with default ID: TXN00000001")
        return "TXN00000001"  # Start with this ID if none exist

# Function to get the last transaction ID from the YAML file
def get_last_transaction_id():
    transactions = load_transactions_from_yaml()
    
    if not transactions:
        logging.info("No transactions found in YAML.")
        return None
    
    # Extract the numeric part of the transaction_id (skip the "TXN" part)
    last_transaction = max(transactions, key=lambda x: int(x['transaction_id'][3:]))
    logging.info(f"Last transaction ID found: {last_transaction['transaction_id']}")
    return last_transaction['transaction_id']


def add_transaction_to_history(transaction_data):
    # Generate a new transaction ID if needed
    transaction_id = generate_next_transaction_id()
    transaction_data['transaction_id'] = transaction_id

    logging.info(f"Adding transaction with ID: {transaction_id}")

    # Extract account information from transaction_data
    account_name = transaction_data.get('account_name', 'Unknown Account')
    account_number = transaction_data.get('account_number', 'Unknown Account Number')

    # Add the transaction to the database as a Transaction instance
    new_transaction = Transaction(
        transaction_id=transaction_id,
        date=transaction_data['date'],
        time=transaction_data['time'],
        amount=transaction_data['amount'],
        currency=transaction_data['currency'],
        type=transaction_data['type'],
        status=transaction_data['status'],
        account_name=account_name,
        account_number=account_number,
        description=transaction_data['description'],
        location=transaction_data['location'],
        second_user=transaction_data.get('second_user')  # Ensure second_user is included if required
    )
    db.session.add(new_transaction)
    db.session.commit()

    # Now save to the YAML file, using a dictionary format
    transactions = load_transactions_from_yaml()

    # Check if the transaction ID already exists in the YAML data
    existing_transaction_ids = {txn['transaction_id'] for txn in transactions}
    if transaction_id not in existing_transaction_ids:
        # Append the transaction data as a dictionary
        transactions.append({
            'transaction_id': transaction_id,
            'date': transaction_data['date'],
            'time': transaction_data['time'],
            'amount': transaction_data['amount'],
            'currency': transaction_data['currency'],
            'type': transaction_data['type'],
            'status': transaction_data['status'],
            'account': {
                'account_number': account_number,
                'name': account_name
            },
            'description': transaction_data['description'],
            'location': transaction_data['location']
        })
        logging.info(f"Transaction with ID {transaction_id} added to YAML transaction list.")

        # Save the updated transactions back to the YAML file
        save_transactions_to_yaml(transactions)
        logging.info(f"Transaction {transaction_id} added to history with status: {transaction_data['status']}")
    else:
        logging.info(f"Transaction {transaction_id} already exists in YAML. Skipping addition.")





# Test function to simulate adding a new transaction
def test_add_transaction():
    transaction_data = {
        'date': '2024-11-05',
        'time': '19:00:00',
        'amount': 1234.56,
        'currency': 'EUR',
        'type': 'debit',
        'status': 'Completed',
        'account_name': 'Test Account',
        'account_number': 'LU123456789012345678',
        'description': 'Test transaction',
        'location': 'Test Location'
    }
    add_transaction_to_history(transaction_data)

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
                mfa=user_data['mfa'],
                email=user_data['email']  # Ensure the email is included
            )
            db.session.add(user)
        db.session.commit()

# Insert transactions from transactions.yaml into the database
def db_insert_transactions_from_config():
    transactions = load_transactions_from_yaml()

    for transaction_data in transactions:
        existing_transaction = Transaction.query.filter_by(transaction_id=transaction_data['transaction_id']).first()
        if existing_transaction:
            logging.info(f"Transaction {transaction_data['transaction_id']} already exists. Skipping.")
            continue

        account_data = transaction_data.get('account', {})
        account_name = account_data.get('name', 'Unknown Account')
        account_number = account_data.get('account_number', 'Unknown Account Number')

        # Insert new transaction into the database
        transaction = Transaction(
            transaction_id=transaction_data['transaction_id'],
            date=transaction_data.get('date', datetime.now().strftime("%Y-%m-%d")),
            time=transaction_data.get('time', datetime.now().strftime("%H:%M:%S")),
            amount=transaction_data.get('amount', 0.0),
            currency=transaction_data.get('currency', 'EUR'),
            type=transaction_data.get('type', 'debit'),
            status=transaction_data.get('status', 'pending'),
            account_name=account_name,
            account_number=account_number,
            description=transaction_data.get('description', 'No description provided'),
            location=transaction_data.get('location', 'Unknown Location')
        )
        db.session.add(transaction)
        logging.info(f"Inserted transaction: {transaction.transaction_id}")

    db.session.commit()

# Print all users (for debugging or confirmation)
def print_all_users():
    users = User.query.all()
    logging.info("\n--- Users in Database ---")
    for user in users:
        logging.info(f"User: {user.username}, MFA: {user.mfa}")

# Print all transactions (for debugging or confirmation)
def print_all_transactions():
    transactions = Transaction.query.all()
    logging.info("\n--- Transactions in Database ---")
    for transaction in transactions:
        logging.info(f"Transaction ID: {transaction.transaction_id}, Amount: {transaction.amount}, Type: {transaction.type}, Status: {transaction.status}")

if __name__ == '__main__':
    build_db(app)  # Initialize the database
    logging.info("Database with users and transactions created successfully.")

    # Print users and transactions
    print_all_users()        # Print all users
    print_all_transactions() # Print all transactions

    # Test adding a transaction
    test_add_transaction()

    # Run the Flask application
    app.run(debug=True)
