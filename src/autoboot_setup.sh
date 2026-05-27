#!/bin/bash
# autoboot_setup.sh - Run this once to make PosturePro start on every boot
# Usage: bash autoboot_setup.sh

echo "Setting up PosturePro autoboot..."

# Copy service file
sudo cp posturopro.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable posturopro.service
sudo systemctl start posturopro.service

echo "Done. PosturePro will now start automatically on every boot."
echo "Check status: sudo systemctl status posturopro"
echo "View logs:    sudo journalctl -u posturopro -f"
echo "Stop:         sudo systemctl stop posturopro"
