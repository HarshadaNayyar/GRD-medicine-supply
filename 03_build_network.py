import pandas as pd

# ---------- products ----------
products = pd.DataFrame([
 # sku_id, name, form, pack_size, unit_cost, shelf_life_days, transfer_allowed
 ("M01AB","Diclofenac 50mg tablet","tablet",10,1.2,730,1),
 ("M01AE","Ibuprofen 400mg tablet","tablet",10,1.0,730,1),
 ("N02BA","Aspirin 75mg tablet","tablet",14,0.8,730,1),
 ("N02BE","Paracetamol 500mg tablet","tablet",10,0.6,1095,1),
 ("N05B","Anxiolytic (demo, controlled)","tablet",10,3.5,730,0),
 ("N05C","Hypnotic (demo, controlled)","tablet",10,4.0,730,0),
 ("R03","Salbutamol syrup","syrup",1,45.0,540,1),
 ("R06","Cetirizine 10mg tablet","tablet",10,0.9,1095,1),
], columns=["sku_id","name","dosage_form","pack_size","unit_cost",
            "shelf_life_days","transfer_allowed"])

# ---------- locations ----------
locations = pd.DataFrame([
 ("WH_GHY","warehouse","Kamrup Metropolitan"),
 ("DIST_GHY","distributor","Kamrup Metropolitan"),
 ("DIST_DIB","distributor","Dibrugarh"),
 ("DIST_SIL","distributor","Cachar"),
], columns=["location_id","type","district"])

# ---------- supply_routes ----------
# lead_days_normal / monsoon (Jun-Sep) / sd = variability. Sab ASSUMPTIONS hain.
routes = pd.DataFrame([
 # origin, dest, permitted, normal, monsoon, sd, kind
 ("WH_GHY","DIST_GHY",1,1,1,0.3,"replenishment"),
 ("WH_GHY","DIST_DIB",1,2,3,0.7,"replenishment"),
 ("WH_GHY","DIST_SIL",1,4,8,1.5,"replenishment"),
 ("DIST_GHY","DIST_DIB",1,2,3,0.7,"transfer"),
 ("DIST_GHY","DIST_SIL",1,4,7,1.5,"transfer"),
 ("DIST_DIB","DIST_GHY",1,2,3,0.7,"transfer"),
 ("DIST_SIL","DIST_GHY",1,4,7,1.5,"transfer"),
 ("DIST_DIB","DIST_SIL",0,None,None,None,"transfer"),  # not permitted
 ("DIST_SIL","DIST_DIB",0,None,None,None,"transfer"),
], columns=["origin","destination","permitted","lead_days_normal",
            "lead_days_monsoon","lead_sd","route_type"])

for name, d in [("products",products),("locations",locations),("supply_routes",routes)]:
    d.to_csv(f"{name}.csv", index=False)
print(products.shape, locations.shape, routes.shape)