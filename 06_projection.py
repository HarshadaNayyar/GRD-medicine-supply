import math
import numpy as np
import pandas as pd
AS_OF = "2019-09-05"      # we pretend "today" is this date (pick any date in the test period)
HORIZON = 21              # look 21 days ahead

batches   = pd.read_csv("inventory_batches.csv", parse_dates=["snapshot_date", "expiry_date"])
ships     = pd.read_csv("shipments.csv", parse_dates=["dispatch_date", "expected_arrival", "actual_arrival"])
fc        = pd.read_csv("forecast_test_predictions.csv", parse_dates=["date"])
routes    = pd.read_csv("supply_routes.csv")
routes    = routes[routes.route_type == "replenishment"].set_index("destination")
products  = pd.read_csv("products.csv").set_index("sku_id")

# stock snapshots exist weekly -> use the closest one on/before AS_OF
snap = batches.loc[batches.snapshot_date <= AS_OF, "snapshot_date"].max()
b_now = batches[batches.snapshot_date == snap]
print("Using stock snapshot of", snap.date())

rows = []
for (loc, sku), g in b_now.groupby(["location_id", "sku_id"]):
    # 1) daily demand rate = next week's forecast / 7
    f = fc[(fc.location_id == loc) & (fc.sku_id == sku) & (fc.date > snap)].sort_values("date")
    if f.empty:
        continue
    rate = f.iloc[0]["pred_ml"] / 7

    # 2) what we hold now (qty, expiry)
    stock = [[r.available_qty, r.expiry_date] for r in g.itertuples()]
    on_hand = sum(q for q, _ in stock)

    # 3) shipments still on the way (dispatched, not yet arrived at snapshot)
    inbound = ships[(ships.destination == loc) & (ships.sku_id == sku) &
                    (ships.dispatch_date <= snap) & (ships.actual_arrival > snap)]
    arrivals = []
    for s in inbound.itertuples():
        r = routes.loc[loc]
        lead = r.lead_days_monsoon if s.dispatch_date.month in (6, 7, 8, 9) else r.lead_days_normal
        est = s.dispatch_date + pd.Timedelta(days=int(lead))      # OUR estimate, not the future truth
        arrivals.append((max(est, snap + pd.Timedelta(days=1)), s.qty))

    # 4) day-by-day projection
    shortage = None
    for d in range(1, HORIZON + 1):
        day = snap + pd.Timedelta(days=d)
        for a_day, qty in arrivals:
            if a_day == day:
                stock.append([qty, day + pd.Timedelta(days=int(products.loc[sku, "shelf_life_days"] * 0.75))])
        stock = [[q, e] for q, e in stock if e > day and q > 0]          # drop expired
        need = rate
        for b in sorted(stock, key=lambda b: b[1]):                       # earliest expiry first
            take = min(b[0], need); b[0] -= take; need -= take
        if need > 0.5 and shortage is None:                               # could not serve demand
            shortage = day

    rows.append((loc, sku, on_hand, round(rate, 1), round(on_hand / rate, 1) if rate > 0 else None,
                 int(inbound.qty.sum()), shortage.date() if shortage is not None else None))

out = pd.DataFrame(rows, columns=["location_id", "sku_id", "on_hand", "daily_demand",
                                  "days_of_cover", "inbound_qty", "shortage_date"])
out.to_csv("shortage_warnings.csv", index=False)
print(out[out.shortage_date.notna()].sort_values("shortage_date").to_string(index=False))
print("\nSKU-locations with a shortage in the next", HORIZON, "days:", out.shortage_date.notna().sum(), "of", len(out))