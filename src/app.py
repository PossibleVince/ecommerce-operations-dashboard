from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# Paths & Page Configuration
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

st.set_page_config(
    page_title="E-commerce Operations Dashboard",
    page_icon="📦",
    layout="wide",
)


# ------------------------------------------------------------
# Load Data
# ------------------------------------------------------------

@st.cache_data
def load_data():
    orders = pd.read_csv(DATA_DIR / "orders.csv")
    inventory = pd.read_csv(PROCESSED_DIR / "inventory_risk.csv")
    shipping = pd.read_csv(DATA_DIR / "shipping.csv")
    returns = pd.read_csv(DATA_DIR / "returns.csv")
    data_quality = pd.read_csv(
        PROCESSED_DIR / "data_quality_summary.csv"
    )

    orders["order_date"] = pd.to_datetime(orders["order_date"])
    shipping["ship_date"] = pd.to_datetime(shipping["ship_date"])
    shipping["delivery_date"] = pd.to_datetime(
        shipping["delivery_date"]
    )
    returns["return_date"] = pd.to_datetime(
        returns["return_date"]
    )

    orders["gross_sales"] = (
        orders["quantity"] * orders["unit_price"]
    )

    return (
        orders,
        inventory,
        shipping,
        returns,
        data_quality,
    )


(
    orders,
    inventory,
    shipping,
    returns,
    data_quality,
) = load_data()


# ------------------------------------------------------------
# Sidebar Filters
# ------------------------------------------------------------

st.sidebar.header("Filters")

min_date = orders["order_date"].min().date()
max_date = orders["order_date"].max().date()

selected_dates = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

available_marketplaces = sorted(
    orders["marketplace"]
    .dropna()
    .unique()
    .tolist()
)

selected_marketplaces = st.sidebar.multiselect(
    "Marketplace",
    options=available_marketplaces,
    default=available_marketplaces,
)

st.sidebar.divider()

st.sidebar.caption(
    "Inventory and data-quality sections use the full synthetic "
    "dataset because inventory is treated as a current snapshot "
    "and data-quality checks are portfolio-wide controls."
)


# ------------------------------------------------------------
# Apply Filters
# ------------------------------------------------------------

if (
    isinstance(selected_dates, (tuple, list))
    and len(selected_dates) == 2
):
    start_date = pd.Timestamp(selected_dates[0])
    end_date = pd.Timestamp(selected_dates[1])
else:
    start_date = pd.Timestamp(min_date)
    end_date = pd.Timestamp(max_date)

filtered_orders = orders[
    orders["order_date"].between(
        start_date,
        end_date,
        inclusive="both",
    )
].copy()

if selected_marketplaces:
    filtered_orders = filtered_orders[
        filtered_orders["marketplace"].isin(
            selected_marketplaces
        )
    ]
else:
    filtered_orders = filtered_orders.iloc[0:0]

# Missing marketplace records are intentionally excluded from
# normal business reporting and remain visible in Data Quality.
filtered_orders = filtered_orders[
    filtered_orders["marketplace"].notna()
].copy()

filtered_order_ids = set(
    filtered_orders["order_id"]
)

filtered_shipping = shipping[
    shipping["order_id"].isin(filtered_order_ids)
].copy()

filtered_returns = returns[
    returns["order_id"].isin(filtered_order_ids)
].copy()


# ------------------------------------------------------------
# Chart Helpers
# ------------------------------------------------------------

def currency_bar_chart(
    df,
    category_col,
    value_col,
    title,
):
    chart_data = (
        df[[category_col, value_col]]
        .dropna()
        .copy()
    )

    bars = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{category_col}:N",
                title=None,
                sort="-y",
            ),
            y=alt.Y(
                f"{value_col}:Q",
                title=None,
                axis=alt.Axis(
                    format="$,.0f"
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{category_col}:N",
                    title="Marketplace",
                ),
                alt.Tooltip(
                    f"{value_col}:Q",
                    title="Revenue",
                    format="$,.2f",
                ),
            ],
        )
    )

    labels = (
        alt.Chart(chart_data)
        .mark_text(
            dy=-10,
            fontSize=13,
        )
        .encode(
            x=alt.X(
                f"{category_col}:N",
                sort="-y",
            ),
            y=f"{value_col}:Q",
            text=alt.Text(
                f"{value_col}:Q",
                format="$,.0f",
            ),
        )
    )

    return (
        (bars + labels)
        .properties(
            title=title,
            height=300,
        )
    )


