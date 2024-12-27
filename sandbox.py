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
        "/tmp/babyagi",
        f"/tmp/babyagi-{uuid.uuid4().hex[:8]}",
        "/workspace/babyagi",
        "~/babyagi"
    ]

    for path in potential_paths:
        try:
            print(f"🔄 Attempting to clone repository to {path}")

            # Ensure path exists
            os.makedirs(path, exist_ok=True)

            # Clone repository
            workspace.git.clone(
                url="https://github.com/nkkko/babyagi-2o.git",
                path=path
            )

            print(f"✅ Successfully cloned to {path}")
            return path
        except Exception as clone_error:
            print(f"❌ Clone failed to {path}: {clone_error}")
            continue

    raise RuntimeError("Could not clone repository to any path")

def setup_environment(workspace, babyagi_path, user_input):
    """
    Set up environment variables and .env file.
    """
    env_vars = {
        "OBJECTIVE": user_input or "Solve a complex problem",
        "LITELLM_MODEL": os.getenv("LITELLM_MODEL", ""),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "")
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
    Run BabyAGI with multiple execution strategies and capture output.
    """
    run_commands = [
        f"python main.py \"{user_input}\""
    ]

    for cmd in run_commands:
        try:
            print(f"🚀 Running BabyAGI with: {cmd}")
            result = workspace.process.exec(cmd, cwd=babyagi_path)
            if result and result.result:
                return result.result  # This contains the output from main.py
            print(f"⚠️ No output received from command: {cmd}")
        except Exception as e:
            print(f"❌ Execution failed: {e}")
            continue

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

        # Clone repository
        babyagi_path = clone_repository_with_fallbacks(workspace)

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