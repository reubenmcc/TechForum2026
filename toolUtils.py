# =============================================================================
# CLAUDE API TOOL DEFINITIONS — used for live API calls
# =============================================================================
CLAUDE_TOOLS = {
    "find_file_by_description": {
        "name": "find_file_by_description",
        "description": "Finds and reads a file by matching a natural language description",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Natural language description of the file to find"},
                "file_directory": {"type": "string", "description": "Directory to search in (default '.')"},
            },
            "required": ["description"],
        },
    },
    "calculate_irr": {
        "name": "calculate_irr",
        "description": "Calculates IRR given a list of cash flows and dates",
        "input_schema": {
            "type": "object",
            "properties": {
                "cash_flows": {"type": "array", "items": {"type": "number"}, "description": "Cash flow amounts (negative = outflow)"},
                "dates": {"type": "array", "items": {"type": "string"}, "description": "Dates for each cash flow (YYYY-MM-DD)"},
            },
            "required": ["cash_flows"],
        },
    },
    "local_irr": {
        "name": "local_irr",
        "description": "Calculates IRR given a list of cash flows and dates",
        "input_schema": {
            "type": "object",
            "properties": {
                "cash_flows": {"type": "array", "items": {"type": "number"},
                               "description": "Cash flow amounts (negative = outflow)"}
            },
            "required": ["cash_flows"],
        },
    },
    "database_query": {
        "name": "database_query",
        "description": "Queries a SQL database to retrieve stored information",
        "input_schema": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "SQL query to execute"}},
            "required": ["sql"],
        },
    },
    "send_email": {
        "name": "send_email",
        "description": "Sends emails to specified recipients",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    "file_read": {
        "name": "file_read",
        "description": "Reads and retrieves content from files",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path to read"}},
            "required": ["path"],
        },
    },
    "python_execute": {
        "name": "python_execute",
        "description": "Executes Python code snippets",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code to execute"}},
            "required": ["code"],
        },
    },
    "alfa_runner": {
        "name": "alfa_runner",
        "description": "Runs MG-Alfa model",
        "input_schema": {
            "type": "object",
            "properties": {"Line of Business name": {"type": "string", "description": "Begin MG-Alfa cashflow model"}},
            "required": ["code"],
        },
    },
}

# =============================================================================
# SCENARIO TOOL SETS — define which tools are exposed per scenario
# =============================================================================
TOOL_SCENARIOS = {
    "scenario_1": ["find_file_by_description"],
    "scenario_2": ["find_file_by_description", "database_query"],
    "scenario_3": ["find_file_by_description", "local_irr"],
    "scenario_4": ["database_query", "file_read", "alfa_runner"],
    "all": list(CLAUDE_TOOLS.keys()),
}


def get_tools_for_scenario(scenario) -> list:
    """Return the list of tool definitions to pass to the Claude API.

    Args:
        scenario: a scenario name (str) from TOOL_SCENARIOS, or a list of tool name strings.
    """
    tool_names = TOOL_SCENARIOS[scenario] if isinstance(scenario, str) else scenario
    return [CLAUDE_TOOLS[name] for name in tool_names if name in CLAUDE_TOOLS]