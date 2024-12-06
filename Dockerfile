# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the entire current directory into the container at /app
COPY . .

# Install the required packages from requirements.txt
RUN pip install -r requirements.txt

# Install langchain and langgraph if needed
RUN pip install -U langchain-community langgraph

# Expose the port that FastAPI will run on (use the port from .env or default)
EXPOSE 8000

# Command to run FastAPI application
CMD ["sh", "-c", "redis-server & uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug"]
