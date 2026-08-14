from pathlib import Path
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime(2026, 8, 1)
START_DATE = TODAY - timedelta(days=180)

MARKETPLACES = ["Amazon", "eBay", "Wayfair"]
WAREHOUSES = ["Richmond, CA", "Reno, NV"]
CARRIERS = ["UPS", "FedEx", "USPS"]
SERVICE_LEVELS = ["Ground", "2-Day", "Standard"]

PRODUCTS = [
    {
        "sku": "SKU-1001",
        "product_name": "Compact Storage Rack",
        "category": "Home",
        "unit_cost": 42.00,
        "unit_price": 89.99,
        "reorder_point": 80,
    },
    {
        "sku": "SKU-1002",
        "product_name": "Ergonomic Office Chair",
        "category": "Furniture",
        "unit_cost": 78.00,
        "unit_price": 169.99,
        "reorder_point": 50,
    },
    {
        "sku": "SKU-1003",
        "product_name": "Adjustable Standing Desk",
        "category": "Furniture",
        "unit_cost": 115.00,
        "unit_price": 249.99,
        "reorder_point": 35,
    },
    {
        "sku": "SKU-1004",
        "product_name": "Kitchen Organizer Set",
        "category": "Home",
        "unit_cost": 18.00,
        "unit_price": 49.99,
        "reorder_point": 120,
    },
    {
        "sku": "SKU-1005",
        "product_name": "Heavy Duty Utility Cart",
        "category": "Storage",
        "unit_cost": 64.00,
        "unit_price": 139.99,
        "reorder_point": 45,
    },
    {
        "sku": "SKU-1006",
        "product_name": "Portable Work Bench",
        "category": "Tools",
        "unit_cost": 57.00,
        "unit_price": 129.99,
        "reorder_point": 40,
    },
    {
        "sku": "SKU-1007",
        "product_name": "Drawer Storage Cabinet",
        "category": "Storage",
        "unit_cost": 31.00,
        "unit_price": 74.99,
        "reorder_point": 70,
    },
    {
        "sku": "SKU-1008",
        "product_name": "Foldable Utility Shelf",
        "category": "Home",
        "unit_cost": 38.00,
        "unit_price": 94.99,
        "reorder_point": 60,
    },
]


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def random_date(start, end):
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def weighted_choice(items, weights):
    return random.choices(items, weights=weights, k=1)[0]


# ------------------------------------------------------------
# Orders
# ------------------------------------------------------------

def generate_orders(n_orders=4200):
    rows = []

    product_weights = [0.16, 0.12, 0.10, 0.18, 0.09, 0.10, 0.13, 0.12]

    for i in range(1, n_orders + 1):
        product = weighted_choice(PRODUCTS, product_weights)
        marketplace = weighted_choice(
            MARKETPLACES,
            [0.58, 0.22, 0.20]
        )

        order_date = random_date(START_DATE, TODAY)
        quantity = weighted_choice([1, 2, 3, 4], [0.70, 0.20, 0.08, 0.02])

        base_price = product["unit_price"]

        discount_pct = weighted_choice(
            [0, 0.05, 0.10, 0.15, 0.20],
            [0.46, 0.20, 0.18, 0.10, 0.06]
        )

        unit_price = round(base_price * (1 - discount_pct), 2)

        status = weighted_choice(
            ["Delivered", "Shipped", "Processing", "Cancelled"],
            [0.78, 0.10, 0.08, 0.04]
        )

        state = weighted_choice(
            ["CA", "TX", "NY", "FL", "WA", "IL", "AZ", "MA"],
            [0.22, 0.15, 0.14, 0.12, 0.10, 0.10, 0.09, 0.08]
        )

        rows.append(
            {
                "order_id": f"ORD-{i:06d}",
                "marketplace": marketplace,
                "sku": product["sku"],
                "order_date": order_date.date(),
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "order_status": status,
                "state": state,
            }
        )

    df = pd.DataFrame(rows)

    # Keep old orders realistic: most Processing orders should not
    # remain open for weeks or months.
    order_dates = pd.to_datetime(df["order_date"])

    old_processing = (
        df["order_status"].eq("Processing")
        & (order_dates < TODAY - timedelta(days=10))
    )

    df.loc[old_processing, "order_status"] = "Delivered"

    # Intentionally leave a small number of old orders in Processing
    # so the dashboard has realistic stale-order exceptions.
    stale_candidates = df[
        (~df["order_status"].eq("Cancelled"))
        & (order_dates < TODAY - timedelta(days=10))
    ]

    stale_idx = stale_candidates.sample(
        n=min(25, len(stale_candidates)),
        random_state=SEED
    ).index

    df.loc[stale_idx, "order_status"] = "Processing"

    # Intentionally duplicate a few rows for data quality checks
    duplicates = df.sample(5, random_state=SEED)
    df = pd.concat([df, duplicates], ignore_index=True)

    # Intentionally create a few missing marketplace values
    missing_idx = df.sample(6, random_state=11).index
    df.loc[missing_idx, "marketplace"] = np.nan

    return df


# ------------------------------------------------------------
# Inventory
# ------------------------------------------------------------

