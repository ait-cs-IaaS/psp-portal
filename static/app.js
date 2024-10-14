let mfaAttemptsLogin = 0;  // To track login-related MFA attempts
let mfaAttemptsPayment = 0; // To track payment-related MFA attempts
const maxAttemptsPayment = 1; // Maximum allowed payment-related attempts
const maxAttemptsLogin = 3;   // Maximum allowed login-related attempts

// Handle login and trigger MFA if required
function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const loginMessage = document.getElementById('login-message');

    // Clear previous messages
    loginMessage.textContent = '';

    // Send login request
    fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.mfa_required) {
            // If MFA is required, show the MFA token input
            document.getElementById('mfa-token-container').style.display = 'block';
            document.getElementById('login-btn').style.display = 'none'; // Hide login button
            loginMessage.textContent = 'Please enter your MFA token.';
        } else {
            loginMessage.textContent = data.error || 'Login failed. Please try again.';
        }
    })
    .catch(error => {
        loginMessage.textContent = 'An error occurred. Please try again.';
        console.error('Error during login request:', error);
    });
}

// Send a POST request to the correct failed authorization endpoint
function sendFailedAuthorization(endpoint) {
    fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '403: MFA verification failed' })
    }).then(response => {
        if (!response.ok) {
            console.error('Failed to send failed-authorization request.');
        }
    }).catch(error => {
        console.error('Error sending failed-authorization request:', error);
    });
}



// Handle MFA token verification after login
function verifyMFA() {
    const mfaToken = document.getElementById('mfa-token').value;
    const mfaMessage = document.getElementById('mfa-message');
    const loginMessage = document.getElementById('login-message');

    // Clear previous messages
    mfaMessage.textContent = '';

    // Send MFA token for verification
    fetch('/verify-login-mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mfaToken })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mfaMessage.style.color = 'green';
            mfaMessage.textContent = 'Login successful! Redirecting to payment portal...';
            setTimeout(() => {
                window.location.href = '/payment-page'; // Redirect to payment portal after successful MFA
            }, 1000);
        } else {
            mfaAttemptsLogin += 1;
            const remainingAttempts = maxAttemptsLogin - mfaAttemptsLogin;
            mfaMessage.textContent = `Invalid MFA token. You have ${remainingAttempts} remaining attempt(s).`;

            // Log out the user after max attempts and send failed authorization
            if (mfaAttemptsLogin >= maxAttemptsLogin) {
                sendFailedAuthorization('/login-unsuccessful'); // Send request for failed authorization
                logout();
            }
        }
    })
    .catch(error => {
        mfaMessage.textContent = 'An error occurred during MFA verification. Please try again.';
        console.error('Error during MFA verification:', error);
    });
}


// Hide MFA fields and reset payment MFA attempts when MFA fails for payments
function handleFailedPaymentMFA() {
    // Hide both payment MFA token input containers
    document.getElementById('mfa-container').style.display = 'none';
    document.getElementById('dual-mfa-container').style.display = 'none';

    // Reset payment-related MFA attempts
    mfaAttemptsPayment = 0;
}

// Hide MFA fields and reset attempts when MFA fails
function handleFailedMFA() {
    // Hide both MFA token input containers
    document.getElementById('mfa-container').style.display = 'none';
    document.getElementById('dual-mfa-container').style.display = 'none';

    // Reset MFA attempts
    mfaAttemptsPayment = 0;
}


// Mock function to simulate data encryption (just for visual representation)
function mockEncrypt(data) {
    return btoa(JSON.stringify(data)); // Base64 encoding to simulate "encryption"
}

// Verify single MFA token for payments less than 50,000
function verifySingleMFA() {
    const mfaToken = document.getElementById('mfa-token').value;

    if (mfaAttemptsPayment >= maxAttemptsPayment) {
        document.getElementById('mfa-message').textContent = 'MFA has already been attempted.';
        return;
    }

    // Check if the token is correct (e.g., 123 for single MFA)
    if (mfaToken === '123') {
        // If MFA is successful, proceed with authorization
        fetch('/authorization-successful', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }).then(() => {
            window.location.href = '/payment-successful';  // Redirect to success page
        });
    } else {
        // Increment payment attempts and handle failed MFA
        mfaAttemptsPayment += 1;
        document.getElementById('mfa-message').textContent = 'Invalid MFA token. MFA cannot be attempted again.';
        
        // Send failed authorization request for single MFA and handle failure
        sendFailedAuthorization('/single-authorization-failed');
        handleFailedPaymentMFA();  // Hide MFA fields and reset attempts
    }
}

// Verify dual MFA tokens for payments 50,000 or more
function verifyDualMFA() {
    const mfaToken1 = document.getElementById('mfa-token1').value;
    const mfaToken2 = document.getElementById('mfa-token2').value;

    if (mfaAttemptsPayment >= maxAttemptsPayment) {
        document.getElementById('mfa-message').textContent = 'MFA has already been attempted.';
        return;
    }

    // Check if both tokens are correct (e.g., 123 and 456 for dual MFA)
    if (mfaToken1 === '123' && mfaToken2 === '456') {
        // If MFA is successful, proceed with dual authorization
        fetch('/dual-authorization-successful', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }).then(() => {
            window.location.href = '/payment-successful';  // Redirect to success page
        });
    } else {
        // Increment payment attempts and handle failed MFA
        mfaAttemptsPayment += 1;
        document.getElementById('mfa-message').textContent = 'Invalid MFA tokens. MFA cannot be attempted again.';
        
        // Send failed authorization request for dual MFA and handle failure
        sendFailedAuthorization('/dual-authorization-failed');
        handleFailedPaymentMFA();  // Hide MFA fields and reset attempts
    }
}

// Process the payment and display appropriate MFA fields based on payment amount
function processPayment() {
    const sum = parseFloat(document.getElementById('sum').value);
    const paymentMessage = document.getElementById('payment-message');

    // Clear previous MFA error message
    document.getElementById('mfa-message').textContent = '';

    if (isNaN(sum) || sum <= 0) {
        paymentMessage.textContent = 'Please enter a valid payment amount.';
        return;
    }

    paymentMessage.textContent = ''; // Clear previous messages

    // If payment sum is less than 50,000, show single MFA field
    if (sum < 50000) {
        document.getElementById('mfa-container').style.display = 'block';
        document.getElementById('dual-mfa-container').style.display = 'none';
    } else {
        // Show dual MFA fields if payment sum is 50,000 or more
        document.getElementById('dual-mfa-container').style.display = 'block';
        document.getElementById('mfa-container').style.display = 'none';
    }
}


// Handle user logout
function logout() {
    fetch('/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    }).then(() => {
        window.location.href = '/'; // Redirect to home page
    });
}