def percent_bar_chart(
    df,
    category_col,
    value_col,
    title,
):
    chart_data = (
        df[[category_col, value_col]]
        .dropna()
        .copy()
    )

    bars = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{category_col}:N",
                title=None,
                sort="-y",
            ),
            y=alt.Y(
                f"{value_col}:Q",
                title=None,
                axis=alt.Axis(
                    format=".1f"
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{category_col}:N",
                    title="Marketplace",
                ),
                alt.Tooltip(
                    f"{value_col}:Q",
                    title="Return Rate",
                    format=".2f",
                ),
            ],
        )
    )

    labels = (
        alt.Chart(chart_data)
        .mark_text(
            dy=-10,
            fontSize=13,
        )
        .encode(
            x=alt.X(
                f"{category_col}:N",
                sort="-y",
            ),
            y=f"{value_col}:Q",
            text=alt.Text(
                f"{value_col}:Q",
                format=".1f",
            ),
        )
    )

    return (
        (bars + labels)
        .properties(
            title=title,
            height=300,
        )
    )


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------

st.title(
    "E-commerce Operations Dashboard"
)

st.caption(
    "Marketplace performance · Inventory risk · "
    "Shipping exceptions · Data quality"
)

st.caption(
    "Synthetic portfolio dataset only — no company, "
    "customer, or production data is included."
)

st.divider()


# ------------------------------------------------------------
# Executive Overview
# ------------------------------------------------------------

st.subheader(
    "Executive Overview"
)

active_orders = (
    filtered_orders[
        filtered_orders["order_status"]
        != "Cancelled"
    ]
    .drop_duplicates(
        subset=["order_id"]
    )
)

revenue = active_orders[
    "gross_sales"
].sum()

order_count = active_orders[
    "order_id"
].nunique()

aov = (
    revenue / order_count
    if order_count
    else 0
)

delivered_orders = (
    filtered_orders[
        filtered_orders["order_status"]
        == "Delivered"
    ]["order_id"]
    .drop_duplicates()
)

delivered_count = (
    delivered_orders.nunique()
)

return_count = (
    filtered_returns[
        "return_id"
    ].nunique()
)

overall_return_rate = (
    return_count
    / delivered_count
    * 100
    if delivered_count
    else 0
)

latest_date = (
    orders["order_date"].max()
)

stale_orders = (
    filtered_orders[
        (
            filtered_orders[
                "order_status"
            ]
            == "Processing"
        )
        & (
            filtered_orders[
                "order_date"
            ]
            < latest_date
            - pd.Timedelta(
                days=10
            )
        )
    ]["order_id"]
    .nunique()
)

k1, k2, k3, k4, k5 = (
    st.columns(5)
)

k1.metric(
    "Revenue",
    f"${revenue:,.0f}",
)

k2.metric(
    "Orders",
    f"{order_count:,}",
)

k3.metric(
    "Avg Order Value",
    f"${aov:,.2f}",
)

k4.metric(
    "Return Rate",
    f"{overall_return_rate:.1f}%",
)

k5.metric(
    "Stale Orders",
    f"{stale_orders:,}",
)


# ------------------------------------------------------------
# Revenue Trend
# ------------------------------------------------------------

st.markdown(
    "#### Revenue Trend"
)

monthly_revenue = (
    active_orders
    .assign(
        month=active_orders[
            "order_date"
        ]
        .dt.to_period("M")
        .dt.to_timestamp()
    )
    .groupby(
        "month",
        as_index=False,
    )["gross_sales"]
    .sum()
)

# Remove the latest month when the dataset only contains
# a partial month. This prevents a false "revenue collapse."
latest_order_date = (
    active_orders[
        "order_date"
    ].max()
)

if pd.notna(
    latest_order_date
):
    latest_month_start = (
        latest_order_date
        .to_period("M")
        .to_timestamp()
    )

    if latest_order_date.day < 20:
        monthly_revenue = (
            monthly_revenue[
                monthly_revenue[
                    "month"
                ]
                < latest_month_start
            ]
            .copy()
        )

monthly_revenue[
    "month_label"
] = (
    monthly_revenue[
        "month"
    ]
    .dt.strftime(
        "%b %Y"
    )
)

month_order = (
    monthly_revenue[
        "month_label"
    ]
    .tolist()
)

