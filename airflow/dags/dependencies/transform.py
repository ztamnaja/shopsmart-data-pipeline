import pandas as pd

def merge_data(**kwargs):
    ti = kwargs['ti']
    product = ti.xcom_pull(task_ids='etl_process.load_and_clean_product')
    transaction = ti.xcom_pull(task_ids='etl_process.load_and_clean_transaction')
    
    if product is None:
        raise ValueError("Product data is None. Check the 'load_and_clean_product' task.")
    if transaction is None:
        raise ValueError("Transaction data is None. Check the 'load_and_clean_transaction' task.")
    
    if not isinstance(product, pd.DataFrame):
        product = pd.read_json(product)
    if not isinstance(transaction, pd.DataFrame):
        transaction = pd.read_json(transaction)
    
    print("Product DataFrame:")
    print(product.head())
    print("\nTransaction DataFrame:")
    print(transaction.head())
    merged_df = pd.merge(transaction, product, on='product_id', how='inner', suffixes=('', '_right'))
    merged_df.drop(columns=['price_right'], inplace=True) # Keep the price column in the transaction because it reflects the price when the customer placed the order. 
    return merged_df
  
  
