# Git Commit Automation Script  

This script automates the process of generating random code files, committing them, and pushing them to Git repositories based on a configurable schedule.

---

## 📌 Features  
- **Automatic Git commits** based on a schedule  
- **Random code generation** with meaningful commit messages  
- **Supports multiple repositories**  
- **Configurable commit frequency and naming conventions**  
- **Uses OpenAI API (optional) for generating intelligent commit messages**  

---

### 1️⃣ Clone the Repository  
```bash
git clone https://github.com/sharan122/git_automation_bot.git
cd git_automation_bot
```

### 2️⃣ Install Dependencies  
Make sure you have Python installed. Then, install required libraries after creating env:
```bash
pip install -r requirements.txt
```

---

## 🛠 Configuration  

### 1️⃣ Edit the `config.json` File  
Modify `config.json` to add your repositories and settings.  

### **Example `config.json` File:**  
```json
{
    "repositories": [
        {
            "name": "my_project",
            "repo_url": "https://github.com/<your_username>/my_project.git",
            "folders": ["src", "utils", "modules"],
            "file_extension": ".py",
            "file_naming_convention": "snake_case",
            "starting_time": "05:00 PM",
            "ending_time": "10:00 PM",
            "minimum_commits": 9,
            "maximum_commits": 15
        }
    ]
}
```

#### **Explanation of Configuration:**  
| Key                   | Description |
|-----------------------|-------------|
| `name`                | The name of your Git repository |
| `repo_url`            | The GitHub URL of your repository |
| `folders`             | List of folders where code files will be added |
| `file_extension`      | File type (`.py`, `.js`, `.ts`, etc.) |
| `file_naming_convention` | Naming style (`snake_case`, `camelCase`, `kebab-case`) |
| `starting_time`       | Time when the script starts committing |
| `ending_time`         | Time when the script stops committing |
| `minimum_commits`     | Minimum commits per session |
| `maximum_commits`     | Maximum commits per session |

---

## ▶️ Running the Script  
Once configured, run the script:  
```bash
python main.py
```
This will:
- Clone the repository (if not already cloned)
- Generate random code files
- Commit and push changes automatically within the configured time range  

---
#### **Create .env file **  

create .env file and configure the api key
OPENAI_API_KEY= your api key