if not monthly_revenue.empty:
    revenue_line = (
        alt.Chart(
            monthly_revenue
        )
        .mark_line(
            point=True,
            strokeWidth=3,
        )
        .encode(
            x=alt.X(
                "month_label:N",
                title=None,
                sort=month_order,
            ),
            y=alt.Y(
                "gross_sales:Q",
                title="Revenue",
                axis=alt.Axis(
                    format="$,.0f"
                ),
                scale=alt.Scale(
                    zero=False
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "month_label:N",
                    title="Month",
                ),
                alt.Tooltip(
                    "gross_sales:Q",
                    title="Revenue",
                    format="$,.2f",
                ),
            ],
        )
        .properties(
            height=300
        )
    )

    st.altair_chart(
        revenue_line,
        use_container_width=True,
    )
else:
    st.info(
        "No revenue data for the selected filters."
    )

st.divider()


# ------------------------------------------------------------
# Marketplace Performance
# ------------------------------------------------------------

st.subheader(
    "Marketplace Performance"
)

marketplace_summary = (
    active_orders
    .groupby(
        "marketplace"
    )
    .agg(
        orders=(
            "order_id",
            "nunique",
        ),
        revenue=(
            "gross_sales",
            "sum",
        ),
        units=(
            "quantity",
            "sum",
        ),
    )
    .reset_index()
)

if not marketplace_summary.empty:
    marketplace_summary[
        "avg_order_value"
    ] = (
        marketplace_summary[
            "revenue"
        ]
        / marketplace_summary[
            "orders"
        ]
    )
else:
    marketplace_summary[
        "avg_order_value"
    ] = pd.Series(
        dtype=float
    )


return_order_map = (
    filtered_orders[
        [
            "order_id",
            "marketplace",
        ]
    ]
    .drop_duplicates(
        subset=["order_id"]
    )
)

return_detail = (
    filtered_returns
    .merge(
        return_order_map,
        on="order_id",
        how="left",
    )
)

delivered_by_marketplace = (
    filtered_orders[
        filtered_orders[
            "order_status"
        ]
        == "Delivered"
    ]
    .drop_duplicates(
        subset=["order_id"]
    )
    .groupby(
        "marketplace"
    )["order_id"]
    .nunique()
    .rename(
        "delivered_orders"
    )
)

returns_by_marketplace = (
    return_detail
    .groupby(
        "marketplace"
    )["return_id"]
    .nunique()
    .rename(
        "returns"
    )
)

return_summary = (
    pd.concat(
        [
            delivered_by_marketplace,
            returns_by_marketplace,
        ],
        axis=1,
    )
    .fillna(0)
)

return_summary[
    "return_rate"
] = (
    return_summary[
        "returns"
    ]
    / return_summary[
        "delivered_orders"
    ]
    * 100
)

return_summary = (
    return_summary
    .reset_index()
)

left, right = (
    st.columns(2)
)

with left:
    if not marketplace_summary.empty:
        st.altair_chart(
            currency_bar_chart(
                marketplace_summary,
                "marketplace",
                "revenue",
                "Revenue by Marketplace",
            ),
            use_container_width=True,
        )

with right:
    if not return_summary.empty:
        st.altair_chart(
            percent_bar_chart(
                return_summary,
                "marketplace",
                "return_rate",
                "Return Rate by Marketplace (%)",
            ),
            use_container_width=True,
        )


st.dataframe(
    marketplace_summary,
    use_container_width=True,
    hide_index=True,
    column_config={
        "marketplace":
            "Marketplace",

        "orders":
            st.column_config.NumberColumn(
                "Orders",
                format="%d",
            ),

        "revenue":
            st.column_config.NumberColumn(
                "Revenue",
                format="$%.2f",
            ),

        "units":
            st.column_config.NumberColumn(
                "Units",
                format="%d",
            ),

        "avg_order_value":
            st.column_config.NumberColumn(
                "Avg Order Value",
                format="$%.2f",
            ),
    },
)

if not return_summary.empty:
    highest_return = (
        return_summary
        .sort_values(
            "return_rate",
            ascending=False,
        )
        .iloc[0]
    )

    st.info(
        f"{highest_return['marketplace']} currently has "
        f"the highest return rate at "
        f"{highest_return['return_rate']:.1f}%. "
        f"This may warrant review of product mix, "
        f"fulfillment, or customer-experience drivers."
    )

st.divider()


# ------------------------------------------------------------
# Inventory Risk
# ------------------------------------------------------------

st.subheader(
    "Inventory Risk"
)

low_stock = inventory[
    inventory[
        "stock_status"
    ]
    == "Low Stock"
].copy()

