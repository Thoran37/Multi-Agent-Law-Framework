# Here are your Instructions

## FrontEnd
cd frontend
npm install --legacy-peer-deps
npm start

## BackEnd
. .\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python -m uvicorn backend.server:app --reload --host 127.0.0.1 --port 8000