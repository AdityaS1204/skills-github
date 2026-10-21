#!/usr/bin/env python3
"""Scan a project for leaked secrets and client-exposed server keys.

Usage: python scan_secrets.py <project_root>
Output: SEVERITY | check | file:line | detail   (values are always redacted)
"""
import base64, json, os, re, subprocess, sys

SKIP_DIRS = {"node_modules", ".git", ".next", "dist", "build", ".expo", ".turbo",
             "coverage", ".vercel", "venv", ".venv", "__pycache__", "Pods", ".gradle"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".woff", ".woff2",
            ".ttf", ".pdf", ".zip", ".lock", ".map", ".mp4", ".mp3"}
MAX_BYTES = 1_000_000

PATTERNS = [
    ("Stripe live secret key", re.compile(r"sk_live_[0-9a-zA-Z]{16,}"), "CRITICAL"),
    ("Stripe test secret key", re.compile(r"sk_test_[0-9a-zA-Z]{16,}"), "MEDIUM"),
    ("Stripe restricted key", re.compile(r"rk_live_[0-9a-zA-Z]{16,}"), "CRITICAL"),
    ("Stripe webhook secret", re.compile(r"whsec_[0-9a-zA-Z]{16,}"), "HIGH"),
    ("Anthropic API key", re.compile(r"sk-ant-[0-9a-zA-Z_\-]{20,}"), "CRITICAL"),
    ("OpenAI API key", re.compile(r"sk-(?:proj-)?[0-9a-zA-Z_\-]{32,}"), "CRITICAL"),
    ("AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}"), "CRITICAL"),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"), "CRITICAL"),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "LOW"),
    ("GitHub token", re.compile(r"gh[pousr]_[0-9a-zA-Z]{36,}"), "CRITICAL"),
    ("Slack token", re.compile(r"xox[baprs]-[0-9a-zA-Z\-]{10,}"), "HIGH"),
    ("Resend/SendGrid key", re.compile(r"(?:re_[0-9a-zA-Z]{20,}|SG\.[0-9a-zA-Z_\-]{20,}\.[0-9a-zA-Z_\-]{20,})"), "HIGH"),
]
JWT_RE = re.compile(r"eyJ[0-9A-Za-z_\-]{10,}\.eyJ[0-9A-Za-z_\-]{10,}\.[0-9A-Za-z_\-]{10,}")
PUBLIC_PREFIX_RE = re.compile(
    r"\b((?:NEXT_PUBLIC|VITE|EXPO_PUBLIC|REACT_APP|PUBLIC|NUXT_PUBLIC)_[A-Z0-9_]*"
    r"(?:SECRET|SERVICE_ROLE|PRIVATE|ADMIN|WEBHOOK|SK_|_SK\b)[A-Z0-9_]*)")
SERVICE_ROLE_USE_RE = re.compile(r"SUPABASE_SERVICE_ROLE|service_role", re.I)


def redact(s):
    return s if len(s) <= 8 else f"{s[:4]}...{s[-2:]} (len {len(s)})"


def jwt_role(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("role")
    except Exception:
        return None


def walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) <= MAX_BYTES:
                    yield p
            except OSError:
                pass


def is_client_file(path, text):
    if re.search(r"""['"]use client['"]""", text[:400]):
        return True
    parts = path.replace("\\", "/").split("/")
    return any(x in parts for x in ("components", "hooks")) and "api" not in parts


def main(root):
    findings = []

    def add(sev, check, path, line, detail):
        findings.append((sev, check, os.path.relpath(path, root), line, detail))

    for p in walk(root):
        base = os.path.basename(p)
        try:
            text = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        is_example = any(x in base for x in (".example", ".sample", ".template"))
        for i, line in enumerate(text.splitlines(), 1):
            for name, rx, sev in PATTERNS:
                m = rx.search(line)
                if m:
                    add("LOW" if is_example else sev, f"hardcoded-secret: {name}", p, i, redact(m.group(0)))
            for m in JWT_RE.finditer(line):
                if jwt_role(m.group(0)) == "service_role":
                    add("CRITICAL", "supabase-service-role-key", p, i,
                        "service_role JWT in source. Bypasses all RLS. " + redact(m.group(0)))
            m = PUBLIC_PREFIX_RE.search(line)
            if m:
                add("HIGH", "secret-in-public-env-var", p, i,
                    f"{m.group(1)} is bundled into client code by its prefix")
        if base.startswith(".env") and not is_example and re.search(r"^[A-Z0-9_]+=.+", text, re.M):
            add("INFO", "env-file-present", p, 1, "Check it is gitignored and not committed")
        if p.endswith((".ts", ".tsx", ".js", ".jsx")) and is_client_file(p, text):
            for i, line in enumerate(text.splitlines(), 1):
                if SERVICE_ROLE_USE_RE.search(line):
                    add("CRITICAL", "service-role-in-client-file", p, i,
                        "Service role referenced in a client component or hook")

    try:
        out = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True, timeout=20)
        if out.returncode == 0:
            for f in out.stdout.splitlines():
                b = os.path.basename(f)
                if b.startswith(".env") and not any(x in b for x in (".example", ".sample", ".template")):
                    add("CRITICAL", "env-file-committed", os.path.join(root, f), 1,
                        "Tracked by git. Rotate every key in it; deleting the file does not remove history")
    except Exception:
        pass
    gi = os.path.join(root, ".gitignore")
    if os.path.exists(gi):
        if not re.search(r"^\s*\.env", open(gi, errors="ignore").read(), re.M):
            add("HIGH", "gitignore-missing-env", gi, 1, ".gitignore does not ignore .env files")
    elif os.path.isdir(os.path.join(root, ".git")):
        add("HIGH", "no-gitignore", root, 0, "No .gitignore found")

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    for sev, check, path, line, detail in sorted(set(findings), key=lambda f: (order[f[0]], f[2], f[3])):
        print(f"{sev} | {check} | {path}:{line} | {detail}")
    if not findings:
        print("OK | scan_secrets | - | no findings")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("usage: scan_secrets.py <project_root>")
    main(os.path.abspath(sys.argv[1]))
