"""Train and evaluate a transparent baseline model. Run: python model_training.py"""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.compose import make_column_selector

DATA = "data/orders_sample.csv"
df = pd.read_csv(DATA).drop_duplicates(subset=["order_id"])
df["final_status"] = df["final_status"].astype(str).str.strip().str.upper()
df = df[df["final_status"].isin(["DELIVERED","RTO"])].copy()
df["target_rto"] = (df["final_status"] == "RTO").astype(int)

numeric = ["order_value","num_items","customer_prior_orders","customer_prior_rto"]
categorical = ["city","state","utm_source","courier"]
X = df[numeric + categorical]
y = df["target_rto"]
pre = ColumnTransformer([
    ("num", Pipeline([("impute", SimpleImputer(strategy="median")),("scale",StandardScaler())]), numeric),
    ("cat", Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]), categorical)
])
model = Pipeline([("preprocess",pre),("classifier",LogisticRegression(max_iter=1000,class_weight="balanced"))])
X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=.25,random_state=42,stratify=y)
model.fit(X_train,y_train)
pred = model.predict(X_test)
prob = model.predict_proba(X_test)[:,1]
print("Hold-out classification report:")
print(classification_report(y_test,pred,digits=3))
print("ROC AUC:", round(roc_auc_score(y_test,prob),3))
print("Note: This is a baseline evaluation, not a production-validated model.")
