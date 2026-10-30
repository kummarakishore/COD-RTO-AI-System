"""Local WhatsApp mock. No real messages are sent."""
from datetime import datetime, timedelta

def build_message(customer_name, order_id, action, discount=30):
    name = customer_name or "there"
    if action == "Ship after confirmation":
        return (f"Hi {name}, we received your COD order {order_id}. "
                "Please reply YES to confirm delivery, or NO to cancel. "
                "We will hold dispatch for up to 24 hours. धन्यवाद!")
    if action == "Nudge to prepaid":
        return (f"Hi {name}, thanks for order {order_id}! Pay online now and get "
                f"₹{discount} off. Reply PAY for the payment link or COD to keep cash on delivery.")
    return "No WhatsApp message required for this action."

def handle_reply(action, reply, hours_elapsed=0):
    r = str(reply or "").strip().lower()
    if hours_elapsed >= 24 and action == "Ship after confirmation":
        return "EXPIRE_AND_REVIEW", "No confirmation within 24 hours; keep on hold and send one final reminder or cancel per policy."
    if action == "Ship after confirmation":
        if r in {"yes","y","confirm","confirmed"}:
            return "CONFIRMED", "Customer confirmed; release order for dispatch."
        if r in {"no","n","cancel"}:
            return "CANCELLED_BY_CUSTOMER", "Customer declined; cancel and record reason."
        return "CLARIFY", "Unclear reply; ask the customer to reply YES or NO."
    if action == "Nudge to prepaid":
        if r in {"pay","paid","payment","yes"}:
            return "PAYMENT_LINK", "Share secure checkout link; mark prepaid only after payment gateway confirmation."
        if r in {"cod","cash","no"}:
            return "KEEP_COD", "Customer prefers COD; continue with original COD policy."
        return "CLARIFY", "Ask customer to reply PAY or COD."
    return "NO_ACTION", "This action does not require a WhatsApp flow."

if __name__ == "__main__":
    action = input("Action [confirm/nudge]: ").strip().lower()
    action = "Ship after confirmation" if action.startswith("c") else "Nudge to prepaid"
    print(build_message("Asha", "KT-DEMO-001", action))
    reply = input("Customer reply (YES/NO/PAY/COD/random): ")
    print(handle_reply(action, reply))
