# COD RTO AI Decision System

A runnable prototype for evaluating Cash-on-Delivery (COD) orders, routing them into four actions, simulating WhatsApp flows, and viewing a founder dashboard.

## What it does
- Cleans duplicate order IDs and normalizes delivery labels.
- Uses transparent rules for an explainable first version of COD decisions.
- Provides four actions: Ship as-is, Ship after confirmation, Nudge to prepaid, Hold / cancel.
- Simulates YES / NO / unclear / 24-hour timeout replies.
- Shows historical insights and estimated economics in Streamlit.
- Includes an optional logistic-regression baseline training script.

## Dataset notes
- Original file: 2,018 rows.
- Unique order IDs: 1,988; duplicate rows/order IDs removed: 30.
- Labeled unique delivered/RTO rows: 1,987.
- One IN_TRANSIT record is excluded from outcome-rate calculations.
- All records are COD; prepaid performance cannot be measured from this file.
- Historical range: 2026-04-01 02:10 to 2026-09-30 23:04.

## Run in under 10 minutes

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## Optional model baseline

```bash
python model_training.py
```

This trains a logistic regression model using historical pre-shipment fields and prints a hold-out report. The live decision flow intentionally uses transparent rules until a model is calibrated, tested for leakage, and approved.

## WhatsApp simulator (terminal)

```bash
python whatsapp_simulator.py
```

No real WhatsApp messages are sent. The simulator only demonstrates state transitions.

## Decision policy
Edit `config.json` to change the repeat-RTO thresholds, prepaid discount and timeout. The Streamlit sidebar also provides session-level controls for the discount and dashboard date.

Default policy:
- Invalid-looking name/address: Hold / cancel for manual review.
- 2+ previous RTOs: Hold / cancel for manual review (not silent auto-cancellation).
- 1 previous RTO: Ship after WhatsApp confirmation.
- First COD order: Nudge to prepaid; keep COD as a fallback.
- Otherwise: Ship as-is.

A first-time buyer is never cancelled solely for being new.

## Economics used
Expected direct cost per RTO = ₹65 forward shipping + ₹65 return shipping + ₹25 packaging/handling + (8% × ₹180 damaged-product cost) = **₹169.40**.

Suggested prepaid incentive = 2% of AOV capped at ₹30. At ₹649 AOV this is ₹12.98, rounded operationally to ₹13; cap protects margin. The app default uses a ₹30 cap.

Gross profit at risk on a genuinely delivered order cancelled = order value × 62%. Discount cost is counted separately.

Dashboard impact is an estimate using historical bucket RTO rates and explicit assumed intervention effectiveness (60% confirmation, 70% prepaid). These assumptions must be replaced with observed experiment results. They are not realized savings.

## LLM boundary
Do not use an LLM for arithmetic, threshold comparisons, duplicate removal, or calculating RTO rates. Use deterministic code. An LLM may help interpret ambiguous Hinglish/locality descriptions or flag semantically incomplete addresses, but its output should be a review signal, not an autonomous cancellation decision. This demo uses deterministic checks and does not call an external LLM.

## Important limitations
- Synthetic/sample dataset and six-month history may not represent future operations.
- Small prior-RTO groups have wide uncertainty (e.g. 34 orders with 2 prior RTOs).
- City/courier/source associations are observational, not causal.
- No prepaid examples, WhatsApp delivery receipts, or customer-confirmation outcomes are supplied.
- Phone and address are personal data: restrict access, mask in production, set retention limits, and do not expose the CSV in a public repo without authorization.

## Repository contents
- `app.py`: Streamlit dashboard and interaction screens.
- `decision_engine.py`: explainable order policy.
- `whatsapp_simulator.py`: mock messages and reply handling.
- `model_training.py`: optional logistic regression baseline.
- `data_analysis.py`: cleaning and policy helper functions.
- `config.json`: editable policy/economic assumptions.
- `data/orders_sample.csv`: privacy-sanitized assignment sample (contact details, names, street addresses and pincodes removed/replaced; analytical fields and outcomes retained).
- `reports/`: memo, decision log and AI usage log.

## Before production
Run a controlled pilot, calibrate risk probabilities, measure false positives and customer conversion, add human review and audit logs, and integrate Shopify, courier and WhatsApp Business APIs securely.


## Privacy note
The repository copy of the dataset is sanitized. Do not upload the original file containing customer phone numbers, names, street addresses or pincodes to a public repository. Keep the original locally under access controls if authorized.
