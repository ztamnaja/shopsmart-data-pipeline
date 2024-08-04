import os
import json
from airflow.models.connection import Connection
from airflow import settings
from airflow.models import Connection
import logging

AIRFLOW_HOME = os.getenv('AIRFLOW_HOME')

def add_conn_airflow():
  # Load connection information from JSON file
  with open(AIRFLOW_HOME+'/connections.json') as f:
      conn_list = json.load(f)
  for con in conn_list:
    print(f'adding conn: {con}')
    connect = conn_list[con]
    conn_id = connect['connection_id']
    conn = Connection(conn_id=conn_id,
                      conn_type=connect['conn_type'],
                      host=connect['host'],
                      login=connect['login'],
                      password=connect['password'],
                      port=connect['port'],
                      schema=connect['schema'], # mysql db
                      extra=connect['extra'],
                      description=connect['description'])
    session = settings.Session()
    conn_name = session.query(Connection).filter(Connection.conn_id == conn.conn_id).first()
    if str(conn_name) == str(conn.conn_id):
        print(f"Connection {conn.conn_id} already exists")
        continue
    session.add(conn)
    session.commit()
    logging.info(Connection.log_info(conn))
    logging.info(f'Connection {conn_id} is created')