def generate_inventory():
    rows = []

    inventory_override = {
        # Overstock
        "SKU-1003": 620,
        "SKU-1005": 480,

        # Low-stock
        "SKU-1004": 18,
        "SKU-1007": 12,

        # Normal
        "SKU-1001": 190,
        "SKU-1002": 110,
        "SKU-1006": 95,
        "SKU-1008": 145,
    }

    for product in PRODUCTS:
        on_hand = inventory_override[product["sku"]]

        reserved = random.randint(
            0,
            max(1, min(30, on_hand // 5))
        )

        warehouse = weighted_choice(
            WAREHOUSES,
            [0.65, 0.35]
        )

        rows.append(
            {
                "sku": product["sku"],
                "product_name": product["product_name"],
                "category": product["category"],
                "unit_cost": product["unit_cost"],
                "on_hand_qty": on_hand,
                "reserved_qty": reserved,
                "available_qty": max(on_hand - reserved, 0),
                "reorder_point": product["reorder_point"],
                "warehouse": warehouse,
                "inventory_value": round(
                    on_hand * product["unit_cost"],
                    2
                ),
            }
        )

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# Shipping
# ------------------------------------------------------------

def generate_shipping(orders):
    rows = []

    shipped_orders = orders[
        orders["order_status"].isin(["Shipped", "Delivered"])
    ].drop_duplicates(subset=["order_id"])

    for _, order in shipped_orders.iterrows():
        carrier = weighted_choice(
            CARRIERS,
            [0.38, 0.34, 0.28]
        )

        service_level = weighted_choice(
            SERVICE_LEVELS,
            [0.58, 0.14, 0.28]
        )

        weight = round(
            max(0.5, np.random.gamma(shape=2.2, scale=6)),
            2
        )

        base_cost = 5.50 + weight * 0.48

        if order["state"] in ["NY", "MA", "FL"]:
            base_cost += 2.25

        if service_level == "2-Day":
            base_cost *= 1.55

        ship_date = pd.to_datetime(order["order_date"]) + timedelta(
            days=random.randint(0, 3)
        )

        transit_days = {
            "Ground": random.randint(3, 7),
            "2-Day": random.randint(1, 3),
            "Standard": random.randint(4, 8),
        }[service_level]

        delivery_date = ship_date + timedelta(days=transit_days)

        delivery_status = (
            "Delivered"
            if order["order_status"] == "Delivered"
            else "In Transit"
        )

        shipping_cost = base_cost

        # Intentional USPS cost spike in the most recent 45 days
        if (
            carrier == "USPS"
            and ship_date >= TODAY - timedelta(days=45)
        ):
            shipping_cost *= 1.28

        # Small number of large shipping-cost outliers
        if random.random() < 0.015:
            shipping_cost *= random.uniform(2.2, 3.8)

        rows.append(
            {
                "order_id": order["order_id"],
                "carrier": carrier,
                "shipping_cost": round(shipping_cost, 2),
                "service_level": service_level,
                "ship_date": ship_date.date(),
                "delivery_date": delivery_date.date(),
                "delivery_status": delivery_status,
                "package_weight_lb": weight,
            }
        )

    df = pd.DataFrame(rows)

    # A few missing shipping costs for DQ review
    if len(df) >= 5:
        missing_idx = df.sample(5, random_state=22).index
        df.loc[missing_idx, "shipping_cost"] = np.nan

    return df


# ------------------------------------------------------------
# Returns
# ------------------------------------------------------------

def generate_returns(orders):
    rows = []

    delivered = orders[
        orders["order_status"] == "Delivered"
    ].drop_duplicates(subset=["order_id"])

    reasons = [
        "Damaged",
        "Not as expected",
        "Wrong item",
        "Changed mind",
        "Late delivery",
    ]

    return_id = 1

    for _, order in delivered.iterrows():

        base_rate = 0.055

        # Make Wayfair return rate intentionally higher
        if order["marketplace"] == "Wayfair":
            base_rate = 0.105

        if random.random() <= base_rate:
            return_date = (
                pd.to_datetime(order["order_date"])
                + timedelta(days=random.randint(5, 35))
            )

            refund_amount = round(
                order["unit_price"]
                * order["quantity"]
                * random.uniform(0.75, 1.0),
                2
            )

            rows.append(
                {
                    "return_id": f"RET-{return_id:05d}",
                    "order_id": order["order_id"],
                    "return_date": return_date.date(),
                    "return_reason": weighted_choice(
                        reasons,
                        [0.22, 0.26, 0.12, 0.25, 0.15]
                    ),
                    "refund_amount": refund_amount,
                }
            )

            return_id += 1

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    print("Generating synthetic e-commerce operations data...")

    orders = generate_orders()
    inventory = generate_inventory()
    shipping = generate_shipping(orders)
    returns = generate_returns(orders)

    orders.to_csv(DATA_DIR / "orders.csv", index=False)
    inventory.to_csv(DATA_DIR / "inventory.csv", index=False)
    shipping.to_csv(DATA_DIR / "shipping.csv", index=False)
    returns.to_csv(DATA_DIR / "returns.csv", index=False)

    print()
    print("Files created:")
    print(f"  {DATA_DIR / 'orders.csv'}")
    print(f"  {DATA_DIR / 'inventory.csv'}")
    print(f"  {DATA_DIR / 'shipping.csv'}")
    print(f"  {DATA_DIR / 'returns.csv'}")

    print()
    print("Row counts:")
    print(f"  Orders:    {len(orders):,}")
    print(f"  Inventory: {len(inventory):,}")
    print(f"  Shipping:  {len(shipping):,}")
    print(f"  Returns:   {len(returns):,}")


if __name__ == "__main__":
    main()
