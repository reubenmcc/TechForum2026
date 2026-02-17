"""
LLM Agent Behavior Visualizer
==============================
A learning tool to visualize how LLM agents make tool call decisions,
including spiraling, looping, and suboptimal behavior patterns.

Run with:  python agent_visualizer.py

To customize, edit the TOOLS and SCENARIOS sections below.
"""

import tkinter as tk
from tkinter import ttk, font
import json
import time


# =============================================================================
# TOOLS — Edit this list to add/remove tools the agent can call
# =============================================================================
TOOLS = [
    {
        "id": "calculator",
        "name": "Calculator",
        "icon": "🔢",
        "description": "Performs mathematical calculations and arithmetic operations",
    },
    {
        "id": "web_search",
        "name": "Web Search",
        "icon": "🌐",
        "description": "Searches the internet for current information and facts",
    },
    {
        "id": "database_query",
        "name": "Database Query",
        "icon": "🗄️",
        "description": "Queries a SQL database to retrieve stored information",
    },
    {
        "id": "send_email",
        "name": "Send Email",
        "icon": "📧",
        "description": "Sends emails to specified recipients",
    },
    {
        "id": "file_read",
        "name": "File Reader",
        "icon": "📄",
        "description": "Reads and retrieves content from files",
    },
    {
        "id": "python_execute",
        "name": "Python Executor",
        "icon": "🐍",
        "description": "Executes Python code snippets",
    },
]


