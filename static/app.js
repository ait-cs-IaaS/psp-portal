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

// Function to handle single MFA verification
function verifySingleMFA() {
    const mfaToken = document.getElementById('mfa-token').value;
    const amount = parseFloat(document.getElementById('sum').value);
    const mfaMessage = document.getElementById('mfa-message');

    if (!mfaToken) {
        mfaMessage.textContent = "Please enter your MFA token.";
        return;
    }

    // Send request to backend to verify single MFA token
    fetch('/verify-payment-mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            amount: amount,
            mfaToken: mfaToken,
            currency: "EUR",
            type: document.getElementById('transaction-type').value,
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

// Function to handle dual MFA verification
function verifyDualMFA() {
    const mfaToken1 = document.getElementById('mfa-token1').value;
    const secondUsername = document.getElementById('second-username').value;
    const amount = parseFloat(document.getElementById('sum').value);
    const iban = document.getElementById('iban').value.trim();
    const accountName = document.getElementById('name').value.trim();
    const currency = document.getElementById('currency').value.trim();
    const type = document.getElementById('transaction-type').value.trim();
    const description = document.getElementById('description').value.trim();
    const location = document.getElementById('location').value.trim();
    const mfaMessage = document.getElementById('mfa-message');

    if (!mfaToken1 || !secondUsername) {
        mfaMessage.textContent = 'MFA token and second employee username are required.';
        return;
    }

    // Send the form data to the backend for dual MFA processing
    fetch('/verify-dual-mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            amount: amount,
            mfaToken: mfaToken1,
            secondUsername: secondUsername,
            iban: iban,
            accountName: accountName,
            currency: currency,
            type: type,
            description: description,
            location: location
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mfaMessage.textContent = 'Email sent for approval!';
        } else {
            mfaMessage.textContent = data.error || 'Transaction not authorized.';
            setTimeout(() => {
                window.location.href = '/payment-unsuccessful';
            }, 1000);
        }
    })
    .catch(error => {
        mfaMessage.textContent = 'An error occurred during MFA verification. Please try again.';
        console.error('Error during dual MFA verification:', error);
    });
}



/// Function to process the payment and show MFA fields based on the payment sum
function processPayment() {
    const iban = document.getElementById('iban').value.trim();
    const accountName = document.getElementById('name').value.trim();
    const sum = parseFloat(document.getElementById('sum').value);
    const currency = document.getElementById('currency').value.trim();
    const type = document.getElementById('transaction-type').value.trim();
    const description = document.getElementById('description').value.trim();
    const location = document.getElementById('location').value.trim();
    const errorMessage = document.getElementById('error-message');

    // Validate the form inputs
    if (!iban || !accountName || isNaN(sum) || sum <= 0 || !currency || !type || !description || !location) {
        errorMessage.style.display = 'block'; // Show error message
        return;
    } else {
        errorMessage.style.display = 'none'; // Hide error message
    }

    // Show appropriate MFA form based on the amount
    if (sum < 50000) {
        document.getElementById('mfa-container').style.display = 'block'; // Show single MFA
        document.getElementById('dual-mfa-container').style.display = 'none'; // Hide dual MFA
    } else {
        document.getElementById('dual-mfa-container').style.display = 'block'; // Show dual MFA
        document.getElementById('mfa-container').style.display = 'none'; // Hide single MFA
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



// Handle MFA token verification on transaction approval page
document.addEventListener("DOMContentLoaded", function () {
    const mfaForm = document.querySelector("form"); // Assuming the MFA form exists on the transaction approval page

    if (mfaForm) {  // Only apply this logic on the transaction approval page
        mfaForm.addEventListener("submit", function (event) {
            const mfaTokenInput = document.querySelector("input[name='mfaToken']");

            // Ensure the MFA token is entered and is a number
            if (!mfaTokenInput.value || isNaN(mfaTokenInput.value)) {
                event.preventDefault(); // Prevent form submission
                alert("Please enter a valid MFA token.");
            }
        });
    }
});
