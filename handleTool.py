"""
agentConversationHandler.py
============================
A handler for managing agentic conversation loops with proper context injection
per agent type. Designed to plug into agentVisual.py and support future agents.

Usage in agentVisual.py _call_claude_api:
    handler = AgentConversationHandler(client, scenario=self._scenario)
    result = handler.run(query)
    steps, final_response, token_totals = result
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any, Callable


# =============================================================================
# Agent Registry — add new agents here
# =============================================================================

@dataclass
class AgentConfig:
    """Defines how a specific agent type should be invoked."""
    name: str

    # System prompt injected at the start of every conversation for this agent
    system_prompt: str = ""

    # Default kwargs merged into tool_input before calling the handler
    # e.g. {"file_directory": "agentDocs"}
    default_tool_kwargs: dict[str, Any] = field(default_factory=dict)

    # Optional callable: (tool_name, tool_input) -> bool
    # Return True if this config owns the given tool call
    owns_tool: Callable[[str, dict], bool] | None = None


# Built-in agent configurations
FILE_READ_AGENT = AgentConfig(
    name="fileReadAgent",
    system_prompt=(
        "You are a helpful assistant with access to a document library. "
        "When asked about financial or policy data, use find_file_by_description "
        "to locate and retrieve the relevant file before answering. "
        "Always base your answer on the actual file contents."
    ),
    default_tool_kwargs={"file_directory": "agentDocs"},
    owns_tool=lambda tool_name, _: tool_name == "find_file_by_description",
)

IRR_AGENT = AgentConfig(
    name="IRR_AGENT",
    system_prompt=(
        "When asked to calculate IRR"
    ),
    default_tool_kwargs={},
    owns_tool=lambda tool_name, _: tool_name == "local_irr",
)

ALFA_Runner = AgentConfig(
    name="alfa_runner",
    system_prompt=(
        "You are a helpful assistant with access to a document library. "
        "When asked about financial or policy data, use find_file_by_description "
        "to locate and retrieve the relevant file before answering. "
        "Always base your answer on the actual file contents."
    ),
    default_tool_kwargs={"file_directory": "agentDocs"},
    owns_tool=lambda tool_name, _: tool_name == "find_file_by_description",
)


ROUTER_AGENT = AgentConfig(
    name="routerAgent",
    system_prompt=(
        "You are an orchestrator with access to specialist tools. "
        "Always start by calling the 'router' tool with the user's complete query. "
        "Then follow the routing instructions returned to call the appropriate specialist tools."
    ),
    default_tool_kwargs={},
    owns_tool=lambda tool_name, _: tool_name == "router",
)

# Registry maps tool_id -> AgentConfig
AGENT_REGISTRY: dict[str, AgentConfig] = {
    "router": ROUTER_AGENT,
    "find_file_by_description": FILE_READ_AGENT,
    "local_irr":IRR_AGENT
    # "database_query": DATABASE_AGENT,
    # "send_email": EMAIL_AGENT,
}


# =============================================================================
# Result type
# =============================================================================

@dataclass
class ConversationResult:
    steps: list[dict[str, Any]]
    final_response: str
    token_totals: dict[str, int]
    error: str | None = None


# =============================================================================
# Handler
# =============================================================================

class AgentConversationHandler:
    """
    Manages a full agentic conversation loop with:
    - Correct system prompt injection based on which tools are active in the scenario
    - Proper default kwargs merged into tool inputs before dispatch
    - Extensible tool dispatch via AGENT_REGISTRY
    - Token tracking
    """

    def __init__(
        self,
        client,
        scenario: dict[str, Any],
        model: str = "claude-opus-4-6",
        max_tokens: int = 4096,
        simulated_results: dict[str, str] | None = None,
        tool_handler: Callable | None = None,
    ):
        """
        Parameters
        ----------
        client          : anthropic.Anthropic client
        scenario        : the current scenario dict from agentVisual.py
        model           : Claude model string
        max_tokens      : max tokens per API call
        simulated_results : optional dict of tool_name -> simulated result string
                            (takes priority over live tool calls)
        tool_handler    : fallback callable(client, tool_name, tool_input) -> str
                          used when a tool isn't simulated and not in AGENT_REGISTRY
        """
        self.client = client
        self.scenario = scenario
        self.model = model
        self.max_tokens = max_tokens
        self.simulated_results = simulated_results or {}
        self.tool_handler = tool_handler

        # Determine active tool IDs for this scenario
        self._active_tool_ids: list[str] = scenario.get("tools", [])

        # Resolve which AgentConfigs apply based on active tools
        self._active_configs: list[AgentConfig] = self._resolve_configs()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, query: str, claude_tools: list[dict]) -> ConversationResult:
        """
        Run the full agentic loop for the given query.

        Parameters
        ----------
        query        : the user's natural language query
        claude_tools : list of Anthropic tool dicts (from toolUtils.get_tools_for_scenario)

        Returns
        -------
        ConversationResult with steps, final_response, token_totals, and optional error
        """
        system_prompt = self._build_system_prompt()
        messages = [{"role": "user", "content": query}]
        steps: list[dict[str, Any]] = []
        total_input = 0
        total_output = 0

        try:
            while True:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "tools": claude_tools,
                    "messages": messages,
                }
                if system_prompt:
                    kwargs["system"] = system_prompt

                response = self.client.messages.create(**kwargs)

                call_input = response.usage.input_tokens
                call_output = response.usage.output_tokens
                total_input += call_input
                total_output += call_output

                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

                if response.stop_reason == "end_turn" or not tool_use_blocks:
                    break

                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in tool_use_blocks:
                    result_str = self._dispatch_tool(block.name, block.input)

                    steps.append({
                        "tool": block.name,
                        "parameters": block.input,
                        "result": result_str,
                        "reasoning": "Claude selected this tool to handle the request.",
                        "status": "success",
                        "tokens": {"input": call_input, "output": call_output},
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

                messages.append({"role": "user", "content": tool_results})

            final_response = " ".join(
                b.text for b in response.content if hasattr(b, "text") and b.text
            ).strip()

            # Persist conversation history for follow-up calls
            messages.append({"role": "assistant", "content": response.content})
            self._messages = messages
            self._system_prompt = system_prompt

            return ConversationResult(
                steps=steps,
                final_response=final_response,
                token_totals={"input": total_input, "output": total_output},
            )

        except Exception as exc:
            self._messages = messages
            self._system_prompt = system_prompt
            return ConversationResult(
                steps=steps,
                final_response="",
                token_totals={"input": total_input, "output": total_output},
                error=str(exc),
            )

    def continue_conversation(self, followup: str, claude_tools: list[dict]) -> "ConversationResult":
        """Continue an existing conversation with a follow-up user message."""
        messages = getattr(self, "_messages", []) + [{"role": "user", "content": followup}]
        system_prompt = getattr(self, "_system_prompt", self._build_system_prompt())
        steps: list[dict] = []
        total_input = 0
        total_output = 0

        try:
            while True:
                kwargs: dict = {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "tools": claude_tools,
                    "messages": messages,
                }
                if system_prompt:
                    kwargs["system"] = system_prompt

                response = self.client.messages.create(**kwargs)

                call_input = response.usage.input_tokens
                call_output = response.usage.output_tokens
                total_input += call_input
                total_output += call_output

                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

                if response.stop_reason == "end_turn" or not tool_use_blocks:
                    break

                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in tool_use_blocks:
                    result_str = self._dispatch_tool(block.name, block.input)
                    steps.append({
                        "tool": block.name,
                        "parameters": block.input,
                        "result": result_str,
                        "reasoning": "Claude selected this tool to handle the follow-up.",
                        "status": "success",
                        "tokens": {"input": call_input, "output": call_output},
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

                messages.append({"role": "user", "content": tool_results})

            final_response = " ".join(
                b.text for b in response.content if hasattr(b, "text") and b.text
            ).strip()

            messages.append({"role": "assistant", "content": response.content})
            self._messages = messages

            return ConversationResult(
                steps=steps,
                final_response=final_response,
                token_totals={"input": total_input, "output": total_output},
            )

        except Exception as exc:
            self._messages = messages
            return ConversationResult(
                steps=steps,
                final_response="",
                token_totals={"input": total_input, "output": total_output},
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_configs(self) -> list[AgentConfig]:
        """Return unique AgentConfigs for the tools active in this scenario."""
        seen: set[str] = set()
        configs: list[AgentConfig] = []
        for tool_id in self._active_tool_ids:
            cfg = AGENT_REGISTRY.get(tool_id)
            if cfg and cfg.name not in seen:
                configs.append(cfg)
                seen.add(cfg.name)
        return configs

    def _build_system_prompt(self) -> str:
        """Combine system prompts from all active agent configs."""
        parts = [cfg.system_prompt for cfg in self._active_configs if cfg.system_prompt]
        return "\n\n".join(parts)

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        """
        Resolve and execute a tool call, with three priority levels:
        1. Simulated results (from agentVisual.py SIMULATED_RESULTS)
        2. AGENT_REGISTRY with merged default_tool_kwargs
        3. Fallback tool_handler (e.g. filereadAgent.handle_tool_call)
        """
        # Priority 1: simulated
        if tool_name in self.simulated_results:
            return self.simulated_results[tool_name]

        # Priority 2: registered agent — merge default kwargs
        cfg = AGENT_REGISTRY.get(tool_name)
        if cfg:
            merged_input = {**cfg.default_tool_kwargs, **tool_input}
            if self.tool_handler:
                return self.tool_handler(self.client, tool_name, merged_input)

        # Priority 3: fallback handler with original input
        if self.tool_handler:
            return self.tool_handler(self.client, tool_name, tool_input)

        return f"No handler registered for tool '{tool_name}'."