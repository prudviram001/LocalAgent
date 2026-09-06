from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class JarvisConfig:
    base_url: str = "http://127.0.0.1:8080"
    model: str = "local-qwen"
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout: int = 120


class LLMClient:
    """Minimal client for a local llama-server OpenAI-compatible API."""

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

        except (urllib.error.URLError, TimeoutError):
            return False

    def chat(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.config.base_url}/v1/chat/completions"

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
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
                result = json.loads(raw)

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"llama-server returned HTTP {exc.code}: {body}"
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not connect to llama-server: {exc}"
            ) from exc

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "llama-server returned invalid JSON."
            ) from exc

        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected llama-server response: {result}"
            ) from exc


class Jarvis:
    def __init__(self):
        self.config = JarvisConfig()
        self.llm = LLMClient(self.config)

        self.system_prompt = """
You are JARVIS, a local-first AI engineering assistant.

Your primary purpose is to assist the user with professional,
technical, and computer-related work.

Core principles:
1. Be concise when the task is simple.
2. Think carefully before answering complex questions.
3. Never pretend that you performed an action unless a tool actually
   performed and verified that action.
4. Clearly distinguish between facts, assumptions, and suggestions.
5. Learn useful information from the current conversation, but do not
   claim permanent memory yet.
6. The system is local-first. Do not assume internet access.
7. The user remains the final decision maker for important actions.

At this stage you do NOT have access to the user's files,
applications, browser, microphone, or computer controls.
Do not claim that you can control them yet.
""".strip()

        self.messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

    def start(self) -> None:
        print("=" * 60)
        print("JARVIS - Local Core")
        print("=" * 60)

        print("Checking llama-server...")

        if not self.llm.health_check():
            print()
            print("ERROR: llama-server is not reachable.")
            print("Make sure this is running first:")
            print()
            print(
                r'.\llama-server.exe -m '
                r'"D:\Test\LocalAgent\models\Qwen3-4B-Instruct-2507-Q4_K_M.gguf" '
                r'-c 4096 --port 8080 -t 8'
            )
            print()
            sys.exit(1)

        print("llama-server: OK")
        print("Qwen: connected")
        print()
        print("Type 'exit' to quit.")
        print("-" * 60)

        while True:
            try:
                user_input = input("\nYou: ").strip()

            except (KeyboardInterrupt, EOFError):
                print("\nJARVIS: Shutting down.")
                break

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                print("JARVIS: Goodbye.")
                break

            self.messages.append(
                {
                    "role": "user",
                    "content": user_input,
                }
            )

            try:
                answer = self.llm.chat(self.messages)

            except RuntimeError as exc:
                print(f"\nJARVIS ERROR: {exc}")

                # Remove the failed user message so the conversation
                # remains consistent for the next request.
                self.messages.pop()
                continue

            self.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            print(f"\nJARVIS: {answer}")


if __name__ == "__main__":
    Jarvis().start()
