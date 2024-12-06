# api/chat_handler.py
import json
import logging
import traceback
from pathlib import Path

from core.agent import get_combined_agent, visualization_agent
from core.data_processing import DataProcessor
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

router = APIRouter()
data_processor = DataProcessor()

# Configure the logging
logging.basicConfig(
    level=logging.INFO,  # Set the level to INFO or DEBUG to see more logs
    format="%(asctime)s [%(levelname)s] %(message)s",  # Add a timestamp and level to log messages
    handlers=[logging.StreamHandler()],  # Log to console
)
logger = logging.getLogger(__name__)


# Serve HTML templates
@router.get("/")
async def get_chat_interface():
    html_path = Path("frontend/templates/chat.html")
    return HTMLResponse(content=html_path.read_text(), status_code=200)


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    logging.info("WebSocket connection open")
    await websocket.accept()

    data_id = websocket.query_params.get("data_id")
    logging.info(f"Received data_id: {data_id}")

    if not data_id:
        logging.info("No data_id provided. Closing connection.")
        await websocket.close(code=1008, reason="data_id is required.")
        return

    try:
        logging.info(f"Initializing agent with data_id: {data_id}")
        agent = get_combined_agent(data_id)
        logging.info("Agent initialized successfully.")
    except Exception as e:
        print(f"Agent initialization failed: {e}")
        traceback.print_exc()
        await websocket.close(code=1011, reason="Agent initialization failed.")
        return

    try:
        while True:
            raw_input_data = await websocket.receive_text()
            logging.info(f"Received message: {raw_input_data}")

            # Parse JSON input if needed
            try:
                input_data = json.loads(raw_input_data)
            except ValueError:
                input_data = {"input": raw_input_data.strip()}  # Treat as plain text

            # Extract query
            query = input_data.get("input", "")
            if not query:
                await websocket.send_text("Error: Missing query in input.")
                continue

            logging.info(f"Processed query: {query}")

            try:
                # Check if the query involves visualization
                if any(
                    keyword in query.lower()
                    for keyword in ["visualization", "visualize", "plot"]
                ):
                    logging.info(
                        "Visualization-related query detected. Routing to visualization handler."
                    )

                    # Call the visualization handler function
                    visualization_response = await visualization_agent(query, data_id)

                    # Send the visualization response back to the user
                    await websocket.send_text(visualization_response)
                else:
                    # Process the query using the agent
                    response = agent.invoke({"input": query})
                    logging.info(f"Agent response: {response}")

                    # Ensure the response is a dictionary with the expected keys
                    if isinstance(response, dict) and "output" in response:
                        await websocket.send_text(response["output"])
                    else:
                        await websocket.send_text(
                            "Unexpected response format from the agent."
                        )
            except Exception as e:
                logger.exception(f"Error processing user input :{e}")
                await websocket.send_text(
                    "An error occurred while processing your request."
                )
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected.")
    except Exception as e:
        logging.info(f"Error during WebSocket communication: {e}")
        traceback.print_exc()

        # Truncate the reason to avoid ProtocolError
        truncated_reason = (str(e)[:120] + "...") if len(str(e)) > 120 else str(e)
        await websocket.close(code=1011, reason=truncated_reason)
    finally:
        logging.info("WebSocket connection closed.")