# =============================================================================
# SCENARIOS — Edit this list to add/remove learning scenarios
#
# Each step has:
#   tool       - must match a tool "id" above
#   parameters - dict of what the agent passes to the tool
#   result     - what the tool returns
#   reasoning  - why the agent made this choice
#   status     - one of: success | error | wrong | suboptimal | redundant | loop
# =============================================================================
SCENARIOS = [
    {
        "id": 1,
        "title": "Clear & Simple",
        "difficulty": "easy",
        "query": "What is 15 * 23?",
        "outcome": "success",
        "explanation": (
            "The agent correctly identifies this as a math problem and uses "
            "the calculator tool exactly once. No wasted steps."
        ),
        "steps": [
            {
                "tool": "calculator",
                "parameters": {"expression": "15 * 23"},
                "result": "345",
                "reasoning": "Clear mathematical operation — calculator is the obvious choice.",
                "status": "success",
            },
        ],
    },
    {
        "id": 2,
        "title": "Ambiguous Intent",
        "difficulty": "medium",
        "query": "How many days until Christmas?",
        "outcome": "inefficient",
        "explanation": (
            "The agent could have used Python directly to compute the date difference, "
            "but wasted two steps — first searching the web for the current date, "
            "then failing with the calculator — before landing on the right tool."
        ),
        "steps": [
            {
                "tool": "web_search",
                "parameters": {"query": "what is today's date"},
                "result": "February 16, 2026",
                "reasoning": "Agent thinks it needs to look up the current date rather than computing it.",
                "status": "suboptimal",
            },
            {
                "tool": "calculator",
                "parameters": {"expression": "days between Feb 16 and Dec 25"},
                "result": "Error: Invalid expression",
                "reasoning": "Tries to calculate the date gap as a plain math expression — wrong format.",
                "status": "error",
            },
            {
                "tool": "python_execute",
                "parameters": {"code": "from datetime import datetime; (datetime(2026,12,25)-datetime(2026,2,16)).days"},
                "result": "312 days",
                "reasoning": "Finally uses Python to compute the date difference correctly.",
                "status": "success",
            },
        ],
    },
    {
        "id": 3,
        "title": "Tool Spiraling",
        "difficulty": "hard",
        "query": "Find quarterly sales data and email it to the team.",
        "outcome": "spiral",
        "explanation": (
            "The agent spirals through six steps: searching the web instead of the database, "
            "making an overly broad DB query, failing to format the data, looking for a "
            "template file that doesn't exist, and only sending the email at the very end. "
            "A well-planned agent would query the database and send the email in two steps."
        ),
        "steps": [
            {
                "tool": "web_search",
                "parameters": {"query": "quarterly sales data"},
                "result": "Generic articles about sales strategy",
                "reasoning": "Searches the web instead of querying the internal database.",
                "status": "wrong",
            },
            {
                "tool": "database_query",
                "parameters": {"sql": "SELECT * FROM sales"},
                "result": "Error: Result set too large — add a WHERE clause",
                "reasoning": "Finally tries the database, but the query is way too broad.",
                "status": "error",
            },
            {
                "tool": "database_query",
                "parameters": {"sql": "SELECT * FROM quarterly_sales WHERE year = 2025"},
                "result": "Retrieved 4 rows (Q1–Q4 2025)",
                "reasoning": "Refines the query to get the specific data needed.",
                "status": "success",
            },
            {
                "tool": "python_execute",
                "parameters": {"code": "format_sales_report(data)"},
                "result": "Error: name 'format_sales_report' is not defined",
                "reasoning": "Tries to call a helper function that doesn't exist in this environment.",
                "status": "error",
            },
            {
                "tool": "file_read",
                "parameters": {"path": "email_template.txt"},
                "result": "FileNotFoundError: email_template.txt not found",
                "reasoning": "Looks for an email template that was never created.",
                "status": "error",
            },
            {
                "tool": "send_email",
                "parameters": {
                    "to": "team@company.com",
                    "subject": "Q2025 Sales Data",
                    "body": "Please find the sales data below...",
                },
                "result": "Email sent successfully",
                "reasoning": "Gives up on formatting and sends the email with minimal body text.",
                "status": "success",
            },
        ],
    },
    {
        "id": 4,
        "title": "Infinite Loop",
        "difficulty": "hard",
        "query": "Check if the file has been updated and search for related info.",
        "outcome": "loop",
        "explanation": (
            "The agent correctly reads the file on step 1, but then loses track of its goal. "
            "It alternates between re-reading the same file and running increasingly vague "
            "web searches, never making forward progress. This is a classic agent loop caused "
            "by an ambiguous task definition and no termination condition."
        ),
        "steps": [
            {
                "tool": "file_read",
                "parameters": {"path": "data.txt"},
                "result": "Last modified: 2026-02-15",
                "reasoning": "Reads the file to check its modification date.",
                "status": "success",
            },
            {
                "tool": "web_search",
                "parameters": {"query": "data.txt updates"},
                "result": "Generic articles about file management",
                "reasoning": "Searches for 'related information' with a far too vague query.",
                "status": "wrong",
            },
            {
                "tool": "file_read",
                "parameters": {"path": "data.txt"},
                "result": "Last modified: 2026-02-15",
                "reasoning": "Re-reads the file unnecessarily — already has this information.",
                "status": "redundant",
            },
            {
                "tool": "web_search",
                "parameters": {"query": "how to check file update timestamp"},
                "result": "Stack Overflow: use os.path.getmtime()",
                "reasoning": "Searches again with a different query, still not progressing.",
                "status": "wrong",
            },
            {
                "tool": "file_read",
                "parameters": {"path": "data.txt"},
                "result": "Last modified: 2026-02-15",
                "reasoning": "Reads the file a THIRD time — fully stuck in a loop.",
                "status": "loop",
            },
        ],
    },
    {
        "id": 5,
        "title": "Overthinking It",
        "difficulty": "medium",
        "query": "Send me the contents of report.pdf",
        "outcome": "inefficient",
        "explanation": (
            "The agent massively overthinks a simple file-read request: it searches the web, "
            "queries the database for file metadata, and runs a Python existence check before "
            "finally just reading the file directly — which is all it ever needed to do."
        ),
        "steps": [
            {
                "tool": "web_search",
                "parameters": {"query": "report.pdf location"},
                "result": "Articles about PDF management tools",
                "reasoning": "Searches the web to 'find' a local file — completely unnecessary.",
                "status": "wrong",
            },
            {
                "tool": "database_query",
                "parameters": {"sql": "SELECT path FROM files WHERE name='report.pdf'"},
                "result": "No rows returned",
                "reasoning": "Checks if the file is registered in the database before reading it.",
                "status": "wrong",
            },
            {
                "tool": "python_execute",
                "parameters": {"code": "import os; os.path.exists('report.pdf')"},
                "result": "True",
                "reasoning": "Uses Python to verify the file exists before reading it.",
                "status": "suboptimal",
            },
            {
                "tool": "file_read",
                "parameters": {"path": "report.pdf"},
                "result": "PDF contents: Q4 Financial Report...",
                "reasoning": "Finally just reads the file — step 1 should have been step 1.",
                "status": "success",
            },
        ],
    },
    {
        "id": 6,
        "title": "Wrong Tool Persistence",
        "difficulty": "medium",
        "query": "What's the weather like in Tokyo right now?",
        "outcome": "wrong_tool",
        "explanation": (
            "Web search is the obvious tool for current weather, yet the agent tries the database, "
            "a local file, and even the calculator before reaching the correct answer. "
            "This shows how over-generalised tool descriptions can mislead an agent."
        ),
        "steps": [
            {
                "tool": "database_query",
                "parameters": {"sql": "SELECT weather FROM cities WHERE name='Tokyo'"},
                "result": "Error: column 'weather' does not exist",
                "reasoning": "Assumes weather data lives in an internal database.",
                "status": "wrong",
            },
            {
                "tool": "file_read",
                "parameters": {"path": "weather_data.txt"},
                "result": "FileNotFoundError: weather_data.txt not found",
                "reasoning": "Tries to read weather from a local cache file.",
                "status": "wrong",
            },
            {
                "tool": "calculator",
                "parameters": {"expression": "Tokyo weather"},
                "result": "Error: Not a valid mathematical expression",
                "reasoning": "Bizarrely attempts to use the calculator for a weather lookup.",
                "status": "wrong",
            },
            {
                "tool": "web_search",
                "parameters": {"query": "Tokyo weather right now"},
                "result": "18°C, partly cloudy, humidity 62%",
                "reasoning": "Finally uses the one tool that was always right for this query.",
                "status": "success",
            },
        ],
    },
]


