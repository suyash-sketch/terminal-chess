# 1. Use standard Python
FROM python:3.11-slim

# 2. Set up a non-root user (Required by Hugging Face Docker Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# 3. Set the main working directory
WORKDIR ${HOME}/app

# 4. Copy ONLY the backend requirements first (this speeds up rebuilds)
COPY --chown=user backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the backend code into the container
COPY --chown=user backend/ ./backend/

# 6. Expose the port that Hugging Face expects
EXPOSE 7860

# 7. Step inside the backend folder so Python can find your files (like game_manager.py)
WORKDIR ${HOME}/app/backend

# 8. Boot up the FastAPI server using Uvicorn
CMD ["uvicorn", "websocket:app", "--host", "0.0.0.0", "--port", "7860"]