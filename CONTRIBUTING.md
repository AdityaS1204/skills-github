# Contributing Skills

This repository follows the **Agent Skills** standard developed for Anthropic Claude and agentic AI runtimes.

---

## Skill Architecture

Every skill lives in its own subdirectory inside [`skills/`](./skills) with the following structure:

```text
skills/<skill-name>/
├── SKILL.md            # [Required] Metadata and core instructions
├── scripts/            # [Optional] Executable scripts (Python, Node, Bash, etc.)
├── examples/           # [Optional] Code samples, input/output demonstrations
├── references/         # [Optional] Heavy documentation, schemas, cheatsheets
└── assets/             # [Optional] Static assets, template files
```

---

## 1. `SKILL.md` Format Requirements

Every `SKILL.md` must start with YAML frontmatter bounded by `---`:

```yaml
---
name: kebab-case-name
description: Clear, action-oriented description detailing capabilities and trigger conditions.
license: MIT
compatibility: (Optional) Python 3.10+ / Node.js 18+
---
```

### Frontmatter Rules:
- **`name`**: Required. 1–64 characters. Must be lowercase alphanumeric characters and hyphens only (`^[a-z0-9-]+$`).
- **`description`**: Required. Up to 1024 characters.
  > 💡 **Tip:** Be descriptive and explicit about *when* the agent should invoke the skill (e.g., *"Use when the user wants to animate SVG elements, add morphing effects, or export CSS/SMIL animations"*).
- **`license`**: Standard SPDX identifier (e.g., `MIT`, `Apache-2.0`).

### Markdown Body Rules:
- **Concise & Actionable:** Keep instructions actionable and within ~5,000 tokens.
- **Checklists:** Use explicit step-by-step checklists so the agent follows a disciplined execution sequence.
- **Progressive Execution:** Direct the agent to execute scripts rather than having it hallucinate boilerplate code.

---

## 2. Using `scripts/`
- When a task involves deterministic formatting, mathematical calculations, file parsing, or image/SVG manipulation, bundle a script in `scripts/`.
- Claude and agent frameworks will run scripts via CLI commands (e.g., `python scripts/process.py`).
- This saves context window tokens because only the script's stdout/stderr is returned to the model.

---

## 3. Using `examples/`
- Place real-world examples showing before-and-after samples or reference patterns.
- Agents can read examples on demand to align their output formatting with expected standards.

---

## 4. Using `references/`
- Place in-depth documentation, API docs, or style guides in `references/`.
- Keep these files separate from `SKILL.md` so they are only loaded into context when specifically needed.
