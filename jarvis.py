from __future__ import annotations

import json
import os
import platform
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


# ============================================================
# CONFIG
# ============================================================

@dataclass
class JarvisConfig:
    base_url: str = "http://127.0.0.1:8080"
    model: str = "local-qwen"
    temperature: float = 0.1
    max_tokens: int = 1024
    timeout: int = 120


# ============================================================
# TOOL IMPLEMENTATIONS
# ============================================================

def open_application(application: str) -> str:
    """
    Open a known Windows application.

    We intentionally keep this allowlisted rather than allowing
    the LLM to execute arbitrary shell commands.
    """

    allowed_apps: dict[str, str] = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
    }

    key = application.strip().lower()

    if key not in allowed_apps:
        return (
            f"I cannot open '{application}' yet. "
            f"Allowed applications: {', '.join(allowed_apps.keys())}"
        )

    executable = allowed_apps[key]

    try:
        subprocess.Popen(
            [executable],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return f"Successfully launched {application}."

    except Exception as exc:
        return f"Failed to launch {application}: {exc}"


def get_system_info() -> str:
    """Return basic local machine information."""

    info = {
        "OS": platform.platform(),
        "Computer": platform.node(),
        "CPU": platform.processor(),
        "Python": platform.python_version(),
    }

    return json.dumps(info, indent=2)


def list_folder(path: str) -> str:
    """List files/folders in a local directory."""

    if not path.strip():
        return "No folder path was provided."

    target = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(target):
        return f"Path does not exist: {target}"

    if not os.path.isdir(target):
        return f"Path is not a folder: {target}"

    try:
        entries = []

        for item in os.listdir(target):
            full = os.path.join(target, item)

            entries.append(
                {
                    "name": item,
                    "type": "folder" if os.path.isdir(full) else "file",
                }
            )

        return json.dumps(entries, indent=2)

    except PermissionError:
        return f"Permission denied: {target}"

    except Exception as exc:
        return f"Failed to list folder: {exc}"


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOL_FUNCTIONS: dict[str, Callable[..., str]] = {
    "open_application": open_application,
    "get_system_info": get_system_info,
    "list_folder": list_folder,
}


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": (
                "Open an allowed application on the local Windows computer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": (
                            "Application name. Examples: "
                            "notepad, calculator, paint, explorer."
                        ),
                    }
                },
                "required": ["application"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": (
                "Get basic information about the local computer."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_folder",
            "description": (
                "List files and folders inside a local directory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Local Windows folder path, "
                            "for example C:\\Users\\User\\Downloads"
                        ),
                    }
                },
                "required": ["path"],
            },
        },
    },
]


# ============================================================
# LOCAL LLM CLIENT
# ============================================================

class LLMClient:
    def __init__(self, config: JarvisConfig):
        self.config = config

    def health_check(self) -> bool:
        url = f"{self.config.base_url}/health"

        try:
            request = urllib.request.Request(
                url,
                method="GET",
            )

            with urllib.request.urlopen(
                request,
                timeout=5,
            ) as response:
                return response.status == 200

        except Exception:
            return False

    def chat(
        self,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:

        url = f"{self.config.base_url}/v1/chat/completions"

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
            "tools": TOOLS,
            "tool_choice": "auto",
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout,
            ) as response:

                raw = response.read().decode("utf-8")
                return json.loads(raw)

        except urllib.error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"llama-server HTTP {exc.code}: {body}"
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not connect to llama-server: {exc}"
            ) from exc


# ============================================================
# JARVIS
# ============================================================

class Jarvis:

    def __init__(self):
        self.config = JarvisConfig()
        self.llm = LLMClient(self.config)

        self.system_prompt = """
You are JARVIS, a local-first AI engineering assistant.

You assist the user with technical and computer-related work.

Important rules:

1. Use tools when the user's request requires a real computer action
   or local information.

2. Never claim that an action was performed unless the corresponding
   tool actually executed successfully.

3. Prefer safe, deterministic tools over arbitrary shell commands.

4. The user remains the final decision maker for important actions.

5. Be concise for simple tasks and thoughtful for complex tasks.

6. You currently have access only to the tools explicitly provided.

7. Do not invent capabilities that are not available.

8. Treat the user's computer as local/private.
""".strip()

        self.messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

    # --------------------------------------------------------
    # TOOL EXECUTION
    # --------------------------------------------------------

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:

        function = TOOL_FUNCTIONS.get(tool_name)

        if function is None:
            return f"Unknown tool: {tool_name}"

        try:
            return function(**arguments)

        except TypeError as exc:
            return (
                f"Invalid arguments for {tool_name}: {exc}"
            )

        except Exception as exc:
            return (
                f"Tool {tool_name} failed: {exc}"
            )

    # --------------------------------------------------------
    # ASK JARVIS
    # --------------------------------------------------------

    def ask(self, user_input: str) -> str:

        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        # First LLM call:
        # decide whether a tool is required.
        response = self.llm.chat(self.messages)

        try:
            assistant_message = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected LLM response: {response}"
            ) from exc

        tool_calls = assistant_message.get("tool_calls", [])

        # ----------------------------------------------------
        # No tool required
        # ----------------------------------------------------

        if not tool_calls:

            content = assistant_message.get("content", "").strip()

            self.messages.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )

            return content

        # ----------------------------------------------------
        # Tool call(s)
        # ----------------------------------------------------

        self.messages.append(assistant_message)

        for tool_call in tool_calls:

            function_data = tool_call["function"]

            tool_name = function_data["name"]

            raw_arguments = function_data.get(
                "arguments",
                "{}",
            )

            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = {}

            print(
                f"\n[Tool] {tool_name}"
                f"\n[Arguments] {arguments}"
            )

            result = self.execute_tool(
                tool_name,
                arguments,
            )

            print(f"[Result] {result}")

            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": result,
                }
            )

        # ----------------------------------------------------
        # Second LLM call:
        # explain the tool result naturally.
        # ----------------------------------------------------

        final_response = self.llm.chat(self.messages)

        try:
            final_message = final_response[
                "choices"
            ][0]["message"]

            content = (
                final_message.get(
                    "content",
                    "",
                ).strip()
            )

        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected final response: {final_response}"
            ) from exc

        self.messages.append(
            {
                "role": "assistant",
                "content": content,
            }
        )

        return content

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    def start(self):

        print("=" * 65)
        print("JARVIS - Tool Engine v0.1")
        print("=" * 65)

        print("Checking llama-server...")

        if not self.llm.health_check():
            print("\nERROR: llama-server is not reachable.")
            print("Make sure your llama-server is running on port 8080.")
            return

        print("llama-server : OK")
        print("Qwen         : CONNECTED")
        print("Tool Engine  : READY")
        print()
        print("Available tools:")
        print("  - open_application")
        print("  - get_system_info")
        print("  - list_folder")
        print()
        print("Type 'exit' to quit.")
        print("-" * 65)

        while True:

            try:
                user_input = input("\nYou: ").strip()

            except (KeyboardInterrupt, EOFError):
                print("\nJARVIS: Shutting down.")
                break

            if not user_input:
                continue

            if user_input.lower() in {
                "exit",
                "quit",
            }:
                print("JARVIS: Goodbye.")
                break

            try:

                answer = self.ask(user_input)

                print(
                    f"\nJARVIS: {answer}"
                )

            except Exception as exc:

                print(
                    f"\nJARVIS ERROR: {exc}"
                )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    Jarvis().start()
