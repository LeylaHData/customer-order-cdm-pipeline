# Kunden- und Bestelldaten in CDM-Form bringen

Dieses Python-Programm liest Kundendaten und Bestellungen aus CSV-Dateien ein, bereinigt die Daten und speichert sie als Contact- und SalesOrder-Entitäten.

## Ausführen

In PyCharm: Rechtsklick auf `src/pipeline.py` und **Run 'pipeline'** auswählen.

Das Programm benötigt nur Python. Zusätzliche Pakete müssen nicht installiert werden.

## Eingabedateien

- `data/raw/raw_customers.csv`
- `data/raw/raw_orders.csv`

Die Aufgaben-PDF enthielt Beispieldaten, aber keine separaten CSV-Dateien. Deshalb verwende ich die Beispieldaten aus dem PDF.

## Was das Programm macht

- Kundennamen werden in Vor- und Nachnamen geteilt.
- E-Mail-Adressen werden kleingeschrieben. Ungültige Adressen werden protokolliert und leer gespeichert.
- Kundenstatus wird in Zahlen umgewandelt: `active` zu `0`, `inactive` zu `1`.
- Zeitstempel werden in UTC im Format `YYYY-MM-DDTHH:MM:SSZ` gespeichert.
- Bestellungen mit unbekannter Kunden-ID werden protokolliert und trotzdem gespeichert.
- Geldbeträge werden als Dezimalwerte eingelesen.

## Ausgabedateien

- `cdm_lakehouse/Contact/Contact.csv`
- `cdm_lakehouse/SalesOrder/SalesOrder.csv`
- `cdm_lakehouse/model.json`

Ein Kontakt kann mehrere Bestellungen haben. Deshalb besteht zwischen Contact und SalesOrder eine 1:N-Beziehung.

## Datenfluss und Beziehung

```mermaid
flowchart TB
    RC["raw_customers.csv"] -->|"cust_id → contactid; full_name → firstname/lastname; email_addr → emailaddress1; signup_date → createdon; user_status → statecode"| ETL["Python-Programm"]
    RO["raw_orders.csv"] -->|"tx_id → salesorderid; customer_id → customerid; amount_usd → totalamount; tx_timestamp → createdon"| ETL
    ETL --> C["Contact/Contact.csv"]
    ETL --> S["SalesOrder/SalesOrder.csv"]
    C -->|"contactid · Primärschlüssel · 1"| REL["Kundenbeziehung"]
    REL -->|"customerid · Fremdschlüssel · N"| S
    M["model.json"] -. beschreibt Felder, Datentypen, Pfade und Beziehung .-> C
    M -.-> S
 ```