import harperdb
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Retrieve the credentials from environment variables
hdb_url = os.getenv("HDB_URL")
hdb_username = os.getenv("HDB_USERNAME")
hdb_password = os.getenv("HDB_PASSWORD")

# Define HarperDB instance with environment variables
hdb = harperdb.HarperDB(url=hdb_url,
                        username=hdb_username,
                        password=hdb_password)

SCHEMA = "finance_repo"

# Table definitions if table does not exist
TABLE1 = "income"
HASH1 = 1

# For now, inputting the users data is solely for backup purposes. In the future, we can change the code to directly retrieve from harpderDB instead of excel

# General format
table_definition1 = {
    "user_id": HASH1,
    "schema": SCHEMA,
    "table": TABLE1,
    "attributes": [
        {"name": "date", "type": "string"},
        {"name": "income_source", "type": "string"},
        {"name": "amount", "type": "number"},
        {"name": "notes", "type": "string"},
    ]
}

# Define the second table
TABLE2 = "expenses"
HASH2 = 2

table_definition2 = {
    "user_id": HASH2,
    "schema": SCHEMA,
    "table": TABLE2,
    "attributes": [
        {"name": "date", "type": "string"},
        {"name": "expense_source", "type": "string"},
        {"name": "amount", "type": "number"},
        {"name": "recurring", "type": "boolean"},
        {"name": "notes", "type": "string"},
    ]
}

# Define the third table
TABLE3 = "portfolio"
HASH3 = 3

table_definition3 = {
    "user_id": HASH3,
    "schema": SCHEMA,
    "table": TABLE3,
    "attributes": [
        {"name": "company", "type": "string"},
        {"name": "num_stock", "type": "number"},
        {"name": "notes", "type": "string"},
    ]
}

# example insert
def income_insert(info):
    income_data = {
        "date": info['date'],
        "income_source": info['income_source'],
        "amount": info['amount'],
        "notes": info['notes'],
    }
    return hdb.insert(SCHEMA, TABLE1, [income_data])

def expense_insert(info):
    expense_data = {
        "date": info['date'],
        "expense_source": info['expense_source'],
        "amount": info['amount'],
        "recurring" : info['recurring'],
        "notes": info['notes'],
    }
    return hdb.insert(SCHEMA, TABLE2, [expense_data])

def portfolio_insert(info):
    portfolio_data = {
        "company": info['company'],
        "num_stock": info['num_stock'],
        "notes": info['notes'],
    }
    return hdb.insert(SCHEMA, TABLE3, [portfolio_data])
    

data_insert1 = {
        "date": "2023-11-09",
        "income_source": "Salary",
        "amount": 5000,
        "notes": "Monthly salary payment",
    }


data_insert2 = {
        "date" : "2023-11-09",
        "expense_source": "Taxes",
        "amount" : 400,
        "recurring" : True,
        "notes" : "Tax on every income"
    }

data_insert3 = {
        "company": "AMD",
        "num_stock" : 16,
        "notes" : "Bought"
    }

income_insert(data_insert1)
expense_insert(data_insert2)
portfolio_insert(data_insert3)
