#!/bin/bash

# 1. Uninstall any old versions of Docker
sudo apt-get remove -y docker docker-engine docker.io containerd runc

# 2. Update package index and install required packages for setting up Docker's repository
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 3. Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 4. Set up the Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Install Docker Engine and required components
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 6. Enable and start Docker service
sudo systemctl enable docker.service
sudo systemctl start docker.service

# Check if Docker started successfully
if sudo systemctl status docker.service | grep -q "active (running)"; then
    echo "Docker started successfully."
else
    echo "Error: Docker service failed to start. Checking logs..."
    sudo journalctl -xeu docker.service | tail -n 10
    exit 1
fi

# 7. Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 8. Make docker-compose executable
sudo chmod +x /usr/local/bin/docker-compose

# 9. Verify installations
echo "Docker version:"
docker --version
echo "docker-compose version:"
docker-compose --version

echo "Docker and docker-compose have been successfully installed and set up."
