# GRD-medicine-supply
# GRD Supply Intelligence

Medicine demand forecasting, stock-out risk detection and order/transfer
recommendations for 3 Assam distributors (Guwahati, Dibrugarh, Silchar).

**Deadline:** 10 Nov 2026

## Data note
Demand patterns come from a public pharmacy dataset (Kaggle, Poland).
Network, stock, shipments and lead times are **synthetic assumptions**.
Nothing here is real GRD performance.

## How to run
Download the Kaggle data into a `data/` folder, then run in order:

python 02_build_demand.py
python 03_build_network.py
python 04_simulate.py
python 05_forecast.py
python 06_projection.py
python 07_recommend.py
python 08_transfer.py

## Files
- `GRD_MEDICINE_SUPPLY.ipynb`: data cleaning
- `check.py`: result checks
- `02` to `08`: pipeline scripts

## Status
Done: cleaning, demand split, network, simulation, forecast,
shortage projection, order and transfer recommendations.
Next: Power BI dashboard, Streamlit approve/reject page, RAG Q&A, report.

## Team
- Power BI: <name>
- Streamlit + RAG: <name>
- Report: <name>
