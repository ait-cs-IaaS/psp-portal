from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from backend.database import User
from backend.database import Transaction

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
        session['username'] = username
        session['mfa_required'] = True  # Indicate MFA is required
        print(f"Login successful for user: {username}, prompting for MFA.")
        return jsonify({"mfa_required": True, "message": "MFA required. Please enter your MFA token."}), 200
    else:
        # Log failed login attempt
        print(f"Login failed for user: {username}")
        return jsonify({"error": "Invalid username or password"}), 401

# MFA verification route
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

# Successful payment route
@api.route('/payment-successful', methods=['GET'])
def payment_success():
    # Check if the user is logged in
    if 'username' not in session:
        # If the user is not logged in, redirect to the login page
        return redirect(url_for('api.index'))

    # Render the successful payment page without any additional messages
    return render_template('payment-successful.html')




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



# Logout route
@api.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the entire session for security
    return redirect(url_for('api.index'))  # Redirect the user to the login page after logout