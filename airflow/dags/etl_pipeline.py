from airflow import DAG
from airflow.utils.task_group import TaskGroup
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
import pandas as pd
from io import StringIO
from dependencies import extract, transform, load, connections
from airflow.operators.python_operator import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLColumnCheckOperator

# Define default arguments for the DAG
default_args = {
    'owner': 'ztamnaja',
    'depends_on_past': False,
    'start_date': datetime(2024, 8, 3),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

POSTGRES_CONN_ID = 'destination_db_conn'

with DAG(
  dag_id='etl_process',
  default_args=default_args,
  schedule_interval='@daily',
  tags=["etl", 'data quality'] 
) as dag:

  with TaskGroup("setup_connections", tooltip="postgres and r2") as setup_connections:
    connect_airflow = PythonOperator(
        task_id = f'add_connection',
        python_callable=connections.add_conn_airflow,
        provide_context=True,
        retries=3,
        retry_delay=timedelta(seconds=5)
        )

  with TaskGroup("etl_process", tooltip="extrct transform load to destination db and data lake") as etl_process:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id='end')
    load_product_task = PythonOperator(
        task_id='load_and_clean_product',
        python_callable=extract.load_and_clean_product,
        dag=dag,
    )

    load_transaction_task = PythonOperator(
        task_id='load_and_clean_transaction',
        python_callable=extract.load_and_clean_transaction,
        dag=dag,
    )

    merge_data_task = PythonOperator(
        task_id='merge_data',
        python_callable=transform.merge_data,
        provide_context=True,
        dag=dag,
    )

    load_r2_data_task = PythonOperator(
        task_id='load_r2_data_backup',
        python_callable=load.load_r2_data,
        provide_context=True,
        dag=dag,
    )

    load_postgres_data_task = PythonOperator(
        task_id='load_processed_data',
        python_callable=load.load_postgres_data,
        provide_context=True,
        dag=dag,
    )
    
    start >> [load_product_task, load_transaction_task] >> merge_data_task >> [ load_r2_data_task, load_postgres_data_task] >> end

  with TaskGroup("data_quality_check", tooltip="check sql columns") as data_quality_check:

    dim_products_check = SQLColumnCheckOperator(
        task_id="data_column_validation_dim_products",
        conn_id=POSTGRES_CONN_ID,
        table='dim_products',
        column_mapping={
            "product_id": {"null_check": {"equal_to": 0}},
            "product_name": {"null_check": {"equal_to": 0}},
            "category": {"null_check": {"equal_to": 0}},
            "price": {"null_check": {"equal_to": 0}, "min": {"geq_to": 0}},
        },
        dag=dag,
      )
    
    dim_customers_check = SQLColumnCheckOperator(
        task_id="data_column_validation_dim_customers",
        conn_id=POSTGRES_CONN_ID,
        table='dim_customers',
        column_mapping={
            "customer_id": {"null_check": {"equal_to": 0}},
        },
        dag=dag,
      )
    
    fact_sales_check = SQLColumnCheckOperator(
        task_id="data_column_validation_fact_sales",
        conn_id=POSTGRES_CONN_ID,
        table='fact_sales',
        column_mapping={
            "transaction_id": {"null_check": {"equal_to": 0}},
            "customer_id": {"null_check": {"equal_to": 0}},
            "product_id": {"null_check": {"equal_to": 0}},
            "quantity": {"null_check": {"equal_to": 0}, "min": {"geq_to": 1}},
            "price": {"null_check": {"equal_to": 0}, "min": {"geq_to": 0}},
            "timestamp": {"null_check": {"equal_to": 0}},
        },
        dag=dag,
      )
    
    [dim_products_check, dim_customers_check, fact_sales_check]
    
# Set task dependencies
setup_connections >>  etl_process  >> data_quality_check
