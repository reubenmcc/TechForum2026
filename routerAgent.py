import anthropic
import os
from dotenv import load_dotenv
from toolUtils import CLAUDE_TOOLS

load_dotenv("keys.env")

client =anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],  # This is the default and can be omitted
)

# ── Intent classifier (used by the router tool in toolCalls.py) ───────────────

def classify_intent(user_message: str) -> str:
    """Return the routing label (e.g. POLICY_LOOKUP or ACTUARIAL_MODEL) for a query."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        system=(
            "You are a routing classifier. Categorize the user's request as exactly one of:\n"
            "  POLICY_LOOKUP  - questions about a specific individual, insured, or policy "
            "(e.g. policy status, face amount, coverage details for a named person)\n"
            "  ACTUARIAL_MODEL - questions about block-level or portfolio-level metrics that "
            "require running or reading MG-ALFA output (e.g. IRR, reserves, cash flows for a block)\n\n"
            "Respond with only the label — no explanation."
        ),
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


# ── Specialist agents ─────────────────────────────────────────────────────────

def handle_policy_lookup(user_message: str) -> anthropic.types.Message:
    """Agent for individual policy/insured queries (Prompt Type 1)."""
    return client.messages.create(
        model="claude-haiku-4-5-20251001",  # fast + cheap for focused file lookups
        max_tokens=1024,
        system=(
            "You are a policy lookup specialist. "
            "When asked about a specific insured or policy, use find_file_by_description "
            "with the full description from the user's prompt to locate the correct file, "
            "then answer the question based on what the file contains."
        ),
        tools=[CLAUDE_TOOLS["find_file_by_description"]],
        messages=[{"role": "user", "content": user_message}]
    )

def handle_mga_alfa_query(user_message: str) -> anthropic.types.Message:
    """Agent for block-level actuarial/MG-ALFA queries (Prompt Type 2)."""
    return client.messages.create(
        model="claude-sonnet-4-6",  # stronger reasoning for actuarial analysis
        max_tokens=2048,
        system=(
            "You are an actuarial modeling specialist with access to MG-ALFA. "
            "To answer questions about block-level metrics like IRR, reserves, or cash flows: "
            "1. Use check_results_file to see if results already exist. "
            "2. If not, use run_alfa to generate them. "
            "3. Use read_output to extract the specific metric requested. "
            "Present results clearly with any relevant context."
        ),
        tools=[CLAUDE_TOOLS["check_results_file"], CLAUDE_TOOLS["run_alfa"], CLAUDE_TOOLS["read_output"]],
        messages=[{"role": "user", "content": user_message}]
    )

# ── Router ────────────────────────────────────────────────────────────────────

def route(user_message: str) -> anthropic.types.Message:
    """
    Uses Claude to reason about the intent of the prompt and dispatch
    to the appropriate specialist agent.
    """
    routing_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        system=(
            "You are a routing classifier. Categorize the user's request as exactly one of:\n"
            "  POLICY_LOOKUP  - questions about a specific individual, insured, or policy "
            "(e.g. policy status, face amount, coverage details for a named person)\n"
            "  ACTUARIAL_MODEL - questions about block-level or portfolio-level metrics that "
            "require running or reading MG-ALFA output (e.g. IRR, reserves, cash flows for a block)\n\n"
            "Respond with only the label — no explanation."
        ),
        messages=[{"role": "user", "content": user_message}]
    )

    intent = routing_response.content[0].text.strip()
    print(f"[Router] Detected intent: {intent}")

    if intent == "POLICY_LOOKUP":
        return handle_policy_lookup(user_message)
    elif intent == "ACTUARIAL_MODEL":
        return handle_mga_alfa_query(user_message)
    else:
        # Fallback: let the router's own reasoning handle edge cases
        raise ValueError(f"Unrecognized intent from router: '{intent}'. "
                         "Consider expanding the classifier labels.")

# ── Entry point ───────────────────────────────────────────────────────────────
# test Orch
if __name__ == "__main__":
    load_dotenv("keys.env")

    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],  # This is the default and can be omitted
    )


    prompts = [
        "Does Sandra Kim have an active Whole Life policy, and if so, what is the face amount?",
        "What is the IRR for the entire block?",
    ]

    for prompt in prompts:
        print(f"\n{'='*60}")
        print(f"Prompt: {prompt}")
        response = route(prompt)
        # Extract the final text response
        for block in response.content:
            if hasattr(block, "text"):
                print(f"Response: {block.text}")