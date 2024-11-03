from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, current_app  # Add current_app import
from backend.database import User, Transaction, db, generate_next_transaction_id, load_transactions_from_yaml, save_transactions_to_yaml, add_transaction_to_history  # Add the function import
from datetime import datetime
import threading
import time
from flask_mail import Message
import logging
import base64
import json
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import request


from flask import current_app

orbis_endpoint = os.getenv('ORBIS')

# Set up logging to print to the console at DEBUG level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Create a blueprint for the routes
api = Blueprint('api', __name__)

# Home route (login page)
@api.route('/')
def index():
    return render_template('login.html')


@api.route('/send-test-email', methods=['GET'])
def send_test_email():
    smtp_server = "smtp.mailgun.org"
    port = 587  # Try 465 for SSL if needed
    login = current_app.config['MAIL_USERNAME']
    password = current_app.config['MAIL_PASSWORD']
    to_address = "a.zelenajova@gmail.com"
    subject = "Test Email from Flask"
    body = "This is a test email from Flask using smtplib directly."

    # Set up the message
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    server = None
    try:
        current_app.logger.info(f"Attempting to send email to: {to_address}")
        
        # Initialize the server connection
        server = smtplib.SMTP(smtp_server, port)
        
        # Start TLS
        response = server.starttls()
        current_app.logger.info(f"TLS response: {response}")

        # Attempt login
        response = server.login(login, password)
        current_app.logger.info(f"Login response: {response}")
        
        # Send the email
        server.sendmail(login, to_address, msg.as_string())
        current_app.logger.info(f"Email sent successfully to: {to_address}")
        
        return f"Test email sent successfully to {to_address}!"
    
    except smtplib.SMTPServerDisconnected as e:
        current_app.logger.error(f"SMTP server disconnected unexpectedly. Error: {e}")
        return "SMTP server disconnected unexpectedly. Please check your connection and settings.", 500
    

    
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
        response = requests.post(orbiscloud_url, json={"encrypted_data": encrypted_data}, verify=False)
        
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
    second_username = data.get('secondUsername')
    amount = data.get('amount')
    iban = data.get('iban')
    account_name = data.get('account_name')
    currency = data.get('currency')
    transaction_type = data.get('type')
    description = data.get('description')
    location = data.get('location')

    # Ensure all required fields are provided
    required_fields = [mfa_token, second_username, amount, iban, account_name, currency, transaction_type, description]
    if not all(required_fields):
        return jsonify({"error": "All fields are required for dual MFA."}), 400

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

    # Create transaction data as a dictionary
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
        'location': location,
        'second_user': second_user.username
    }

    # Add the transaction to history
    add_transaction_to_history(transaction_data)

    # Send the approval link to the second user
    approval_link = url_for('api.login_dual_mfa', transaction_id=transaction_id, _external=True)
    try:
        logging.info("Attempting to send email...")
        mail = current_app.extensions.get('mail')

        # Create the email message
        msg = Message(
            subject="Transaction Approval Needed",
            recipients=[second_user.email],
            body=f"Hello {second_user.username},\n\nYou need to approve the transaction {transaction_id} for {currency} {amount}.\n\nPlease click the link below to approve:\n\n{approval_link}\n\nThanks!",
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )

        # Send the email
        mail.send(msg)
        logging.info(f"Email sent to {second_user.email}.")

        return jsonify({"success": True, "message": f"Email sent to {second_user.username} for approval", "transaction_id": transaction_id}), 200
    except Exception as e:
        logging.error(f"Failed to send email. Error: {str(e)}")
        return jsonify({"error": f"Failed to send email. Error: {str(e)}"}), 500






from flask import flash, session  # Import necessary modules

@api.route('/login-dual-mfa/<transaction_id>', methods=['GET', 'POST'])
def login_dual_mfa(transaction_id):
    logging.info(f"Entering login_dual_mfa with transaction_id: {transaction_id}")

    # Retrieve the transaction from the database
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()

    # Check if the transaction exists and if the link has already been used
    if not transaction:
        logging.error(f"Transaction {transaction_id} not found.")
        return "Transaction not found", 404
    elif transaction.link_used:
        logging.warning(f"Transaction {transaction_id} link has already been used.")
        return "This approval link has already been used and is now inactive.", 403

    if request.method == 'GET':
        # Render the login page for second user's dual MFA verification
        return render_template('login-dual-mfa.html', transaction_id=transaction_id)

    if request.method == 'POST':
        # Capture login form details
        username = request.form.get('username')
        password = request.form.get('password')
        mfa_token = request.form.get('mfaToken')

        # Look up second user in the database
        second_user = User.query.filter_by(username=username).first()

        # Confirm credentials and log
        if not second_user or second_user.password != password or str(second_user.mfa) != str(mfa_token):
            flash("Invalid credentials. Please try again.")
            logging.warning(f"Invalid login attempt for user: {username} in dual MFA.")
            return render_template('login-dual-mfa.html', transaction_id=transaction_id)

        # Mark the link as used
        transaction.link_used = True
        db.session.commit()

        # Set session data for dual MFA and log the designated user
        session['dual_mfa_user'] = username
        logging.info(f"Dual MFA login successful. Session set for user: {session['dual_mfa_user']}")
        return redirect(url_for('api.confirm_dual_mfa', transaction_id=transaction_id))


