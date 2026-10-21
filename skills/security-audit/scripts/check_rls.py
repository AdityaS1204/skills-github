#!/usr/bin/env python3
"""Check Supabase/Postgres SQL migrations for row level security gaps.

Usage: python check_rls.py <project_root>
Reads *.sql under supabase/ (or the whole project if none). It can only see what
is in the repo, so the live database must still be verified in the dashboard.
Output: SEVERITY | check | file:line | detail
"""
import os, re, sys

SKIP_DIRS = {"node_modules", ".git", ".next", "dist", "build"}

def sql_files(root):
    base = os.path.join(root, "supabase")
    start = base if os.path.isdir(base) else root
    for dp, dns, fns in os.walk(start):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in sorted(fns):
            if fn.endswith(".sql"):
                yield os.path.join(dp, fn)

def strip_comments(sql):
    sql = re.sub(r"--[^\n]*", lambda m: " " * len(m.group(0)), sql)
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), sql, flags=re.S)

def line_of(text, idx):
    return text.count("\n", 0, idx) + 1

NAME = r'((?:"?[\w]+"?\.)?"?[\w]+"?)'
def norm(n):
    n = n.replace('"', "").lower()
    return n if "." in n else "public." + n

def main(root):
    files = list(sql_files(root))
    if not files:
        print("INFO | check_rls | - | no .sql files found. Verify RLS in the Supabase dashboard (Table Editor > RLS)")
        return
    tables, rls_on, policies, findings = {}, set(), [], []
    for f in files:
        raw = open(f, encoding="utf-8", errors="ignore").read()
        t = strip_comments(raw)
        rel = os.path.relpath(f, root)
        for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?" + NAME, t, re.I):
            tables.setdefault(norm(m.group(1)), (rel, line_of(t, m.start())))
        for m in re.finditer(r"alter\s+table\s+(?:only\s+)?(?:if\s+exists\s+)?" + NAME +
                             r"\s+enable\s+row\s+level\s+security", t, re.I):
            rls_on.add(norm(m.group(1)))
        for m in re.finditer(r"alter\s+table\s+(?:only\s+)?(?:if\s+exists\s+)?" + NAME +
                             r"\s+disable\s+row\s+level\s+security", t, re.I):
            rls_on.discard(norm(m.group(1)))
            findings.append(("HIGH", "rls-disabled", rel, line_of(t, m.start()), f"RLS explicitly disabled on {norm(m.group(1))}"))
        for m in re.finditer(r"create\s+policy\s+(\"[^\"]+\"|\w+)\s+on\s+" + NAME + r"(.*?);", t, re.I | re.S):
            body = m.group(3)
            policies.append((norm(m.group(2)), rel, line_of(t, m.start()), m.group(1), body))
        for m in re.finditer(r"create\s+(?:or\s+replace\s+)?view\s+" + NAME + r"(.*?);", t, re.I | re.S):
            if not re.search(r"security_invoker\s*=\s*(true|on)", m.group(2), re.I):
                findings.append(("MEDIUM", "view-without-security-invoker", rel, line_of(t, m.start()),
                                 f"View {norm(m.group(1))} runs with creator rights and can bypass RLS (Postgres 15+: use security_invoker = true)"))
        for m in re.finditer(r"create\s+(?:or\s+replace\s+)?function\s+" + NAME + r"(.*?)\$\$.*?\$\$(.*?);", t, re.I | re.S):
            full = m.group(0)
            if re.search(r"security\s+definer", full, re.I) and not re.search(r"set\s+search_path", full, re.I):
                findings.append(("HIGH", "security-definer-no-search-path", rel, line_of(t, m.start()),
                                 f"{norm(m.group(1))} is SECURITY DEFINER without SET search_path"))

    skip_tables = re.compile(r"^(public\.)?(schema_migrations|_prisma_migrations)$")
    pol_by_table = {}
    for tbl, rel, ln, name, body in policies:
        pol_by_table.setdefault(tbl, []).append(name)
        if re.search(r"using\s*\(\s*true\s*\)", body, re.I) or re.search(r"with\s+check\s*\(\s*true\s*\)", body, re.I):
            for_cmd = re.search(r"\bfor\s+(select|insert|update|delete|all)\b", body, re.I)
            cmd = for_cmd.group(1).lower() if for_cmd else "all"
            sev = "MEDIUM" if cmd == "select" else "CRITICAL"
            findings.append((sev, "policy-always-true", rel, ln,
                             f"{name} on {tbl} allows {cmd.upper()} for everyone matched by its role (using/with check true)"))
        if re.search(r"\bto\s+(anon|public)\b", body, re.I) and re.search(r"for\s+(insert|update|delete|all)", body, re.I):
            findings.append(("HIGH", "anon-write-policy", rel, ln, f"{name} on {tbl} lets unauthenticated users write"))
        if not re.search(r"auth\.uid\(\)|auth\.jwt\(\)|auth\.role\(\)|is_admin|has_role|exists\s*\(", body, re.I) \
           and not re.search(r"using\s*\(\s*true\s*\)", body, re.I) and re.search(r"using|with\s+check", body, re.I):
            findings.append(("LOW", "policy-no-user-check", rel, ln,
                             f"{name} on {tbl} never references auth.uid()/auth.jwt(). Confirm it is intentional"))

    for tbl, (rel, ln) in sorted(tables.items()):
        if not tbl.startswith("public.") or skip_tables.match(tbl):
            continue
        if tbl not in rls_on:
            findings.append(("CRITICAL", "rls-not-enabled", rel, ln,
                             f"Table {tbl} has no ENABLE ROW LEVEL SECURITY in the repo. With the anon key, anyone can read/write it via the API"))
        elif tbl not in pol_by_table:
            findings.append(("MEDIUM", "rls-enabled-no-policies", rel, ln,
                             f"{tbl} has RLS on but no policies in the repo: denies everything (safe) but the app may be broken or policies live only in the dashboard"))

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    for sev, check, rel, ln, detail in sorted(findings, key=lambda f: (order[f[0]], f[2], f[3])):
        print(f"{sev} | {check} | {rel}:{ln} | {detail}")
    print(f"INFO | check_rls | - | parsed {len(files)} sql file(s), {len(tables)} table(s), {len(policies)} polic(ies). "
          "Repo SQL may differ from the live DB: verify in the dashboard")

if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("usage: check_rls.py <project_root>")
    main(os.path.abspath(sys.argv[1]))
