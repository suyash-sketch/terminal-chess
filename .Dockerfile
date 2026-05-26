# 1. Use standard Python
FROM python:3.11-slim

# 2. Set the main working directory
WORKDIR /app

# 3. Copy only backend requirements and install them
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the backend code into the container
COPY backend/ ./backend/

# 5. Expose the port that the backend will run on
EXPOSE 7860

# 6. Set the working directory to the backend and run the server
WORKDIR /app/backend

# 7. Start the FastAPI server using Uvicorn
CMD [ "uvicorn", "websocket:app", "--host", "0.0.0.0", "--port", "7860" ]