@api.route('/confirm-dual-mfa/<transaction_id>', methods=['GET', 'POST'])
def confirm_dual_mfa(transaction_id):
    logging.info(f"Entered confirm_dual_mfa route with transaction_id: {transaction_id}")

    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        logging.error(f"Transaction {transaction_id} not found")
        return "Transaction not found", 404

    # Check if session has the correct dual MFA user
    if 'dual_mfa_user' not in session:
        logging.warning("Session is empty or expired. Redirecting to dual MFA login.")
        flash("Session expired. Please log in to approve the transaction.")
        return redirect(url_for('api.login_dual_mfa', transaction_id=transaction_id))

    # Verify that the logged-in user is the designated second user
    if session['dual_mfa_user'] != transaction.second_user:
        flash("Unauthorized access. You are not the designated approver for this transaction.")
        logging.warning("Unauthorized access attempt for dual MFA confirmation.")
        return redirect(url_for('api.payment_unsuccess'))

    if request.method == 'GET':
        logging.info("Rendering confirmation page for dual MFA.")
        return render_template('confirm-dual-mfa.html', transaction=transaction)

    # Handle POST request for approval
    if request.method == 'POST':
        transaction.status = 'Completed'
        db.session.commit()

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
            'location': transaction.location,
            'second_user': transaction.second_user
        }
        send_to_orbiscloud(transaction_data)
        flash("Transaction successfully confirmed and sent.")
        return redirect(url_for('api.payment_success'))






# Verify payment and handle MFA
@api.route('/verify-payment-mfa', methods=['POST'])
def verify_payment_mfa():
    data = request.json
    print("Received data for payment MFA verification:", data)  # Debugging statement
    second_email = data.get('secondEmail', None)  # Second email for dual MFA only
    mfa_token = data.get('mfaToken')
    amount = data.get('amount')
    iban = data.get('iban')
    account_name = data.get('account_name')
    currency = data.get('currency')
    transaction_type = data.get('type')
    description = data.get('description')
    location = data.get('location')

    # Transaction data object for single MFA
    transaction_data = {
        'amount': amount,
        'currency': currency,
        'type': transaction_type,
        'account_name': account_name,
        'account_number': iban,
        'description': description,
        'location': location,
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



# Transaction history route with enhanced filtering and sorting logic
@api.route('/transaction-history', methods=['GET'])
def transaction_history():
    if 'username' not in session:
        return redirect(url_for('api.index'))
    
    # Pagination and sorting parameters
    page = request.args.get('page', 1, type=int)
    amount_sort = request.args.get('amount_sort', 'desc')  # Default amount sorting order is descending

    # Filtering parameters from request arguments
    filter_id = request.args.get('filter_id', '').strip()
    filter_date = request.args.get('filter_date', '').strip()
    filter_status = request.args.get('filter_status', '').strip()
    filter_amount_from = request.args.get('filter_amount_from', None, type=float)
    filter_amount_to = request.args.get('filter_amount_to', 1000000000.0, type=float)
    filter_account_name = request.args.get('filter_account_name', '').strip()
    filter_account_number = request.args.get('filter_account_number', '').strip()
    
    # Start the base query for transactions
    transactions_query = Transaction.query

    # Apply filters to the query
    if filter_id:
        transactions_query = transactions_query.filter(Transaction.transaction_id.ilike(f"%{filter_id}%"))
    if filter_date:
        transactions_query = transactions_query.filter(Transaction.date == filter_date)
    if filter_status:
        transactions_query = transactions_query.filter(Transaction.status.ilike(f"%{filter_status}%"))
    if filter_amount_from is not None:
        transactions_query = transactions_query.filter(Transaction.amount >= filter_amount_from)
    if filter_amount_to:
        transactions_query = transactions_query.filter(Transaction.amount <= filter_amount_to)
    if filter_account_name:
        transactions_query = transactions_query.filter(Transaction.account_name.ilike(f"%{filter_account_name}%"))
    if filter_account_number:
        transactions_query = transactions_query.filter(Transaction.account_number.ilike(f"%{filter_account_number}%"))

    # Sorting logic based on amount_sort
    if amount_sort == 'asc':
        transactions_query = transactions_query.order_by(Transaction.amount.asc())
    elif amount_sort == 'desc':
        transactions_query = transactions_query.order_by(Transaction.amount.desc())
    else:
        # Default to sorting by date and time in descending order if no amount sorting is applied
        transactions_query = transactions_query.order_by(Transaction.date.desc(), Transaction.time.desc())

    # Paginate the results
    transactions_paginated = transactions_query.paginate(page=page, per_page=12, error_out=False)
    transactions = transactions_paginated.items
    
    # Pass filters and sorting to the template to keep them persistent
    filters = {
        'filter_id': filter_id,
        'filter_date': filter_date,
        'filter_status': filter_status,
        'filter_amount_from': '' if filter_amount_from is None else filter_amount_from,
        'filter_amount_to': '' if filter_amount_to == 1000000000.0 else filter_amount_to,
        'filter_account_name': filter_account_name,
        'filter_account_number': filter_account_number,
        'amount_sort': amount_sort
    }
    
    # Render the transaction history page with pagination, filters, and sorting
    return render_template('transaction-history.html', 
                           transactions=transactions, 
                           page=page, 
                           total_pages=transactions_paginated.pages,
                           filters=filters)





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
