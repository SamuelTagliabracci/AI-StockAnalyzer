"""Trading agents — each reads the shared data pool and emits a reasoned verdict.

Tier 1 (live): Claude Code, the scheduled premium analyst (see claude_analyst.py).
Later tiers: Ollama local / cloud models, external-AI stubs. All write to the same
agent_verdicts ledger so their calls can be compared head-to-head (R5 validation).
"""
