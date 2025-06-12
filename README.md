# ollama-openwebui-installer
Ollama and OpenWebUI Installer
This repository provides a Python script to install Ollama and OpenWebUI on macOS and Linux without Docker, optimizing for maximum system resource usage. The script automatically installs all dependencies, including Python 3.11 and Node.js.
Features

Installs Ollama and OpenWebUI natively.
Automatically installs Python 3.11, Node.js (>= 20.10), and other dependencies.
Configures services to use all CPU cores and GPU (if available).
Sets up persistent services using systemd (Linux) or launchd (macOS).
User-friendly installation process.

Prerequisites

macOS or Linux.
Internet connection.
Administrative privileges (sudo).

Installation
Run the following command to download and execute the installer:
curl -fsSL https://raw.githubusercontent.com/yourusername/ollama-openwebui-installer/main/install_ollama_openwebui.py | python3

Replace yourusername with your GitHub username.
Usage

After installation, access OpenWebUI at http://localhost:8080.
Sign up to create an admin account.
Download a model using:ollama pull llama3



Notes

Linux Support: The script assumes an Ubuntu/Debian-based system with apt. For other distributions, manual dependency installation may be required.
Security: Services bind to 0.0.0.0, making them externally accessible. Configure a firewall (e.g., ufw) for production use.
GPU Support: NVIDIA GPUs are auto-detected on Linux for Ollama acceleration.

Troubleshooting

Ensure ports 8080 and 11434 are free.
Check service status:
Linux: sudo systemctl status ollama openwebui
macOS: sudo launchctl list com.ollama.ollama com.openwebui


If Python 3.11 installation fails, ensure your system has the required package manager (apt for Linux, Homebrew for macOS).

License
MIT License
