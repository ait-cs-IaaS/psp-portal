let mfaAttemptsLogin = 0;  // To track login-related MFA attempts
let mfaAttemptsPayment = sessionStorage.getItem('mfaAttemptsPayment') ? parseInt(sessionStorage.getItem('mfaAttemptsPayment')) : 0;
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

// Reset payment MFA attempts when the user navigates to the payment page (optional)
// Optionally, do not reset here if you want to persist attempts across navigation
// You can reset in the successful payment or logout function instead
function loadPaymentPage() {
    mfaAttemptsPayment = 0;
    sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);  // Reset in sessionStorage
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

            // Reset payment MFA attempts after successful login
            mfaAttemptsPayment = 0;  // Reset payment-related MFA attempts here
            sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);  // Reset in sessionStorage

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

// Verify single MFA token for payments less than 50,000
function verifySingleMFA() {
    const mfaToken = document.getElementById('mfa-token').value;
    const amount = parseFloat(document.getElementById('sum').value);
    const mfaMessage = document.getElementById('mfa-message');

    // Each time user clicks "Submit Payment", reset the MFA attempt counter to allow a fresh start
    mfaAttemptsPayment = 0;
    sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);  // Reset in sessionStorage

    // Log the current number of payment MFA attempts
    console.log("MFA attempts for payment (reset to 0): " + mfaAttemptsPayment);

    if (mfaAttemptsPayment >= maxAttemptsPayment) {
        // Prevent further MFA attempts if the limit is reached
        mfaMessage.textContent = 'MFA has already been attempted.';
        return;
    }

    // Send request to backend to verify single MFA token
    fetch('/verify-payment-mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            amount: amount,
            mfaToken: mfaToken,  // Use the same MFA token as for login
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reset payment MFA attempts after successful payment
            mfaAttemptsPayment = 0;
            sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);  // Store in sessionStorage

            mfaMessage.style.color = 'green';
            mfaMessage.textContent = 'Payment successful! Redirecting...';

            // Redirect to the success page after 1 second
            setTimeout(() => {
                window.location.href = '/payment-successful';  // Redirect to success page
            }, 1000);
        } else {
            mfaAttemptsPayment += 1;  // Increment the number of attempts
            sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);  // Store in sessionStorage
            mfaMessage.textContent = 'Invalid MFA token. Payment not authorized.';
            sendFailedAuthorization('/single-authorization-failed');
        }
    })
    .catch(error => {
        console.error('Error during single MFA verification:', error);
        mfaMessage.textContent = 'An error occurred during MFA verification. Please try again.';
    });
}

// Verify dual MFA tokens for payments 50,000 or more
function verifyDualMFA() {
    const mfaToken1 = document.getElementById('mfa-token1').value;  // Logged-in user's MFA
    const mfaToken2 = document.getElementById('mfa-token2').value;  // Second user's MFA
    const amount = parseFloat(document.getElementById('sum').value);
    const secondUsername = prompt("Enter the username of the second user for dual MFA");

    if (mfaAttemptsPayment >= maxAttemptsPayment) {
        document.getElementById('mfa-message').textContent = 'MFA has already been attempted.';
        return;
    }

    // Send request to backend to verify dual MFA tokens
    fetch('/verify-payment-mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            amount: amount,
            mfaToken: mfaToken1,           // Logged-in user's MFA
            secondUsername: secondUsername, // Second username
            secondMfaToken: mfaToken2,      // Second user's MFA
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reset payment MFA attempts after successful payment
            mfaAttemptsPayment = 0;
            sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);  // Store in sessionStorage

            window.location.href = '/payment-successful';  // Redirect to success page
        } else {
            mfaAttemptsPayment += 1;
            sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);  // Store in sessionStorage
            document.getElementById('mfa-message').textContent = 'Invalid MFA tokens. Payment not authorized.';
            sendFailedAuthorization('/dual-authorization-failed');
            handleFailedPaymentMFA();  // Hide MFA fields and reset attempts
        }
    })
    .catch(error => {
        document.getElementById('mfa-message').textContent = 'An error occurred. Please try again.';
        console.error('Error during dual MFA verification:', error);
    });
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
        // Reset MFA attempts after logout
        mfaAttemptsPayment = 0;
        sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);  // Store in sessionStorage
        window.location.href = '/'; // Redirect to home page
    });
}
