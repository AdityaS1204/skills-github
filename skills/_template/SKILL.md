---
name: skill-name-here
description: Clear, specific summary of what the skill does and when an agent should trigger it. Include triggering keywords and use-cases.
license: MIT
compatibility: Python 3.10+ / Node.js 18+ (optional)
---

# Skill Name

Provide a concise overview of this skill's capabilities and purpose.

## When to Use
- Scenario 1 (e.g., when the user asks to...)
- Scenario 2 (e.g., when debugging...)

## Progressive Workflow
1. Step 1: Analyze the input and verify prerequisites.
2. Step 2: Use bundled scripts if deterministic logic is required:
   ```bash
   python scripts/run.py --input <file>
   ```
3. Step 3: Refer to deep-dive documentation in `references/` if extra domain knowledge is required.
4. Step 4: Validate output against standards shown in `examples/`.

## Bundled Resources
- `scripts/`: Executable helper tools (kept out of context window until run).
- `examples/`: Sample inputs and expected outputs.
- `references/`: Detailed specifications and reference manuals.
