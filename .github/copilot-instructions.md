# Development Agent Rules

## Workflow

When implementing changes:

1. Analyze the request.
2. Create a plan.
3. Identify affected files.
4. Implement changes.
5. Create tests.
6. Verify correctness.
7. Summarize results.

## Safety

Never:

- delete unrelated code
- change APIs without explanation
- introduce breaking changes silently

## Code Changes

Prefer:

- small commits
- focused modifications
- reuse existing abstractions

## Python

Use:

- Python 3.12+
- type hints
- pytest
- pathlib

Avoid:

- global mutable state
- duplicated logic
- premature optimization

## Reviews

When reviewing:

- find bugs first
- style issues last

## Documentation

Update documentation when behavior changes.

## If Uncertain

Stop and ask for clarification.