from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, current_app  # Add current_app import
from backend.database import User, Transaction, db, load_transactions_from_yaml, save_transactions_to_yaml, add_transaction_to_history  # Add the function import
from datetime import datetime
import random
from flask_mail import Message
import logging



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


@api.route('/verify-dual-mfa', methods=['POST'])
def verify_dual_mfa():
    data = request.json
    mfa_token = data.get('mfaToken')
    second_email = data.get('secondEmail')  # Use second email (from "second username" field)
    amount = data.get('amount')

    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session['username']
    user = User.query.filter_by(username=username).first()

    if not user or str(user.mfa) != str(mfa_token):
        return jsonify({"error": "Invalid MFA token for the logged-in user"}), 401

    # If the MFA is valid, send an email to the second user
    try:
        logging.info("Trying to send email...")
        mail = current_app.extensions.get('mail')

        # Create the message
        msg = Message(
            subject="Transaction Approval Needed",
            recipients=[second_email],
            body=f"Hello,\n\nPlease approve the transaction for {amount} EUR.\n\nThanks!",
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )

        # Send the email
        mail.send(msg)

        logging.info(f"Email successfully sent to {second_email}.")  # Log success
        return jsonify({"success": True, "message": f"Email sent to {second_email} for approval"}), 200
    except Exception as e:
        logging.error(f"Failed to send email. Error: {str(e)}")  # Log the error message
        return jsonify({"error": f"Failed to send email. Error: {str(e)}"}), 500


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
        return jsonify({"success": True, "message": "Payment authorized with single MFA"}), 200




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
