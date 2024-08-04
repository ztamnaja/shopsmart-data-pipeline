FROM apache/airflow:latest

# ADD requirements.txt .
RUN pip install apache-airflow-providers-docker
COPY requirements.txt .
ENV _PIP_ADDITIONAL_REQUIREMENTS="-r requirements.txt"
