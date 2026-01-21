# Syllabus DSL Specification — v1.0 (Minimal)

## 1. Purpose

This document defines the **formal Domain-Specific Language (DSL)** for the
University Syllabus Compiler.

- Markdown is only a **surface syntax**
- The compiler interprets Markdown into a **semantic course model**
- All rules are enforced **strictly at compile time**
- Any violation results in a hard failure (`SyllabusError`)
- No best-effort or partial rendering is permitted

This specification defines **DSL v1.0** and is intentionally minimal and stable.

---

## 2. Semantic Model

A syllabus is interpreted into the following hierarchy:

```
Course
 ├── Metadata
 ├── Units (exactly 5)
 │    ├── Theory topics (optional)
 │    ├── Laboratory topics (optional)
 │    └── X-Activity topics (optional)
 └── Credit Structure (L, T, P, X, C)
```

---

## 3. Course-Level Constraints

### 3.1 Unit Count (MANDATORY)

- A course **MUST contain exactly 5 units**
- Fewer or more than 5 units is invalid

---

### 3.2 LTPXC Presence Rules (MANDATORY)

Let `(L, T, P, X, C)` be the declared credit structure.

- If `(L + T) > 0` → **Theory content MUST exist**
- If `(L + T) = 0` → **Theory content MUST NOT exist**
- If `P > 0` → **Laboratory content MUST exist**
- If `P = 0` → **Laboratory content MUST NOT exist**
- If `X > 0` → **X-Activity content MUST exist**
- If `X = 0` → **X-Activity content MUST NOT exist**

---

### 3.3 Credit Validation (MANDATORY)

Credits must satisfy the equation **exactly**:

```
L + T + (P / 2) + (X / 3) = C
```

Rules:
- Fractional values are allowed
- No rounding is permitted
- Exact arithmetic is required

---

### 3.4 Hour Validation (MANDATORY)

Total instructional hours must satisfy:

- Theory hours = `15 × (L + T)`
- Laboratory hours = `15 × P`
- X-Activity hours = `15 × X`

Aggregated hours across all units **MUST match exactly**.

---

## 4. Unit-Level Constraints

### 4.1 Unit Structure

- Each unit **MAY contain**:
  - Theory topics
  - Laboratory topics
  - X-Activity topics
- Units must respect the LTPXC presence rules

---

### 4.2 Empty Unit Rule (MANDATORY)

A unit is **INVALID** if:

- The unit heading exists
- AND all allowed sections contain **zero topics**

At least one valid topic must exist in any section permitted by LTPXC.

---

## 5. Topic Definition (v1.0)

- A **topic** is defined as:
  - One non-empty list item extracted from Markdown tokens
- Topic text is treated as **opaque**
  - No normalization
  - No semantic equivalence
  - No duplicate detection

---

## 6. Error Semantics

- All violations **MUST raise `SyllabusError`**
- Validation is **fail-fast**
- Exactly **one error** is reported per compilation attempt
- Error messages **MUST**:
  - Identify the violated rule
  - Identify the course
  - Identify the unit (if applicable)

---

## 7. Versioning Rule

- This document defines **DSL v1.0**
- Any change to:
  - Rule meaning
  - Topic semantics
  - Structural constraints

**REQUIRES a new DSL version**.

Syllabi compiled under DSL v1.0 **must remain valid forever**.

---

## 8. Explicitly Out of Scope (Deferred)

The following are NOT part of DSL v1.0:

- Unit numbering continuity (I–V)
- Duplicate topic detection
- Topic count limits per unit
- Topic normalization
- Cross-unit semantic analysis

These may be introduced in DSL v1.1 or later.
