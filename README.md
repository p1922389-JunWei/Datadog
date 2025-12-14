## Running with Docker

**Start the application:**
```bash
docker-compose up --build
```

This will:
- Start the API server on `http://localhost:8000`
- Run the traffic generator (10 test requests)
- Display all messages in the chat interface

**Access the application:**
- Open `http://localhost:8000`
- View message logs and chat with the AI

**Stop the application:**
```bash
docker-compose down
```

python3 -m venv venv
source venv/bin/activate 
pip install -r requirements.txt

# activate terminal 1 aka main.py
dotenv run -- ddtrace-run uvicorn main:app --reload

# activate termimal 2
python traffic.py

https://youtu.be/YqS3FUdbTxk
