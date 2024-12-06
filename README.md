# FastAPI Project - Local Setup

This guide will help you set up and run a FastAPI project locally.

## Prerequisites

Make sure you have the following installed:

- Python 3.10
- Virtual Environment (optional but recommended)
- OpenAI API Key

## Setup Instructions

1. **Install Dependencies:**

   Create a virtual environment (optional, but recommended):

   ````bash
   conda create --name venv python=3.10
    ```

   To activate a environment:
   ```bash
   conda activate venv
    ```
   2 To install all dependencies


    pip install -r requirements.txt


   ````

2. Set up Environment Variables:

Create a .env file in the root of your project directory and add your OpenAI API key:

    OPENAI_API_KEY=your-openai-api-key

Replace your-openai-api-key with your actual OpenAI API key.

6. Use uvicorn to run the application

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

Then Go to given link below:
Postman link: https://web.postman.co/workspace/My-Workspace~43c7f112-8870-4a8c-86c4-5c28e6ddb6ea/request/37916682-c6964be9-8fd1-4c76-8994-575b7398683e?action=share&source=copy-link&creator=37916682

## Installing Docker and Docker Compose

    bash scripts/docker_chatbot_install.sh

## Starting the server

Go to the folder containing the docker-compose.yml file and run the following:

    bash scripts/start_chatbot_server.sh
"# ausaichatbot" 
