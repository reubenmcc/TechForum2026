"""
LLM Agent Behavior Visualizer
==============================
A learning tool to visualize how LLM agents make tool call decisions,
including spiraling, looping, and suboptimal behavior patterns.

Run with:  python agentVisual.py

To customize, edit the TOOLS and SCENARIOS sections below.
"""

import tkinter as tk
from tkinter import ttk
import json
import threading
from createAgent import create
from toolUtils import CLAUDE_TOOLS, get_tools_for_scenario
from toolCalls import handle_tool_call
from handleTool import AgentConversationHandler, AGENT_REGISTRY

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    ANTHROPIC_AVAILABLE = False
# Simulated results returned to the model after each tool call
SIMULATED_RESULTS = {
    "get_cash_flows": (
        "Cash flows for deal: [-1,000,000 (2024-01-01), +150,000 (2024-04-01), "
        "+175,000 (2024-07-01), +200,000 (2024-10-01), +225,000 (2025-01-01)]"
    ),
    "database_query": "3 rows returned: id=101 val=42000 | id=102 val=38500 | id=103 val=51200",
    "send_email": "Email delivered successfully (message-id: <abc123@mail.example.com>)",
    "file_read": "2,340 bytes read. First line: 'Q4 2025 Financial Report v2.1'",
    "python_execute": "stdout: Done\nreturn value: 0",
    "documentLookup":"Sandra Kim has a 20-Year Term Life, with $750,000 in coverage",
    "alfa_runner": "MG-ALFA run complete. Cashflows written to /models/wholelife_cf_output.csv. Run ID: ALFA-2025-WL-001",
}


# =============================================================================
# TOOLS — Full catalogue. Each scenario picks a subset via its "tools" list.
# =============================================================================
TOOLS = [
    {"id": "find_file_by_description", "name": "Get Document",   "icon": "🔢", "description": "Retrieves file based on description"},
    {"id": "local_irr",      "name": "Local IRR",        "icon": "📈", "description": "Calculates IRR locally using Brent's method"},
    {"id": "database_query", "name": "Database Query",   "icon": "🗄️", "description": "Queries a SQL database to retrieve stored information"},
    {"id": "send_email",     "name": "Send Email",       "icon": "📧", "description": "Sends emails to specified recipients"},
    {"id": "file_read",      "name": "File Reader",      "icon": "📄", "description": "Reads and retrieves content from files"},
    {"id": "python_execute", "name": "Python Executor",  "icon": "🐍", "description": "Executes Python code snippets"},
    {"id": "check_results_file", "name": "Check for cash flows",  "icon": "🔢", "description": "Check results for MG-Alfa models"},
    {"id": "run_alfa", "name": "MG-Alfa Runner",  "icon": "🔢", "description": "Run MG-Alfa models"},
    {"id": "read_output", "name": "MG-Alfa Output reader",  "icon": "📄", "description": "Check results for MG-Alfa models"},
    {"id": "router", "name": "Router", "icon": "🔀", "description": "Classifies prompt intent and dispatches to the correct specialist agent"},
]