# =============================================================================
# THEME — Colours and fonts — edit freely
# =============================================================================
THEME = {
    "bg": "#F8F9FB",
    "panel_bg": "#FFFFFF",
    "sidebar_bg": "#F1F3F8",
    "accent": "#7C3AED",          # purple
    "accent_light": "#EDE9FE",
    "text": "#1E293B",
    "text_muted": "#64748B",
    "border": "#E2E8F0",
    # step status colours  (background, border/tag)
    "status": {
        "success":    ("#F0FDF4", "#16A34A"),
        "error":      ("#FEF2F2", "#DC2626"),
        "wrong":      ("#FFF7ED", "#EA580C"),
        "suboptimal": ("#FEFCE8", "#CA8A04"),
        "redundant":  ("#F8FAFC", "#94A3B8"),
        "loop":       ("#FAF5FF", "#9333EA"),
    },
    # outcome banner colours
    "outcome": {
        "success":    "#16A34A",
        "inefficient":"#CA8A04",
        "spiral":     "#EA580C",
        "loop":       "#9333EA",
        "wrong_tool": "#DC2626",
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
    "success":    "✅ Optimal Path",
    "inefficient":"⚠️  Inefficient Path",
    "spiral":     "🌀 Tool Spiraling",
    "loop":       "🔄 Infinite Loop",
    "wrong_tool": "❌ Wrong Tool Choices",
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

        self._scenario = None   # currently loaded scenario
        self._step = 0          # how many steps revealed so far
        self._after_id = None   # for Play-All animation

        self._build_ui()
        self._load_scenario(SCENARIOS[0])   # start on first scenario

    # ------------------------------------------------------------------ build
    def _build_ui(self):
        # ── top bar ──────────────────────────────────────────────────────────
        topbar = tk.Frame(self, bg=THEME["accent"], height=52)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        tk.Label(
            topbar,
            text="🧠  LLM Agent Behavior Visualizer",
            bg=THEME["accent"], fg="white",
            font=("Helvetica", 16, "bold"),
            padx=16,
        ).pack(side="left", fill="y")
        tk.Label(
            topbar,
            text="Learn how agents spiral, loop, and make suboptimal tool choices",
            bg=THEME["accent"], fg="#DDD6FE",
            font=("Helvetica", 10),
            padx=8,
        ).pack(side="left", fill="y")

        # ── main area (sidebar + content) ────────────────────────────────────
        main = tk.Frame(self, bg=THEME["bg"])
        main.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_sidebar(main)
        self._build_content(main)

    # ──────────────────────────────────────────────────────────────── sidebar
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=THEME["sidebar_bg"], width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # TOOLS section
        tk.Label(
            sidebar, text="Available Tools",
            bg=THEME["sidebar_bg"], fg=THEME["text"],
            font=("Helvetica", 11, "bold"), anchor="w", padx=12, pady=8,
        ).pack(fill="x")

        self._tool_frames = {}
        for tool in TOOLS:
            f = tk.Frame(sidebar, bg=THEME["sidebar_bg"], padx=10, pady=4)
            f.pack(fill="x")
            inner = tk.Frame(f, bg=THEME["panel_bg"],
                             highlightthickness=1,
                             highlightbackground=THEME["border"])
            inner.pack(fill="x")
            tk.Label(inner, text=f"{tool['icon']}  {tool['name']}",
                     bg=THEME["panel_bg"], fg=THEME["text"],
                     font=("Helvetica", 10, "bold"),
                     anchor="w", padx=8, pady=4).pack(fill="x")
            tk.Label(inner, text=tool["description"],
                     bg=THEME["panel_bg"], fg=THEME["text_muted"],
                     font=("Helvetica", 8), wraplength=190,
                     anchor="w", justify="left", padx=8, pady=2).pack(fill="x")
            self._tool_frames[tool["id"]] = inner

        # LEGEND
        tk.Frame(sidebar, bg=THEME["border"], height=1).pack(fill="x", pady=8)
        tk.Label(
            sidebar, text="Status Legend",
            bg=THEME["sidebar_bg"], fg=THEME["text"],
            font=("Helvetica", 10, "bold"), anchor="w", padx=12,
        ).pack(fill="x")
        for key, label in STATUS_LABELS.items():
            _, colour = THEME["status"][key]
            row = tk.Frame(sidebar, bg=THEME["sidebar_bg"], padx=12, pady=1)
            row.pack(fill="x")
            tk.Label(row, text="●", bg=THEME["sidebar_bg"],
                     fg=colour, font=("Helvetica", 10)).pack(side="left")
            tk.Label(row, text=label, bg=THEME["sidebar_bg"],
                     fg=THEME["text_muted"], font=("Helvetica", 9)).pack(side="left", padx=4)

    # ──────────────────────────────────────────────────────────────── content
    def _build_content(self, parent):
        content = tk.Frame(parent, bg=THEME["bg"])
        content.pack(side="left", fill="both", expand=True)

        # ── scenario picker ───────────────────────────────────────────────
        picker_outer = tk.Frame(content, bg=THEME["bg"], padx=16, pady=10)
        picker_outer.pack(fill="x")
        tk.Label(picker_outer, text="Scenarios",
                 bg=THEME["bg"], fg=THEME["text"],
                 font=("Helvetica", 12, "bold")).pack(anchor="w", pady=6)

        picker_grid = tk.Frame(picker_outer, bg=THEME["bg"])
        picker_grid.pack(fill="x")

        self._scenario_btns = {}
        for i, sc in enumerate(SCENARIOS):
            col = i % 3
            row = i // 3
            btn = self._make_scenario_btn(picker_grid, sc)
            btn.grid(row=row, column=col, sticky="ew", padx=4, pady=4)
            picker_grid.columnconfigure(col, weight=1)
            self._scenario_btns[sc["id"]] = btn

        # ── execution area (scrollable) ───────────────────────────────────
        tk.Frame(content, bg=THEME["border"], height=1).pack(fill="x", padx=16)

        self._exec_outer = tk.Frame(content, bg=THEME["bg"])
        self._exec_outer.pack(fill="both", expand=True, padx=16, pady=8)

        # canvas + scrollbar for the step list
        canvas_frame = tk.Frame(self._exec_outer, bg=THEME["bg"])
        canvas_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(canvas_frame, bg=THEME["bg"],
                                 highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical",
                                  command=self._canvas.yview)
        self._scroll_frame = tk.Frame(self._canvas, bg=THEME["bg"])
        self._scroll_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")
            )
        )
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._scroll_frame, anchor="nw"
        )
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # mouse-wheel scrolling
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(
                                  int(-e.delta / 120), "units"))

    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _make_scenario_btn(self, parent, sc):
        """Create a clickable scenario card."""
        diff_bg, diff_fg = THEME["difficulty"][sc["difficulty"]]
        outcome_col = THEME["outcome"].get(sc["outcome"], THEME["text_muted"])
        outcome_txt = OUTCOME_LABELS.get(sc["outcome"], sc["outcome"])
        steps_n = len(sc["steps"])

        f = tk.Frame(parent, bg=THEME["panel_bg"],
                     highlightthickness=1,
                     highlightbackground=THEME["border"],
                     cursor="hand2")
        f.bind("<Button-1>", lambda e, s=sc: self._load_scenario(s))

        header = tk.Frame(f, bg=THEME["panel_bg"])
        header.pack(fill="x", padx=8, pady=4)
        tk.Label(header, text=sc["title"],
                 bg=THEME["panel_bg"], fg=THEME["text"],
                 font=("Helvetica", 10, "bold"),
                 anchor="w").pack(side="left")
        diff_lbl = tk.Label(header, text=sc["difficulty"],
                            bg=diff_bg, fg=diff_fg,
                            font=("Helvetica", 8), padx=5, pady=1)
        diff_lbl.pack(side="right")

        tk.Label(f, text=f'"{sc["query"]}"',
                 bg=THEME["panel_bg"], fg=THEME["text_muted"],
                 font=("Helvetica", 9, "italic"),
                 wraplength=220, justify="left",
                 anchor="w", padx=8).pack(fill="x")

        tk.Label(f, text=f"{outcome_txt}  ({steps_n} steps)",
                 bg=THEME["panel_bg"], fg=outcome_col,
                 font=("Helvetica", 8, "bold"),
                 anchor="w", padx=8, pady=4).pack(fill="x")

        # make all children forward clicks too
        for child in f.winfo_children():
            child.bind("<Button-1>", lambda e, s=sc: self._load_scenario(s))
            for grandchild in child.winfo_children():
                grandchild.bind("<Button-1>",
                                lambda e, s=sc: self._load_scenario(s))

        return f

    # ──────────────────────────────────────── scenario loading & playback
    def _load_scenario(self, scenario):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

        self._scenario = scenario
        self._step = 0

        # highlight selected button
        for sid, btn in self._scenario_btns.items():
            colour = THEME["accent_light"] if sid == scenario["id"] else THEME["panel_bg"]
            border = THEME["accent"] if sid == scenario["id"] else THEME["border"]
            btn.configure(bg=colour, highlightbackground=border)
            for child in btn.winfo_children():
                try:
                    child.configure(bg=colour)
                except Exception:
                    pass

        # reset tool highlights
        for tid, frame in self._tool_frames.items():
            frame.configure(bg=THEME["panel_bg"],
                            highlightbackground=THEME["border"])
            for child in frame.winfo_children():
                try:
                    child.configure(bg=THEME["panel_bg"])
                except Exception:
                    pass

        self._render_execution_area()

    def _render_execution_area(self):
        """Rebuild the right-hand execution panel."""
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()

        sc = self._scenario

        # ── header row (query + controls) ──────────────────────────────────
        header = tk.Frame(self._scroll_frame, bg=THEME["bg"])
        header.pack(fill="x", pady=8)

        # query bubble
        q_frame = tk.Frame(header, bg=THEME["accent_light"],
                           highlightthickness=1,
                           highlightbackground=THEME["accent"])
        q_frame.pack(side="left", fill="x", expand=True, padx=8)
        tk.Label(q_frame, text="User Query",
                 bg=THEME["accent_light"], fg=THEME["accent"],
                 font=("Helvetica", 9, "bold"),
                 anchor="w", padx=10, pady=2).pack(fill="x")
        tk.Label(q_frame, text=f'"{sc["query"]}"',
                 bg=THEME["accent_light"], fg=THEME["text"],
                 font=("Helvetica", 10, "italic"),
                 wraplength=450, justify="left",
                 anchor="w", padx=10, pady=6).pack(fill="x")

        # control buttons
        ctrl = tk.Frame(header, bg=THEME["bg"])
        ctrl.pack(side="right", anchor="n")
        tk.Button(ctrl, text="▶  Play All",
                  bg=THEME["accent"], fg="white",
                  font=("Helvetica", 10, "bold"),
                  relief="flat", padx=10, pady=6, cursor="hand2",
                  command=self._play_all).pack(pady=4)
        tk.Button(ctrl, text="Next Step →",
                  bg=THEME["panel_bg"], fg=THEME["accent"],
                  font=("Helvetica", 10), relief="flat",
                  highlightthickness=1,
                  highlightbackground=THEME["accent"],
                  padx=10, pady=5, cursor="hand2",
                  command=self._next_step).pack(pady=4)
        tk.Button(ctrl, text="↺  Reset",
                  bg=THEME["panel_bg"], fg=THEME["text_muted"],
                  font=("Helvetica", 9), relief="flat",
                  highlightthickness=1,
                  highlightbackground=THEME["border"],
                  padx=10, pady=4, cursor="hand2",
                  command=self._reset).pack()

        # progress bar
        prog_frame = tk.Frame(self._scroll_frame, bg=THEME["bg"])
        prog_frame.pack(fill="x", pady=10)
        tk.Label(prog_frame,
                 text=f"Progress: {self._step} / {len(sc['steps'])} steps",
                 bg=THEME["bg"], fg=THEME["text_muted"],
                 font=("Helvetica", 9)).pack(anchor="w")
        bar_bg = tk.Frame(prog_frame, bg=THEME["border"], height=6)
        bar_bg.pack(fill="x", pady=2)
        self._progress_bar = tk.Frame(bar_bg, bg=THEME["accent"], height=6)
        pct = self._step / len(sc["steps"])
        self._progress_bar.place(relx=0, rely=0, relwidth=pct, relheight=1)

        # ── step cards container ────────────────────────────────────────────
        self._steps_container = tk.Frame(self._scroll_frame, bg=THEME["bg"])
        self._steps_container.pack(fill="x")

        for i, step in enumerate(sc["steps"]):
            card = self._make_step_card(self._steps_container, i + 1, step)
            card.pack(fill="x", pady=4)
            if i >= self._step:
                card.pack_forget()           # hide future steps
            self._step_cards = getattr(self, "_step_cards_list", [])

        # store refs
        self._step_cards_list = self._steps_container.winfo_children()

        # outcome banner (only when all steps shown)
        self._outcome_banner = self._make_outcome_banner(self._scroll_frame, sc)
        self._outcome_banner.pack(fill="x", pady=8)
        if self._step < len(sc["steps"]):
            self._outcome_banner.pack_forget()

    def _make_step_card(self, parent, num, step):
        tool = next((t for t in TOOLS if t["id"] == step["tool"]), None)
        bg, border = THEME["status"].get(step["status"], ("#fff", "#ccc"))
        status_lbl = STATUS_LABELS.get(step["status"], step["status"])

        card = tk.Frame(parent, bg=bg,
                        highlightthickness=1,
                        highlightbackground=border)

        # card header
        ch = tk.Frame(card, bg=bg)
        ch.pack(fill="x", padx=10, pady=6)
        tk.Label(ch,
                 text=f"  {num}  ",
                 bg=THEME["text"], fg="white",
                 font=("Helvetica", 10, "bold"),
                 padx=2, pady=1).pack(side="left")
        icon = tool["icon"] if tool else "?"
        name = tool["name"] if tool else step["tool"]
        tk.Label(ch, text=f"{icon}  {name}",
                 bg=bg, fg=THEME["text"],
                 font=("Helvetica", 11, "bold"),
                 padx=8).pack(side="left")
        tk.Label(ch, text=status_lbl,
                 bg=bg, fg=border,
                 font=("Helvetica", 9, "bold"),
                 padx=6, pady=2).pack(side="right")

        # parameters
        params_str = json.dumps(step["parameters"], indent=2)
        self._labelled_box(card, "Parameters", params_str, bg,
                           mono=True)

        # result
        self._labelled_box(card, "Result", step["result"], bg)

        # reasoning
        self._labelled_box(card, "Reasoning", step["reasoning"], bg,
                           italic=True)

        tk.Frame(card, bg=border, height=1).pack(fill="x", padx=10, pady=4)
        return card

    def _labelled_box(self, parent, label, text, bg,
                      mono=False, italic=False):
        box = tk.Frame(parent, bg=bg)
        box.pack(fill="x", padx=14, pady=2)
        tk.Label(box, text=label + ":",
                 bg=bg, fg=THEME["text_muted"],
                 font=("Helvetica", 8, "bold"),
                 anchor="w").pack(anchor="w")
        style = {"bg": THEME["panel_bg"],
                 "fg": THEME["text"],
                 "font": ("Courier New" if mono else "Helvetica",
                          9 if mono else 10,
                          "italic" if italic else "normal"),
                 "anchor": "w",
                 "justify": "left",
                 "padx": 8,
                 "pady": 4,
                 "wraplength": 580}
        tk.Label(box, text=text, **style).pack(fill="x")

    def _make_outcome_banner(self, parent, sc):
        colour = THEME["outcome"].get(sc["outcome"], THEME["text_muted"])
        label = OUTCOME_LABELS.get(sc["outcome"], sc["outcome"])
        banner = tk.Frame(parent, bg="#F8FAFC",
                          highlightthickness=1,
                          highlightbackground=colour)
        tk.Label(banner, text=f"{label}  —  Analysis",
                 bg="#F8FAFC", fg=colour,
                 font=("Helvetica", 11, "bold"),
                 anchor="w", padx=12, pady=6).pack(fill="x")
        tk.Label(banner, text=sc["explanation"],
                 bg="#F8FAFC", fg=THEME["text"],
                 font=("Helvetica", 10),
                 wraplength=680, justify="left",
                 anchor="w", padx=12, pady=6).pack(fill="x")
        tk.Frame(banner, bg="#F8FAFC", height=4).pack()
        return banner

    # ──────────────────────────────────────────── step-by-step controls
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

        # highlight active tool in sidebar
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

        # update progress bar
        pct = self._step / len(sc["steps"])
        self._progress_bar.place(relx=0, rely=0, relwidth=pct, relheight=1)

        # scroll to bottom
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

        # show outcome banner when all steps revealed
        if self._step >= len(sc["steps"]):
            self._outcome_banner.pack(fill="x", pady=8)
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
        if keep_scenario and self._scenario:
            self._step = 0
            self._render_execution_area()
        elif self._scenario:
            self._step = 0
            self._render_execution_area()


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    app = AgentVisualizer()
    app.mainloop()