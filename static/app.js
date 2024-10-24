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

// Reset payment MFA attempts when the user navigates to the payment page
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
            mfaAttemptsPayment = 0;
            sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);

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

    // Reset MFA attempt counter before every new submission
    mfaAttemptsPayment = 0;
    sessionStorage.setItem('mfaAttemptsPayment', mfaAttemptsPayment);

    // Send request to backend to verify single MFA token
    fetch('/verify-payment-mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            amount: amount,
            mfaToken: mfaToken,
            currency: "EUR",
            type: "debit",
            accountName: document.getElementById('name').value,
            iban: document.getElementById('iban').value,
            description: document.getElementById('description').value,
            location: document.getElementById('location').value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mfaMessage.style.color = 'green';
            mfaMessage.textContent = 'Payment successful! Redirecting...';
            setTimeout(() => {
                window.location.href = '/payment-successful';
            }, 1000);
        } else {
            mfaMessage.textContent = 'Invalid MFA token. Payment not authorized.';
            setTimeout(() => {
                window.location.href = '/payment-unsuccessful';
            }, 1000);
        }
    })
    .catch(error => {
        console.error('Error during single MFA verification:', error);
        mfaMessage.textContent = 'An error occurred during MFA verification. Please try again.';
    });
}

function verifyDualMFA() {
    const mfaToken1Element = document.getElementById('mfa-token1');
    const secondUsernameElement = document.getElementById('second-username');

    if (!mfaToken1Element || !secondUsernameElement) {
        console.error('MFA token or second email field is missing. Ensure the dual MFA fields are displayed.');
        document.getElementById('mfa-message').textContent = 'MFA token and second email fields are missing.';
        return;
    }

    const mfaToken1 = mfaToken1Element.value;
    const secondUsername = secondUsernameElement.value;
    const amount = parseFloat(document.getElementById('sum').value);

    // Add detailed logging for troubleshooting
    console.log('MFA Token 1:', mfaToken1);
    console.log('Second Username (Email):', secondUsername);
    console.log('Amount:', amount);

    if (!mfaToken1 || !secondUsername) {
        document.getElementById('mfa-message').textContent = 'All fields must be filled out for dual MFA.';
        return;
    }

    fetch('/verify-dual-mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            amount: amount,
            mfaToken: mfaToken1,
            secondEmail: secondUsername  // Use the second email (from the second username field)
        })
    })
    .then(response => {
        console.log('Response status:', response.status);  // Log the status code
        return response.json();  // Check if the response is valid JSON
    })
    .then(data => {
        console.log('Response data:', data);  // Log the response data for debugging
        if (data.success) {
            document.getElementById('mfa-message').textContent = 'Email sent for approval!';
            console.log(`Email sent to ${secondUsername} for transaction approval.`);  // Log email sent
        } else {
            document.getElementById('mfa-message').textContent = 'Invalid MFA token or second email. Payment not authorized.';
            console.log('Error message:', data.error);  // Log the error message from the backend
            setTimeout(() => {
                window.location.href = '/payment-unsuccessful';
            }, 1000);
        }
    })
    .catch(error => {
        document.getElementById('mfa-message').textContent = 'An error occurred. Please try again.';
        console.error('Error during dual MFA verification:', error);  // Log any errors in the request
    });
    
}




// Function to process the payment and show MFA fields based on the payment sum
function processPayment() {
    const sum = parseFloat(document.getElementById('sum').value);
    const paymentMessage = document.getElementById('payment-message');
    if (isNaN(sum) || sum <= 0) {
        paymentMessage.textContent = 'Please enter a valid payment amount.';
        return;
    }
    paymentMessage.textContent = ''; // Clear any previous messages

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
