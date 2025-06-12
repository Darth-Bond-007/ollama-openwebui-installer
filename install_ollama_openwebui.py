import os
import platform
import subprocess
import sys
import shutil
import multiprocessing
import urllib.request
import getpass
from pathlib import Path
import time
import tempfile

def check_system():
    """Check if the system is macOS or Linux."""
    system = platform.system()
    if system not in ["Linux", "Darwin"]:
        print("Error: This installer supports only macOS and Linux.")
        sys.exit(1)
    return system

def run_command(command, error_message, silent=False, retries=1):
    """Run a shell command with retries and handle errors."""
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                text=True,
                capture_output=True
            )
            if not silent:
                print(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Attempt {attempt} failed: {e}")
            print(f"Command output: {e.output}")
            print(f"Command stderr: {e.stderr}")
            if attempt == retries:
                print(f"{error_message}: {e}")
                raise
            print("Retrying...")
            time.sleep(2)

def install_homebrew():
    """Install Homebrew on macOS if not present."""
    print("Checking for Homebrew...")
    brew_path = "/opt/homebrew/bin" if platform.machine().startswith("arm") else "/usr/local/bin"
    if shutil.which("brew") is None:
        print("Installing Homebrew...")
        homebrew_install = (
            '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        )
        run_command(homebrew_install, "Failed to install Homebrew", retries=2)
    # Fix permissions
    try:
        run_command(
            f"sudo chown -R $(whoami):admin {brew_path} /opt/homebrew /opt/homebrew/Cellar",
            "Failed to fix Homebrew permissions",
            retries=2
        )
    except subprocess.CalledProcessError:
        print("Warning: Failed to fix Homebrew permissions, continuing...")
    # Clean up Homebrew
    try:
        run_command("brew cleanup", "Failed to clean Homebrew", retries=2, silent=True)
        run_command("brew update-reset", "Failed to reset Homebrew", retries=2, silent=True)
    except subprocess.CalledProcessError:
        print("Warning: Failed to clean or reset Homebrew, continuing...")
    # Check Homebrew health, ignore failures
    try:
        run_command("brew doctor", "Homebrew health check failed", retries=2)
    except subprocess.CalledProcessError:
        print("Warning: brew doctor failed, continuing...")
    try:
        run_command("brew update", "Failed to update Homebrew", retries=2)
    except subprocess.CalledProcessError:
        print("Warning: Failed to update Homebrew, continuing...")
    os.environ["PATH"] = f"{brew_path}:{os.environ['PATH']}"
    try:
        run_command(
            f"echo 'export PATH={brew_path}:$PATH' >> ~/.zshrc",
            "Failed to update PATH"
        )
    except subprocess.CalledProcessError:
        print("Warning: Failed to update PATH in ~/.zshrc, continuing...")

def check_python_version():
    """Check if the current Python is 3.11."""
    python_version = sys.version_info
    return python_version.major == 3 and python_version.minor == 11

def install_python(system):
    """Install Python 3.11 and return its binary path."""
    print("Checking for Python 3.11...")
    python_bin = "/opt/homebrew/bin/python3.11" if system == "Darwin" else "python3.11"
    try:
        python_version = run_command(
            f"{python_bin} --version",
            "Python 3.11 check failed",
            silent=False
        )
        if "3.11" in python_version:
            print(f"Python 3.11 found: {python_version.strip()}")
            return python_bin
    except subprocess.CalledProcessError:
        pass

    print("Installing Python 3.11...")
    if system == "Linux":
        try:
            run_command(
                "sudo apt-get update && sudo apt-get install -y software-properties-common && "
                "sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update && "
                "sudo apt-get install -y python3.11 python3.11-dev python3.11-venv",
                "Failed to install Python 3.11 on Linux",
                retries=2
            )
            python_bin = "python3.11"
        except subprocess.CalledProcessError:
            print("Error: Failed to install Python 3.11 on Linux.")
            sys.exit(1)
    elif system == "Darwin":
        try:
            install_homebrew()
            print("Attempting to install Python 3.11 via Homebrew...")
            try:
                run_command(
                    "brew unlink python@3.13 || true",
                    "Failed to unlink Python 3.13",
                    silent=True
                )
                brew_list = run_command(
                    "brew list python@3.11 || true",
                    "Failed to check installed packages",
                    silent=True
                )
                if "python@3.11" in brew_list:
                    print("Python 3.11 is installed but not linked.")
                else:
                    run_command(
                        "brew install python@3.11",
                        "Failed to install Python 3.11 via Homebrew",
                        retries=2
                    )
                run_command(
                    "brew link --force python@3.11",
                    "Failed to link Python 3.11",
                    retries=2
                )
                python_bin = "/opt/homebrew/bin/python3.11"
                if os.path.exists(python_bin):
                    python_version = run_command(
                        f"{python_bin} --version",
                        "Python 3.11 verification failed after Homebrew install",
                        silent=False
                    )
                    print(f"Python 3.11 installed via Homebrew: {python_version.strip()}")
                    return python_bin
                else:
                    raise subprocess.CalledProcessError(1, "brew install", "Python 3.11 binary not found")
            except subprocess.CalledProcessError:
                print("Homebrew installation failed, falling back to Python.org installer...")
        except Exception as e:
            print(f"Homebrew setup failed: {e}, falling back to Python.org installer...")
        temp_dir = tempfile.mkdtemp()
        python_pkg = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg"
        pkg_path = os.path.join(temp_dir, "python-3.11.9-macos11.pkg")
        urllib.request.urlretrieve(python_pkg, pkg_path)
        try:
            run_command(
                f"sudo installer -pkg {pkg_path} -target /",
                "Failed to install Python 3.11 from package",
                retries=2
            )
        finally:
            os.remove(pkg_path)
        python_bin = "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11"
        os.environ["PATH"] = f"{os.path.dirname(python_bin)}:{os.environ['PATH']}"
        try:
            run_command(
                f"echo 'export PATH={os.path.dirname(python_bin)}:$PATH' >> ~/.zshrc",
                "Failed to update PATH for Python 3.11"
            )
        except subprocess.CalledProcessError:
            print("Warning: Failed to update PATH in ~/.zshrc, continuing...")

    try:
        python_version = run_command(
            f"{python_bin} --version",
            "Python 3.11 final verification failed",
            silent=False
        )
        print(f"Python 3.11 installed: {python_version.strip()}")
        return python_bin
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
            silent=False
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
            "Failed to install Node.js on Linux",
            retries=2
        )
    elif system == "Darwin":
        install_homebrew()
        run_command(
            "brew install node@20 || true",
            "Failed to install Node.js on macOS",
            retries=2
        )

        try:
            run_command("brew link --overwrite --force node@20", "Failed to link Node.js")
        except subprocess.CalledProcessError:
            print("Warning: Failed to force-link node@20, attempting manual symlink...")

            node_path = "/opt/homebrew/opt/node@20/bin/node"
            npm_path = "/opt/homebrew/opt/node@20/bin/npm"

            if os.path.exists(node_path):
                run_command(f"sudo ln -sf {node_path} /opt/homebrew/bin/node", "Failed to symlink node binary")
            if os.path.exists(npm_path):
                run_command(f"sudo ln -sf {npm_path} /opt/homebrew/bin/npm", "Failed to symlink npm binary")

        # Ensure PATH persistence
        run_command(
            "echo 'export PATH=/opt/homebrew/bin:$PATH' >> ~/.zshrc",
            "Failed to export Homebrew path"
        )

def install_dependencies(system):
    """Install system dependencies."""
    print("Installing system dependencies...")
    if system == "Linux":
        run_command(
            "sudo apt-get update && sudo apt-get install -y curl git",
            "Failed to install Linux dependencies",
            retries=2
        )
    elif system == "Darwin":
        install_homebrew()
        run_command(
            "brew install curl git",
            "Failed to install macOS dependencies",
            retries=2
        )
    python_bin = install_python(system)
    install_node(system)
    return python_bin

def install_ollama(system):
    """Install Ollama."""
    print("Installing Ollama...")
    ollama_install_script = "https://ollama.com/install.sh"
    install_path = "/tmp/ollama_install.sh"
    urllib.request.urlretrieve(ollama_install_script, install_path)
    run_command(f"chmod +x {install_path} && sudo {install_path}", "Failed to install Ollama")
    os.remove(install_path)

    cpu_count = multiprocessing.cpu_count()
    print(f"Configuring Ollama to use {cpu_count} CPU cores...")
    if system == "Linux" and shutil.which("nvidia-smi"):
        print("NVIDIA GPU detected. Enabling GPU support for Ollama...")
        run_command(
            "sudo systemctl set-environment OLLAMA_NUM_THREADS=0 OLLAMA_USE_GPU=1",
            "Failed to set Ollama GPU environment"
        )

def install_openwebui(python_bin):
    """Install OpenWebUI."""
    print("Installing OpenWebUI...")
    install_dir = Path("/opt/open-webui")
    install_dir.mkdir(parents=True, exist_ok=True)

    run_command(
        f"{python_bin} -m venv {install_dir}/venv",
        "Failed to create virtual environment"
    )

    run_command(
        f"{install_dir}/venv/bin/pip install --upgrade pip && {install_dir}/venv/bin/pip install open-webui",
        "Failed to install OpenWebUI"
    )

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
    python_bin = install_python(system)
    if not check_python_version():
        print("Current Python is not 3.11, re-running with Python 3.11...")
        if os.path.exists(python_bin):
            os.execv(python_bin, [python_bin, *sys.argv])
        else:
            print(f"Error: Python 3.11 binary ({python_bin}) not found after installation.")
            sys.exit(1)

    install_node(system)
    install_ollama(system)
    install_openwebui(python_bin)
    configure_services(system)
    print("Installation complete! Access OpenWebUI at http://localhost:8080")
    print("To download a model, run: ollama pull llama3")

if __name__ == "__main__":
    main()
