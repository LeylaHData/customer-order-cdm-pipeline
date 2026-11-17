import csv
from pathlib import Path
import logging
import re
from datetime import datetime, timezone

from decimal import Decimal, InvalidOperation
import json

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def normalize_timestamp(value):
    value = value.strip().replace(" ", "T")

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

project_folder = Path(__file__).resolve().parent.parent
customers_file = project_folder / "data" / "raw" / "raw_customers.csv"

contacts = []

with customers_file.open(encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        name_parts = row["full_name"].strip().split()

        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:])

        email = row["email_addr"].strip().lower()

        if email and not EMAIL_PATTERN.fullmatch(email):
            logging.warning("Ungültige E-Mail für %s; Wert wird geleert", row["cust_id"])
            email = ""
        status = row["user_status"].strip().lower()

        contact = {
            "contactid": row["cust_id"].strip(),
            "firstname": first_name,
            "lastname": last_name,
            "emailaddress1": email,
            "createdon": normalize_timestamp(row["signup_date"]),
            "statecode": 0 if status == "active" else 1,
        }

        contacts.append(contact)
        print(contact)

contact_file = project_folder / "cdm_lakehouse" / "Contact" / "Contact.csv"
contact_file.parent.mkdir(parents=True, exist_ok=True)

contact_columns = [
    "contactid",
    "firstname",
    "lastname",
    "emailaddress1",
    "createdon",
    "statecode",
]

with contact_file.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=contact_columns)
    writer.writeheader()
    writer.writerows(contacts)

print(f"Kontakte gespeichert: {contact_file}")

orders_file = project_folder / "data" / "raw" / "raw_orders.csv"
orders = []

customer_ids = {contact["contactid"] for contact in contacts}

with orders_file.open(encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        order_id = row["tx_id"].strip()
        customer_id = row["customer_id"].strip()

        if customer_id not in customer_ids:
            logging.warning(
                "Verwaiste Bestellung %s: Kunde %s existiert nicht",
                order_id,
                customer_id,
            )

        try:
            amount = str(Decimal(row["amount_usd"].strip()))
            created = normalize_timestamp(row["tx_timestamp"])
        except (InvalidOperation, ValueError) as error:
            logging.warning("Bestellung %s wird übersprungen: %s", order_id, error)
            continue

        order = {
            "salesorderid": order_id,
            "customerid": customer_id,
            "totalamount": amount,
            "createdon": created,
        }

        orders.append(order)

salesorder_file = (
    project_folder / "cdm_lakehouse" / "SalesOrder" / "SalesOrder.csv"
)
salesorder_file.parent.mkdir(parents=True, exist_ok=True)

order_columns = [
    "salesorderid",
    "customerid",
    "totalamount",
    "createdon",
]

with salesorder_file.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=order_columns)
    writer.writeheader()
    writer.writerows(orders)

print(f"Bestellungen gespeichert: {salesorder_file}")

csv_settings = {
    "$type": "CsvFormatSettings",
    "columnHeaders": True,
    "delimiter": ",",
}

model = {
    "name": "EnterpriseDataLake",
    "description": "Manifest for customer and sales data",
    "version": "1.0",
    "entities": [
        {
            "$type": "LocalEntity",
            "name": "Contact",
            "attributes": [
                {"name": "contactid", "dataType": "string"},
                {"name": "firstname", "dataType": "string"},
                {"name": "lastname", "dataType": "string"},
                {"name": "emailaddress1", "dataType": "string"},
                {"name": "createdon", "dataType": "dateTime"},
                {"name": "statecode", "dataType": "int64"},
            ],
            "partitions": [
                {
                    "name": "ContactPartitions",
                    "location": "Contact/Contact.csv",
                    "fileFormatSettings": csv_settings,
                }
            ],
        },
        {
            "$type": "LocalEntity",
            "name": "SalesOrder",
            "attributes": [
                {"name": "salesorderid", "dataType": "string"},
                {"name": "customerid", "dataType": "string"},
                {"name": "totalamount", "dataType": "decimal"},
                {"name": "createdon", "dataType": "dateTime"},
            ],
            "partitions": [
                {
                    "name": "SalesOrderPartitions",
                    "location": "SalesOrder/SalesOrder.csv",
                    "fileFormatSettings": csv_settings,
                }
            ],
        },
    ],
    "relationships": [
        {
            "$type": "SingleKeyRelationship",
            "name": "Contact_SalesOrder_Relationship",
            "fromAttribute": {
                "entityName": "SalesOrder",
                "attributeName": "customerid",
            },
            "toAttribute": {
                "entityName": "Contact",
                "attributeName": "contactid",
            },
        }
    ],
}

model_file = project_folder / "cdm_lakehouse" / "model.json"
model_file.write_text(json.dumps(model, indent=2), encoding="utf-8")

print(f"Manifest gespeichert: {model_file}")