# =============================================================================
# SCENARIOS — Add or edit entries here.
#   • "tools"       — list of tool IDs available for this prompt (sidebar updates)
#   • "description" — shown above the user prompt
#   • "query"       — the stored user prompt text (editable at runtime)
#   • "steps"       — pre-built tool-call sequence; leave [] for Live-only scenarios
# =============================================================================
SCENARIOS = [
    {   "id": 1,
        "title": "Find insured documents",
        "difficulty": "easy",
        "description": (
            "An insurance agent wants to find the status of an insured."
        ),
        "query": "Does Sandra Kim have an active Whole Life policy, and if so, what is the face amount?",
        "tools": ["find_file_by_description"],
        "outcome": "success",
        "explanation": (
            "Optimal 1-step path: the coverage summary is read by Claude to generate a prompt"
            "No redundant or wrong-tool calls."
        ),
        "steps": [
            {
                "tool": "find_file_by_description",
                "parameters": {},
                "result": SIMULATED_RESULTS["documentLookup"],
                "reasoning": "I need the coverge letter for Sandra Kim.",
                "status": "success",
            }
        ],
        "response": "",
    },
    {
        "id": 2,
        "title": "Find insured documents (extra tool)",
        "difficulty": "easy",
        "description": (
            "Same question as Scenario 1, but now a database tool is also available — "
            "watch how the agent tries it first before finding the right tool."
        ),
        "query": "Does Sandra Kim have an active Whole Life policy, and if so, what is the face amount?",
        "tools": ["find_file_by_description", "database_query"],
        "outcome": "wrong_tool",
        "explanation": (
            "Wrong tool choice: the agent queried the database first, but Sandra Kim's policy "
            "is stored as a document. The correct single-step path was find_file_by_description."
        ),
        "steps": [
            {
                "tool": "database_query",
                "parameters": {"sql": "SELECT * FROM policies WHERE insured_name = 'Sandra Kim'"},
                "result": "0 rows returned. No policy record found for 'Sandra Kim' in the policies table.",
                "reasoning": "I'll check the database first to see if Sandra Kim's policy details are stored there.",
                "status": "wrong",
            },
            {
                "tool": "find_file_by_description",
                "parameters": {},
                "result": SIMULATED_RESULTS["documentLookup"],
                "reasoning": "Database returned nothing. The policy must be stored as a document — let me look it up.",
                "status": "success",
            },
        ],
        "response": "",
    },
    {
        "id": 3,
        "title": "Profitability Lookup",
        "difficulty": "easy",
        "description": (
            "An actuarial analyst needs the Internal Rate of Return for a line of business. "
            "Only get-cash-flow and IRR tools are available — watch how the agent picks "
            "the correct two-step sequence with no wasted calls."
        ),
        "query": "What is the IRR for Wholelife?",
        "tools": ["check_results_file", "run_alfa", "read_output"],
        "outcome": "success",
        "explanation": (
            "Optimal 2-step path: cash flows fetched first, IRR calculated second. "
            "No redundant or wrong-tool calls."
        ),
        "steps": [
            {
                "tool": "find_file_by_description",
                "parameters": {"deal_id": "D-2024-007"},
                "result": SIMULATED_RESULTS["get_cash_flows"],
                "reasoning": "I need the cash flow schedule for D-2024-007 before I can calculate IRR.",
                "status": "success",
            },
            {
                "tool": "calculate_irr",
                "parameters": {
                    "cash_flows": [-1000000, 150000, 175000, 200000, 225000],
                    "dates": ["2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01", "2025-01-01"],
                },
                "result": "calculate_irr",
                "reasoning": "Cash flows retrieved. I can now compute the IRR directly.",
                "status": "success",
            },
        ],
        "response": "",
    },
    {
        "id": 4,
        "title": "Profitability Extended",
        "difficulty": "Medium",
        "description": (
            "An actuarial analyst needs the Internal Rate of Return for a line of business. "
            "However the cashflows do not exist yet. The LLM must run MG-ALFA before getting the cashflows."
        ),
        "query": "What is the IRR for the entire block?",
        "tools": ["check_results_file", "run_alfa", "read_output"],
        "outcome": "spiral",
        "explanation": (
            "Tool spiraling detected: MG-ALFA was re-run twice and the database was queried "
            "redundantly after the cashflows were already generated. "
            "The optimal path was alfa_runner → file_read."
        ),
        "steps": [
            {
                "tool": "alfa_runner",
                "parameters": {"line_of_business": "Wholelife", "projection_years": 30},
                "result": SIMULATED_RESULTS["alfa_runner"],
                "reasoning": "No cashflows exist yet. Running MG-ALFA to generate Wholelife projections.",
                "status": "success",
            },
            {
                "tool": "database_query",
                "parameters": {"sql": "SELECT * FROM cashflows WHERE lob = 'Wholelife'"},
                "result": SIMULATED_RESULTS["database_query"],
                "reasoning": "Checking the database to confirm the cashflow output was stored.",
                "status": "redundant",
            },
            {
                "tool": "alfa_runner",
                "parameters": {"line_of_business": "Wholelife", "projection_years": 30, "discount_rate": 0.05},
                "result": SIMULATED_RESULTS["alfa_runner"],
                "reasoning": "Results unclear — re-running MG-ALFA with an explicit discount rate to be sure.",
                "status": "redundant",
            },
            {
                "tool": "database_query",
                "parameters": {"sql": "SELECT irr FROM cashflows WHERE lob = 'Wholelife' ORDER BY run_date DESC LIMIT 1"},
                "result": SIMULATED_RESULTS["database_query"],
                "reasoning": "Re-querying the database to retrieve IRR directly — maybe it was stored.",
                "status": "redundant",
            },
            {
                "tool": "file_read",
                "parameters": {"path": "/models/wholelife_cf_output.csv"},
                "result": SIMULATED_RESULTS["file_read"],
                "reasoning": "Database does not have the IRR. Reading the MG-ALFA output file to extract cashflows.",
                "status": "success",
            },
        ],
        "response": "",
    },
    {
        "id": 5,
        "title": "Router Agent",
        "difficulty": "medium",
        "description": (
            "A multi-agent routing pattern: a lightweight classifier first reads the prompt and "
            "decides which specialist agent to call — a policy-lookup agent or an actuarial-model agent. "
            "Watch how two separate LLM calls collaborate to answer a single question."
        ),
        "query": "Does Sandra Kim have an active Whole Life policy, and if so, what is the face amount?",
        "tools": ["router", "find_file_by_description", "check_results_file", "run_alfa", "read_output"],
        "outcome": "success",
        "explanation": (
            "Optimal multi-agent path: the router correctly classified the intent as POLICY_LOOKUP "
            "and dispatched to the policy-lookup specialist, which retrieved the document in one call. "
            "No redundant routing or wrong-agent dispatches."
        ),
        "steps": [
            {
                "tool": "router",
                "parameters": {"prompt": "Does Sandra Kim have an active Whole Life policy, and if so, what is the face amount?"},
                "result": "Intent classified: POLICY_LOOKUP → dispatching to policy-lookup specialist agent (claude-haiku-4-5).",
                "reasoning": (
                    "The prompt names a specific individual and asks about their policy details. "
                    "This matches the POLICY_LOOKUP pattern, not a block-level actuarial query."
                ),
                "status": "success",
            },
            {
                "tool": "find_file_by_description",
                "parameters": {"description": "Sandra Kim Whole Life policy"},
                "result": SIMULATED_RESULTS["documentLookup"],
                "reasoning": (
                    "Specialist agent: I need to locate Sandra Kim's policy document "
                    "to answer questions about coverage and face amount."
                ),
                "status": "success",
            },
        ],
        "response": "",
    },
    {
        "id": 6,
        "title": "Live Query",
        "difficulty": "easy",
        "description": (
            "Send your own prompt directly to the Claude API and watch it decide "
            "which tools to call in real time. All tools are available. "
            "Edit the prompt below and click Run Live."
        ),
        "query": "What is the IRR for deal D-2024-007?",
        "tools": [t["id"] for t in TOOLS],
        "outcome": "success",
        "explanation": "",
        "steps": [],
        "response": "",
    },
]


