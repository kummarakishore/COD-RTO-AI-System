import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path
from decision_engine import decide_order
from whatsapp_simulator import build_message, handle_reply

st.set_page_config(page_title="COD RTO Control Tower", page_icon="📦", layout="wide")
ROOT = Path(__file__).parent
st.title("📦 COD RTO Control Tower")
st.caption("Decision support prototype for COD orders | Historical data: Apr–Sep 2026")

@st.cache_data
def load_data():
    raw = pd.read_csv(ROOT/"data"/"orders_sample.csv")
    data = raw.drop_duplicates(subset="order_id").copy()
    data["final_status"] = data["final_status"].astype(str).str.strip().str.upper()
    data = data[data["final_status"].isin(["DELIVERED","RTO"])].copy()
    data["is_rto"] = (data["final_status"]=="RTO").astype(int)
    data["date"] = pd.to_datetime(data["order_datetime"], errors="coerce").dt.date
    return raw, data

raw, data = load_data()
with st.sidebar:
    st.header("Policy settings")
    st.caption("Edit config.json for persistent policy changes.")
    cfg = json.loads((ROOT/"config.json").read_text())
    t = cfg["thresholds"]
    hold_at = st.number_input("Hold at prior RTO count", 1, 5, int(t["hold_cancel_prior_rto"]))
    confirm_at = st.number_input("Confirm at prior RTO count", 1, 5, int(t["confirmation_prior_rto"]))
    discount_pct = st.slider("Prepaid discount (%)", 0, 5, int(t["prepaid_discount_percent"]))
    discount_cap = st.number_input("Discount cap (₹)", 0, 100, int(t["prepaid_discount_cap_inr"]))
    cfg["thresholds"]["hold_cancel_prior_rto"] = int(hold_at)
    cfg["thresholds"]["confirmation_prior_rto"] = int(confirm_at)
    cfg["thresholds"]["prepaid_discount_percent"] = int(discount_pct)
    cfg["thresholds"]["prepaid_discount_cap_inr"] = int(discount_cap)
    selected_date = st.date_input("Dashboard date", value=pd.to_datetime(data["date"].max()).date())

tab1, tab2, tab3, tab4 = st.tabs(["Founder dashboard","Order decision","WhatsApp simulator","Data insights"])

with tab1:
    st.subheader(f"Daily view — {selected_date.strftime('%d %b %Y')}")
    day = data[data["date"] == selected_date].copy()
    if day.empty:
        st.info("No records for this date in the sample dataset. Choose a date between April and September 2026.")
    else:
        actions = day.apply(lambda r: decide_order(r.to_dict(), cfg), axis=1)
        day["action"] = [x["action"] for x in actions]
        counts = day["action"].value_counts()
        cols = st.columns(4)
        labels = ["Ship as-is","Ship after confirmation","Nudge to prepaid","Hold / cancel"]
        for c, label in zip(cols, labels):
            c.metric(label, int(counts.get(label,0)))
        # Transparent estimates, not realized cash savings.
        economics = cfg["economics"]
        cost_per_rto = (economics["forward_shipping_inr"] + economics["return_shipping_inr"] +
                        economics["packaging_handling_inr"] +
                        economics["returned_product_damage_rate"]*economics["product_cost_inr"])
        rate = data.groupby("action")["is_rto"].mean().to_dict() if "action" in data else {}
        # estimate RTO exposures using historical outcome rate by decision bucket
        history = data.copy()
        history["action"] = history.apply(lambda r: decide_order(r.to_dict(), cfg)["action"], axis=1)
        rates = history.groupby("action")["is_rto"].mean().to_dict()
        avoid = 0.0
        for a in labels:
            n = int(counts.get(a,0))
            factor = 0 if a=="Ship as-is" else (economics["confirmation_rto_avoidance_assumption"] if a=="Ship after confirmation" else economics["prepaid_rto_avoidance_assumption"] if a=="Nudge to prepaid" else 1)
            avoid += n * rates.get(a,0) * factor * cost_per_rto
        held = day[day["action"]=="Hold / cancel"]
        lost = float((held["order_value"] * economics["gross_margin_delivered"] * (1-held["is_rto"])).sum())
        nudged = int(counts.get("Nudge to prepaid",0))
        disc = nudged * .70 * min(discount_cap, float(day.loc[day["action"]=="Nudge to prepaid","order_value"].mean() or 0)*discount_pct/100) if nudged else 0
        net = avoid - lost - disc
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Estimated RTO cost avoided", f"₹{avoid:,.0f}")
        m2.metric("Estimated genuine-sale margin at risk", f"₹{lost:,.0f}")
        m3.metric("Estimated prepaid discount cost", f"₹{disc:,.0f}")
        m4.metric("Estimated net impact", f"₹{net:,.0f}")
        st.caption(f"RTO cost model = ₹{cost_per_rto:.2f} per RTO (₹65 forward + ₹65 return + ₹25 handling + expected ₹14.40 damage). Savings are estimates, not realized accounting.")
        st.dataframe(day[["order_id","customer_name","city","order_value","customer_prior_orders","customer_prior_rto","action","final_status"]], use_container_width=True)
