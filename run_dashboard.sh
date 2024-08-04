#!/bin/bash

pip install -r requirements.txt

# Check if installation was successful
if [ $? -ne 0 ]; then
  echo "Failed to install required packages."
  exit 1
fi

python ./shopsmart-dash.py

# Check if the dashboard script is running
if [ $? -ne 0 ]; then
  echo "Failed to run the dashboard script."
  exit 1
fi

echo "Dashboard script is running."
