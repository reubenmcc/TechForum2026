# Tool Selection Visualizer

## Description

The purpose of this app is to allow you to visualize tool-selecting behavior.
The application includes 5 scenarios where Claude can pick which tools to use.

| Scenario | Description |
|----------|-------------|
| Scenario 1 | One tool — information retrieval |
| Scenario 2 | Two tools, with the same prompt as Scenario 1 |
| Scenario 3 | Workflow based on being an Actuarial Analyst |
| Scenario 4 | A larger task than Scenario 3 |
| Scenario 5 | A Router Agent |

---

## File Descriptions

| File | Description |
|------|-------------|
| `alfaAgent.py` | Mock-up of the Mg-ALFA workflow |
| `agentVisual.py` | Front end of the application; also includes simulated workflows |
| `createAgent.py` | Creates the Anthropic client |
| `filereadAgent.py` | Picks a file to read based on context from the prompt |
| `handleTool.py` | Conversation handler |
| `irragent.py` | Calculates the Internal Rate of Return |
| `routerAgent.py` | Routes between the two agents from Scenarios 1 and 3 |
| `toolCalls.py` | Contains all tool calls |
| `toolUtils.py` | Claude API tool descriptions |

---

## How to Install

### Prerequisites
- Python 3.x
- Git

### Steps

**1. Create a virtual environment**
```bash
python -m venv {path}
```

**2. Clone the repository**
```bash
git clone https://github.com/reubenmcc/TechForum2026.git
```

**3. Activate the environment and install packages**
```bash
cd {path_to_your_environment}
cd Scripts
activate
cd ..
pip install -r requirements.txt
```

**4. Add your API key**

In the project root directory, create a file called `keys.env` and add the following line:
```
ANTHROPIC_API_KEY={your_api_key}
```

**5. Run the application**

Double-click `run.bat` or run it from the terminal:
```bash
./run.bat
```

> **Note:** `run.bat` is a Windows script. Mac/Linux users should run the equivalent shell command directly.
