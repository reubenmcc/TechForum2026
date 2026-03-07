import os
import pypdf
from irrAgent import local_irr
from aflaAgent import check_results_file, run_alfa, read_output

listofFiles = {
    "cashflows.csv":"Csv of Cashflows by Line of Business",
    "PolicyInfo.csv":"Coverage Info by Policy Number",
    "PremiumPaid.csv":"Premiums Paid by Policy Number",
    "01_policy_declaration_mercer.pdf":"Policy Description of John Mercer",
    "02_policy_declaration_kim.pdf":"Policy Description of Sandra Kim",
    "03_beneficiary_designation_mercer.pdf":"Beneficiary Description of John Mercer",
    "04_beneficiary_designation_kim.pdf":"Beneficiary Description of Sandra Kim",
    "05_claims_processing_letter.pdf":"Claims Processing Letter for John Mercer",
    "06_coverage_summary_kim.pdf":"Annual Coverage Description of Sandra Kim",
}

def find_file_by_description(client, description: str, file_directory: str = ".") -> str:
    """
    Uses Claude to match a description to a file, then reads it.
    """
    # Step 1: List files in the directory
    try:
        dir_files = set(os.listdir(file_directory))
    except FileNotFoundError:
        return f"Directory '{file_directory}' not found."

    if not dir_files:
        return "No files found in the specified directory."

    # Step 2: Build file list with semantic descriptions where available
    file_info_lines = []
    for filename in dir_files:
        desc = listofFiles.get(filename, "(no description)")
        file_info_lines.append(f"{filename} — {desc}")

    file_info = "\n".join(file_info_lines)

    # Step 3: Ask Claude to pick the best match
    match_response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Given these files and their descriptions:\n{file_info}\n\n"
                    f"Which single file best matches this description: '{description}'?\n"
                    "Reply with ONLY the exact filename from the list above, nothing else.\n"
                    "If nothing matches, reply with the single closest filename anyway."
                )
            }
        ]
    )

    filename = match_response.content[0].text.strip()

    # Step 4: Read and return the file contents
    filepath = os.path.join(file_directory, filename)
    try:
        if filename.lower().endswith(".pdf"):
            reader = pypdf.PdfReader(filepath)
            contents = "\n\n".join(page.extract_text() for page in reader.pages)
        else:
            with open(filepath, "r") as f:
                contents = f.read()
        return f"File: {filename}\n\n{contents}"
    except Exception as e:
        return f"Could not read file '{filename}': {str(e)}"


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

    return "Unknown tool."