# AI Agent Skills Repository

A modular, extensible collection of production-grade **Agent Skills** designed for Claude, Anthropic Agentic frameworks, and compatible AI agent runtimes based on the [Agent Skills open specification](https://agentskills.io).

---

## 📂 Repository Structure

Skills are organized into self-contained directories under the root [`skills/`](./skills) folder. Each skill encapsulates instructions, metadata, executable scripts, and reference material:

```text
skills-github/
├── skills/
│   ├── _template/               # Starter template for creating new skills
│   │   ├── SKILL.md             # Standard frontmatter & workflow layout
│   │   ├── scripts/             # Executable scripts (Python, Bash, Node, etc.)
│   │   ├── examples/            # Reference implementations and sample outputs
│   │   └── references/          # Deep-dive documentation and specs
│   │
│   └── animate-svg/             # SVG Animation Skill
│       ├── SKILL.md             # Core skill instructions & metadata
│       ├── scripts/             # Helper scripts (e.g. SVG parsers, optimizers)
│       └── examples/            # Animated SVG examples and templates
│
├── CONTRIBUTING.md              # Guide to adding and structuring new skills
├── .gitignore                   # Ignore rules for python, node, and OS files
└── README.md                    # Repository index and documentation
```

---

## ⚡ The Agent Skills Concept: Progressive Disclosure

This repository follows Claude's **progressive disclosure** design pattern to keep agent token consumption minimal and execution deterministic:

| Tier | Component | Token Overhead | When Loaded |
|---|---|---|---|
| **Level 1** | YAML Frontmatter (`name`, `description`) | ~50–100 tokens | At agent startup to decide if the skill is relevant. |
| **Level 2** | Markdown Body (`SKILL.md`) | < 5,000 tokens | Only when user request matches the skill's trigger intent. |
| **Level 3** | Subfolders (`scripts/`, `references/`) | 0 prompt tokens | Scripts execute via CLI; only their output enters context. References are read on demand. |

---

## 🛠️ Available Skills

| Skill | Directory | Description | Status |
|---|---|---|---|
| **animate-svg** | [`skills/animate-svg/`](./skills/animate-svg/) | SVG animation techniques, CSS keyframes, SMIL, and GSAP workflows | 🟡 Initialized |

---

## 🚀 Adding a New Skill

1. **Copy the template:**
   ```bash
   cp -r skills/_template skills/my-new-skill
   ```
2. **Edit `SKILL.md`:**
   Ensure the YAML frontmatter includes:
   ```yaml
   ---
   name: my-new-skill
   description: Specific explanation of what the skill does and explicit trigger scenarios.
   ---
   ```
3. **Add helper scripts and examples:**
   - Place deterministic code or automated transforms in `scripts/`.
   - Place input/output examples in `examples/`.
   - Place reference documentation in `references/`.

For complete formatting rules and guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## 📜 License

Distributed under the [MIT License](LICENSE).
