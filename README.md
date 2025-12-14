python3 -m venv venv
source venv/bin/activate 
pip install -r requirements.txt

# activate terminal 1 aka main.py
dotenv run -- ddtrace-run uvicorn main:app --reload

# activate termimal 2
python traffic.py

https://youtu.be/YqS3FUdbTxk