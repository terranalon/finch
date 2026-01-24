# Future Features

Implementation-ready plans for features not yet scheduled.

## Workflow

1. **Brainstorm**: Discuss the idea with Claude using `/brainstorming`
2. **Plan**: Claude writes the plan using `/writing-plans` structure
3. **Save**: Plan saved to `docs/future-features/NNN-feature-name.md`
4. **Implement**: When ready, open a session and run `/executing-plans` on the plan file

## Creating a New Plan

Start with: "Let's plan a future feature: [description]"

Claude will use the brainstorming and writing-plans skills to create an implementation-ready plan.

**Naming**: `NNN-short-description.md` (e.g., `001-rebalancing-suggestions.md`)

## Feature Index

| ID | Feature | Status |
|----|---------|--------|
| - | - | - |

## What Makes a Good Plan

Per the `writing-plans` skill:

- **Header** with Goal, Architecture, Tech Stack
- **Directive** pointing agents to `executing-plans`
- **Tasks** as numbered bite-sized steps (2-5 min each)
- **Files** with exact paths (Create/Modify/Test)
- **TDD flow**: failing test → verify fail → implement → verify pass → commit
- **Complete code** in the plan, not just descriptions
- **Commands with expected output**
- **Open Questions** resolved before implementation