overstock = inventory[
    inventory[
        "stock_status"
    ]
    == "Overstock"
].copy()

overstock_value = (
    overstock[
        "inventory_value"
    ]
    .sum()
)

i1, i2, i3 = (
    st.columns(3)
)

i1.metric(
    "Low Stock SKUs",
    f"{len(low_stock)}",
)

i2.metric(
    "Overstock SKUs",
    f"{len(overstock)}",
)

i3.metric(
    "Overstock Inventory Value",
    f"${overstock_value:,.0f}",
)

inventory_display = inventory[
    [
        "sku",
        "product_name",
        "available_qty",
        "reorder_point",
        "avg_weekly_sales",
        "weeks_of_supply",
        "inventory_value",
        "stock_status",
    ]
].copy()

st.dataframe(
    inventory_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "sku":
            "SKU",

        "product_name":
            "Product",

        "available_qty":
            st.column_config.NumberColumn(
                "Available",
                format="%d",
            ),

        "reorder_point":
            st.column_config.NumberColumn(
                "Reorder Point",
                format="%d",
            ),

        "avg_weekly_sales":
            st.column_config.NumberColumn(
                "Avg Weekly Sales",
                format="%.1f",
            ),

        "weeks_of_supply":
            st.column_config.NumberColumn(
                "Weeks of Supply",
                format="%.1f",
            ),

        "inventory_value":
            st.column_config.NumberColumn(
                "Inventory Value",
                format="$%.2f",
            ),

        "stock_status":
            "Status",
    },
)

if not overstock.empty:
    highest_overstock = (
        overstock
        .sort_values(
            "weeks_of_supply",
            ascending=False,
        )
        .iloc[0]
    )

    st.warning(
        f"{highest_overstock['sku']} "
        f"({highest_overstock['product_name']}) has "
        f"{highest_overstock['weeks_of_supply']:.1f} "
        f"weeks of supply. Consider reviewing purchase "
        f"plans, markdown strategy, or inventory "
        f"reduction options."
    )

st.divider()


# ------------------------------------------------------------
# Logistics & Exceptions
# ------------------------------------------------------------

st.subheader(
    "Logistics & Exceptions"
)

shipping_with_orders = (
    filtered_shipping
    .merge(
        filtered_orders[
            [
                "order_id",
                "marketplace",
            ]
        ]
        .drop_duplicates(
            subset=["order_id"]
        ),
        on="order_id",
        how="left",
    )
)

valid_shipping = (
    shipping_with_orders[
        shipping_with_orders[
            "shipping_cost"
        ]
        .notna()
    ]
    .copy()
)

shipping_outliers = (
    pd.DataFrame()
)

if not valid_shipping.empty:
    shipping_threshold = (
        valid_shipping[
            "shipping_cost"
        ]
        .quantile(
            0.99
        )
    )

    shipping_outliers = (
        valid_shipping[
            valid_shipping[
                "shipping_cost"
            ]
            >= shipping_threshold
        ]
        .sort_values(
            "shipping_cost",
            ascending=False,
        )
        .copy()
    )

left, right = (
    st.columns(2)
)

with left:
    st.markdown(
        "#### Shipping Cost Trend"
    )

    monthly_shipping = (
        valid_shipping
        .assign(
            month=valid_shipping[
                "ship_date"
            ]
            .dt.to_period("M")
            .dt.to_timestamp()
        )
        .groupby(
            [
                "month",
                "carrier",
            ],
            as_index=False,
        )["shipping_cost"]
        .mean()
    )

    if not monthly_shipping.empty:
        shipping_line = (
            alt.Chart(
                monthly_shipping
            )
            .mark_line(
                point=True,
                strokeWidth=2,
            )
            .encode(
                x=alt.X(
                    "month:T",
                    title=None,
                    axis=alt.Axis(
                        format="%b %Y"
                    ),
                ),
                y=alt.Y(
                    "shipping_cost:Q",
                    title="Avg Shipping Cost",
                    axis=alt.Axis(
                        format="$,.2f"
                    ),
                    scale=alt.Scale(
                        zero=False
                    ),
                ),
                color=alt.Color(
                    "carrier:N",
                    title="Carrier",
                ),
                tooltip=[
                    alt.Tooltip(
                        "month:T",
                        title="Month",
                        format="%b %Y",
                    ),
                    alt.Tooltip(
                        "carrier:N",
                        title="Carrier",
                    ),
                    alt.Tooltip(
                        "shipping_cost:Q",
                        title="Avg Cost",
                        format="$,.2f",
                    ),
                ],
            )
            .properties(
                height=340
            )
        )

        st.altair_chart(
            shipping_line,
            use_container_width=True,
        )


