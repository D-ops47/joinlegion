"""Flip joinlegion.ai/app over to the live app subdomain.

Run this ONCE app.joinlegion.ai is resolving and serving the Lovable app.
It edits netlify.toml in place:

  - uncomments the APP GATE redirect block (/app and /app/* -> the subdomain)
  - removes the placeholder /app/* -> /app.html rule, which would otherwise
    shadow the new deep-link rule because Netlify applies the FIRST match

Verify first, then deploy:
    python3 enable_app_subdomain.py --check     # is the subdomain ready?
    python3 enable_app_subdomain.py             # make the edit
"""
import re
import shutil
import subprocess
import sys

TOML = "/home/ubuntu/joinlegion/netlify.toml"
TARGET = "https://app.joinlegion.ai"

LIVE_BLOCK = f"""[[redirects]]
  from = "/app"
  to = "{TARGET}"
  status = 302
  force = true

[[redirects]]
  from = "/app/*"
  to = "{TARGET}/:splat"
  status = 302
  force = true
"""


def check():
    """Confirm the subdomain resolves AND serves the app before switching."""
    print(f"checking {TARGET} ...")
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w",
         "%{http_code} %{redirect_url} %{ssl_verify_result}", "-L", "--max-time", "20",
         TARGET],
        capture_output=True, text=True)
    print("  response:", r.stdout or "(no response)")
    code = (r.stdout.split() or ["000"])[0]
    if code.startswith("2"):
        print("  OK: subdomain is serving content over HTTPS.")
        return True
    print("  NOT READY: DNS may still be propagating, or Lovable has not"
          " finished issuing the certificate.")
    return False


def enable():
    src = open(TOML).read()

    # Already switched? Detect by the live target being present in an ACTIVE
    # (uncommented) rule, not just anywhere in the file — the target also
    # appears inside the explanatory comments.
    active = "\n".join(l for l in src.splitlines()
                       if not l.lstrip().startswith("#"))
    if TARGET in active:
        print("already enabled; nothing to do")
        return

    shutil.copy(TOML, TOML + ".bak")

    # 1. Replace the commented-out block with the live one.
    commented = re.search(
        r"# \[\[redirects\]\]\n#   from = \"/app\"\n.*?#   force = true\n",
        src, re.S)
    if not commented:
        print("ERROR: could not find the commented APP GATE block")
        sys.exit(1)
    src = src[:commented.start()] + LIVE_BLOCK + src[commented.end():]

    # 2. Drop the placeholder deep-link rule. It points /app/* at /app.html and
    #    sits LOWER in the file, but leaving it is still wrong: it documents
    #    behaviour that no longer applies and would take over again if the live
    #    block were ever removed.
    # Matches the rule whatever order its keys are in, and tolerates the
    # comment block that documents it.
    placeholder = re.search(
        r'\[\[redirects\]\]\n(?:\s+\w+\s*=\s*[^\n]+\n)*?'
        r'\s+to\s*=\s*"/app\.html"\n(?:\s+\w+\s*=\s*[^\n]+\n)*',
        src)
    if placeholder and '"/app/*"' in placeholder.group(0):
        src = src[:placeholder.start()] + src[placeholder.end():]
    else:
        print("WARNING: placeholder /app/* -> /app.html rule not removed;"
              " check it is not shadowing the live rule")

    open(TOML, "w").write(src)
    print("netlify.toml updated (backup at netlify.toml.bak)")

    # Sanity check: the file must still parse.
    try:
        import tomllib
        with open(TOML, "rb") as f:
            cfg = tomllib.load(f)
        app_rules = [r for r in cfg.get("redirects", [])
                     if r.get("from", "").startswith("/app")]
        print("\nactive /app rules now:")
        for r in app_rules:
            print(f"  {r['from']:12} -> {r['to']:45} "
                  f"{r.get('status')} force={r.get('force')}")
    except Exception as e:
        print("TOML PARSE FAILED, restoring backup:", e)
        shutil.copy(TOML + ".bak", TOML)
        sys.exit(1)


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    enable()