# =============================================================================
# THEME
# =============================================================================
THEME = {
    "bg": "#F8F9FB",
    "panel_bg": "#FFFFFF",
    "sidebar_bg": "#F1F3F8",
    "accent": "#7C3AED",
    "accent_light": "#EDE9FE",
    "text": "#1E293B",
    "text_muted": "#64748B",
    "border": "#E2E8F0",
    "status": {
        "success":    ("#F0FDF4", "#16A34A"),
        "error":      ("#FEF2F2", "#DC2626"),
        "wrong":      ("#FFF7ED", "#EA580C"),
        "suboptimal": ("#FEFCE8", "#CA8A04"),
        "redundant":  ("#F8FAFC", "#94A3B8"),
        "loop":       ("#FAF5FF", "#9333EA"),
    },
    "outcome": {
        "success":     "#16A34A",
        "inefficient": "#CA8A04",
        "spiral":      "#EA580C",
        "loop":        "#9333EA",
        "wrong_tool":  "#DC2626",
    },
    "difficulty": {
        "easy":   ("#F0FDF4", "#15803D"),
        "medium": ("#FEFCE8", "#A16207"),
        "hard":   ("#FEF2F2", "#B91C1C"),
    },
}

STATUS_LABELS = {
    "success":    "✅ Success",
    "error":      "❌ Error",
    "wrong":      "⚠️  Wrong Tool",
    "suboptimal": "🟡 Suboptimal",
    "redundant":  "🔁 Redundant",
    "loop":       "🔄 Loop",
}

OUTCOME_LABELS = {
    "success":     "✅ Optimal Path",
    "inefficient": "⚠️  Inefficient Path",
    "spiral":      "🌀 Tool Spiraling",
    "loop":        "🔄 Infinite Loop",
    "wrong_tool":  "❌ Wrong Tool Choices",
}


