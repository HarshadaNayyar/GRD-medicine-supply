import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
# ---------- 1. weekly demand per SKU x location ----------
log = pd.read_csv("daily_log.csv", parse_dates=["date"])
flag = pd.read_csv("daily_demand.csv", parse_dates=["date"])[["date", "all_zero_sales"]].drop_duplicates()
log = log.merge(flag, on="date")

weekly = (log.groupby(["sku_id", "location_id", pd.Grouper(key="date", freq="W-SUN")])
             .agg(demand=("requested_qty", "sum"),
                  closed_days=("all_zero_sales", "sum"))
             .reset_index())
weekly = weekly.sort_values(["sku_id", "location_id", "date"]).reset_index(drop=True)

# ---------- 2. features (only past information) ----------
g = weekly.groupby(["sku_id", "location_id"])["demand"]
weekly["lag1"]  = g.shift(1)
weekly["lag2"]  = g.shift(2)
weekly["lag4"]  = g.shift(4)
weekly["lag52"] = g.shift(52)
weekly["roll4"]  = g.transform(lambda s: s.shift(1).rolling(4).mean())
weekly["roll13"] = g.transform(lambda s: s.shift(1).rolling(13).mean())
weekly["woy"] = weekly["date"].dt.isocalendar().week.astype(int)
weekly["woy_sin"] = np.sin(2 * np.pi * weekly["woy"] / 52)
weekly["woy_cos"] = np.cos(2 * np.pi * weekly["woy"] / 52)
weekly["sku_code"] = weekly["sku_id"].astype("category").cat.codes
weekly["loc_code"] = weekly["location_id"].astype("category").cat.codes
# ---------- 3. split: train | validation | test (chronological) ----------
last = weekly["date"].max()
test_start = last - pd.Timedelta(weeks=51)
val_start  = test_start - pd.Timedelta(weeks=52)
data  = weekly.dropna(subset=["lag52", "roll13"]).copy()
train = data[data["date"] < val_start]
val   = data[(data["date"] >= val_start) & (data["date"] < test_start)].copy()
test  = data[data["date"] >= test_start].copy()
last_day = log["date"].max()
last_full_end = last_day - pd.Timedelta(days=(last_day.weekday() + 1) % 7)
test = test[test["date"] <= last_full_end].copy()      # drop the incomplete last week

# ---------- 4. forecasts ----------
test["pred_recent4"] = test["roll4"]          # A) baseline
test["pred_seasonal"] = test["lag52"]         # B) same week last year

feats = ["lag1", "lag2", "lag4", "lag52", "roll4", "roll13",
         "woy_sin", "woy_cos", "sku_code", "loc_code"]

def wape(actual, pred):
    tot = actual.sum()
    return np.nan if tot == 0 else 100 * np.abs(actual - pred).sum() / tot

# C) ML: choose settings on VALIDATION only
best = None
for lr in [0.03, 0.05, 0.1]:
    for depth in [3, 5, None]:
        m = HistGradientBoostingRegressor(loss="poisson", learning_rate=lr, max_depth=depth,
                max_iter=300, categorical_features=[8, 9], random_state=0)
        m.fit(train[feats], train["demand"])
        score = wape(val["demand"], m.predict(val[feats]))
        if best is None or score < best[0]:
            best = (score, lr, depth)
print("Best on validation:", best)

tv = pd.concat([train, val])
model = HistGradientBoostingRegressor(loss="poisson", learning_rate=best[1], max_depth=best[2],
        max_iter=300, categorical_features=[8, 9], random_state=0)
model.fit(tv[feats], tv["demand"])
test["pred_ml"] = model.predict(test[feats])
test["pred_blend"] = 0.7 * test["pred_ml"] + 0.3 * test["pred_seasonal"]

# ---------- 5. metrics ----------
def bias(actual, pred):
    return 100 * (pred.sum() - actual.sum()) / actual.sum()

scored = test[test["closed_days"] == 0]
rows = []
for name in ["pred_recent4", "pred_seasonal", "pred_ml", "pred_blend"]:
    rows.append((name, wape(scored["demand"], scored[name]), bias(scored["demand"], scored[name])))
res = pd.DataFrame(rows, columns=["model", "WAPE_%", "bias_%"]).round(1)
print(res.to_string(index=False))

base = res.loc[res.model == "pred_recent4", "WAPE_%"].iloc[0]
ml   = res.loc[res.model == "pred_ml", "WAPE_%"].iloc[0]
print(f"\nImprovement of ML over baseline: {100 * (base - ml) / base:.1f}%")

print("\nWAPE by SKU:")
by = scored.groupby("sku_id").apply(lambda d: pd.Series({
      "recent4": wape(d.demand, d.pred_recent4),
      "seasonal": wape(d.demand, d.pred_seasonal),
      "ml": wape(d.demand, d.pred_ml)})).round(1)
print(by)

test.to_csv("forecast_test_predictions.csv", index=False)


# ---------- future forecast: next 4 weeks (recursive) ----------
last_day = log["date"].max()
last_full_end = last_day - pd.Timedelta(days=(last_day.weekday() + 1) % 7)   # last COMPLETE week (Sunday)
HORIZON_WEEKS = 4

future_rows = []
for (sku, loc), s in weekly.groupby(["sku_id", "location_id"]):
    s = s.sort_values("date")
    hist = list(s.loc[s["date"] <= last_full_end, "demand"])
    sku_code, loc_code = int(s["sku_code"].iloc[0]), int(s["loc_code"].iloc[0])
    for h in range(1, HORIZON_WEEKS + 1):
        wk_end = last_full_end + pd.Timedelta(weeks=h)
        woy = int(wk_end.isocalendar().week)
        x = pd.DataFrame([{
            "lag1": hist[-1], "lag2": hist[-2], "lag4": hist[-4], "lag52": hist[-52],
            "roll4": np.mean(hist[-4:]), "roll13": np.mean(hist[-13:]),
            "woy_sin": np.sin(2 * np.pi * woy / 52), "woy_cos": np.cos(2 * np.pi * woy / 52),
            "sku_code": sku_code, "loc_code": loc_code}])[feats]
        pred = float(max(model.predict(x)[0], 0))
        hist.append(pred)                       # next step uses this forecast as its lag
        future_rows.append((sku, loc, wk_end, h, round(pred, 1)))

future = pd.DataFrame(future_rows, columns=["sku_id", "location_id", "week_ending", "weeks_ahead", "forecast_ml"])
future.to_csv("future_forecast.csv", index=False)
print("\nLast complete week:", last_full_end.date())
print(future[future.sku_id == "N02BE"].to_string(index=False))