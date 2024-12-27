"""
This file implements a code generation and execution system that:
1. Generates code using OpenAI's language model
2. Executes the generated code in a secure sandbox environment

Key components:
- Uses OpenAI API to generate code based on user prompts
- Uses Daytona SDK to create isolated workspaces for safe code execution
- Includes error handling and environment validation
"""

# Import required libraries:
# - langchain_openai: For interacting with OpenAI's API
# - PromptTemplate: For creating structured prompts
# - Daytona: For creating secure sandbox environments
# - os, dotenv: For handling environment variables

from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get required API keys and URLs from environment variables
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables")
if not os.getenv("DAYTONA_API_KEY"):
    raise ValueError("DAYTONA_API_KEY not found in environment variables")
if not os.getenv("DAYTONA_SERVER_URL"):
    raise ValueError("DAYTONA_SERVER_URL not found in environment variables")

# Get the required environment variables with type checking
daytona_api_key = os.getenv("DAYTONA_API_KEY")
daytona_server_url = os.getenv("DAYTONA_SERVER_URL")

if not daytona_api_key or not daytona_server_url:
    raise ValueError("Missing required environment variables")

# Create a prompt template for code generation
code_generation_prompt = PromptTemplate(
    input_variables=["language", "task"],
    template="""
You are an expert {language} developer. Write clean, efficient, and well-documented code for the following task:

Task: {task}

Please provide:
1. A complete implementation
2. Brief comments explaining key parts
3. Example usage if applicable

Code:
"""
)

# Initialize the LLM with lower temperature for more focused code generation
llm = OpenAI(
    temperature=0.2,
    max_tokens=1000
)

# Create the code generation chain using RunnableSequence
code_chain = code_generation_prompt | llm

def generate_code(language: str, task: str):
    """
    Generate code for a given task in the specified programming language.
    """
    return code_chain.invoke({
        "language": language,
        "task": task
    })

def execute_in_sandbox(code: str):
    """
    Execute generated code in a Daytona workspace sandbox.
    """
    # Initialize Daytona with your configuration
    config = DaytonaConfig(
        api_key=str(daytona_api_key),
        server_url=str(daytona_server_url),
        target="local"
    )
    daytona = Daytona(config=config)

    # Create a Python workspace
    params = CreateWorkspaceParams(language="python")
    workspace = daytona.create(params=params)

    try:
        # Execute the code in the sandbox
        response = workspace.process.code_run(code)

        if response.code != 0:
            return f"Error: {response.code} {response.result}"
        return response.result
    finally:
        # Always clean up the workspace
        daytona.remove(workspace)

# Example usage
if __name__ == "__main__":
    # Generate Python code
    task = "Create a function that takes a list of numbers and returns the moving average with a specified window size"
    generated_code = generate_code("Python", task)

    # Execute in sandbox
    result = execute_in_sandbox(generated_code)
    print("Code execution result:", result)