with right:
    st.markdown(
        "#### High-Cost Shipping Exceptions"
    )

    st.metric(
        "Shipments for Review",
        f"{len(shipping_outliers):,}",
    )

    if not shipping_outliers.empty:
        exception_display = (
            shipping_outliers[
                [
                    "order_id",
                    "carrier",
                    "shipping_cost",
                    "service_level",
                    "package_weight_lb",
                ]
            ]
            .head(10)
        )

        st.dataframe(
            exception_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "order_id":
                    "Order",

                "carrier":
                    "Carrier",

                "shipping_cost":
                    st.column_config.NumberColumn(
                        "Shipping Cost",
                        format="$%.2f",
                    ),

                "service_level":
                    "Service",

                "package_weight_lb":
                    st.column_config.NumberColumn(
                        "Weight (lb)",
                        format="%.1f",
                    ),
            },
        )


# ------------------------------------------------------------
# Shipping Business Insight
# ------------------------------------------------------------

usps_shipping = (
    valid_shipping[
        valid_shipping[
            "carrier"
        ]
        == "USPS"
    ]
    .copy()
)

if not usps_shipping.empty:
    latest_ship_date = (
        shipping[
            "ship_date"
        ]
        .max()
    )

    recent_start = (
        latest_ship_date
        - pd.Timedelta(
            days=44
        )
    )

    prior_start = (
        recent_start
        - pd.Timedelta(
            days=45
        )
    )

    recent_usps = (
        usps_shipping[
            usps_shipping[
                "ship_date"
            ]
            .between(
                recent_start,
                latest_ship_date,
            )
        ]
    )

    prior_usps = (
        usps_shipping[
            usps_shipping[
                "ship_date"
            ]
            .between(
                prior_start,
                recent_start
                - pd.Timedelta(
                    days=1
                ),
            )
        ]
    )

    if (
        not recent_usps.empty
        and not prior_usps.empty
    ):
        recent_avg = (
            recent_usps[
                "shipping_cost"
            ]
            .mean()
        )

        prior_avg = (
            prior_usps[
                "shipping_cost"
            ]
            .mean()
        )

        usps_change = (
            (
                recent_avg
                - prior_avg
            )
            / prior_avg
            * 100
        )

        st.info(
            f"USPS average shipping cost in the most recent "
            f"45-day period is \\${recent_avg:.2f}, compared "
            f"with \\${prior_avg:.2f} in the prior period "
            f"({usps_change:+.1f}%). This is a synthetic "
            f"cost-pressure scenario included for "
            f"operational analysis."
        )

st.caption(
    "High-cost shipping exceptions represent approximately "
    "the top 1% of observed shipping costs. They are flagged "
    "for review rather than automatically classified as errors."
)

st.divider()


# ------------------------------------------------------------
# Data Quality
# ------------------------------------------------------------

st.subheader(
    "Data Quality"
)

issues_to_review = int(
    data_quality.loc[
        data_quality[
            "status"
        ]
        == "Review",
        "issue_count",
    ]
    .sum()
)

checks_to_review = int(
    (
        data_quality[
            "status"
        ]
        == "Review"
    )
    .sum()
)

checks_passed = int(
    (
        data_quality[
            "status"
        ]
        == "OK"
    )
    .sum()
)

d1, d2, d3 = (
    st.columns(3)
)

d1.metric(
    "Exceptions",
    f"{issues_to_review}",
)

d2.metric(
    "Checks Needing Review",
    f"{checks_to_review}",
)

d3.metric(
    "Checks Passed",
    f"{checks_passed}",
)

st.dataframe(
    data_quality,
    use_container_width=True,
    hide_index=True,
    column_config={
        "check":
            "Check",

        "issue_count":
            st.column_config.NumberColumn(
                "Issues",
                format="%d",
            ),

        "status":
            "Status",
    },
)

if issues_to_review:
    st.warning(
        f"{issues_to_review} data-quality exceptions are "
        f"currently flagged for review."
    )
else:
    st.success(
        "No current data-quality exceptions detected."
    )


# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------

st.divider()

st.caption(
    "Portfolio project built with Python, Pandas, Streamlit, "
    "Altair, and synthetic operational data."
)