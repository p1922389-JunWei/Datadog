## Running with Docker
**Requirements:**

Make sure you install Docker Desktop. With this, you don't need to create venv.
All you have to do create the .env file and ask Jun Wei for the env keys

**Start the application:**
```bash
docker-compose up --build
```

This will automatically:
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

## Tutorial

[YouTube Tutorial](https://youtu.be/YqS3FUdbTxk)
