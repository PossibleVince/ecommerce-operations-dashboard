from pathlib import Path
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    orders = pd.read_csv(DATA_DIR / "orders.csv")
    inventory = pd.read_csv(DATA_DIR / "inventory.csv")
    shipping = pd.read_csv(DATA_DIR / "shipping.csv")
    returns = pd.read_csv(DATA_DIR / "returns.csv")

    orders["order_date"] = pd.to_datetime(orders["order_date"])
    shipping["ship_date"] = pd.to_datetime(shipping["ship_date"])
    shipping["delivery_date"] = pd.to_datetime(shipping["delivery_date"])
    returns["return_date"] = pd.to_datetime(returns["return_date"])

    return orders, inventory, shipping, returns


def clean_orders(orders):
    df = orders.copy()

    df["gross_sales"] = (
        df["quantity"] * df["unit_price"]
    )

    df["is_cancelled"] = df["order_status"].eq("Cancelled")

    df["is_stale"] = (
        df["order_status"].eq("Processing")
        & (
            df["order_date"]
            < df["order_date"].max() - pd.Timedelta(days=10)
        )
    )

    return df


def build_order_metrics(orders):
    active_orders = orders[
        ~orders["is_cancelled"]
    ].drop_duplicates(subset=["order_id"])

    total_revenue = active_orders["gross_sales"].sum()
    total_orders = active_orders["order_id"].nunique()

    avg_order_value = (
        total_revenue / total_orders
        if total_orders > 0
        else 0
    )

    cancelled_orders = orders.loc[
        orders["is_cancelled"],
        "order_id"
    ].nunique()

    stale_orders = orders.loc[
        orders["is_stale"],
        "order_id"
    ].nunique()

    return {
        "revenue": round(total_revenue, 2),
        "orders": int(total_orders),
        "avg_order_value": round(avg_order_value, 2),
        "cancelled_orders": int(cancelled_orders),
        "stale_orders": int(stale_orders),
    }


def build_marketplace_summary(orders):
    active = orders[
        ~orders["is_cancelled"]
    ].drop_duplicates(subset=["order_id"])

    summary = (
        active
        .groupby("marketplace", dropna=False)
        .agg(
            orders=("order_id", "nunique"),
            revenue=("gross_sales", "sum"),
            units=("quantity", "sum"),
        )
        .reset_index()
    )

    summary["avg_order_value"] = (
        summary["revenue"] / summary["orders"]
    )

    return summary.sort_values(
        "revenue",
        ascending=False
    )


def build_shipping_summary(shipping):
    df = shipping.copy()

    valid_cost = df[df["shipping_cost"].notna()].copy()

    carrier_summary = (
        valid_cost
        .groupby("carrier")
        .agg(
            shipments=("order_id", "nunique"),
            avg_shipping_cost=("shipping_cost", "mean"),
            total_shipping_cost=("shipping_cost", "sum"),
            avg_package_weight=("package_weight_lb", "mean"),
        )
        .reset_index()
    )

    carrier_summary["avg_shipping_cost"] = (
        carrier_summary["avg_shipping_cost"].round(2)
    )

    carrier_summary["total_shipping_cost"] = (
        carrier_summary["total_shipping_cost"].round(2)
    )

    carrier_summary["avg_package_weight"] = (
        carrier_summary["avg_package_weight"].round(2)
    )

    return carrier_summary


def detect_shipping_outliers(shipping):
    df = shipping[
        shipping["shipping_cost"].notna()
    ].copy()

    # Treat the most expensive 1% of shipments as
    # high-cost exceptions for operational review.
    upper_bound = df["shipping_cost"].quantile(0.99)

    outliers = df[
        df["shipping_cost"] >= upper_bound
    ].copy()

    outliers["outlier_threshold"] = round(
        upper_bound,
        2
    )

    return outliers.sort_values(
        "shipping_cost",
        ascending=False
    )

def build_return_summary(orders, returns):
    order_marketplace = (
        orders[
            ["order_id", "marketplace"]
        ]
        .drop_duplicates(subset=["order_id"])
    )

    return_detail = returns.merge(
        order_marketplace,
        on="order_id",
        how="left"
    )

    delivered_counts = (
        orders[
            orders["order_status"].eq("Delivered")
        ]
        .drop_duplicates(subset=["order_id"])
        .groupby("marketplace")["order_id"]
        .nunique()
        .rename("delivered_orders")
    )

    return_counts = (
        return_detail
        .groupby("marketplace")["return_id"]
        .nunique()
        .rename("returns")
    )

    summary = pd.concat(
        [delivered_counts, return_counts],
        axis=1
    ).fillna(0)

    summary["return_rate"] = (
        summary["returns"]
        / summary["delivered_orders"]
    )

    summary = summary.reset_index()

    summary["return_rate"] = (
        summary["return_rate"] * 100
    ).round(2)

    return summary.sort_values(
        "return_rate",
        ascending=False
    )


