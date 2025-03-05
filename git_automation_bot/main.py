import os
import json
import random
import time
import subprocess
import openai
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Load configuration
CONFIG_FILE = "config.json"
with open(CONFIG_FILE, "r") as file:
    config = json.load(file)

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def clone_repo(repo_name, repo_url):
    """Clones the repo if not already cloned."""
    if not os.path.exists(repo_name):
        print(f"Cloning repository {repo_name}...")
        subprocess.run(["git", "clone", repo_url, repo_name], check=True)
    else:
        print(f"Repository {repo_name} already exists.")

def strip_code_fences(generated_text):
    """
    Removes triple backticks and leftover single backticks
    so the code has no markdown formatting.
    """
    if "```" in generated_text:
        parts = generated_text.split("```")
        if len(parts) > 1:
            code = parts[1]
        else:
            code = parts[0]
    else:
        code = generated_text
    
    code = code.replace("`", "")
    return code.strip()

def generate_code(prompt):
    """
    Calls your custom GPT model and returns only the generated code,
    ensuring we remove backticks.
    """
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": prompt}]
    )
    raw_text = response.choices[0].message.content.strip()
    clean_code = strip_code_fences(raw_text)
    return clean_code

def generate_commit_message_from_code(code):
    """
    Uses GPT to generate a short commit message based on the code content.
    The message should be random but relevant, with no references to GPT or disclaimers.
    """
    client = openai.OpenAI()
    commit_prompt = (
        "Analyze the following code snippet and create a short Git commit message. "
        "The commit message should be relevant to what the code does, "
        "concise, and contain no references to GPT or disclaimers. "
        "Use 12 words or fewer.\n\n"
        f"{code}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": commit_prompt}]
    )
    commit_message = response.choices[0].message.content.strip()
    # Remove any stray backticks or code fences
    commit_message = commit_message.replace("`", "").replace("```", "")
    return commit_message

def get_random_filename(naming_convention, extension):
    """Generates a filename using the specified naming convention and extension."""
    if naming_convention == "snake_case":
        base_name = "generated_code_example"
    elif naming_convention == "camelCase":
        base_name = "generatedCodeExample"
    elif naming_convention == "kebab-case":
        base_name = "generated-code-example"
    else:
        base_name = "generated_code"
    return f"{base_name}{extension}"

def commit_and_push(repo_name, commit_message):
    """Stages, commits, and pushes changes to the remote repo."""
    os.chdir(repo_name)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    # Detect current branch (could be 'main' or 'master' or something else)
    current_branch = subprocess.check_output(["git", "branch", "--show-current"]).strip().decode("utf-8")
    subprocess.run(["git", "push", "origin", current_branch], check=True)
    os.chdir("..")

def automate_commits(repo_name):
    """
    Main function:
    1) Clones the repo if needed.
    2) Waits until the current time is between 'starting_time' and 'ending_time'.
    3) Performs random commits (between 'minimum_commits' and 'maximum_commits').
    4) Stops if the window closes.
    """
    repo_config = next((r for r in config["repositories"] if r["name"] == repo_name), None)
    if not repo_config:
        print("Repository not found in config.")
        return
    
    # Clone if needed
    clone_repo(repo_name, repo_config["repo_url"])
    
    # Parse times from config (e.g., "05:00 PM" -> datetime.time(17, 0))
    start_time = datetime.strptime(repo_config["starting_time"], "%I:%M %p").time()
    end_time = datetime.strptime(repo_config["ending_time"], "%I:%M %p").time()
    
    # Parse commit limits
    min_commits = int(repo_config["minimum_commits"])
    max_commits = int(repo_config["maximum_commits"])
    
    # Wait until we're within the allowed time window or we've passed it
    while True:
        now = datetime.now().time()
        if start_time <= now <= end_time:
            print(f"We're in the commit window ({repo_config['starting_time']} - {repo_config['ending_time']}).")
            break
        elif now > end_time:
            print(f"We've passed the end time ({repo_config['ending_time']}). Exiting...")
            return
        else:
            # Not yet at start_time
            print("Not yet in commit window. Sleeping 60s...")
            time.sleep(60)
    
    # Now we are in the window, let's do the commits
    commit_count = random.randint(min_commits, max_commits)
    for _ in range(commit_count):
        # Check if we are still within the time window
        now = datetime.now().time()
        if now > end_time:
            print(f"Reached the end time ({repo_config['ending_time']}). Stopping commits...")
            break
        
        # Pick a random folder from config
        folder = random.choice(repo_config["folders"])
        directory = os.path.join(repo_name, folder)
        os.makedirs(directory, exist_ok=True)  # Ensure the folder exists
        
        # Build a minimal prompt to produce code only (no comments).
        extension = repo_config["file_extension"]
        prompt = (
            f"Generate valid code for a feature in the {folder} folder. "
            f"Output only code for the {extension} file with no comments or explanations."
        )
        
        # Build a random filename based on naming convention & extension
        filename = get_random_filename(repo_config["file_naming_convention"], extension)
        file_path = os.path.join(directory, filename)
        
        # Generate code
        code = generate_code(prompt)
        
        # Write the code to the file
        with open(file_path, "w") as file:
            file.write(code)
        
        # Generate a commit message using the code content
        commit_message = generate_commit_message_from_code(code)
        
        # Commit & push
        commit_and_push(repo_name, commit_message)
        
        # Random sleep between commits (5-15 minutes)
        time.sleep(random.randint(300, 900))

if __name__ == "__main__":
    repo_name = input("Enter repository name: ")
    automate_commits(repo_name)
