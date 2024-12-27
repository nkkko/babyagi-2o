import os
import sys
import uuid
import traceback
from typing import Optional, Dict, Any

from daytona_sdk import Daytona, CreateWorkspaceParams, DaytonaConfig
from dotenv import load_dotenv

def comprehensive_error_logging(error: Exception, context: str = ""):
    """
    Provide comprehensive error logging with detailed information.
    """
    print(f"\n❌ Error in {context}:")
    print(f"Type: {type(error)}")
    print(f"Details: {str(error)}")
    print("Detailed Traceback:")
    traceback.print_exc()

def create_resilient_workspace(daytona_client):
    """
    Create a workspace with multiple resilience strategies.
    """
    workspace_creation_strategies = [
        # Strategy 1: Create with explicit parameters
        lambda: daytona_client.create(params=CreateWorkspaceParams(
            language="python",
            id=f"babyagi-{uuid.uuid4().hex[:8]}"
        )),

        # Strategy 2: Default creation
        lambda: daytona_client.create(),

        # Strategy 3: Try to get current workspace
        lambda: daytona_client.get_current_workspace()
            if os.getenv("DAYTONA_WORKSPACE_ID")
            else None
    ]

    for i, strategy in enumerate(workspace_creation_strategies, 1):
        try:
            print(f"\n🔄 Attempting Workspace Creation Strategy {i}")
            workspace = strategy()
            if workspace:
                print(f"✅ Workspace created successfully with Strategy {i}")
                return workspace
        except Exception as e:
            print(f"❌ Strategy {i} failed: {e}")

    return None

def clone_repository_with_fallbacks(workspace):
    """
    Clone repository with multiple path fallbacks.
    """
    potential_paths = [
        "/tmp/babyagi"
    ]

    for path in potential_paths:
        try:
            print(f"🔄 Attempting to clone repository to {path}")

            # Clean up any existing directory
            workspace.process.exec(f"rm -rf {path}")
            workspace.process.exec(f"mkdir -p {path}")

            # Clone repository
            clone_result = workspace.git.clone(
                url="https://github.com/nkkko/babyagi-2o.git",
                path=path
            )

            # Verify the clone and copy files if needed
            print("📋 Copying current directory contents to workspace...")

            # List current directory contents
            current_dir = os.path.dirname(os.path.abspath(__file__))
            files_to_copy = ['main.py', 'requirements.txt']

            for file in files_to_copy:
                try:
                    with open(os.path.join(current_dir, file), 'rb') as f:
                        content = f.read()
                        workspace.fs.upload_file(f"{path}/{file}", content)
                        print(f"✅ Uploaded {file}")
                except Exception as e:
                    print(f"⚠️ Error copying {file}: {e}")

            # Verify the files exist
            result = workspace.process.exec("ls -la", cwd=path)
            if result and result.result:
                print(f"📁 Directory contents of {path}:")
                print(result.result)

                # Check if main.py exists
                check_main = workspace.process.exec(f"ls -l main.py", cwd=path)
                if check_main and check_main.result:
                    print(f"✅ Successfully set up workspace at {path}")
                    return path
                else:
                    print(f"⚠️ main.py not found in {path}")
                    continue

        except Exception as setup_error:
            print(f"❌ Setup failed for {path}: {setup_error}")
            continue

    raise RuntimeError("Could not set up workspace in any path")

def setup_environment(workspace, babyagi_path, user_input):
    """
    Set up environment variables and .env file.
    """
    env_vars = {
        "OBJECTIVE": user_input or "Solve a complex problem",
        "LITELLM_MODEL": os.getenv("LITELLM_MODEL", ""),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "PYTHONUNBUFFERED": "1"  # Add this to ensure unbuffered output
    }

    # Filter out empty values and create .env content
    filtered_env_vars = {k: v for k, v in env_vars.items() if v}
    env_content = "\n".join([f"{key}={value}" for key, value in filtered_env_vars.items()])

    # Create .env file
    env_path = os.path.join(babyagi_path, ".env")
    workspace.fs.upload_file(env_path, env_content.encode())
    print(f"✅ .env file created at {env_path}")

    return env_vars

