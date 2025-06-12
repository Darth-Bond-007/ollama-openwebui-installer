import os
import platform
import subprocess
import sys
import shutil
import multiprocessing
import urllib.request
import getpass
from pathlib import Path

def check_system():
    """Check if the system is macOS or Linux."""
    system = platform.system()
    if system not in ["Linux", "Darwin"]:
        print("Error: This installer supports only macOS and Linux.")
        sys.exit(1)
    return system

def run_command(command, error_message, silent=False):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=silent
        )
        return result.stdout if silent else None
    except subprocess.CalledProcessError as e:
        print(f"{error_message}: {e}")
        sys.exit(1)

def install_homebrew():
    """Install Homebrew on macOS if not present."""
    print("Checking for Homebrew...")
    if shutil.which("brew") is None:
        print("Installing Homebrew...")
        homebrew_install = (
            '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        )
        run_command(homebrew_install, "Failed to install Homebrew")
        # Add Homebrew to PATH
        if platform.machine().startswith("arm"):
            brew_path = "/opt/homebrew/bin"
        else:
            brew_path = "/usr/local/bin"
        os.environ["PATH"] = f"{brew_path}:{os.environ['PATH']}"
        run_command(f"echo 'export PATH={brew_path}:$PATH' >> ~/.zshrc", "Failed to update PATH")

def install_python(system):
    """Install Python 3.11 if not present."""
    print("Checking for Python 3.11...")
    try:
        python_version = run_command(
            "python3.11 --version",
            "Python 3.11 check failed",
            silent=True
        )
        if "3.11" in python_version:
            print("Python 3.11 found.")
            return
    except subprocess.CalledProcessError:
        pass

    print("Installing Python 3.11...")
    if system == "Linux":
        run_command(
            "sudo apt-get update && sudo apt-get install -y software-properties-common && "
            "sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update && "
            "sudo apt-get install -y python3.11 python3.11-dev python3.11-venv",
            "Failed to install Python 3.11 on Linux"
        )
    elif system == "Darwin":
        install_homebrew()
        run_command(
            "brew install python@3.11",
            "Failed to install Python 3.11 on macOS"
        )
        # Ensure python3.11 is in PATH
        brew_prefix = run_command("brew --prefix python@3.11", "Failed to get Python 3.11 prefix", silent=True).strip()
        python_bin = f"{brew_prefix}/bin"
        os.environ["PATH"] = f"{python_bin}:{os.environ['PATH']}"
        run_command(
            f"echo 'export PATH={python_bin}:$PATH' >> ~/.zshrc",
            "Failed to update PATH for Python 3.11"
        )
        # Verify installation
        try:
            python_version = run_command(
                "python3.11 --version",
                "Python 3.11 installation verification failed",
                silent=True
            )
            print(f"Python 3.11 installed: {python_version.strip()}")
        except subprocess.CalledProcessError:
            print("Error: Python 3.11 installation failed or not found in PATH.")
            sys.exit(1)

def install_node(system):
    """Install Node.js >= 20.10."""
    print("Checking for Node.js...")
    try:
        node_version = run_command(
            "node --version",
            "Node.js check failed",
            silent=True
        )
        version = node_version.strip().lstrip("v")
        if tuple(map(int, version.split("."))) >= (20, 10, 0):
            print(f"Node.js {version} found.")
            return
    except subprocess.CalledProcessError:
        pass

    print("Installing Node.js...")
    if system == "Linux":
        run_command(
            "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && "
            "sudo apt-get install -y nodejs",
            "Failed to install Node.js on Linux"
        )
    elif system == "Darwin":
        install_homebrew()
        run_command(
            "brew install node@20",
            "Failed to install Node.js on macOS"
        )

def install_dependencies(system):
    """Install system dependencies."""
    print("Installing system dependencies...")
    if system == "Linux":
        run_command(
            "sudo apt-get update && sudo apt-get install -y curl git",
            "Failed to install Linux dependencies"
        )
    elif system == "Darwin":
        install_homebrew()
        run_command(
            "brew install curl git",
            "Failed to install macOS dependencies"
        )
    install_python(system)
    install_node(system)

def install_ollama(system):
    """Install Ollama."""
    print("Installing Ollama...")
    ollama_install_script = "https://ollama.com/install.sh"
    install_path = "/tmp/ollama_install.sh"
    urllib.request.urlretrieve(ollama_install_script, install_path)
    run_command(f"chmod +x {install_path} && sudo {install_path}", "Failed to install Ollama")
    os.remove(install_path)

    # Configure Ollama to use all CPU cores or GPU
    cpu_count = multiprocessing.cpu_count()
    print(f"Configuring Ollama to use {cpu_count} CPU cores...")
    if system == "Linux" and shutil.which("nvidia-smi"):
        print("NVIDIA GPU detected. Enabling GPU support for Ollama...")
        run_command(
            "sudo systemctl set-environment OLLAMA_NUM_THREADS=0 OLLAMA_USE_GPU=1",
            "Failed to set Ollama GPU environment"
        )

def install_openwebui():
    """Install OpenWebUI."""
    print("Installing OpenWebUI...")
    install_dir = Path("/opt/open-webui")
    install_dir.mkdir(parents=True, exist_ok=True)

    # Create virtual environment
    run_command(
        f"python3.11 -m venv {install_dir}/venv",
        "Failed to create virtual environment"
    )

    # Install OpenWebUI
    run_command(
        f"{install_dir}/venv/bin/pip install --upgrade pip && {install_dir}/venv/bin/pip install open-webui",
        "Failed to install OpenWebUI"
    )

    # Set ownership
    user = getpass.getuser()
    run_command(f"sudo chown -R {user}:{user} {install_dir}", "Failed to set ownership")

def configure_services(system):
    """Configure systemd (Linux) or launchd (macOS) services."""
    print("Configuring services...")
    openwebui_venv = "/opt/open-webui/venv/bin/open-webui"
    ollama_service_content = ""
    openwebui_service_content = ""

    if system == "Linux":
        ollama_service_content = """[Unit]
Description=Ollama Service
After=network.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Restart=always
Environment="OLLAMA_NUM_THREADS=0"
Environment="OLLAMA_HOST=0.0.0.0:11434"

[Install]
WantedBy=multi-user.target
"""

        openwebui_service_content = """[Unit]
Description=Open WebUI Service
After=network.target

[Service]
ExecStart={openwebui_venv} serve --host 0.0.0.0 --port 8080
WorkingDirectory=/opt/open-webui
Restart=always
User={user}
Environment="OLLAMA_BASE_URL=http://localhost:11434"

[Install]
WantedBy=multi-user.target
""".format(openwebui_venv=openwebui_venv, user=getpass.getuser())

        with open("/tmp/ollama.service", "w") as f:
            f.write(ollama_service_content)
        with open("/tmp/openwebui.service", "w") as f:
            f.write(openwebui_service_content)

        run_command(
            "sudo mv /tmp/ollama.service /etc/systemd/system/ && sudo mv /tmp/openwebui.service /etc/systemd/system/ && "
            "sudo systemctl daemon-reload && sudo systemctl enable ollama.service && sudo systemctl enable openwebui.service && "
            "sudo systemctl start ollama.service && sudo systemctl start openwebui.service",
            "Failed to configure services"
        )

    elif system == "Darwin":
        ollama_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ollama.ollama</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/ollama</string>
        <string>serve</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>OLLAMA_NUM_THREADS</key>
        <string>0</string>
        <key>OLLAMA_HOST</key>
        <string>0.0.0.0:11434</string>
    </dict>
</dict>
</plist>
"""

        openwebui_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openwebui</string>
    <key>ProgramArguments</key>
    <array>
        <string>{openwebui_venv}</string>
        <string>serve</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8080</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>OLLAMA_BASE_URL</key>
        <string>http://localhost:11434</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>/opt/open-webui</string>
</dict>
</plist>
"""

        with open("/tmp/com.ollama.ollama.plist", "w") as f:
            f.write(ollama_plist)
        with open("/tmp/com.openwebui.plist", "w") as f:
            f.write(openwebui_plist)

        run_command(
            "sudo mv /tmp/com.ollama.ollama.plist /Library/LaunchDaemons/ && sudo mv /tmp/com.openwebui.plist /Library/LaunchDaemons/ && "
            "sudo chown root:wheel /Library/LaunchDaemons/com.ollama.ollama.plist /Library/LaunchDaemons/com.openwebui.plist && "
            "sudo launchctl load /Library/LaunchDaemons/com.ollama.ollama.plist && sudo launchctl load /Library/LaunchDaemons/com.openwebui.plist",
            "Failed to configure macOS services"
        )

def main():
    """Main installation function."""
    print("Starting Ollama and OpenWebUI installation...")
    system = check_system()
    install_dependencies(system)
    install_ollama(system)
    install_openwebui()
    configure_services(system)
    print("Installation complete! Access OpenWebUI at http://localhost:8080")
    print("To download a model, run: ollama pull llama3")

if __name__ == "__main__":
    main()
