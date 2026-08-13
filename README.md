# E-commerce Operations Dashboard

A synthetic e-commerce operations project focused on the metrics that matter in day-to-day marketplace operations: **sales, inventory, shipping cost, margin, returns, and operational exceptions**.

The project uses generated data only. No company or customer data is included.

## Business Goal

The dashboard is designed for an operations team that sells across multiple marketplaces and needs one place to answer questions such as:

* Which channel is driving the most revenue?
* Are shipping costs increasing?
* Which products are overstocked or at risk of running out?
* Which SKUs have weak margins?
* Are returns or cancellations increasing?
* Which orders need operational attention?
* Are there data-quality issues that could affect reporting?

The goal is not just to visualize sales. It is to connect **revenue, inventory, logistics, and exceptions** so the dashboard can support actual operating decisions.

## Planned Dashboard Areas

### Executive Overview

* Revenue
* Orders
* Average Order Value
* Gross Margin
* Shipping Cost per Order
* Return Rate

### Marketplace Performance

* Amazon
* eBay
* Wayfair
* Revenue and order mix
* Margin by channel

### Inventory

* Units on hand
* Weeks of supply
* Low-stock SKUs
* Overstock risk
* Inventory value

### Logistics

* Shipping cost trends
* Average shipping cost per order
* Carrier performance
* Delivery delays
* High-cost shipments

### Exceptions

* Cancelled orders
* Returns
* Stale orders
* Inventory mismatches
* Unusual shipping cost
* Missing or incomplete records

## Technology

* Python
* Pandas
* Streamlit
* SQL
* Synthetic data
* Git / GitHub

## Project Structure

```text
ecommerce-operations-dashboard/
├── README.md
├── data/
│   ├── orders.csv
│   ├── inventory.csv
│   ├── shipping.csv
│   └── returns.csv
├── src/
│   ├── generate_data.py
│   ├── transform_data.py
│   └── app.py
├── sql/
│   ├── kpi_queries.sql
│   └── data_quality_checks.sql
└── assets/
    └── screenshots/
```

## Current Status

**In development**

The first version will use synthetic marketplace and operations data to build a working Streamlit dashboard with business-focused KPIs and exception monitoring.
