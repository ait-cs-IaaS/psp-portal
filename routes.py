from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, current_app  # Add current_app import
from backend.database import User, Transaction, db, generate_next_transaction_id, load_transactions_from_yaml, save_transactions_to_yaml, add_transaction_to_history  # Add the function import
from datetime import datetime
import threading
import time
from flask_mail import Message
import logging
import base64
import json
import requests

from flask import current_app

orbis_endpoint = os.getenv('ORBIS')

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

    if user:
        print(f"User found: {user.username}, Password in DB: {user.password}, Provided Password: {password}")
    else:
        print(f"No user found for username: {username}")

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


def auto_expire_transaction(app, transaction_id):
    with app.app_context():  # Use the Flask app context in the thread
        time.sleep(120)  # Wait for 2 minutes
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        if transaction and transaction.status == 'Pending Approval':
            transaction.status = 'Not Authorized'
            db.session.commit()
            logging.info(f"Transaction {transaction_id} automatically marked as Not Authorized.")


def send_to_orbiscloud(transaction_data):
    try:
        # Convert transaction data to JSON string and "encrypt" with base64
        json_data = json.dumps(transaction_data)
        encrypted_data = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")

        global orbis_endpoint
        # Construct OrbisCloud endpoint URL with "encrypted" string as a parameter
        orbiscloud_url = f"{ orbis_endpoint }/transactions"
        
        # Log the "encrypted" data that will be sent to OrbisCloud
        logging.info(f"Sending 'encrypted' transaction to OrbisCloud: {encrypted_data}")
        
        # Send the POST request to OrbisCloud with the encrypted data in JSON format
        response = requests.post(orbiscloud_url, json={"encrypted_data": encrypted_data})
        
        # Check the response from OrbisCloud
        if response.status_code == 200:
            logging.info(f"Transaction {transaction_data['transaction_id']} successfully sent to OrbisCloud.")
        else:
            logging.error(f"Failed to send transaction to OrbisCloud: {response.text}")
    except Exception as e:
        logging.error(f"Error sending to OrbisCloud: {str(e)}")



@api.route('/verify-dual-mfa', methods=['POST'])
def verify_dual_mfa():
    data = request.json
    mfa_token = data.get('mfaToken')
    second_username = data.get('secondUsername')  # Second employee username
    amount = data.get('amount')
    iban = data.get('iban')
    account_name = data.get('accountName')
    currency = data.get('currency')
    transaction_type = data.get('type')
    description = data.get('description')
    location = data.get('location')

    # Ensure the user is logged in
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session['username']
    user = User.query.filter_by(username=username).first()

    # Verify that the MFA token for the logged-in user is correct
    if not user or str(user.mfa) != str(mfa_token):
        return jsonify({"error": "Invalid MFA token for the logged-in user"}), 400

    # Ensure that the second username corresponds to a valid user other than the logged-in user
    second_user = User.query.filter_by(username=second_username).first()

    if not second_user:
        return jsonify({"error": "The second user with the provided username does not exist"}), 404
    
    if second_user.username == username:
        return jsonify({"error": "The second user cannot be the same as the logged-in user"}), 400

    # Generate the transaction ID (TXN...)
    transaction_id = generate_next_transaction_id()

    # Save transaction data to the database (pending approval)
    transaction_data = {
        'transaction_id': transaction_id,
        'date': datetime.now().strftime("%Y-%m-%d"),
        'time': datetime.now().strftime("%H:%M:%S"),
        'amount': amount,
        'currency': currency,
        'type': transaction_type,
        'status': 'Pending Approval',
        'account_name': account_name,
        'account_number': iban,
        'description': description,
        'location': location
    }

    # Add the transaction to history, mark it as pending approval
    add_transaction_to_history(transaction_data)

    # Start a background thread to auto-expire the transaction in 2 minutes
    app = current_app._get_current_object()  # Explicitly get current app for the thread
    expire_thread = threading.Thread(target=auto_expire_transaction, args=(app, transaction_id,))
    expire_thread.start()

    # Generate the approval link for the second user
    approval_link = url_for('api.confirm_dual_mfa', transaction_id=transaction_id, _external=True)

    # Send an email to the second user with the transaction ID and approval link
    try:
        logging.info("Trying to send email...")
        mail = current_app.extensions.get('mail')

        # Create the message
        msg = Message(
            subject="Transaction Approval Needed",
            recipients=[second_user.email],  # Use the second user's email for sending
            body=f"Hello {second_user.username},\n\nYou need to approve the transaction {transaction_id} for {currency} {amount} .\n\nPlease click the following link to view the transaction details and approve it:\n\n{approval_link}\n\nThanks!",
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )

        # Send the email
        mail.send(msg)

        logging.info(f"Email successfully sent to {second_user.email}.")  # Log success
        return jsonify({"success": True, "message": f"Email sent to {second_user.username} for approval", "transaction_id": transaction_id}), 200
    except Exception as e:
        logging.error(f"Failed to send email. Error: {str(e)}")  # Log the error message
        return jsonify({"error": f"Failed to send email. Error: {str(e)}"}), 500



