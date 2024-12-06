#!/bin/bash

# Function to start Docker containers
start_containers() {
    # Change directory to where the Compose file is located
    cd "$(dirname "$COMPOSE_FILE")" || exit

    # Start the containers defined in docker-compose.yml (build if necessary)
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up --build --remove-orphans
}

# Get the absolute path to the directory containing this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Specify the path to your docker-compose.yml file (assuming it's in the same directory as the script)
COMPOSE_FILE="$SCRIPT_DIR/../docker-compose.yml"

# Specify a unique project name for this Docker Compose run
PROJECT_NAME="KynAI"

# Maximum number of retries before giving up
MAX_RETRIES=5
RETRY_COUNT=0

# Loop to restart containers on failure
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Stop the containers defined in docker-compose.yml
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down

    # Call function to start containers
    start_containers

    # Check the exit code of the last executed command
    if [ $? -ne 0 ]; then
        echo "Containers crashed or exited with an error. Restarting..."
        RETRY_COUNT=$((RETRY_COUNT + 1))
    else
        echo "Containers exited gracefully. Exiting loop."
        break
    fi

    # Delay before attempting to restart containers again
    sleep 5
done

# If max retries are reached, exit with error
if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "Max retries reached. Exiting."
    exit 1
fi
