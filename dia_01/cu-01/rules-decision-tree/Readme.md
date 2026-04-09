cp example.txt .env
En .env y reeplazar valores:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python populate_cloudant.py --validate
python populate_cloudant.py
