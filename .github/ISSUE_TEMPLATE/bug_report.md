---
name: Bug Report
about: Report a defect or unexpected behavior
title: "[BUG] "
labels: ["bug", "needs-triage"]
---

## Description
A clear and concise description of what the bug is.

## Reproduction Steps
1. Go to '...'
2. Call '...'
3. Observe '...'
4. Get error '...'

## Expected Behavior
What should happen instead?

## Actual Behavior
What actually happened?

## Environment
- OS: [e.g., Ubuntu 22.04, macOS 13.2]
- Python: [e.g., 3.11.4]
- Aletheia Version: [e.g., 1.9.0]
- Installation: [pip / Docker / source]

## Logs & Traceback
```
Paste full error traceback here
```

## Minimal Reproduction Code
```python
# Minimal code that reproduces the bug
from aletheia import AgentGuard

guard = AgentGuard()
result = guard.check("...")
# Expected: ..., Got: ...
```

## Impact
- [ ] Blocking (system down)
- [ ] High (feature broken)
- [ ] Medium (degraded behavior)
- [ ] Low (minor inconvenience)

## Additional Context
Any other context or screenshots?
