"""
Toggle Qwen Code AI provider between Ollama (local) and Cloud.

Usage:
    python tools/toggle_model.py ollama    # Switch to local Ollama
    python tools/toggle_model.py cloud     # Switch to cloud provider
    python tools/toggle_model.py           # Show current provider
"""

import json
import sys
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent.parent / ".qwen" / "settings.json"

PROVIDERS = {
    "ollama": {
        "provider": "ollama",
        "model": "qwen3-vl",
        "baseUrl": "http://localhost:11434",
    },
    "cloud": None,  # Remove model section to use default cloud
}


def load_settings():
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print(f"✓ Updated {SETTINGS_PATH}")


def get_current_provider(settings):
    model_config = settings.get("model")
    if model_config is None:
        return "cloud"
    return model_config.get("provider", "cloud")


def switch_to(provider):
    settings = load_settings()
    current = get_current_provider(settings)

    if current == provider:
        print(f"Already using {provider.upper()} provider")
        return

    if provider == "cloud":
        # Remove model section to use cloud default
        settings.pop("model", None)
        print("Switching to: CLOUD provider")
    elif provider == "ollama":
        settings["model"] = PROVIDERS["ollama"]
        print("Switching to: OLLAMA provider (qwen3-vl)")
    else:
        print(f"✗ Unknown provider: {provider}")
        print("Use: ollama or cloud")
        sys.exit(1)

    save_settings(settings)
    print("\n⚠ Restart Qwen Code for changes to take effect")


def show_status():
    settings = load_settings()
    current = get_current_provider(settings)

    if current == "ollama":
        model_config = settings.get("model", {})
        model_name = model_config.get("model", "unknown")
        print(f"Current: OLLAMA ({model_name})")
        print(f"  URL: {model_config.get('baseUrl')}")
    else:
        print("Current: CLOUD (default)")

    print("\nSwitch with:")
    print("  python tools/toggle_model.py ollama")
    print("  python tools/toggle_model.py cloud")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_status()
    else:
        switch_to(sys.argv[1].lower())