def build_inventory_risk(inventory, orders):
    df = inventory.copy()

    recent_cutoff = (
        orders["order_date"].max()
        - pd.Timedelta(days=56)
    )

    recent_sales = (
        orders[
            (orders["order_date"] >= recent_cutoff)
            & (~orders["is_cancelled"])
        ]
        .groupby("sku")["quantity"]
        .sum()
        .rename("units_sold_8w")
    )

    df = df.merge(
        recent_sales,
        on="sku",
        how="left"
    )

    df["units_sold_8w"] = (
        df["units_sold_8w"].fillna(0)
    )

    df["avg_weekly_sales"] = (
        df["units_sold_8w"] / 8
    )

    df["weeks_of_supply"] = np.where(
        df["avg_weekly_sales"] > 0,
        df["available_qty"]
        / df["avg_weekly_sales"],
        np.nan
    )

    df["stock_status"] = "Normal"

    df.loc[
        df["available_qty"]
        <= df["reorder_point"],
        "stock_status"
    ] = "Low Stock"

    df.loc[
        df["weeks_of_supply"] >= 12,
        "stock_status"
    ] = "Overstock"

    df["weeks_of_supply"] = (
        df["weeks_of_supply"].round(1)
    )

    return df.sort_values(
        ["stock_status", "weeks_of_supply"],
        ascending=[True, False]
    )


def build_data_quality_summary(
    orders,
    shipping,
    inventory,
    returns
):
    duplicate_orders = (
        orders["order_id"].duplicated().sum()
    )

    missing_marketplace = (
        orders["marketplace"].isna().sum()
    )

    missing_shipping_cost = (
        shipping["shipping_cost"].isna().sum()
    )

    invalid_inventory = (
        (inventory["on_hand_qty"] < 0)
        | (inventory["available_qty"] < 0)
    ).sum()

    orphan_returns = (
        ~returns["order_id"].isin(
            orders["order_id"]
        )
    ).sum()

    summary = pd.DataFrame(
        [
            {
                "check": "Duplicate order IDs",
                "issue_count": int(duplicate_orders),
            },
            {
                "check": "Missing marketplace",
                "issue_count": int(missing_marketplace),
            },
            {
                "check": "Missing shipping cost",
                "issue_count": int(missing_shipping_cost),
            },
            {
                "check": "Negative inventory quantity",
                "issue_count": int(invalid_inventory),
            },
            {
                "check": "Returns without matching order",
                "issue_count": int(orphan_returns),
            },
        ]
    )

    summary["status"] = np.where(
        summary["issue_count"] > 0,
        "Review",
        "OK"
    )

    return summary


def save_outputs(
    marketplace_summary,
    shipping_summary,
    shipping_outliers,
    return_summary,
    inventory_risk,
    data_quality_summary
):
    marketplace_summary.to_csv(
        OUTPUT_DIR / "marketplace_summary.csv",
        index=False
    )

    shipping_summary.to_csv(
        OUTPUT_DIR / "shipping_summary.csv",
        index=False
    )

    shipping_outliers.to_csv(
        OUTPUT_DIR / "shipping_outliers.csv",
        index=False
    )

    return_summary.to_csv(
        OUTPUT_DIR / "return_summary.csv",
        index=False
    )

    inventory_risk.to_csv(
        OUTPUT_DIR / "inventory_risk.csv",
        index=False
    )

    data_quality_summary.to_csv(
        OUTPUT_DIR / "data_quality_summary.csv",
        index=False
    )


def main():
    print("Loading data...")
    orders, inventory, shipping, returns = load_data()

    print("Transforming order data...")
    orders = clean_orders(orders)

    kpis = build_order_metrics(orders)

    marketplace_summary = build_marketplace_summary(
        orders
    )

    shipping_summary = build_shipping_summary(
        shipping
    )

    shipping_outliers = detect_shipping_outliers(
        shipping
    )

    return_summary = build_return_summary(
        orders,
        returns
    )

    inventory_risk = build_inventory_risk(
        inventory,
        orders
    )

    data_quality_summary = (
        build_data_quality_summary(
            orders,
            shipping,
            inventory,
            returns
        )
    )

    save_outputs(
        marketplace_summary,
        shipping_summary,
        shipping_outliers,
        return_summary,
        inventory_risk,
        data_quality_summary
    )

    print()
    print("Core KPIs:")
    print(
        f"  Revenue: "
        f"${kpis['revenue']:,.2f}"
    )
    print(
        f"  Orders: "
        f"{kpis['orders']:,}"
    )
    print(
        f"  AOV: "
        f"${kpis['avg_order_value']:,.2f}"
    )
    print(
        f"  Cancelled orders: "
        f"{kpis['cancelled_orders']:,}"
    )
    print(
        f"  Stale orders: "
        f"{kpis['stale_orders']:,}"
    )

    print()
    print("Processed files written to:")
    print(f"  {OUTPUT_DIR}")


if __name__ == "__main__":
    main()