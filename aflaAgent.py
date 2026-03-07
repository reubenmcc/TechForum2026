import os
import time
import random

# ---------------------------------------------------------------------------
# Line-of-business registry
# Maps LOB codes to human-readable names and their expected output file paths.
# ---------------------------------------------------------------------------
LOB_REGISTRY = {
    "TLIFE": {
        "name": "Term Life",
        "output_file": "TLIFE_cashflows.csv",
    },
    "WLIFE": {
        "name": "Whole Life",
        "output_file": "WLIFE_cashflows.csv",
    },
    "FANN": {
        "name": "Fixed Annuity",
        "output_file": "FANN_cashflows.csv",
    },
    "LTC": {
        "name": "Long-Term Care",
        "output_file": "LTC_cashflows.csv",
    },
    "GRP": {
        "name": "Group Benefits",
        "output_file": "GRP_cashflows.csv",
    },
}

# ---------------------------------------------------------------------------
# Tool implementations  (the "real" side – swap these for actual Alfa calls)
# ---------------------------------------------------------------------------

def check_results_file(lob_code: str, output_directory: str = "agentDocs/cashflows") -> str:
    """
    Check whether the Mg-Alfa output file already exists for a given LOB.
    Returns a plain-text status string consumed by the agent.
    """
    lob = LOB_REGISTRY.get(lob_code.upper())
    if lob is None:
        return f"Unknown LOB code '{lob_code}'. Valid codes: {list(LOB_REGISTRY.keys())}"

    filepath = os.path.join(output_directory, lob["output_file"])
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        return f"Results file found: {filepath} ({size} bytes)"
    else:
        return f"Results file NOT found: {filepath}"


def run_alfa(lob_code: str, output_directory: str = "agentDocs/cashflows") -> str:
    """
    Simulate (or invoke) the Mg-Alfa cash-flow model for a given LOB.
    In production, replace the body of this function with the actual
    subprocess / API call that launches Alfa.
    """
    lob = LOB_REGISTRY.get(lob_code.upper())
    if lob is None:
        return f"Unknown LOB code '{lob_code}'."

    filepath = os.path.join(output_directory, lob["output_file"])

    # --- SIMULATION: write a fake CSV so the agent can read it back ----------
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    rows = ["period,premium_cf,benefit_cf,expense_cf,net_cf,reserve"]
    npv = 0.0
    reserve = random.uniform(50_000_000, 200_000_000)
    for t in range(1, 21):
        prem    =  round(reserve * random.uniform(0.04, 0.06), 2)
        benefit = -round(reserve * random.uniform(0.03, 0.05), 2)
        expense = -round(reserve * random.uniform(0.005, 0.015), 2)
        net     =  round(prem + benefit + expense, 2)
        reserve =  round(reserve * random.uniform(0.97, 1.02), 2)
        npv    +=  net / (1.05 ** t)
        rows.append(f"{t},{prem},{benefit},{expense},{net},{reserve}")

    with open(filepath, "w") as f:
        f.write("\n".join(rows))
    # -------------------------------------------------------------------------

    elapsed = round(random.uniform(2.5, 8.0), 1)   # simulated run time
    return (
        f"Mg-Alfa run complete for {lob['name']} ({lob_code}). "
        f"Output written to {filepath}. "
        f"Elapsed: {elapsed}s."
    )


def read_output(lob_code: str, output_directory: str = "agentDocs/cashflows") -> str:
    """
    Read the Mg-Alfa output file for a given LOB and return its contents.
    """
    lob = LOB_REGISTRY.get(lob_code.upper())
    if lob is None:
        return f"Unknown LOB code '{lob_code}'."

    filepath = os.path.join(output_directory, lob["output_file"])
    try:
        with open(filepath, "r") as f:
            contents = f.read()
        return f"Output file: {filepath}\n\n{contents}"
    except FileNotFoundError:
        return f"Output file not found: {filepath}. Run the model first."
    except Exception as e:
        return f"Could not read output file '{filepath}': {e}"



# ---------------------------------------------------------------------------
# Tool dispatcher  (mirrors handle_tool_call in filereadAgent.py)
# ---------------------------------------------------------------------------

def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    output_directory = tool_input.get("output_directory", "agentDocs/cashflows")
    lob_code         = tool_input.get("lob_code", "")

    if tool_name == "check_results_file":
        return check_results_file(lob_code, output_directory)

    elif tool_name == "run_alfa":
        return run_alfa(lob_code, output_directory)

    elif tool_name == "read_output":
        return read_output(lob_code, output_directory)

    return f"Unknown tool: {tool_name}"

# ---------------------------------------------------------------------------
# Tool schema (passed to Claude's `tools` parameter)
# ---------------------------------------------------------------------------
ALFA_TOOLS = [
    {
        "name": "check_results_file",
        "description": (
            "Check whether the Mg-Alfa output results file already exists for a "
            "given line of business. Always call this before run_alfa."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lob_code": {
                    "type": "string",
                    "description": "Line-of-business code, e.g. TLIFE, WLIFE, FANN, LTC, GRP.",
                },
                "output_directory": {
                    "type": "string",
                    "description": "Root directory to look in. Defaults to '.'.",
                },
            },
            "required": ["lob_code"],
        },
    },
    {
        "name": "run_alfa",
        "description": (
            "Execute the Mg-Alfa stochastic cash-flow model for a line of business. "
            "Only call this when check_results_file confirms no output file exists."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lob_code": {
                    "type": "string",
                    "description": "Line-of-business code to run.",
                },
                "output_directory": {
                    "type": "string",
                    "description": "Root directory for output. Defaults to '.'.",
                },
            },
            "required": ["lob_code"],
        },
    },
    {
        "name": "read_output",
        "description": (
            "Read the Mg-Alfa output file for a line of business and return its contents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lob_code": {
                    "type": "string",
                    "description": "Line-of-business code whose output to read.",
                },
                "output_directory": {
                    "type": "string",
                    "description": "Root directory for output. Defaults to '.'.",
                },
            },
            "required": ["lob_code"],
        },
    },
]

# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

def run_alfa_agent(client, lob_code: str, output_directory: str = "agentDocs/cashflows") -> str:
    """
    Drives Claude through the check → (run) → read workflow for Mg-Alfa.

    Parameters
    ----------
    client          : anthropic.Anthropic  (or any compatible client)
    lob_code        : LOB to project, e.g. "TLIFE"
    output_directory: where Alfa output files live / will be written

    Returns
    -------
    The agent's final natural-language summary.
    """
    system = (
        "You are an actuarial model execution agent for Mg-Alfa, a stochastic "
        "cash-flow projection platform. "
        "When asked to run a model for a line of business:\n"
        "1. Call check_results_file to see if results already exist.\n"
        "2. If the file is missing, call run_alfa to execute the model.\n"
        "3. Call read_output to retrieve the results.\n"
        "4. Summarise the cash-flow projections for the user.\n"
        "Always follow that exact sequence. Never skip the check."
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"Please run the Mg-Alfa cash-flow model for line of business '{lob_code}'. "
                f"Output directory: '{output_directory}'."
            ),
        }
    ]

    # Agentic loop – keep going until Claude stops calling tools
    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=system,
            tools=ALFA_TOOLS,
            messages=messages,
        )

        # Append the assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        # If Claude is done, return its final text
        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    return block.text
            return "(Agent finished with no text response.)"

        # Otherwise, execute every tool call and feed results back
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = handle_tool_call(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason – bail out
            return f"Agent stopped unexpectedly: stop_reason={response.stop_reason}"