# =============================================================================
# APP
# =============================================================================
class AgentVisualizer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LLM Agent Behavior Visualizer")
        self.configure(bg=THEME["bg"])
        self.geometry("1200x780")
        self.minsize(900, 600)

        self._scenario = None
        self._step = 0
        self._after_id = None
        self._active_id = SCENARIOS[0]["id"]
        self._live_handler = None
        self._live_claude_tools = None
        self._live_tool_selection = {}  # tool_id -> bool, only used for Live scenario

        self._build_ui()
        self._load_scenario(SCENARIOS[0])

    # ------------------------------------------------------------------ build
    def _build_ui(self):
        # top bar
        topbar = tk.Frame(self, bg=THEME["accent"], height=52)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        tk.Label(topbar, text="🧠  LLM Agent Behavior Visualizer",
                 bg=THEME["accent"], fg="white",
                 font=("Helvetica", 16, "bold"), padx=16).pack(side="left", fill="y")
        tk.Label(topbar, text="Watch Claude make real-time tool call decisions with live API responses",
                 bg=THEME["accent"], fg="#DDD6FE",
                 font=("Helvetica", 10), padx=8).pack(side="left", fill="y")

        main = tk.Frame(self, bg=THEME["bg"])
        main.pack(fill="both", expand=True)
        self._build_sidebar(main)
        self._build_content(main)

    # ---------------------------------------------------------------- sidebar
    def _build_sidebar(self, parent):
        self._sidebar = tk.Frame(parent, bg=THEME["sidebar_bg"], width=280)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        tk.Label(self._sidebar, text="Available Tools",
                 bg=THEME["sidebar_bg"], fg=THEME["text"],
                 font=("Helvetica", 11, "bold"),
                 anchor="w", padx=12, pady=8).pack(fill="x")

        self._tools_panel = tk.Frame(self._sidebar, bg=THEME["sidebar_bg"])
        self._tools_panel.pack(fill="x")
        self._tool_frames = {}

        tk.Frame(self._sidebar, bg=THEME["border"], height=1).pack(fill="x", pady=8)
        tk.Label(self._sidebar, text="Status Legend",
                 bg=THEME["sidebar_bg"], fg=THEME["text"],
                 font=("Helvetica", 10, "bold"), anchor="w", padx=12).pack(fill="x")
        for key, label in STATUS_LABELS.items():
            _, colour = THEME["status"][key]
            row = tk.Frame(self._sidebar, bg=THEME["sidebar_bg"], padx=12, pady=1)
            row.pack(fill="x")
            tk.Label(row, text="●", bg=THEME["sidebar_bg"],
                     fg=colour, font=("Helvetica", 10)).pack(side="left")
            tk.Label(row, text=label, bg=THEME["sidebar_bg"],
                     fg=THEME["text_muted"], font=("Helvetica", 9)).pack(side="left", padx=4)

    def _update_tools_panel(self, scenario):
        for w in self._tools_panel.winfo_children():
            w.destroy()
        self._tool_frames = {}
        tool_ids = scenario.get("tools", [t["id"] for t in TOOLS])
        is_live_scenario = scenario.get("id") == SCENARIOS[-1]["id"]

        # Initialise selection state for the Live scenario (all on by default)
        if is_live_scenario:
            for tid in tool_ids:
                if tid not in self._live_tool_selection:
                    self._live_tool_selection[tid] = True

        # Legend row
        legend = tk.Frame(self._tools_panel, bg=THEME["sidebar_bg"], padx=10, pady=3)
        legend.pack(fill="x")
        for badge_text, badge_bg, badge_fg in [
            ("⚡ Live", "#DCFCE7", "#15803D"),
            ("🎭 Mock", "#F1F5F9", "#475569"),
        ]:
            tk.Label(legend, text=badge_text, bg=badge_bg, fg=badge_fg,
                     font=("Helvetica", 7, "bold"), padx=5, pady=1).pack(side="left", padx=(0, 4))
        tk.Label(legend, text="= execution type", bg=THEME["sidebar_bg"],
                 fg=THEME["text_muted"], font=("Helvetica", 7)).pack(side="left")

        for tool in [t for t in TOOLS if t["id"] in tool_ids]:
            is_live = tool["id"] in AGENT_REGISTRY and tool["id"] not in SIMULATED_RESULTS
            badge_text = "⚡ Live" if is_live else "🎭 Mock"
            badge_bg   = "#DCFCE7" if is_live else "#F1F5F9"
            badge_fg   = "#15803D" if is_live else "#475569"

            enabled = (not is_live_scenario) or self._live_tool_selection.get(tool["id"], True)
            card_bg  = THEME["panel_bg"] if enabled else THEME["sidebar_bg"]
            card_border = THEME["border"] if enabled else "#CBD5E1"
            name_fg  = THEME["text"] if enabled else THEME["text_muted"]

            f = tk.Frame(self._tools_panel, bg=THEME["sidebar_bg"], padx=10, pady=4)
            f.pack(fill="x")
            inner = tk.Frame(f, bg=card_bg,
                             highlightthickness=1, highlightbackground=card_border)
            inner.pack(fill="x")

            header_row = tk.Frame(inner, bg=card_bg)
            header_row.pack(fill="x", padx=8, pady=(4, 0))
            tk.Label(header_row, text=f"{tool['icon']}  {tool['name']}",
                     bg=card_bg, fg=name_fg,
                     font=("Helvetica", 10, "bold"), anchor="w").pack(side="left")
            tk.Label(header_row, text=badge_text, bg=badge_bg, fg=badge_fg,
                     font=("Helvetica", 7, "bold"), padx=5, pady=1).pack(side="right")

            if is_live_scenario:
                tog_bg = "#16A34A" if enabled else THEME["border"]
                tog_fg = "white"
                tog_txt = "✓" if enabled else "+"
                tog_btn = tk.Button(header_row, text=tog_txt,
                                    bg=tog_bg, fg=tog_fg,
                                    font=("Helvetica", 8, "bold"),
                                    relief="flat", padx=4, pady=0, cursor="hand2",
                                    borderwidth=0)
                tog_btn.pack(side="right", padx=(0, 4))
                tog_btn.configure(command=lambda tid=tool["id"], btn=tog_btn, card=inner, hr=header_row, nl=None: self._toggle_live_tool(tid))

            tk.Label(inner, text=tool["description"],
                     bg=card_bg, fg=THEME["text_muted"],
                     font=("Helvetica", 8), wraplength=230,
                     anchor="w", justify="left", padx=8, pady=2).pack(fill="x")
            self._tool_frames[tool["id"]] = inner

    def _toggle_live_tool(self, tool_id):
        self._live_tool_selection[tool_id] = not self._live_tool_selection.get(tool_id, True)
        self._update_tools_panel(self._scenario)

    # --------------------------------------------------------------- content
    def _build_content(self, parent):
        content = tk.Frame(parent, bg=THEME["bg"])
        content.pack(side="left", fill="both", expand=True)

        # scenario number picker — stays fixed above scroll area
        picker_row = tk.Frame(content, bg=THEME["bg"])
        picker_row.pack(fill="x", padx=16, pady=(10, 6))
        tk.Label(picker_row, text="Scenario:",
                 bg=THEME["bg"], fg=THEME["text_muted"],
                 font=("Helvetica", 9, "bold")).pack(side="left", padx=(0, 10))
        self._picker_btns = {}
        for sc in SCENARIOS:
            label = str(sc["id"]) if sc["id"] != SCENARIOS[-1]["id"] else "Live"
            btn = tk.Button(picker_row, text=label,
                            font=("Helvetica", 10, "bold"),
                            relief="flat", width=4, pady=5, cursor="hand2",
                            command=lambda s=sc: self._select_scenario(s))
            btn.pack(side="left", padx=3)
            self._picker_btns[sc["id"]] = btn
        self._refresh_picker_buttons()

        tk.Frame(content, bg=THEME["border"], height=1).pack(fill="x", padx=16)

        # scrollable execution area
        self._exec_outer = tk.Frame(content, bg=THEME["bg"])
        self._exec_outer.pack(fill="both", expand=True, padx=16, pady=8)

        canvas_frame = tk.Frame(self._exec_outer, bg=THEME["bg"])
        canvas_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(canvas_frame, bg=THEME["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self._canvas.yview)
        self._scroll_frame = tk.Frame(self._canvas, bg=THEME["bg"])
        self._scroll_frame.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas_window = self._canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._canvas_window, width=e.width))
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-e.delta / 120), "units"))

    def _refresh_picker_buttons(self):
        for sc_id, btn in self._picker_btns.items():
            is_active = sc_id == self._active_id
            btn.configure(
                bg=THEME["accent"] if is_active else THEME["panel_bg"],
                fg="white" if is_active else THEME["text"],
                highlightthickness=1,
                highlightbackground=THEME["accent"] if is_active else THEME["border"],
            )

    def _select_scenario(self, scenario):
        self._active_id = scenario["id"]
        self._refresh_picker_buttons()
        self._load_scenario(scenario)

    # ------------------------------------------ scenario loading & rendering
    def _load_scenario(self, scenario):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if scenario.get("id") != 99:
            self._live_handler = None
            self._live_claude_tools = None
        self._scenario = scenario
        self._step = 0
        self._update_tools_panel(scenario)
        self._render_execution_area()

    def _render_execution_area(self):
        for w in self._scroll_frame.winfo_children():
            w.destroy()

        sc = self._scenario

        # ── description ──────────────────────────────────────────────────────
        desc = sc.get("description", "")
        if desc:
            desc_box = tk.Frame(self._scroll_frame, bg=THEME["panel_bg"],
                                highlightthickness=1, highlightbackground=THEME["border"])
            desc_box.pack(fill="x", padx=4, pady=(4, 8))
            tk.Label(desc_box, text=desc,
                     bg=THEME["panel_bg"], fg=THEME["text_muted"],
                     font=("Helvetica", 10, "italic"),
                     wraplength=720, justify="left",
                     anchor="w", padx=12, pady=10).pack(fill="x")

        # ── user prompt + controls ────────────────────────────────────────────
        header = tk.Frame(self._scroll_frame, bg=THEME["bg"])
        header.pack(fill="x", pady=(0, 8))

        q_frame = tk.Frame(header, bg=THEME["accent_light"],
                           highlightthickness=1, highlightbackground=THEME["accent"])
        q_frame.pack(side="left", fill="x", expand=True, padx=(4, 8))
        tk.Label(q_frame, text="User Prompt",
                 bg=THEME["accent_light"], fg=THEME["accent"],
                 font=("Helvetica", 9, "bold"),
                 anchor="w", padx=10, pady=2).pack(fill="x")
        self._query_var = tk.StringVar(value=sc["query"])
        tk.Entry(q_frame, textvariable=self._query_var,
                 bg=THEME["accent_light"], fg=THEME["text"],
                 font=("Helvetica", 10, "italic"),
                 relief="flat", bd=0,
                 insertbackground=THEME["accent"],
                 highlightthickness=0).pack(fill="x", padx=10, pady=6)

        ctrl = tk.Frame(header, bg=THEME["bg"])
        ctrl.pack(side="right", anchor="n", padx=(0, 4))

        if sc["steps"]:
            step_row = tk.Frame(ctrl, bg=THEME["bg"])
            step_row.pack(pady=(8, 2))
            tk.Button(step_row, text="▶  Play All",
                      bg=THEME["accent"], fg="white",
                      font=("Helvetica", 9, "bold"), relief="flat",
                      padx=8, pady=4, cursor="hand2",
                      command=self._play_all).pack(side="left", padx=2)
            tk.Button(step_row, text="→ Next Step",
                      bg=THEME["panel_bg"], fg=THEME["text"],
                      font=("Helvetica", 9), relief="flat",
                      padx=8, pady=4, cursor="hand2",
                      highlightthickness=1, highlightbackground=THEME["border"],
                      command=self._next_step).pack(side="left", padx=2)
            tk.Button(step_row, text="↺ Reset",
                      bg=THEME["panel_bg"], fg=THEME["text_muted"],
                      font=("Helvetica", 9), relief="flat",
                      padx=8, pady=4, cursor="hand2",
                      highlightthickness=1, highlightbackground=THEME["border"],
                      command=self._reset).pack(side="left", padx=2)

        live_label = "⚡ Run Live" if ANTHROPIC_AVAILABLE else "⚡ Run Live (pip install anthropic)"
        self._live_btn = tk.Button(ctrl, text=live_label,
                                   bg="#059669", fg="white",
                                   font=("Helvetica", 9, "bold"), relief="flat",
                                   padx=10, pady=4, cursor="hand2",
                                   state="normal" if ANTHROPIC_AVAILABLE else "disabled",
                                   command=self._run_live)
        self._live_btn.pack(pady=(4, 0))

        # ── progress bar ──────────────────────────────────────────────────────
        prog_frame = tk.Frame(self._scroll_frame, bg=THEME["bg"])
        if sc["steps"]:
            prog_frame.pack(fill="x", pady=10)
            tk.Label(prog_frame,
                     text=f"Progress: {self._step} / {len(sc['steps'])} steps",
                     bg=THEME["bg"], fg=THEME["text_muted"],
                     font=("Helvetica", 9)).pack(anchor="w")
            bar_bg = tk.Frame(prog_frame, bg=THEME["border"], height=6)
            bar_bg.pack(fill="x", pady=2)
            self._progress_bar = tk.Frame(bar_bg, bg=THEME["accent"], height=6)
            self._progress_bar.place(relx=0, rely=0,
                                     relwidth=self._step / len(sc["steps"]),
                                     relheight=1)
        else:
            self._progress_bar = tk.Frame(prog_frame, bg=THEME["accent"], height=6)

        # ── step cards ────────────────────────────────────────────────────────
        self._steps_container = tk.Frame(self._scroll_frame, bg=THEME["bg"])
        self._steps_container.pack(fill="x")
        for i, step in enumerate(sc["steps"]):
            card = self._make_step_card(self._steps_container, i + 1, step)
            card.pack(fill="x", pady=4)
            if i >= self._step:
                card.pack_forget()

        # outcome banner
        self._outcome_banner = self._make_outcome_banner(self._scroll_frame, sc)
        if sc["steps"] and self._step >= len(sc["steps"]):
            self._outcome_banner.pack(fill="x", pady=8)

        # follow-up prompt area (shown after live runs complete)
        self._followup_frame = self._make_followup_frame(self._scroll_frame)

    # ----------------------------------------------------------------- cards
    def _make_step_card(self, parent, num, step):
        tool = next((t for t in TOOLS if t["id"] == step["tool"]), None)
        bg, border = THEME["status"].get(step["status"], ("#fff", "#ccc"))
        card = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=border)

        ch = tk.Frame(card, bg=bg)
        ch.pack(fill="x", padx=10, pady=6)
        tk.Label(ch, text=f"  {num}  ", bg=THEME["text"], fg="white",
                 font=("Helvetica", 10, "bold"), padx=2, pady=1).pack(side="left")
        tk.Label(ch, text=f"{tool['icon'] if tool else '?'}  {tool['name'] if tool else step['tool']}",
                 bg=bg, fg=THEME["text"],
                 font=("Helvetica", 11, "bold"), padx=8).pack(side="left")
        tk.Label(ch, text=STATUS_LABELS.get(step["status"], step["status"]),
                 bg=bg, fg=border,
                 font=("Helvetica", 9, "bold"), padx=6, pady=2).pack(side="right")

        self._labelled_box(card, "Parameters", json.dumps(step["parameters"], indent=2), bg, mono=True)
        self._labelled_box(card, "Result", step["result"], bg)
        self._labelled_box(card, "Reasoning", step["reasoning"], bg, italic=True)
        tokens = step.get("tokens")
        if tokens:
            self._labelled_box(
                card, "Tokens (this API call)",
                f"Input: {tokens['input']:,}  |  Output: {tokens['output']:,}  |  Total: {tokens['input'] + tokens['output']:,}",
                bg,
            )
        tk.Frame(card, bg=border, height=1).pack(fill="x", padx=10, pady=4)
        return card

    def _labelled_box(self, parent, label, text, bg, mono=False, italic=False):
        box = tk.Frame(parent, bg=bg)
        box.pack(fill="x", padx=14, pady=2)
        tk.Label(box, text=label + ":", bg=bg, fg=THEME["text_muted"],
                 font=("Helvetica", 8, "bold"), anchor="w").pack(anchor="w")
        font_family = "Courier New" if mono else "Helvetica"
        font_size = 9 if mono else 10
        font_style = "italic" if italic else "normal"
        lines = text.count("\n") + 1 if text else 1
        widget = tk.Text(box, height=lines,
                         bg=THEME["panel_bg"], fg=THEME["text"],
                         font=(font_family, font_size, font_style),
                         wrap="word", padx=8, pady=4,
                         relief="flat", borderwidth=0,
                         state="normal")
        widget.insert("1.0", text)
        widget.config(state="disabled")
        widget.pack(fill="x")

    def _make_outcome_banner(self, parent, sc):
        colour = THEME["outcome"].get(sc["outcome"], THEME["text_muted"])
        banner = tk.Frame(parent, bg="#F8FAFC",
                          highlightthickness=1, highlightbackground=colour)
        tk.Label(banner, text=f"{OUTCOME_LABELS.get(sc['outcome'], sc['outcome'])}  —  Analysis",
                 bg="#F8FAFC", fg=colour,
                 font=("Helvetica", 11, "bold"),
                 anchor="w", padx=12, pady=6).pack(fill="x")
        tk.Label(banner, text=sc["explanation"],
                 bg="#F8FAFC", fg=THEME["text"],
                 font=("Helvetica", 10),
                 wraplength=680, justify="left",
                 anchor="w", padx=12, pady=6).pack(fill="x")

        token_totals = sc.get("token_totals", {})
        if token_totals:
            tk.Frame(banner, bg=THEME["border"], height=1).pack(fill="x", padx=12, pady=4)
            total = token_totals["input"] + token_totals["output"]
            tk.Label(
                banner,
                text=(
                    f"🔢  Token Usage — "
                    f"Input: {token_totals['input']:,}  |  "
                    f"Output: {token_totals['output']:,}  |  "
                    f"Total: {total:,}"
                ),
                bg="#F8FAFC", fg=THEME["text_muted"],
                font=("Helvetica", 9, "bold"),
                anchor="w", padx=12, pady=6,
            ).pack(fill="x")

        response_text = sc.get("response", "")
        if response_text:
            tk.Frame(banner, bg=THEME["border"], height=1).pack(fill="x", padx=12, pady=4)
            tk.Label(banner, text="Model Response:",
                     bg="#F8FAFC", fg=THEME["text_muted"],
                     font=("Helvetica", 9, "bold"),
                     anchor="w", padx=12).pack(fill="x")
            lines = response_text.count("\n") + 1
            resp_widget = tk.Text(banner, height=lines,
                                  bg=THEME["panel_bg"], fg=THEME["text"],
                                  font=("Helvetica", 10),
                                  wrap="word", padx=12, pady=8,
                                  relief="flat", borderwidth=0,
                                  state="normal")
            resp_widget.insert("1.0", response_text)
            resp_widget.config(state="disabled")
            resp_widget.pack(fill="x", padx=12, pady=(0, 8))
        tk.Frame(banner, bg="#F8FAFC", height=4).pack()
        return banner

    # ---------------------------------------------------- playback controls
    def _next_step(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._reveal_step()

    def _reveal_step(self):
        sc = self._scenario
        if sc is None or self._step >= len(sc["steps"]):
            return

        cards = self._steps_container.winfo_children()
        if self._step < len(cards):
            cards[self._step].pack(fill="x", pady=4)

        active_tool_id = sc["steps"][self._step]["tool"]
        for tid, frame in self._tool_frames.items():
            is_active = tid == active_tool_id
            col = THEME["accent_light"] if is_active else THEME["panel_bg"]
            bord = THEME["accent"] if is_active else THEME["border"]
            frame.configure(bg=col, highlightbackground=bord)
            for child in frame.winfo_children():
                try:
                    child.configure(bg=col)
                except Exception:
                    pass

        self._step += 1
        pct = self._step / len(sc["steps"])
        self._progress_bar.place(relx=0, rely=0, relwidth=pct, relheight=1)
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

        if self._step >= len(sc["steps"]):
            self._outcome_banner.pack(fill="x", pady=8)
            if self._live_handler is not None:
                self._followup_frame.pack(fill="x", pady=(0, 8))
            self._canvas.update_idletasks()
            self._canvas.yview_moveto(1.0)

    def _play_all(self):
        self._reset(keep_scenario=True)
        self._schedule_next_step()

    def _schedule_next_step(self):
        sc = self._scenario
        if sc and self._step < len(sc["steps"]):
            self._reveal_step()
            self._after_id = self.after(1400, self._schedule_next_step)

    def _reset(self, keep_scenario=False):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._step = 0
        self._render_execution_area()

    # -------------------------------------------------------- live API
    def _run_live(self):
        query = self._query_var.get().strip()
        if not query:
            return
        self._live_btn.configure(state="disabled", text="Running…")
        threading.Thread(target=self._call_claude_api, args=(query,), daemon=True).start()


    # ---------------------------------------------------------------------------
    # Add to imports at the top of agentVisual.py:
    # ---------------------------------------------------------------------------
    # from agentConversationHandler import AgentConversationHandler

    # ---------------------------------------------------------------------------
    # Replace _call_claude_api inside the AgentVisualizer class:
    # ---------------------------------------------------------------------------
    def _call_claude_api(self, query):
        try:
            from createAgent import create
            from toolUtils import get_tools_for_scenario
            from toolCalls import handle_tool_call
            from handleTool import AgentConversationHandler

            client = create()

            handler = AgentConversationHandler(
                client=client,
                scenario=self._scenario,
                model="claude-opus-4-6",
                max_tokens=4096,
                simulated_results=SIMULATED_RESULTS,  # pass the existing dict
                tool_handler=handle_tool_call,  # fallback for real tool calls
            )

            selected_tool_ids = [
                tid for tid in self._scenario["tools"]
                if self._live_tool_selection.get(tid, True)
            ]
            claude_tools = get_tools_for_scenario(selected_tool_ids)
            result = handler.run(query=query, claude_tools=claude_tools)

            if result.error:
                self.after(0, lambda e=result.error: self._on_live_result([], e, "", {}, None, None))
                return

            steps = result.steps
            final_response = result.final_response
            token_totals = result.token_totals

            if not steps:
                steps = [{
                    "tool": "python_execute",
                    "parameters": {"note": "No tools called"},
                    "result": "Claude responded directly without using any tools.",
                    "reasoning": "The query was answered without needing a tool.",
                    "status": "success",
                }]

            self.after(0, lambda s=steps, r=final_response, t=token_totals, h=handler, ct=claude_tools:
            self._on_live_result(s, None, r, t, h, ct))

        except Exception as exc:
            self.after(0, lambda e=exc: self._on_live_result([], str(e), "", {}, None, None))

    def _on_live_result(self, steps, error, final_response="", token_totals=None, handler=None, claude_tools=None):
        self._live_btn.configure(state="normal", text="⚡ Run Live")
        self._live_handler = handler
        self._live_claude_tools = claude_tools
        if error:
            import tkinter.messagebox as mb
            mb.showerror("API Error", str(error))
            return
        if not steps:
            steps = [{
                "tool": "python_execute",
                "parameters": {"note": "No tools called"},
                "result": "Claude responded directly without using any tools.",
                "reasoning": "The query was answered without needing a tool.",
                "status": "success",
            }]
        live_scenario = {
            "id": 99,
            "title": "Live Query",
            "difficulty": "easy",
            "description": self._scenario.get("description", ""),
            "query": self._query_var.get(),
            "tools": self._scenario.get("tools", [t["id"] for t in TOOLS]),
            "outcome": "success",
            "explanation": (
                f"Real Claude API response using claude-opus-4-6. "
                f"The model made {len(steps)} tool call(s) to answer your query."
            ),
            "steps": steps,
            "response": final_response,
            "token_totals": token_totals or {},
        }
        self._load_scenario(live_scenario)
        self._play_all()

    # -------------------------------------------------- follow-up prompt
    def _make_followup_frame(self, parent):
        frame = tk.Frame(parent, bg=THEME["accent_light"],
                         highlightthickness=1, highlightbackground=THEME["accent"])
        tk.Label(frame, text="Follow-up Prompt",
                 bg=THEME["accent_light"], fg=THEME["accent"],
                 font=("Helvetica", 9, "bold"),
                 anchor="w", padx=10, pady=2).pack(fill="x")
        inner = tk.Frame(frame, bg=THEME["accent_light"])
        inner.pack(fill="x", padx=10, pady=(0, 8))
        self._followup_var = tk.StringVar()
        entry = tk.Entry(inner, textvariable=self._followup_var,
                         bg=THEME["panel_bg"], fg=THEME["text"],
                         font=("Helvetica", 10),
                         relief="flat", bd=0,
                         insertbackground=THEME["accent"],
                         highlightthickness=0)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)
        entry.bind("<Return>", lambda _e: self._run_followup())
        self._followup_btn = tk.Button(inner, text="Send ↩",
                                       bg=THEME["accent"], fg="white",
                                       font=("Helvetica", 9, "bold"), relief="flat",
                                       padx=10, pady=4, cursor="hand2",
                                       command=self._run_followup)
        self._followup_btn.pack(side="left")
        return frame

    def _run_followup(self):
        followup = self._followup_var.get().strip()
        if not followup or self._live_handler is None:
            return
        self._followup_btn.configure(state="disabled", text="Running…")
        self._live_btn.configure(state="disabled")
        threading.Thread(
            target=self._call_followup_api,
            args=(followup, self._live_handler, self._live_claude_tools),
            daemon=True,
        ).start()

    def _call_followup_api(self, followup, handler, claude_tools):
        try:
            result = handler.continue_conversation(followup, claude_tools)
            if result.error:
                self.after(0, lambda e=result.error: self._on_followup_result([], e, "", {}, handler, claude_tools))
                return
            steps = result.steps
            final_response = result.final_response
            token_totals = result.token_totals
            if not steps:
                steps = [{
                    "tool": "python_execute",
                    "parameters": {"note": "No tools called"},
                    "result": "Claude responded directly without using any tools.",
                    "reasoning": "The follow-up was answered without needing a tool.",
                    "status": "success",
                }]
            self.after(0, lambda s=steps, r=final_response, t=token_totals, h=handler, ct=claude_tools:
                       self._on_followup_result(s, None, r, t, h, ct))
        except Exception as exc:
            self.after(0, lambda e=exc: self._on_followup_result([], str(e), "", {}, handler, claude_tools))

    def _on_followup_result(self, steps, error, final_response="", token_totals=None, handler=None, claude_tools=None):
        self._live_handler = handler
        self._live_claude_tools = claude_tools
        self._live_btn.configure(state="normal", text="⚡ Run Live")
        if error:
            import tkinter.messagebox as mb
            mb.showerror("API Error", str(error))
            self._followup_btn.configure(state="normal", text="Send ↩")
            return
        followup_text = self._followup_var.get().strip()
        self._followup_var.set("")
        live_scenario = {
            "id": 99,
            "title": "Live Query (Follow-up)",
            "difficulty": "easy",
            "description": self._scenario.get("description", ""),
            "query": followup_text,
            "tools": self._scenario.get("tools", [t["id"] for t in TOOLS]),
            "outcome": "success",
            "explanation": (
                f"Follow-up response using claude-opus-4-6. "
                f"The model made {len(steps)} tool call(s)."
            ),
            "steps": steps,
            "response": final_response,
            "token_totals": token_totals or {},
        }
        self._load_scenario(live_scenario)
        self._play_all()


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    app = AgentVisualizer()
    app.mainloop()
