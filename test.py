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


def add_transaction_to_history(transaction_data):
    transaction_id = generate_next_transaction_id()
    transaction_data['transaction_id'] = transaction_id

    logging.info(f"Adding transaction with ID: {transaction_id}")

    # Add the transaction to the database
    new_transaction = Transaction(
        transaction_id=transaction_data['transaction_id'],
        date=transaction_data['date'],
        time=transaction_data['time'],
        amount=transaction_data['amount'],
        currency=transaction_data['currency'],
        type=transaction_data['type'],
        status=transaction_data['status'],
        account_name=transaction_data['account_name'],
        account_number=transaction_data['account_number'],
        description=transaction_data['description'],
        location=transaction_data['location']
    )
    db.session.add(new_transaction)
    db.session.commit()

    # Load the current transactions from YAML and append the new transaction
    transactions = load_transactions_from_yaml()
    
    # Ensure no duplicates are being appended
    existing_transaction_ids = {txn['transaction_id'] for txn in transactions}
    
    if transaction_id not in existing_transaction_ids:
        transactions.append({
            'transaction_id': transaction_data['transaction_id'],
            'date': transaction_data['date'],
            'time': transaction_data['time'],
            'amount': transaction_data['amount'],
            'currency': transaction_data['currency'],
            'type': transaction_data['type'],
            'status': transaction_data['status'],
            'account': {
                'account_number': transaction_data['account_number'],
                'name': transaction_data['account_name']
            },
            'description': transaction_data['description'],
            'location': transaction_data['location']
        })
        logging.info(f"Transaction with ID {transaction_id} appended to transaction list.")
        logging.info(f"Number of transactions to be saved: {len(transactions)}")
        
        # Save the updated transactions back to the YAML file
        save_transactions_to_yaml(transactions)

        logging.info(f"Transaction {transaction_id} added to history with status: {transaction_data['status']}")
    else:
        logging.info(f"Transaction {transaction_id} already exists in YAML. Skipping addition.")