with tab2:
    st.subheader("Evaluate a new COD order")
    with st.form("order_form"):
        a,b = st.columns(2)
        name = a.text_input("Customer name", "Asha Sharma")
        phone = b.text_input("Phone", "9876543210")
        address = st.text_area("Delivery address", "Flat 12, Green Park, MG Road, Bengaluru")
        city = a.text_input("City", "Bengaluru")
        pincode = b.text_input("Pincode", "560001")
        order_value = a.number_input("Order value (₹)", 1, 10000, 649)
        prior_orders = b.number_input("Previous orders", 0, 100, 0)
        prior_rto = a.number_input("Previous RTOs", 0, 20, 0)
        submitted = st.form_submit_button("Get decision")
    if submitted:
        result = decide_order({"customer_name":name,"phone":phone,"address":address,"city":city,"pincode":pincode,
                               "order_value":order_value,"customer_prior_orders":prior_orders,"customer_prior_rto":prior_rto}, cfg)
        st.success(result["action"])
        st.write(result["reason"])
        st.metric("Illustrative risk score", f'{result["risk_score"]:.0%}')
        st.caption("Risk score is a policy indicator, not a calibrated probability. LLM address interpretation is not connected in this demo.")
with tab3:
    st.subheader("WhatsApp flow simulator")
    action = st.selectbox("Flow", ["Ship after confirmation","Nudge to prepaid"])
    cust = st.text_input("Customer name for message", "Asha")
    order = st.text_input("Order ID", "KT-DEMO-001")
    disc = min(discount_cap, 30)
    st.chat_message("assistant").write(build_message(cust, order, action, disc))
    reply = st.selectbox("Simulate customer response", ["YES","NO","PAY","COD","random reply","No reply after 24 hours"])
    if st.button("Process reply"):
        hours = 24 if reply=="No reply after 24 hours" else 0
        outcome, explanation = handle_reply(action, "" if hours else reply, hours)
        st.write("**System outcome:**", outcome)
        st.write(explanation)
with tab4:
    st.subheader("Historical dataset insights")
    st.write(f"Raw rows: {len(raw):,} | Duplicate order IDs removed: {raw['order_id'].duplicated().sum():,} | Labeled unique orders: {len(data):,}")
    st.metric("Historical RTO rate", f"{data['is_rto'].mean():.1%}")
    c1,c2 = st.columns(2)
    with c1:
        st.write("RTO rate by previous RTO count")
        st.dataframe((data.groupby("customer_prior_rto")["is_rto"].agg(["count","mean"]).rename(columns={"count":"orders","mean":"RTO rate"}).assign(**{"RTO rate":lambda x:x["RTO rate"].map(lambda v:f"{v:.1%}")})), use_container_width=True)
    with c2:
        st.write("RTO rate by acquisition source")
        st.dataframe((data.groupby("utm_source")["is_rto"].agg(["count","mean"]).rename(columns={"count":"orders","mean":"RTO rate"}).assign(**{"RTO rate":lambda x:x["RTO rate"].map(lambda v:f"{v:.1%}")})), use_container_width=True)
    st.bar_chart(data.groupby("courier")["is_rto"].mean().sort_values(ascending=False))
    st.warning("The sample contains COD orders only. It cannot establish prepaid RTO performance or causal impact of discounts.")
