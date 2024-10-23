from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from backend.database import User, Transaction, db, load_transactions_from_yaml, save_transactions_to_yaml, add_transaction_to_history  # Add the function import
from datetime import datetime
import random
from flask_mail import Message


# Create a blueprint for the routes
api = Blueprint('api', __name__)

# Home route (login page)
@api.route('/')
def index():
    return render_template('login.html')

# Login route
@api.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Debugging: Check if username and password were sent to the backend
    print(f"Received login attempt for username: {username}")

    # Query the database for the user
    user = User.query.filter_by(username=username).first()

    if user and user.password == password:
        # Store the user's username in session and trigger MFA request
        session['username'] = username  # <-- This saves the logged-in user's username in the session
        session['mfa_required'] = True  # Indicate MFA is required
        print(f"Login successful for user: {username}, prompting for MFA.")
        return jsonify({"mfa_required": True, "message": "MFA required. Please enter your MFA token."}), 200
    else:
        # Log failed login attempt
        print(f"Login failed for user: {username}")
        return jsonify({"error": "Invalid username or password"}), 401

# MFA verification route (login)
@api.route('/verify-login-mfa', methods=['POST'])
def verify_mfa():
    data = request.json
    mfa_token = data.get('mfaToken')

    # Ensure user is logged in and MFA is required
    if 'username' in session and session.get('mfa_required'):
        user = User.query.filter_by(username=session['username']).first()

        # Ensure that both tokens are compared as strings
        if user and str(user.mfa) == str(mfa_token):  # Convert to string for comparison
            session.pop('mfa_required', None)  # MFA passed, remove requirement
            print(f"MFA verification successful for user: {user.username}")
            return jsonify({"success": True, "message": "Login successful!"}), 200
        else:
            print(f"MFA verification failed for user: {user.username}")
            return jsonify({"error": "Invalid MFA token"}), 401
    else:
        return jsonify({"error": "Unauthorized or session expired"}), 401

# Payment route
@api.route('/payment-page', methods=['GET'])
def payment():
    # Check if user is logged in by verifying the session
    if 'username' not in session:
        # If the user is not logged in, redirect them to the login page
        return redirect(url_for('api.index'))

    # If the user is logged in, render the payment.html template
    return render_template('payment-page.html')

@api.route('/verify-payment-mfa', methods=['POST'])
def verify_payment_mfa():
    data = request.json
    amount = data.get('amount')
    mfa_token = data.get('mfaToken')
    second_username = data.get('secondUsername')  # Second username for dual MFA
    second_mfa_token = data.get('secondMfaToken')

    # Transaction data from the form, ensure all fields are provided
    transaction_data = {
        'amount': amount,
        'currency': data.get('currency', 'EUR'),  # Default to 'EUR' if not provided
        'type': data.get('type', 'credit'),  # Default type to 'credit' if not provided
        'account_name': data.get('accountName', 'Default Account Name'),  # Use a default if not provided
        'account_number': data.get('iban', 'Default IBAN'),  # Use a default IBAN if not provided
        'description': data.get('description', 'Payment description'),  # Default description if not provided
        'location': data.get('location', 'Unknown Location'),  # Default location if not provided
        'date': datetime.now().strftime("%Y-%m-%d"),
        'time': datetime.now().strftime("%H:%M:%S"),
    }

    # Ensure user is logged in
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Fetch the logged-in user from the session
    username = session['username']
    user = User.query.filter_by(username=username).first()

    # Verify the logged-in user's MFA token
    if not user or str(user.mfa) != str(mfa_token):
        # If MFA fails, mark transaction as "Not Authorized" and add to history
        transaction_data['status'] = "Not Authorized"
        add_transaction_to_history(transaction_data)
        return jsonify({"error": "Invalid MFA token for the logged-in user"}), 401

    # If the amount is 50,000 or more, verify the second MFA token for dual authentication
    if amount >= 50000:
        second_user = User.query.filter_by(username=second_username).first()

        if not second_user or str(second_user.mfa) != str(second_mfa_token):
            # If second MFA fails, mark transaction as "Not Authorized" and add to history
            transaction_data['status'] = "Not Authorized"
            add_transaction_to_history(transaction_data)
            return jsonify({"error": "Invalid second MFA token or user"}), 401

        # Both MFA tokens are verified, mark transaction as "Completed"
        transaction_data['status'] = "Completed"
        add_transaction_to_history(transaction_data)
        return jsonify({"success": True, "message": "Payment authorized with double MFA"}), 200

    # For payments under 50,000, only the logged-in user's MFA is required
    transaction_data['status'] = "Completed"
    add_transaction_to_history(transaction_data)

    return jsonify({"success": True, "message": "Payment authorized with single MFA"}), 200


# Transaction history route
@api.route('/transaction-history', methods=['GET'])
def transaction_history():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('api.index'))

    # Get the current page number from query parameters (default to 1)
    page = request.args.get('page', 1, type=int)

    # Query the transactions ordered by date descending
    transactions_query = Transaction.query.order_by(Transaction.date.desc(), Transaction.time.desc())

    # Pagination: 12 transactions per page, no error out
    transactions_paginated = transactions_query.paginate(page=page, per_page=12, error_out=False)

    # Get the transactions for the current page
    transactions = transactions_paginated.items

    return render_template('transaction-history.html', transactions=transactions, page=page)


@api.route('/payment-successful', methods=['GET'])
def payment_success():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('api.index'))  # If not logged in, redirect to login

    return render_template('payment-successful.html')



# Logout route
@api.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the entire session for security
    return redirect(url_for('api.index'))  # Redirect the user to the login page after logout
