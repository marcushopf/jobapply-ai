#!/usr/bin/env python3
"""
LLM client — wraps LiteLLM with a single chat() interface.

Key lookup order:
  1. Environment variable / .env  — CI, power users
  2. OS keychain                  — returning users (silent)
  3. First-run prompt             — saves to keychain, never asked again

Provider selection:
  - Default (production): Google Gemini  (GOOGLE_API_KEY)
  - Testing override:     Ollama         (local, no key needed — set LLM_MODEL=ollama/auto or a specific model)
  - Rate-limit fallback:  Ollama         (automatic when Gemini hits 15 RPM; requires Ollama running)

Ollama model auto-selection:
  Set LLM_MODEL=ollama/auto to let the app detect your RAM and pick the best installed model.
  RAM tiers: ≥32GB → qwen2.5:14b, ≥16GB → qwen2.5:7b, ≥8GB → llama3.1:8b, else → llama3.2:3b
"""

import getpass
import json
import os
import subprocess
import sys
import time
import urllib.request

import litellm

litellm.suppress_debug_info = True

_KEYCHAIN_SERVICE = "jobapply-ai"
_GEMINI_MODEL = "gemini/gemini-2.0-flash"
_OLLAMA_DEFAULT_URL = "http://localhost:11434"

# Preferred models per RAM tier — ordered best-to-fallback within each tier.
# qwen2.5 is prioritised for its superior structured-output / instruction following.
_OLLAMA_TIERS = [
    (32, ["qwen2.5:14b", "llama3.3:70b", "qwen2.5:7b", "llama3.1:8b"]),
    (16, ["qwen2.5:7b", "mistral:7b", "llama3.1:8b", "llama3.2:3b"]),
    (8,  ["llama3.1:8b", "qwen2.5:3b", "llama3.2:3b"]),
    (0,  ["llama3.2:3b", "llama3.2:1b"]),
]


def _ram_gb() -> float:
    """Return total system RAM in GB."""
    try:
        raw = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=2).strip()
        return int(raw) / (1024 ** 3)
    except Exception:
        return 8.0  # conservative fallback


def _ollama_installed_models(base_url: str) -> set[str]:
    """Return the set of model names installed in Ollama (e.g. {'llama3.1:8b', 'qwen2.5:7b'})."""
    try:
        resp = urllib.request.urlopen(f"{base_url}/api/tags", timeout=2)
        data = json.loads(resp.read())
        return {m["name"] for m in data.get("models", [])}
    except Exception:
        return set()


def _auto_select_ollama_model(base_url: str) -> str:
    """Pick the best installed Ollama model based on available RAM."""
    ram = _ram_gb()
    installed = _ollama_installed_models(base_url)
    installed_short = {name.split(":")[0] for name in installed}

    for min_ram, candidates in _OLLAMA_TIERS:
        if ram >= min_ram:
            for model in candidates:
                short = model.split(":")[0]
                if model in installed or short in installed_short:
                    return f"ollama/{model}"
            break  # right tier found but none installed — fall through to default

    # Nothing matched — return the smallest candidate as a hint
    return "ollama/llama3.2:3b"


def _resolve_ollama_model(raw_model: str, base_url: str) -> str:
    """Resolve 'ollama/auto' to a concrete model name; pass through everything else."""
    if raw_model == "ollama/auto":
        chosen = _auto_select_ollama_model(base_url)
        print(f"  Ollama auto-select: {_ram_gb():.0f}GB RAM detected → using {chosen}", flush=True)
        return chosen
    return raw_model


def _ollama_available(base_url: str) -> bool:
    """Return True if the Ollama server is reachable."""
    try:
        urllib.request.urlopen(f"{base_url}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def _resolve_key(env_var: str, keychain_account: str, label: str, help_url: str,
                 required: bool = True) -> str:
    """Three-step key lookup: env var → OS keychain → first-run prompt."""

    # 1. Env var / .env
    val = os.getenv(env_var, "").strip()
    if val:
        return val

    # 2. OS keychain
    try:
        import keyring
        val = (keyring.get_password(_KEYCHAIN_SERVICE, keychain_account) or "").strip()
        if val:
            return val
    except Exception:
        pass

    if not required:
        return ""

    # 3. First-run prompt
    print(f"\n  No {label} found.")
    print(f"  Get your free key at: {help_url}\n")
    val = getpass.getpass(f"  Paste your {env_var}: ").strip()
    if not val:
        sys.exit("No key provided — exiting.")

    try:
        import keyring
        keyring.set_password(_KEYCHAIN_SERVICE, keychain_account, val)
        print(f"  Key saved to your system keychain. You won't be asked again.\n")
    except Exception:
        print(f"  Keychain unavailable — key used for this session only.")
        print(f"  To persist it, add {env_var}=<key> to a .env file.\n")

    return val


def _setup_provider(model: str) -> str:
    """Resolve API keys based on the chosen model and wire up env vars."""
    if model.startswith("ollama/"):
        return "ollama"

    # Default: Gemini
    key = _resolve_key(
        env_var="GOOGLE_API_KEY",
        keychain_account="google_api_key",
        label="Google API key",
        help_url="https://aistudio.google.com/apikey",
    )
    os.environ["GOOGLE_API_KEY"] = key
    return "google"


class LLMClient:
    def __init__(self):
        # Treat empty/whitespace env values as unset so `LLM_MODEL=` in .env
        # falls through to the default instead of becoming model="".
        ollama_url = os.getenv("OLLAMA_BASE_URL", "").strip() or _OLLAMA_DEFAULT_URL
        raw_model = os.getenv("LLM_MODEL", "").strip() or _GEMINI_MODEL

        # Resolve ollama/auto → best installed model for this machine
        self.model = _resolve_ollama_model(raw_model, ollama_url)
        self.provider = _setup_provider(self.model)

        # Automatic Ollama fallback when primary provider hits rate limits.
        # Only wired up when primary is not already Ollama.
        self._ollama_api_base = ollama_url
        if not self.model.startswith("ollama/"):
            raw_fallback = os.getenv("LLM_FALLBACK_MODEL", "").strip() or "ollama/auto"
            fallback = _resolve_ollama_model(raw_fallback, ollama_url)
            self._fallback_model = fallback if _ollama_available(ollama_url) else None
        else:
            self._fallback_model = None

    def chat(self, prompt: str, max_tokens: int = 1024, retries: int = 3) -> str:
        for attempt in range(retries):
            try:
                kwargs = dict(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                )
                if self.model.startswith("ollama/"):
                    kwargs["api_base"] = self._ollama_api_base
                response = litellm.completion(**kwargs)
                return response.choices[0].message.content
            except Exception as e:
                if "429" in str(e) and attempt < retries - 1:
                    if self._fallback_model:
                        try:
                            print(f"\n  Rate limited — falling back to {self._fallback_model}...",
                                  flush=True)
                            resp = litellm.completion(
                                model=self._fallback_model,
                                messages=[{"role": "user", "content": prompt}],
                                max_tokens=max_tokens,
                                api_base=self._ollama_api_base,
                            )
                            return resp.choices[0].message.content
                        except Exception:
                            self._fallback_model = None  # Ollama failed — disable for this session
                    wait = 65
                    print(f"\n  Rate limited — waiting {wait}s before retry "
                          f"{attempt + 2}/{retries}...", flush=True)
                    time.sleep(wait)
                else:
                    raise
