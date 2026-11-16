"""
setup_webhook_tunnel.py — Start a smee.io tunnel to receive GitHub webhooks locally.

What this does:
  1. Checks if smee-client is installed (npm install -g smee-client)
  2. Creates a smee.io channel if SMEE_URL is not in .env
  3. Starts the tunnel: GitHub → smee.io → localhost:8000/webhooks/github
  4. Prints the smee URL to paste into your GitHub webhook settings

Usage:
  python setup_webhook_tunnel.py

Then in GitHub (repo Settings → Webhooks → Add webhook):
  Payload URL:  <the smee.io URL printed below>
  Content type: application/json
  Secret:       <same as GITHUB_WEBHOOK_SECRET in .env>
  Events:       Pull requests  ✓
"""
import os
import subprocess
import sys
import webbrowser

BACKEND_PORT = 8000
TARGET_PATH = "/webhooks/github"
TARGET_URL = f"http://localhost:{BACKEND_PORT}{TARGET_PATH}"

# On Windows npm global CLIs are .cmd files
SMEE_CMD = "smee.cmd" if sys.platform == "win32" else "smee"

# ── Check smee-client is installed ───────────────────────────────────────────
def check_smee():
    result = subprocess.run([SMEE_CMD, "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌  smee-client not found.")
        print("    Install it with:  npm install -g smee-client")
        sys.exit(1)
    print(f"✅  smee-client found.")

# ── Read SMEE_URL from .env if set ───────────────────────────────────────────
def get_smee_url() -> str:
    env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("SMEE_URL="):
                url = line.split("=", 1)[1].strip()
                if url and url != "PASTE_SMEE_URL_HERE":
                    return url

    # No URL set — open smee.io so user can create a channel
    print("\n📋  No SMEE_URL found in backend/.env")
    print("    Opening https://smee.io/new in your browser...")
    print("    Copy the URL it gives you, then paste it here:\n")
    webbrowser.open("https://smee.io/new")
    url = input("    Smee URL: ").strip()
    if not url.startswith("https://smee.io/"):
        print("❌  Invalid URL. Must start with https://smee.io/")
        sys.exit(1)

    # Save to .env
    with open(env_path, "a") as f:
        f.write(f"\nSMEE_URL={url}\n")
    print(f"    Saved SMEE_URL to backend/.env")
    return url

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    check_smee()
    smee_url = get_smee_url()

    print(f"\n{'='*60}")
    print(f"  🚀  CodeSheriff Webhook Tunnel")
    print(f"{'='*60}")
    print(f"  Smee URL  : {smee_url}")
    print(f"  Target    : {TARGET_URL}")
    print(f"\n  Paste this into GitHub webhook settings:")
    print(f"  → Payload URL: {smee_url}")
    print(f"\n  Press Ctrl+C to stop the tunnel.")
    print(f"{'='*60}\n")

    subprocess.run([
        SMEE_CMD,
        "--url", smee_url,
        "--target", TARGET_URL,
    ])

if __name__ == "__main__":
    main()
