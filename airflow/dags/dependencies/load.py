import psycopg2
import os
from io import StringIO 
import boto3
from datetime import date
import pandas as pd
from airflow.hooks.base_hook import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook

def r2_connect():
    conn = BaseHook.get_connection('r2_backup_lake_conn')
    accountid = conn.extra_dejson.get('accountid')
    access_key_id = conn.login
    access_key_secret = conn.password

    return boto3.resource('s3',  
                        endpoint_url = f'https://{accountid}.r2.cloudflarestorage.com',  
                        aws_access_key_id = access_key_id,  
                        aws_secret_access_key = access_key_secret,
                        region_name='auto'
    )
    
def pg_connect():
  """ Connect to the PostgreSQL database server """
  conn = None
  try:
    pg_hook = PostgresHook(
      postgres_conn_id='destination_db_conn',
      schema='shopsmart'
    )
    conn = pg_hook.get_conn()
    return conn
  except (Exception, psycopg2.DatabaseError) as error:
    print(error)

def upload_to_r2(r2, df, table_name,  bucketname):
    today = date.today()
    datestr = today.strftime("%m-%d-%y")
    filename = f"{table_name}/{datestr}-{table_name}.csv"
    
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    print(bucketname, filename)
    resp = r2.Object(bucketname, filename).put(Body=csv_buffer.getvalue())
    if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception(f"Cannot save {filename} to R2")
    
    print(f"Successfully uploaded {filename} to R2")

def load_r2_data(**kwargs):
    ti = kwargs['ti']
    
    # Pull data from previous tasks
    products = ti.xcom_pull(task_ids='etl_process.load_and_clean_product')
    transactions = ti.xcom_pull(task_ids='etl_process.load_and_clean_transaction')
    sales = ti.xcom_pull(task_ids='etl_process.merge_data')
    
    bucketname = 'shopsmart'
    r2 = r2_connect()
    
    # Upload each table to R2
    upload_to_r2(r2, products, 'products', bucketname)
    upload_to_r2(r2, transactions, 'transactions',bucketname)
    upload_to_r2(r2, sales, 'sales', bucketname)


def insert_df(conn, df, table, key_column, columns_to_insert=None):
    cursor = conn.cursor()
    
    if columns_to_insert is None:
        columns_to_insert = list(df.columns)
    
    # Filter the DataFrame to include only the columns we want to insert
    df_to_insert = df[columns_to_insert]
    
    tuples = [tuple(x) for x in df_to_insert.to_numpy()]
    cols = ','.join(columns_to_insert)
    
    # Create a string for all columns except the key
    update_cols = ','.join([f"{col} = EXCLUDED.{col}" for col in columns_to_insert if col != key_column])
    
    # SQL query to execute, not insert duplicate key
    if update_cols:
        query = f"""
        INSERT INTO {table}({cols}) 
        VALUES %s 
        ON CONFLICT ({key_column}) 
        DO UPDATE SET {update_cols}
        """
    else:
        query = f"""
        INSERT INTO {table}({cols}) 
        VALUES %s 
        ON CONFLICT ({key_column}) 
        DO NOTHING
        """
    
    try:
        psycopg2.extras.execute_values(cursor, query, tuples)
        conn.commit()
        print(f"Successfully inserted/updated data in {table}")
    except Exception as error:
        print(f"Error inserting/updating {table}: {error}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def load_postgres_data(**kwargs):
    ti = kwargs['ti']
    
    # Pull data from previous tasks
    products = ti.xcom_pull(task_ids='etl_process.load_and_clean_product')
    transactions = ti.xcom_pull(task_ids='etl_process.load_and_clean_transaction')
    sales = ti.xcom_pull(task_ids='etl_process.merge_data')
    
    conn = pg_connect()
    
    try:
        # Insert data into each table
        insert_df(conn, products, 'dim_products', 'product_id')
        insert_df(conn, transactions, 'dim_customers', 'customer_id', columns_to_insert=['customer_id'])
        insert_df(conn, sales, 'fact_sales', 'transaction_id', columns_to_insert=['transaction_id', 'customer_id', 'product_id', 'quantity', 'price', 'timestamp'])
        
        print("All data inserted/updated successfully")
    except Exception as error:
        print(f"An error occurred: {error}")
        raise
    finally:
        conn.close()