"""Model adapter interfaces and implementations for SLOP affordance selection."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Protocol

from action_router import ActionInvocation
from slop_tree import SlopNode


class ModelAdapter(Protocol):
    """Protocol for model integrations that select one SLOP affordance."""

    def choose_action(self, user_text: str, tree: Any) -> ActionInvocation:
        """Choose an action invocation from user text and projected state."""


class DeterministicAdapter:
    """Deterministic action selector used for tests and offline demos."""

    def choose_action(self, user_text: str, tree: Any) -> ActionInvocation:
        """Select an action with the prototype's stable string-matching logic."""
        normalized = user_text.strip().lower()
        if normalized.startswith("create "):
            return ActionInvocation(
                action="create_item",
                params={"title": user_text.strip()[len("create ") :].strip()},
            )
        if "complete" in normalized:
            open_item = _first_incomplete_todo(tree)
            if open_item is None:
                raise ValueError("no incomplete todo item is available to complete")
            return ActionInvocation(
                action="complete_item",
                params={"id": open_item.id},
            )
        raise ValueError(f"deterministic adapter cannot choose an action for: {user_text!r}")


class OpenAIAdapter:
    """OpenAI adapter using SLOP affordances as function tools.

    Expected tool-call response formats:
    - Responses API: ``{"output": [{"type": "function_call", "name": "...",
      "arguments": "{...}"}]}``, including equivalent nested ``content`` items.
    - Chat Completions API: ``{"choices": [{"message": {"tool_calls": [
      {"function": {"name": "...", "arguments": "{...}"}}]}}]}``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4.1-mini",
        assembler: Any | None = None,
        num_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 10.0,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIAdapter")
        self._model = model
        self._assembler = assembler
        self._num_retries = num_retries
        self._retry_delay = retry_delay
        self._max_retry_delay = max_retry_delay
        self._timeout = timeout

    def choose_action(self, user_text: str, tree: Any) -> ActionInvocation:
        """Ask OpenAI to select exactly one available SLOP affordance."""
        if self._assembler is None:
            from slop_assembler import SlopAssembler

            self._assembler = SlopAssembler()
        tool_set = self._assembler.tools_for_tree(tree)
        if not tool_set.tools:
            raise ValueError("tree exposes no SLOP affordances")

        payload = {
            "model": self._model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "Select exactly one available SLOP affordance. "
                        "Use the projected state ids and tool schemas."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{user_text}\n\n<slop-state>\n{self._assembler.render_text(tree)}\n</slop-state>",
                },
            ],
            "tools": tool_set.tools,
            "tool_choice": "required",
        }
        data = self._post_response(payload)
        tool_name, arguments = self._extract_tool_call(data)
        resolution = tool_set.resolve(tool_name)
        if resolution is None:
            raise ValueError(f"model selected unknown tool: {tool_name}")
        params = {key: str(value) for key, value in arguments.items()}
        return ActionInvocation(action=resolution.action, params=params)

    def _post_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._request_with_retries(request)

    async def _post_response_async(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Async-compatible wrapper for callers already running an event loop."""
        import asyncio

        return await asyncio.to_thread(self._post_response, payload)

    def _request_with_retries(self, request: urllib.request.Request) -> dict[str, Any]:
        delay = self._retry_delay
        for attempt in range(self._num_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if not _is_retryable_status(exc.code) or attempt >= self._num_retries:
                    raise
                retry_after = _retry_after_seconds(exc.headers.get("Retry-After"))
                sleep_for = retry_after if retry_after is not None else delay
            except urllib.error.URLError:
                if attempt >= self._num_retries:
                    raise
                sleep_for = delay
            time.sleep(min(sleep_for, self._max_retry_delay))
            delay = min(delay * 2, self._max_retry_delay)
        raise RuntimeError("unreachable retry state")

    def _extract_tool_call(self, data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        for item in data.get("output", []):
            if item.get("type") in {"function_call", "tool_call"}:
                return item["name"], _decode_arguments(item.get("arguments", {}))
            for content in item.get("content", []):
                if content.get("type") in {"function_call", "tool_call"}:
                    return content["name"], _decode_arguments(content.get("arguments", {}))
        for choice in data.get("choices", []):
            message = choice.get("message") or {}
            for tool_call in message.get("tool_calls") or []:
                function = tool_call.get("function") or {}
                if function.get("name"):
                    return function["name"], _decode_arguments(function.get("arguments", {}))
            function_call = message.get("function_call") or {}
            if function_call.get("name"):
                return (
                    function_call["name"],
                    _decode_arguments(function_call.get("arguments", {})),
                )
        raise ValueError("OpenAI response did not include a function call")


MockModel = DeterministicAdapter


def _decode_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        return json.loads(raw or "{}")
    return dict(raw or {})


def _is_retryable_status(status: int) -> bool:
    return status == 429 or 500 <= status <= 599


def _retry_after_seconds(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def _first_incomplete_todo(tree: Any) -> Any | None:
    nodes = [tree]
    while nodes:
        node = nodes.pop(0)
        props = getattr(node, "properties", None) or {}
        if node.type == "todo" and not bool(props.get("completed")):
            return node
        nodes.extend(getattr(node, "children", None) or [])
    return None
