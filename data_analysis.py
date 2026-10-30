import pandas as pd

def load_clean_data(path="data/orders_sample.csv"):
    raw = pd.read_csv(path)
    df = raw.drop_duplicates(subset="order_id").copy()
    df["final_status"] = df["final_status"].astype(str).str.strip().str.upper()
    df = df[df["final_status"].isin(["DELIVERED","RTO"])].copy()
    df["is_rto"] = (df["final_status"] == "RTO").astype(int)
    return raw, df

def apply_policy(row):
    pr = int(row.get("customer_prior_rto",0) or 0)
    po = int(row.get("customer_prior_orders",0) or 0)
    name = str(row.get("customer_name","")).strip().lower()
    address = str(row.get("address","")).strip().lower()
    if len(name)<3 or name in {"test","asdf","abc","dummy","unknown"} or len(address)<12 or address in {"test","asdf","unknown"}:
        return "Hold / cancel"
    if pr >= 2: return "Hold / cancel"
    if pr == 1: return "Ship after confirmation"
    if po == 0: return "Nudge to prepaid"
    return "Ship as-is"
