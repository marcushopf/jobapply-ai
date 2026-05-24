#!/usr/bin/env python3
"""
LLM client — wraps LiteLLM with a single chat() interface.

Key lookup order (for GOOGLE_API_KEY):
  1. Environment variable / .env  — CI, power users
  2. OS keychain                  — returning users (silent)
  3. First-run prompt             — saves to keychain, never asked again

Override model: set LLM_MODEL in .env
"""

import getpass
import os
import sys

import litellm

litellm.suppress_debug_info = True

_KEYCHAIN_SERVICE = "jobapply-ai"
_GEMINI_MODEL = "gemini/gemini-2.0-flash"


def _resolve_key(env_var: str, keychain_account: str, label: str, help_url: str) -> str:
    """Three-step key lookup: env var → OS keychain → first-run prompt."""

    # 1. Env var / .env (CI, overrides)
    val = os.getenv(env_var, "").strip()
    if val:
        return val

    # 2. OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
    try:
        import keyring
        val = (keyring.get_password(_KEYCHAIN_SERVICE, keychain_account) or "").strip()
        if val:
            return val
    except Exception:
        pass

    # 3. First-run prompt — save to keychain so this never runs again
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


class LLMClient:
    def __init__(self):
        key = _resolve_key(
            env_var="GOOGLE_API_KEY",
            keychain_account="google_api_key",
            label="Google API key",
            help_url="https://aistudio.google.com/apikey",
        )
        os.environ["GOOGLE_API_KEY"] = key  # make sure litellm picks it up
        self.model = os.getenv("LLM_MODEL", _GEMINI_MODEL)
        self.provider = "google"

    def chat(self, prompt: str, max_tokens: int = 1024) -> str:
        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
