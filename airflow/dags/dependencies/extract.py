import pandas as pd
import os

# Define paths
AIRFLOW_HOME = os.getenv('AIRFLOW_HOME')
RAWDATA_PATH = AIRFLOW_HOME + '/raw_data'

# Define functions for each step of the ETL process
def load_and_clean_product():
    product = pd.read_csv(f'{RAWDATA_PATH}/product_catalog[1].csv')
    product.dropna(axis=0, inplace=True)
    product['price'] = pd.to_numeric(product['price'], errors='coerce')
    product.dropna(subset=['price'], inplace=True)
    product = product[product['price'] >= 0]
    product.drop_duplicates(inplace=True)
    return product
def load_and_clean_transaction():
    transaction = pd.read_json(f'{RAWDATA_PATH}/customer_transactions[3].json')
    transaction.dropna(axis=0, inplace=True)
    transaction['quantity'] = pd.to_numeric(transaction['quantity'], errors='coerce').astype('int64')
    transaction['price'] = pd.to_numeric(transaction['price'], errors='coerce').astype('float64')
    transaction['timestamp'] = pd.to_datetime(transaction['timestamp'], errors='coerce').astype('datetime64[ns]')
    transaction.dropna(subset=['price'], inplace=True)
    transaction = transaction[transaction['price'] >= 0]
    transaction.drop_duplicates(inplace=True)
    for col in ['transaction_id', 'customer_id', 'product_id']:
        transaction[col] = transaction[col].astype('str')
    return transaction
  