def install_dependencies(workspace, babyagi_path):
    """
    Install dependencies with multiple fallback strategies.
    """
    dependency_commands = [
        "pip install -r requirements.txt",
        "python -m pip install -r requirements.txt",
        "pip3 install -r requirements.txt"
    ]

    for cmd in dependency_commands:
        try:
            print(f"🔧 Installing dependencies with: {cmd}")
            result = workspace.process.exec(cmd, cwd=babyagi_path)
            print(f"📦 Result: {result.result}")
            return True
        except Exception as e:
            print(f"❌ Dependency installation failed: {e}")
            continue

    return False

def run_babyagi(workspace, babyagi_path, user_input):
    """
    Run BabyAGI with output capture.
    """
    try:
        # Ensure babyagi_path is properly formatted and exists
        print(f"\n🔍 Verifying workspace setup:")
        ls_result = workspace.process.exec("ls -la", cwd=babyagi_path)
        print("Directory contents:")
        print(ls_result.result if ls_result and ls_result.result else "No files found")

        # Construct the correct path to main.py
        main_script = os.path.join(babyagi_path, "main.py")

        # Verify main.py exists
        print(f"\n🔍 Checking for main.py:")
        check_main = workspace.process.exec(f"ls -l main.py", cwd=babyagi_path)
        if not (check_main and check_main.result):
            print("⚠️ main.py not found in workspace")
            return None

        # First attempt with relative path
        run_command = f"python main.py \"{user_input}\""
        print(f"\n🚀 Running BabyAGI with: {run_command}")
        print(f"📂 Working directory: {babyagi_path}")

        result = workspace.process.exec(
            command=run_command,
            cwd=babyagi_path
        )

        if result and result.result:
            print("\n=== BabyAGI Output ===")
            print(result.result)
            return result.result

        # Second attempt with python -u
        print("\n🔄 Retrying with unbuffered output...")
        run_command = f"python -u main.py \"{user_input}\""
        result = workspace.process.exec(
            command=run_command,
            cwd=babyagi_path
        )

        if result and result.result:
            print("\n=== BabyAGI Output (Unbuffered) ===")
            print(result.result)
            return result.result

        # Final attempt with absolute path
        print("\n🔄 Retrying with absolute path...")
        run_command = f"cd {babyagi_path} && python main.py \"{user_input}\""
        result = workspace.process.exec(command=run_command)

        if result and result.result:
            print("\n=== BabyAGI Output (Absolute Path) ===")
            print(result.result)
            return result.result

        print("\n⚠️ No output received from any attempt")

        # Additional debugging information
        print("\n📁 Final workspace check:")
        workspace.process.exec("pwd", cwd=babyagi_path)
        workspace.process.exec("ls -la", cwd=babyagi_path)

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        traceback.print_exc()

    return None

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
        workspace = create_resilient_workspace(daytona_client)
        if not workspace:
            raise RuntimeError("Failed to create workspace")

        try:
            # Set up workspace
            babyagi_path = clone_repository_with_fallbacks(workspace)
            if not babyagi_path:
                raise RuntimeError("Failed to set up workspace directory")

            # Verify workspace setup
            print("\n🔍 Verifying workspace setup:")
            result = workspace.process.exec("ls -la", cwd=babyagi_path)
            print(result.result if result and result.result else "No files found")

            # Setup environment
            setup_environment(workspace, babyagi_path, user_input)

            # Install dependencies
            if not install_dependencies(workspace, babyagi_path):
                raise RuntimeError("Failed to install dependencies")

            # Run BabyAGI
            result = run_babyagi(workspace, babyagi_path, user_input)

            return {
                "workspace": workspace,
                "result": result,
                "path": babyagi_path
            }

        except Exception as e:
            print(f"❌ Error during workspace setup: {e}")
            traceback.print_exc()
            return None

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
            print("❌ Error: .env file not found")
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
                Daytona().remove(workspace)
                print("✅ Task completed successfully!")
            except Exception as e:
                print(f"❌ Cleanup failed: {e}")
        else:
            print("❌ BabyAGI execution failed")

    except Exception as e:
        comprehensive_error_logging(e, "Main Execution")

if __name__ == "__main__":
    main()