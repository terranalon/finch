# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---

## Key Decisions

- **Decision 1**: Rationale
- **Decision 2**: Rationale

## Out of Scope

- [What this feature explicitly does NOT include]

---

## Task 1: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py`
- Test: `tests/exact/path/to/test.py`

**Step 1.1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 1.2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 1.3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 1.4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

**Step 1.5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```

---

## Task 2: [Component Name]

**Files:**
- Modify: `exact/path/to/file.py`
- Test: `tests/exact/path/to/test.py`

**Step 2.1: Write the failing test**

[Test code]

**Step 2.2: Run test to verify it fails**

Run: [command]
Expected: [output]

**Step 2.3: Write minimal implementation**

[Implementation code]

**Step 2.4: Run test to verify it passes**

Run: [command]
Expected: PASS

**Step 2.5: Commit**

```bash
git add [files]
git commit -m "feat: description"
```

---

## Database Migration (if needed)

**Files:**
- Create: `backend/alembic/versions/xxx_description.py`

```sql
-- Description of what this migration does

CREATE TABLE example (
    id SERIAL PRIMARY KEY,
    -- columns
);

-- Data migration if needed
INSERT INTO new_table SELECT ... FROM old_table;
```

---

## Verification Checklist

| Test | How to Verify |
|------|---------------|
| Basic functionality | Description |
| Edge case | Description |
| Error handling | Description |

```bash
# Full test suite
pytest backend/tests/ -v

# Manual verification
# 1. Do X
# 2. Verify Y
```

---

## Open Questions

- [ ] Question that needs resolution before/during implementation