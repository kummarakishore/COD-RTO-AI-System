import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def address_quality(address):
    """Deterministic checks only; an LLM can be added for Hinglish interpretation."""
    value = str(address or "").strip()
    lower = value.lower()
    if len(value) < 12 or lower in {"test", "asdf", "unknown", "na", "n/a"}:
        return False, "Address appears incomplete or placeholder-like"
    if re.fullmatch(r"[\W_]+", value):
        return False, "Address contains no meaningful characters"
    return True, "Address passes basic completeness checks"

def name_quality(name):
    value = str(name or "").strip()
    if len(value) < 3 or value.lower() in {"test", "asdf", "abc", "dummy", "unknown"}:
        return False, "Customer name appears invalid or placeholder-like"
    return True, "Name passes basic checks"

def decide_order(order, config=None):
    cfg = config or load_config()
    t = cfg["thresholds"]
    prior_rto = int(order.get("customer_prior_rto", 0) or 0)
    prior_orders = int(order.get("customer_prior_orders", 0) or 0)
    name_ok, name_msg = name_quality(order.get("customer_name"))
    addr_ok, addr_msg = address_quality(order.get("address"))
    value = float(order.get("order_value", 0) or 0)

    # Explicit, explainable policy. Never cancel solely because a buyer is new.
    if not name_ok or not addr_ok:
        return {"action": "Hold / cancel", "risk_score": 0.95,
                "reason": name_msg if not name_ok else addr_msg,
                "risk_band": "High"}
    if prior_rto >= int(t["hold_cancel_prior_rto"]):
        return {"action": "Hold / cancel", "risk_score": 0.85,
                "reason": f"{prior_rto} previous RTOs; repeated history warrants manual review before dispatch",
                "risk_band": "High"}
    if prior_rto >= int(t["confirmation_prior_rto"]):
        return {"action": "Ship after confirmation", "risk_score": 0.55,
                "reason": "One previous RTO; ask the customer to confirm delivery intent",
                "risk_band": "Medium"}
    if bool(t["first_time_nudge"]) and prior_orders == 0:
        return {"action": "Nudge to prepaid", "risk_score": 0.40,
                "reason": "First-time COD buyer; offer a small prepaid incentive rather than cancelling",
                "risk_band": "Medium"}
    return {"action": "Ship as-is", "risk_score": 0.15,
            "reason": "No repeat-RTO or address-quality warning; ship normally",
            "risk_band": "Low"}
