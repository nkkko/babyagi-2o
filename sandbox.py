import os
import sys
import json
import traceback
from time import sleep
from daytona_sdk import Daytona, CreateWorkspaceParams, DaytonaConfig
from dotenv import load_dotenv

# Load environment variables from the user's environment
load_dotenv()

def comprehensive_error_logging(error: Exception, context: str = ""):
    """
    Provide comprehensive error logging with detailed information.
    """
    print(f"\n❌ Error in {context}:")
    print(f"Type: {type(error)}")
    print(f"Details: {str(error)}")
    print("Detailed Traceback:")
    traceback.print_exc()

def clone_repository_with_fallbacks(workspace):
    """
    Clone repository by uploading necessary files directly.
    """
    try:
        workspace_dir = "/tmp/babyagi/workspace"
        print(f"🔄 Setting up workspace in {workspace_dir}")

        # Clean up any existing directory
        workspace.process.exec(f"rm -rf {workspace_dir}")

        # Create workspace directory
        workspace.process.exec(f"mkdir -p {workspace_dir}")

        # Files to upload
        current_dir = os.path.dirname(os.path.abspath(__file__))
        files_to_copy = ['main.py', 'requirements.txt', 'get-pip.py']

        for file in files_to_copy:
            try:
                file_path = os.path.join(current_dir, file)
                with open(file_path, 'rb') as f:
                    content = f.read()
                workspace.fs.upload_file(f"{workspace_dir}/{file}", content)
                print(f"✅ Uploaded {file} to {workspace_dir}/{file}")

                # Verify file exists by listing
                ls_result = workspace.process.exec(f"ls -la {workspace_dir}/{file}")
                if ls_result and ls_result.result:
                    print(f"📄 {file} exists and is {len(content)} bytes")
                else:
                    raise RuntimeError(f"{file} not found after upload")
            except Exception as e:
                print(f"⚠️ Error uploading {file}: {e}")
                raise

        print(f"✅ Successfully set up workspace at {workspace_dir}")
        return workspace_dir

    except Exception as setup_error:
        print(f"❌ Workspace setup failed: {setup_error}")
        traceback.print_exc()
        raise RuntimeError(f"Could not set up workspace: {str(setup_error)}")

def install_pip(workspace, workspace_dir):
    """
    Install pip using get-pip.py.
    """
    try:
        print("\n🛠 Installing pip...")
        get_pip_path = f"{workspace_dir}/get-pip.py"
        install_pip_cmd = f"python3 {get_pip_path}"
        result = workspace.process.exec(install_pip_cmd)
        if result and result.result:
            print(f"📦 pip installation output:\n{result.result}")
        else:
            raise RuntimeError("pip installation failed without output")
        return True
    except Exception as e:
        print(f"❌ pip installation failed: {e}")
        traceback.print_exc()
        return False

def setup_virtualenv(workspace, workspace_dir):
    """
    Set up a Python virtual environment.
    """
    try:
        print("\n🛠 Setting up virtual environment...")
        venv_path = f"{workspace_dir}/venv"
        create_venv_cmd = f"python3 -m venv {venv_path}"
        result = workspace.process.exec(create_venv_cmd)
        if result and result.result:
            print(f"📦 Virtual environment setup output:\n{result.result}")

        # Upgrade pip in the virtual environment
        upgrade_pip_cmd = f"{venv_path}/bin/pip install --upgrade pip"
        result = workspace.process.exec(upgrade_pip_cmd)
        if result and result.result:
            print(f"📦 pip upgrade output:\n{result.result}")

        return venv_path
    except Exception as e:
        print(f"❌ Virtual environment setup failed: {e}")
        traceback.print_exc()
        return None

def install_dependencies(workspace, venv_path, workspace_dir):
    """
    Install dependencies from requirements.txt within the virtual environment.
    """
    try:
        print("\n📦 Installing dependencies...")
        install_reqs_cmd = f"{venv_path}/bin/pip install -r {workspace_dir}/requirements.txt"
        result = workspace.process.exec(install_reqs_cmd)
        if result and result.result:
            print(f"📦 Dependencies installation output:\n{result.result}")
        else:
            raise RuntimeError("Dependencies installation failed without output")

        # Install additional packages if needed
        additional_packages = ['litellm', 'python-dotenv', 'requests', 'anthropic', 'openai']
        for package in additional_packages:
            install_pkg_cmd = f"{venv_path}/bin/pip install {package}"
            result = workspace.process.exec(install_pkg_cmd)
            if result and result.result:
                print(f"📦 Installed {package}:\n{result.result}")
            else:
                raise RuntimeError(f"Installation of {package} failed without output")

        return True
    except Exception as e:
        print(f"❌ Dependencies installation failed: {e}")
        traceback.print_exc()
        return False

