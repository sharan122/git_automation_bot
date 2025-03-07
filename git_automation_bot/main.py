import os
import json
import random
import time
import subprocess
import openai
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


CONFIG_FILE = "config.json"
with open(CONFIG_FILE, "r") as file:
    config = json.load(file)

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def clone_repo(repo_name: str, repo_url: str):
   
    if not os.path.exists(repo_name):
        print(f"Cloning repository {repo_name}...")
        subprocess.run(["git", "clone", repo_url, repo_name], check=True)
    else:
        print(f"Repository {repo_name} already exists.")

def strip_code_fences(generated_text: str) -> str:
    if "```" in generated_text:
        parts = generated_text.split("```")
     
        if len(parts) > 1:
            code = parts[1]
        else:
            code = parts[0]
    else:
        code = generated_text

    code = code.replace("`", "").strip()

    if code.lower().startswith("python"):
        code = code[6:].strip()

    return code

def generate_code(folder: str, extension: str) -> str:
    prompt = (
        f"Generate a detailed, functional code snippet for a feature in the '{folder}' folder. "
        f"Output only code for a '{extension}' file with no comments or explanations. "
        f"Ensure it demonstrates some real logic or functionality."
    )
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": prompt}]
    )
    raw_text = response.choices[0].message.content
    return strip_code_fences(raw_text)

def generate_filename_from_code(
    code_snippet: str, naming_convention: str, extension: str
) -> str:

    filename_prompt = (
        "You are given the following code snippet. Derive a short, standard file name (2-3 words) "
        "that reflects what the code does. Avoid words like 'data', 'tool', 'process', 'manage', 'script'. "
        "No disclaimers or references to GPT. The filename should be unique and relevant to the snippet's logic. "
        "Output only the name, no punctuation or extra text.\n\n"
        f"Code snippet:\n{code_snippet}\n\n"
        f"Naming convention: {naming_convention}. "
        "Examples:\n"
        "- snake_case -> mystic_orange, silent_forest\n"
        "- camelCase -> mysticOrange, silentForest\n"
        "- kebab-case -> mystic-orange, silent-forest\n"
        "Return only the filename in the correct style."
    )

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": filename_prompt}]
    )
    raw_filename = response.choices[0].message.content.strip()
    raw_filename = raw_filename.replace("`", "").replace("```", "")

    # Minimal cleanup (remove non-alphanumeric except underscores/dashes)
    cleaned = "".join(ch for ch in raw_filename if ch.isalnum() or ch in ["_", "-"])

    # Apply naming convention
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

def generate_commit_message_from_code(code: str) -> str:

    commit_prompt = (
        "Analyze the following code snippet and create a unique, human-sounding Git commit message. "
        "Avoid phrases like 'added' or 'implemented' at the start. "
        "Keep it under 15 words, no disclaimers or GPT references.\n\n"
        f"{code}"
    )
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": commit_prompt}]
    )
    commit_message = response.choices[0].message.content.strip()
    commit_message = commit_message.replace("`", "").replace("```", "")
    return commit_message

def commit_and_push(repo_name: str, commit_message: str):
    os.chdir(repo_name)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    current_branch = subprocess.check_output(["git", "branch", "--show-current"]).strip().decode("utf-8")
    subprocess.run(["git", "push", "origin", current_branch], check=True)
    os.chdir("..")

def automate_commits(repo_config: dict):

    repo_name = repo_config["name"]
    repo_url = repo_config["repo_url"]

    # Clone if needed
    clone_repo(repo_name, repo_url)
    
    
    start_time = datetime.strptime(repo_config["starting_time"], "%I:%M %p").time()
    end_time = datetime.strptime(repo_config["ending_time"], "%I:%M %p").time()
    
    
    min_commits = int(repo_config["minimum_commits"])
    max_commits = int(repo_config["maximum_commits"])
    
   
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
    

    commit_count = random.randint(min_commits, max_commits)

    
    used_filenames = set()

    for _ in range(commit_count):
       
        now = datetime.now().time()
        if now > end_time:
            print(f"Reached the end time ({repo_config['ending_time']}). Stopping commits...")
            break
        
       
        folder = random.choice(repo_config["folders"])
        directory = os.path.join(repo_name, folder)
        os.makedirs(directory, exist_ok=True)
        
        
        code = generate_code(folder, repo_config["file_extension"])
        
       
        while True:
            filename = generate_filename_from_code(
                code,
                repo_config["file_naming_convention"],
                repo_config["file_extension"]
            )
            if filename not in used_filenames:
                used_filenames.add(filename)
                break
            # If it's a duplicate, try again

        file_path = os.path.join(directory, filename)
        
        # Write the code to the file
        with open(file_path, "w") as f:
            f.write(code)
        
       
        commit_message = generate_commit_message_from_code(code)
        
       
        commit_and_push(repo_name, commit_message)
        
        # Random sleep between commits (5-15 minutes)
        time.sleep(random.randint(300, 900))

def main():
  
    repositories = config.get("repositories", [])
    if not repositories:
        print("No repositories found in config.json.")
        return
    
    # Randomly select one repository from config
    chosen_repo = random.choice(repositories)
    automate_commits(chosen_repo)

if __name__ == "__main__":
    main()
