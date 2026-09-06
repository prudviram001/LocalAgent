"""
JARVIS - Phase 3: Memory + Thinking Indicator
A local AI agent that USES TOOLS and REMEMBERS across restarts.
Talks to your llama-server (llama.cpp / LM Studio) - 100% offline.

New in Phase 3:
  * Persistent memory saved to memory.json (survives restarts = "learning")
  * remember / recall tools
  * A "Jarvis is thinking..." spinner so it never looks frozen
"""

import requests
import json
import datetime
import os
import sys
import threading
import time
import itertools

# ---------------------------------------------------------------------------
# CONFIG - points to YOUR local server.
# If you use LM Studio, change 8080 to 1234.
# ---------------------------------------------------------------------------
SERVER_URL = "http://localhost:8080/v1/chat/completions"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Safe folder Jarvis may read/write in (safety boundary)
WORKSPACE = os.path.join(BASE_DIR, "workspace")
os.makedirs(WORKSPACE, exist_ok=True)

# Persistent memory file (this is what makes Jarvis "learn")
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")


# ---------------------------------------------------------------------------
# MEMORY - load & save long-term facts
# ---------------------------------------------------------------------------
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"facts": []}
    return {"facts": []}


def save_memory(mem):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2, ensure_ascii=False)


MEMORY = load_memory()


# ---------------------------------------------------------------------------
# TOOLS
# ---------------------------------------------------------------------------
def get_current_time(_=None):
    return datetime.datetime.now().strftime("%A, %d %B %Y, %I:%M %p")


def calculate(expression):
    try:
        allowed = "0123456789+-*/(). "
        if not all(c in allowed for c in expression):
            return "Error: only numbers and + - * / ( ) are allowed."
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


def list_files(_=None):
    files = os.listdir(WORKSPACE)
    return "Files in workspace: " + (", ".join(files) if files else "(empty)")


def write_file(args):
    try:
        filename, content = args.split("||", 1)
        filename = os.path.basename(filename.strip())
        path = os.path.join(WORKSPACE, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Saved '{filename}' ({len(content)} characters)."
    except Exception as e:
        return f"Error: {e} (use format: filename||content)"


def read_file(filename):
    try:
        filename = os.path.basename(filename.strip())
        path = os.path.join(WORKSPACE, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"


def remember(fact):
    """Save a fact to long-term memory (survives restarts)."""
    fact = fact.strip()
    if not fact:
        return "Nothing to remember."
    if fact in MEMORY["facts"]:
        return "I already remember that."
    MEMORY["facts"].append(fact)
    save_memory(MEMORY)
    return f"Remembered: {fact}"


def recall(_=None):
    """Return everything Jarvis remembers."""
    if not MEMORY["facts"]:
        return "I don't have any saved memories yet."
    return "Here is what I remember:\n- " + "\n- ".join(MEMORY["facts"])


def forget(fact):
    """Remove a remembered fact (matches by contained text)."""
    fact = fact.strip().lower()
    before = len(MEMORY["facts"])
    MEMORY["facts"] = [f for f in MEMORY["facts"] if fact not in f.lower()]
    save_memory(MEMORY)
    removed = before - len(MEMORY["facts"])
    return f"Forgot {removed} item(s)." if removed else "Nothing matched."


TOOLS = {
    "get_current_time": get_current_time,
    "calculate": calculate,
    "list_files": list_files,
    "write_file": write_file,
    "read_file": read_file,
    "remember": remember,
    "recall": recall,
    "forget": forget,
}

TOOLS_DESCRIPTION = """
You have access to these tools. To use one, reply ONLY with a JSON object:
{"tool": "<tool_name>", "input": "<input string>"}

Available tools:
- get_current_time : input="" -> current date and time
- calculate : input="23*47+10" -> result of a math expression
- list_files : input="" -> lists files in the workspace
- write_file : input="notes.txt||Hello world" -> saves text to a file (use || between name and content)
- read_file : input="notes.txt" -> reads a file's content
- remember : input="The user's name is Prudvi" -> saves a fact to long-term memory
- recall : input="" -> lists everything you remember about the user
- forget : input="name" -> removes remembered facts matching that text

RULES:
- When the user tells you something personal or important about themselves
  (their name, preferences, projects, goals), use the 'remember' tool to save it.
- If you do NOT need a tool, reply normally in plain text.
- After a tool result comes back, give the user a natural final answer.
"""


def build_system_prompt():
    known = ""
    if MEMORY["facts"]:
        known = "\n\nThings you already remember about the user:\n- " + \
                "\n- ".join(MEMORY["facts"])
    return (
        "You are Jarvis, a helpful local AI assistant running on the user's "
        "computer. You are polite, concise, and address the user respectfully. "
        "You can use tools and you remember important things about the user.\n"
        + TOOLS_DESCRIPTION + known
    )


# ---------------------------------------------------------------------------
# THINKING INDICATOR (spinner in a background thread)
# ---------------------------------------------------------------------------
class Thinking:
    def __init__(self, label="Jarvis is thinking"):
        self.label = label
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin)
        self._thread.start()
        return self

    def _spin(self):
        for ch in itertools.cycle("|/-\\"):
            if self._stop.is_set():
                break
            sys.stdout.write(f"\r  {self.label}... {ch}")
            sys.stdout.flush()
            time.sleep(0.1)
        # clear the line
        sys.stdout.write("\r" + " " * (len(self.label) + 15) + "\r")
        sys.stdout.flush()

    def __exit__(self, *a):
        self._stop.set()
        self._thread.join()


# ---------------------------------------------------------------------------
# TALK TO THE LOCAL MODEL
# ---------------------------------------------------------------------------
def ask_model(messages):
    payload = {"messages": messages, "temperature": 0.7, "max_tokens": 512}
    with Thinking():
        r = requests.post(SERVER_URL, json=payload, timeout=180)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


def try_parse_tool(text):
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        obj = json.loads(text[start:end + 1])
        if "tool" in obj and obj["tool"] in TOOLS:
            return obj["tool"], obj.get("input", "")
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# AGENT LOOP
# ---------------------------------------------------------------------------
def main():
    print("=" * 55)
    print("  JARVIS is online.  (type 'quit' to exit)")
    if MEMORY["facts"]:
        print(f"  Memory loaded: I remember {len(MEMORY['facts'])} thing(s) about you.")
    print("=" * 55)

    messages = [{"role": "system", "content": build_system_prompt()}]

    while True:
        try:
            user = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nJarvis: Goodbye!")
            break

        if user.lower() in ("quit", "exit", "bye"):
            print("Jarvis: Goodbye, sir.")
            break
        if not user:
            continue

        messages.append({"role": "user", "content": user})

        for _ in range(5):
            reply = ask_model(messages)
            tool_call = try_parse_tool(reply)

            if tool_call:
                name, tool_input = tool_call
                print(f"  [Jarvis uses tool: {name}({tool_input!r})]")
                result = TOOLS[name](tool_input)
                print(f"  [Tool result: {str(result)[:150]}]")
                messages.append({"role": "assistant", "content": reply})
                messages.append({
                    "role": "user",
                    "content": f"Tool '{name}' returned: {result}\n"
                               f"Now give the user a natural final answer.",
                })
                continue
            else:
                print(f"Jarvis: {reply}")
                messages.append({"role": "assistant", "content": reply})
                break


if __name__ == "__main__":
    main()
