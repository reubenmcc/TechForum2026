from irrAgent import local_irr
from aflaAgent import check_results_file, run_alfa, read_output
from filereadAgent import find_file_by_description

def handle_tool_call(client, tool_name: str, tool_input: dict) -> str:
    if tool_name == "check_results_file":
        return check_results_file(
            lob_code=tool_input.get("lob_code", ""),
            output_directory=tool_input.get("output_directory", "agentDocs/cashflows"),
        )

    elif tool_name == "run_alfa":
        return run_alfa(
            lob_code=tool_input.get("lob_code", ""),
            output_directory=tool_input.get("output_directory", "agentDocs/cashflows"),
        )

    elif tool_name == "read_output":
        return read_output(
            lob_code=tool_input.get("lob_code", ""),
            output_directory=tool_input.get("output_directory", "agentDocs/cashflows"),
        )

    elif tool_name == "find_file_by_description":
        return find_file_by_description(
            client=client,
            description=tool_input["description"],
            file_directory=tool_input.get("file_directory", ".")
        )

    elif tool_name == "local_irr":
        return local_irr(
            cash_flows=tool_input.get("cash_flows", ".")
        )

    elif tool_name == "router":
        import routerAgent
        intent = routerAgent.classify_intent(tool_input.get("prompt", ""))
        if intent == "POLICY_LOOKUP":
            return (
                "Intent classified: POLICY_LOOKUP → dispatching to policy-lookup specialist agent (claude-haiku-4-5). "
                "Call find_file_by_description to retrieve the relevant policy document."
            )
        elif intent == "ACTUARIAL_MODEL":
            return (
                "Intent classified: ACTUARIAL_MODEL → dispatching to actuarial-model specialist agent (claude-sonnet-4-6). "
                "Call check_results_file, then run_alfa if needed, then read_output to answer the query."
            )
        else:
            return f"Intent classified: {intent} — unable to route to a known specialist."

    return "Unknown tool."