@api.route('/confirm-dual-mfa/<transaction_id>', methods=['GET', 'POST'])
def confirm_dual_mfa(transaction_id):
    # Retrieve the transaction from the database
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()

    if not transaction:
        return "Transaction not found", 404

    if request.method == 'GET':
        # Render a template showing the transaction details and a form for entering the MFA token
        return render_template('confirm-dual-mfa.html', transaction=transaction)
    
    if request.method == 'POST':
        # Get the second user's MFA token from the form
        second_mfa_token = request.form.get('mfaToken')

        # Ensure the second user is logged in
        if 'username' not in session:
            return jsonify({"error": "Unauthorized"}), 401

        # Find the second user by their session username
        second_user = User.query.filter_by(username=session['username']).first()

        if not second_user or str(second_user.mfa) != str(second_mfa_token):
            return jsonify({"error": "Invalid MFA token for the second user"}), 400

        # If the MFA token is valid, approve the transaction
        transaction.status = 'Completed'
        db.session.commit()

        # Convert transaction data to dictionary format before sending
        transaction_data = {
            'transaction_id': transaction.transaction_id,
            'date': transaction.date,
            'time': transaction.time,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'type': transaction.type,
            'status': transaction.status,
            'account_name': transaction.account_name,
            'account_number': transaction.account_number,
            'description': transaction.description,
            'location': transaction.location
        }

        send_to_orbiscloud(transaction_data)

        return jsonify({"success": True, "message": "Transaction approved successfully!"})



# Verify payment and handle MFA
@api.route('/verify-payment-mfa', methods=['POST'])
def verify_payment_mfa():
    data = request.json
    amount = data.get('amount')
    mfa_token = data.get('mfaToken')
    second_email = data.get('secondEmail', None)  # Second email for dual MFA only

    transaction_data = {
        'amount': amount,
        'currency': data.get('currency', 'EUR'),
        'type': data.get('type', 'debit'),
        'account_name': data.get('accountName', 'Default Account Name'),
        'account_number': data.get('iban', 'Default IBAN'),
        'description': data.get('description', 'Payment description'),
        'location': data.get('location', 'Unknown Location'),
        'date': datetime.now().strftime("%Y-%m-%d"),
        'time': datetime.now().strftime("%H:%M:%S"),
    }

    # Check if the user is logged in
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session['username']
    user = User.query.filter_by(username=username).first()

    if not user or str(user.mfa) != str(mfa_token):
        transaction_data['status'] = "Not Authorized"
        add_transaction_to_history(transaction_data)
        return jsonify({"error": "Invalid MFA token for the logged-in user"}), 401

    # If amount is greater than or equal to 50,000, initiate dual MFA verification
    if float(amount) >= 50000:
        # Ensure second email is provided for dual MFA
        if not second_email:
            return jsonify({"error": "Second email required for dual verification"}), 400

        try:
            # Send email to second approver for dual verification
            mail = current_app.extensions.get('mail')
            msg = Message(
                subject="Transaction Approval Required",
                recipients=[second_email],  # Send to second email
                body=f"Hello,\n\nYou need to approve a transaction of {amount} EUR. Please confirm your approval.\n\nThanks!",
                sender=current_app.config['MAIL_DEFAULT_SENDER']  # Sender is defined in app.py
            )
            mail.send(msg)

            return jsonify({"success": True, "message": f"Email sent to {second_email} for approval"}), 200

        except Exception as e:
            return jsonify({"error": f"Failed to send email. Error: {str(e)}"}), 500

    else:
        # Single MFA verification successful
        transaction_data['status'] = "Completed"
        add_transaction_to_history(transaction_data)
        send_to_orbiscloud(transaction_data)
        return jsonify({"success": True, "message": "Payment authorized with single MFA"}), 200


@api.route('/transaction', methods=['POST'])
def receive_transaction():
    """
    Endpoint to receive transactions from OrbisCloud, decode and save them.
    """
    data = request.get_json()

    # Check if encrypted data is in the request
    if not data or "encrypted_data" not in data:
        return jsonify({"error": "No encrypted transaction data received"}), 400

    try:
        # Decode and parse the transaction data
        decoded_data = base64.b64decode(data["encrypted_data"]).decode("utf-8")
        transaction_data = json.loads(decoded_data)

        # Add transaction to history
        add_transaction_to_history(transaction_data)

        logging.info(f"Received transaction from OrbisCloud: {transaction_data}")
        return jsonify({"status": "Transaction received and added to history"}), 200

    except (json.JSONDecodeError, base64.binascii.Error) as e:
        logging.error(f"Failed to decode or parse transaction data: {str(e)}")
        return jsonify({"error": f"Failed to decode transaction data: {str(e)}"}), 400
    except Exception as e:
        logging.error(f"Error adding transaction to history: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500



# Transaction history route
@api.route('/transaction-history', methods=['GET'])
def transaction_history():
    if 'username' not in session:
        return redirect(url_for('api.index'))
    page = request.args.get('page', 1, type=int)
    transactions_query = Transaction.query.order_by(Transaction.date.desc(), Transaction.time.desc())
    transactions_paginated = transactions_query.paginate(page=page, per_page=12, error_out=False)
    transactions = transactions_paginated.items
    return render_template('transaction-history.html', transactions=transactions, page=page)



@api.route('/payment-successful', methods=['GET'])
def payment_success():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('api.index'))  # If not logged in, redirect to login

    return render_template('payment-successful.html')

@api.route('/payment-unsuccessful', methods=['GET'])
def payment_unsuccess():
    return render_template('payment-unsuccessful.html')

# Logout route
@api.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the entire session for security
    return redirect(url_for('api.index'))  # Redirect the user to the login page after logout