def run_babyagi(workspace, venv_path, workspace_dir, user_input):
    """
    Run main.py within the virtual environment and capture output.
    """
    try:
        print("\n🚀 Running BabyAGI...")
        # Command to run main.py and redirect output to output.txt
        run_cmd = f"{venv_path}/bin/python {workspace_dir}/main.py \"{user_input}\" > {workspace_dir}/output.txt 2>&1"
        result = workspace.process.exec(run_cmd)
        if result:
            print("✅ BabyAGI execution command issued.")

        # Wait for the script to finish
        sleep(5)  # Adjust sleep time as needed

        # Retrieve the output file
        print("\n📥 Downloading BabyAGI output...")
        output_content = workspace.fs.download_file(f"{workspace_dir}/output.txt")
        if output_content:
            output = output_content.decode('utf-8')
            print("\n=== BabyAGI Output ===")
            print(output)
            return output
        else:
            raise RuntimeError("Failed to retrieve output.txt")

    except Exception as e:
        print(f"❌ Running BabyAGI failed: {e}")
        traceback.print_exc()
        return None

def setup_environment(workspace, workspace_dir, user_input):
    """
    Set up environment variables by creating a .env file.
    """
    try:
        print("\n🔧 Setting up environment variables...")
        env_vars = {
            "OBJECTIVE": user_input or "Solve a complex problem",
            "LITELLM_MODEL": os.getenv("LITELLM_MODEL", "gpt-4o-mini"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": f"{workspace_dir}/venv/lib/python3.11/site-packages",
            "PATH": f"{workspace_dir}/venv/bin:$PATH"
        }

        env_content = "\n".join([f"{key}={value}" for key, value in env_vars.items() if value])
        env_path = f"{workspace_dir}/.env"
        workspace.fs.upload_file(env_path, env_content.encode())
        print(f"✅ Created .env file at {env_path}")

        # Verify .env file
        verify_env_cmd = f"cat {env_path}"
        result = workspace.process.exec(verify_env_cmd)
        if result and result.result:
            print("\n📄 .env file contents:")
            print(result.result)
        else:
            raise RuntimeError("Failed to verify .env file")

        return True

    except Exception as e:
        print(f"❌ Setting up environment variables failed: {e}")
        traceback.print_exc()
        return False

def setup_babyagi_workspace(user_input: str):
    """
    Set up BabyAGI workspace with comprehensive error handling.
    """
    try:
        # Create Daytona client
        config = DaytonaConfig(
            api_key=os.getenv("DAYTONA_API_KEY"),
            server_url=os.getenv("DAYTONA_SERVER_URL"),
            target=os.getenv("DAYTONA_TARGET", "local")
        )
        daytona_client = Daytona(config=config)

        # Create workspace
        print("\n🔄 Attempting Workspace Creation Strategy 1")
        workspace = daytona_client.create(params=CreateWorkspaceParams(
            language="python",
            id=f"babyagi-{uuid.uuid4().hex[:8]}"
        ))
        if not workspace:
            raise RuntimeError("Failed to create workspace with Strategy 1")
        print("✅ Workspace created successfully with Strategy 1")

        # Clone repository by uploading files
        workspace_dir = clone_repository_with_fallbacks(workspace)

        # Set up environment variables
        if not setup_environment(workspace, workspace_dir, user_input):
            raise RuntimeError("Failed to set up environment variables")

        # Install pip
        if not install_pip(workspace, workspace_dir):
            raise RuntimeError("Failed to install pip")

        # Set up virtual environment
        venv_path = setup_virtualenv(workspace, workspace_dir)
        if not venv_path:
            raise RuntimeError("Failed to set up virtual environment")

        # Install dependencies
        if not install_dependencies(workspace, venv_path, workspace_dir):
            raise RuntimeError("Failed to install dependencies")

        # Run BabyAGI
        output = run_babyagi(workspace, venv_path, workspace_dir, user_input)

        return {
            "workspace": workspace,
            "result": output,
            "path": workspace_dir
        }

    except Exception as e:
        comprehensive_error_logging(e, "Workspace Setup")
        return None

def main():
    """
    Main execution function.
    """
    try:
        # Validate environment
        if not os.path.exists(".env"):
            print("❌ Error: .env file not found in the current directory")
            return

        # Load environment variables
        load_dotenv(override=True)

        # Get user input
        user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("🤔 Enter your task for BabyAGI: ")

        # Run BabyAGI
        result = setup_babyagi_workspace(user_input)

        if result:
            workspace = result["workspace"]
            output = result["result"]

            # Display the output
            if output:
                print("\n🤖 BabyAGI Output:")
                print(output)

            try:
                # Cleanup
                print("\n🧹 Cleaning up workspace...")
                daytona_client = Daytona().client  # Assuming Daytona can remove the workspace
                daytona_client.remove(workspace)
                print("✅ Task completed successfully!")
            except Exception as e:
                print(f"❌ Cleanup failed: {e}")
        else:
            print("❌ BabyAGI execution failed")

    except Exception as e:
        comprehensive_error_logging(e, "Main Execution")

if __name__ == "__main__":
    main()