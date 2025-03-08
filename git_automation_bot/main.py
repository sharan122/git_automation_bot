import os
import json
import random
import time
import subprocess
import openai
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Load configuration
CONFIG_FILE = "config.json"
with open(CONFIG_FILE, "r") as file:
    config = json.load(file)

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")


def clone_repo(repo_name: str, repo_url: str):
    """Clones the repo if not already cloned."""
    if not os.path.exists(repo_name):
        print(f"Cloning repository {repo_name}...")
        subprocess.run(["git", "clone", repo_url, repo_name], check=True)
    else:
        print(f"Repository {repo_name} already exists.")


def strip_code_fences(code: str) -> str:


    code = re.sub(r"```+", "", code).strip()


    code = code.replace("`", "").strip()


    if code.lower().startswith("python"):
        code = code[6:].strip()

    return code


def apply_naming_convention(raw_filename: str, naming_convention: str, extension: str) -> str:
    """
    Applies snake_case, camelCase, or kebab-case to the raw filename,
    then appends the file extension. Also does minimal cleanup.
    """
    # Remove any unwanted characters except alphanumerics, underscore, dash
    cleaned = "".join(ch for ch in raw_filename if ch.isalnum() or ch in ["_", "-"])

    if naming_convention == "snake_case":
        # Convert leftover dashes to underscores and make lowercase
        cleaned = cleaned.replace("-", "_").lower()
    elif naming_convention == "camelCase":
        # Convert underscores/dashes to minimal camelCase
        parts = cleaned.replace("-", "_").split("_")
        if len(parts) > 1:
            cleaned = parts[0].lower() + "".join(word.capitalize() for word in parts[1:])
        else:
            cleaned = cleaned[0].lower() + cleaned[1:] if cleaned else "file"
    elif naming_convention == "kebab-case":
        # Convert underscores to dashes, make lowercase
        cleaned = cleaned.replace("_", "-").lower()
    else:
        # Fallback if unknown convention
        cleaned = cleaned.lower()

    if not cleaned:
        cleaned = "file"

    return f"{cleaned}{extension}"


def generate_code_file_and_commit(
    folder: str,
    extension: str,
    naming_convention: str
    ) -> (str, str, str): # type: ignore


    prompt = f"""
You will produce three items in strict JSON format (no markdown, no extra text):
1. code_snippet: A detailed, functional code snippet for a feature in the '{folder}' folder for a '{extension}' file.
   - No comments or explanations.
   - No disclaimers or GPT references.
   - Must demonstrate real logic or functionality.
2. file_name: A short (2-3 words) file name describing the code snippet's logic
   - Must be unique, standard, and relevant to the snippet's content.
   - No disclaimers or GPT references.
   - Note that the file name should be related to the logic of the code and should be unique, should not follow a same pattern and each time create a new file name
   - file name should look like created by human
   - avoid using py before the file name extension
3. commit_message: A unique, human-sounding Git commit message analyzing the code snippet.
   - Avoid 'added' or 'implemented' at the start.
   - Under 15 words, no disclaimers or GPT references.

Return exactly this JSON structure with keys: code_snippet, file_name, commit_message
and nothing else. Example:

{{
  "code_snippet": "...",
  "file_name": "...",
  "commit_message": "..."
}}
"""

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7  # You can adjust temperature for more or less creativity
    )
    raw_output = response.choices[0].message.content.strip()

    # Attempt to parse the JSON
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        # If GPT doesn't return valid JSON, fallback or re-try
        # For simplicity, we do a minimal fallback
        print("GPT returned invalid JSON. Raw output:", raw_output)
        return ("", "file.py", "Commit message")

    # Extract fields from JSON
    code_snippet = parsed.get("code_snippet", "")
    file_name = parsed.get("file_name", "file")
    commit_message = parsed.get("commit_message", "Update code")

    # Clean up the code snippet
    code_snippet = strip_code_fences(code_snippet)

    # Apply naming convention to the file_name
    final_file_name = apply_naming_convention(file_name, naming_convention, extension)

    # Also strip out any leftover code fences or backticks in commit message
    commit_message = strip_code_fences(commit_message)

    return code_snippet, final_file_name, commit_message


def commit_and_push(repo_name: str, commit_message: str):
    """Stages, commits, and pushes changes to the remote repo."""
    os.chdir(repo_name)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    # Detect current branch (could be 'main', 'master', etc.)
    current_branch = subprocess.check_output(["git", "branch", "--show-current"]).strip().decode("utf-8")
    subprocess.run(["git", "push", "origin", current_branch], check=True)
    os.chdir("..")


def automate_commits(repo_config: dict):
    repo_name = repo_config["name"]
    repo_url = repo_config["repo_url"]

    # Clone if needed
    clone_repo(repo_name, repo_url)

    # Parse times (e.g., "05:00 PM" -> datetime.time(17, 0))
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
            print("Not yet in commit window. Sleeping 60s...")
            time.sleep(60)

    # Number of commits for this session
    commit_count = random.randint(min_commits, max_commits)

    # Keep track of used filenames in this run to avoid duplicates
    used_filenames = set()

    for _ in range(commit_count):
        # Check if we are still within the time window
        now = datetime.now().time()
        if now > end_time:
            print(f"Reached the end time ({repo_config['ending_time']}). Stopping commits...")
            break

        # Pick a random folder
        folder = random.choice(repo_config["folders"])
        directory = os.path.join(repo_name, folder)
        os.makedirs(directory, exist_ok=True)

        # Single GPT call => code, file_name, commit_message
        code_snippet, raw_file_name, commit_message = generate_code_file_and_commit(
            folder=folder,
            extension=repo_config["file_extension"],
            naming_convention=repo_config["file_naming_convention"]
        )

        # Ensure unique filename in this run
        while raw_file_name in used_filenames:
            # If GPT returns duplicates, re-call the function or rename
            # For simplicity, let's just add a random suffix
            suffix = str(random.randint(100, 999))
            name_part, ext = os.path.splitext(raw_file_name)
            raw_file_name = f"{name_part}{suffix}{ext}"

        used_filenames.add(raw_file_name)

        # Write the code to the file
        file_path = os.path.join(directory, raw_file_name)
        with open(file_path, "w") as f:
            f.write(code_snippet)

        # Commit & push
        commit_and_push(repo_name, commit_message)

        # Random sleep between commits (5-15 minutes)
        time.sleep(random.randint(300, 900))


def main():
    """
    Picks a random repository from config.json and runs automate_commits on it.
    """
    repositories = config.get("repositories", [])
    if not repositories:
        print("No repositories found in config.json.")
        return

    # Randomly select one repository from config
    chosen_repo = random.choice(repositories)
    automate_commits(chosen_repo)


if __name__ == "__main__":
    main()
