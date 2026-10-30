import math
import pandas as pd

TODAY = pd.Timestamp("2019-09-05")      # same date as 07_recommend.py
REVIEW_DAYS = 7
BUFFER_DAYS = 1                         # arrive at least 1 day before the shortage
MIN_SHELF_DAYS = 90                     # donor batch must have 90+ days left when it arrives

rec      = pd.read_csv("recommendations.csv", parse_dates=["shortage_date"])
W        = pd.read_csv("shortage_warnings.csv", parse_dates=["shortage_date"]).set_index(["location_id", "sku_id"])
routes   = pd.read_csv("supply_routes.csv")
products = pd.read_csv("products.csv").set_index("sku_id")
batches  = pd.read_csv("inventory_batches.csv", parse_dates=["snapshot_date", "expiry_date"])
snap     = batches.loc[batches.snapshot_date <= TODAY, "snapshot_date"].max()
batches  = batches[batches.snapshot_date == snap]

monsoon = TODAY.month in (6, 7, 8, 9)
def lead_of(rt):
    return int(rt.lead_days_monsoon if monsoon else rt.lead_days_normal)

repl = routes[routes.route_type == "replenishment"].set_index("destination")
xfer = routes[routes.route_type == "transfer"]

rows = []
for r in rec[rec.status == "TOO LATE - check transfer"].itertuples():
    R = W.loc[(r.location_id, r.sku_id)]
    pack = int(products.loc[r.sku_id, "pack_size"])
    safety = math.ceil(1.65 * repl.loc[r.location_id].lead_sd)
    days_left = (r.shortage_date - TODAY).days
    need = math.ceil(R.daily_demand * (r.lead_days - days_left + safety) / pack) * pack   # cover the gap until a normal order lands
    need = max(need, pack)

    if products.loc[r.sku_id, "transfer_allowed"] == 0:
        rows.append((r.location_id, r.sku_id, "-", "-", 0, "REJECTED", "controlled product, transfer not allowed"))
        continue

    for t in xfer[xfer.destination == r.location_id].itertuples():
        D = t.origin
        if t.permitted == 0:
            rows.append((r.location_id, r.sku_id, D, "-", 0, "REJECTED", "route not permitted"))
            continue
        if (D, r.sku_id) not in W.index:
            continue
        d = W.loc[(D, r.sku_id)]
        d_safety = math.ceil(1.65 * repl.loc[D].lead_sd)
        keep = d.daily_demand * (lead_of(repl.loc[D]) + REVIEW_DAYS + d_safety)   # donor's own protection target
        spare = d.on_hand + d.inbound_qty - keep
        if spare <= 0:
            rows.append((r.location_id, r.sku_id, D, "-", 0, "REJECTED", f"donor has no surplus (spare {spare:.0f})"))
            continue

        # try road first, then express (EXPRESS = half the road time, assumption)
        road = lead_of(t)
        options = [("road", road), ("express", max(1, math.ceil(road / 2)))]
        chosen = None
        for mode, days in options:
            arrival = TODAY + pd.Timedelta(days=days)
            if arrival <= r.shortage_date - pd.Timedelta(days=BUFFER_DAYS):
                chosen = (mode, days, arrival)
                break
        if chosen is None:
            rows.append((r.location_id, r.sku_id, D, "-", 0, "REJECTED", "arrives after shortage date"))
            continue
        mode, days, arrival = chosen

        b = batches[(batches.location_id == D) & (batches.sku_id == r.sku_id) &
                    (batches.expiry_date - arrival >= pd.Timedelta(days=MIN_SHELF_DAYS))]
        elig = int(b.available_qty.sum())
        qty = int(min(need, spare, elig) // pack * pack)
        if qty <= 0:
            why = (f"no batch with {MIN_SHELF_DAYS}+ days shelf life" if elig == 0
                   else f"transferable stock below one pack (need {need}, spare {spare:.0f}, eligible {elig})")
            rows.append((r.location_id, r.sku_id, D, mode, 0, "REJECTED", why))
            continue
        status = "RECOMMEND" if qty >= need else "PARTIAL"
        rows.append((r.location_id, r.sku_id, D, mode, qty, status,
                     f"arrives {arrival.date()}, before shortage {r.shortage_date.date()}; need {need}, donor spare {spare:.0f}"))

out = pd.DataFrame(rows, columns=["to_location", "sku_id", "from_location", "mode", "qty", "decision", "reason"])
out.to_csv("transfer_candidates.csv", index=False)
print(out.to_string(index=False))


# ---------- fallback: every TOO LATE row must end with a decision ----------
# ---------- fallback: every TOO LATE row must end with a decision ----------
final = []
for r in rec[rec.status == "TOO LATE - check transfer"].itertuples():
    item = out[(out.to_location == r.location_id) & (out.sku_id == r.sku_id)]
    done = item[item.decision.isin(["RECOMMEND", "PARTIAL"])]
    if not done.empty:
        x = done.iloc[0]
        final.append((r.location_id, r.sku_id, f"TRANSFER from {x.from_location} ({x.mode})",
                      x.qty, x.reason, "not needed"))
        continue

    # why no transfer: list the real rejection reasons
    why_no = "; ".join(f"{x.from_location}: {x.reason}" if x.from_location != "-" else x.reason
                       for x in item.itertuples())
    days = max(1, math.ceil(lead_of(repl.loc[r.location_id]) / 2))      # express = half the normal time (assumption)
    arrival = TODAY + pd.Timedelta(days=days)
    pack = int(products.loc[r.sku_id, "pack_size"])
    qty = max(int(r.order_qty), pack)
    if arrival <= r.shortage_date - pd.Timedelta(days=BUFFER_DAYS):
        action = "EXPEDITE warehouse shipment (express)"
        note = f"arrives {arrival.date()}, shortage {r.shortage_date.date()}"
    elif arrival <= r.shortage_date:
        action = "EXPEDITE - AT RISK (no time buffer)"
        note = f"arrives {arrival.date()}, same day as shortage {r.shortage_date.date()}"
    else:
        action, qty = "ESCALATE - stockout unavoidable", 0
        note = f"even express arrives {arrival.date()}, after shortage {r.shortage_date.date()}"
    final.append((r.location_id, r.sku_id, action, qty, f"Not possible ({why_no})", note))

plan = pd.DataFrame(final, columns=["location_id", "sku_id", "action", "qty",
                                    "borrow_from_distributor", "warehouse_express"])
plan.to_csv("urgent_actions.csv", index=False)
print("\nFINAL ACTIONS FOR 'TOO LATE' ITEMS")
print(plan.to_string(index=False))