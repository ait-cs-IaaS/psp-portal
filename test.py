# Email Configuration using environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')  # Update with correct SMTP server
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')  # Using port 587 for TLS
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False') == 'True'  # Enable TLS
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True' # Do not use SSL, as TLS is enabled
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Get mail username from .env
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Get mail password from .env
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')  # Get sender address from .env
