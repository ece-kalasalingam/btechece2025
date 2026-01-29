# Syllabus DSL Specification — v1.3 (Normative)

## 1. Purpose

This document defines the **formal Domain-Specific Language (DSL)** for the
University Syllabus Compiler.

- Markdown is only a **surface syntax**
- The compiler interprets Markdown into a **semantic course model**
- All rules are enforced **strictly at compile time**
- Any violation within a syllabus file results in a hard failure (`SyllabusError`)
- No best-effort, partial rendering, or error recovery is permitted

This specification defines **DSL v1.3**.

DSL v1.3.1 **supersedes v1.2.1** by making all previously implicit enforcement rules explicit.

---

## 2. Semantic Model

A syllabus is interpreted into the following hierarchy:

```
Programme Context
 ├── Programme Outcomes (PO / PSO / SO)
 └── Courses

Course
 ├── Metadata
 │    ├── Course Code
 │    ├── L-T-P-X-C Structure
 │    └── Pre-requisite (optional)
 ├── Course Objectives
 ├── Course Outcomes
 ├── Articulation Matrices (conditional)
 ├── Units (exactly 5)
 │    ├── Theory Content
 │    ├── Laboratory Experiments
 │    └── X-Activity Components
 └── Credit & Hour Validation
```

---

## 3. Programme-Level Constraints (MANDATORY)

### 3.1 Programme Outcomes Definition

If a programme context exists, the following outcome sets **MUST** be defined:

- NBA Programme Outcomes (PO)
- Programme Specific Outcomes (PSO)
- ABET Student Outcomes (SO)

Each outcome set **MUST** satisfy:

- Sequential numbering starting from 1
- No gaps or duplicates
- Format: `<PREFIX><n> : <description>`

---

## 4. Course-Level Constraints

### 4.1 Unit Count (MANDATORY)

- A course **MUST contain exactly 5 units**
- Fewer or more than 5 units is invalid

---

### 4.2 L-T-P-X-C Declaration (MANDATORY)

Each course **MUST declare** an L-T-P-X-C structure.

Credits **MUST** satisfy the exact equation:

```
L + T + (P / 2) + (X / 3) = C
```

Rules:
- Exact arithmetic is required
- Fractional credits are allowed
- Floating-point arithmetic is forbidden
- No rounding or approximation is permitted

---
## 4.3 Topic Cardinality Constraints (DSL v1.2)

For each Unit, topic counts are constrained as follows.

### 4.3.1 Theory Topics
If Theory Content is permitted by LTPXC:

- Each unit MUST contain **at least 4 theory topics**
- Each unit MUST contain **at most 8 theory topics**

### 4.3.2 Laboratory Experiments
If Laboratory Content is permitted by LTPXC:

- Each unit MUST contain **at least 1 laboratory experiment**
- Each unit MUST contain **at most 3 laboratory experiments**

### 4.3.3 X-Activity Components
If X-Activity Content is permitted by LTPXC:

- Each unit MUST contain **at least 1 X-Activity component**
- Each unit MUST contain **at most 3 X-Activity components**

Violation of any topic cardinality rule MUST raise `SyllabusError`.

NOTE:
- Topic text is opaque; only topic counts are validated.
- Cardinality constraints apply **per unit**, not across units.
- These constraints are **policy-level rules**, not syntactic rules.


### 4.4 Hour Validation (MANDATORY)

Total instructional hours **MUST** satisfy:

- Total Theory hours = `15 × (L + T)`
- Total Laboratory hours = `15 × P`
- Total X-Activity hours = `15 × X`

Hours are aggregated across **all units** and **MUST match exactly**.

---

### 4.5 Course Objectives and Outcomes (MANDATORY)

- Course Objectives **MUST** be defined as a list
- Course Outcomes **MUST** be defined as a list
- Each Course Outcome **MUST** follow the format:
  ```
  CO<n> : <description>
  ```
- CO numbering **MUST** be sequential starting from 1

---

## 5. Unit-Level Constraints

### 5.1 Unit Structure (MANDATORY)

- A course **MUST contain exactly 5 units**
- Units **MUST be numbered sequentially**:
  ```
  Unit 1, Unit 2, Unit 3, Unit 4, Unit 5
  ```
- Gaps, duplicates, or out-of-order units are invalid

---

### 5.2 Section Presence Rules (MANDATORY, PER UNIT)

Let `(L, T, P, X)` be the declared credit structure.

For **each unit**:

- If `(L + T) > 0` → **Theory Content MUST exist**
- If `(L + T) = 0` → **Theory Content MUST NOT exist**
- If `P > 0` → **Laboratory Experiments MUST exist**
- If `P = 0` → **Laboratory Experiments MUST NOT exist**
- If `X > 0` → **X-Activity MUST exist**
- If `X = 0` → **X-Activity MUST NOT exist**

Presence rules are enforced **uniformly across all units**.

---

### 5.3 Section Ordering (MANDATORY)

Within each unit, sections **MUST appear in the following order**:

```
Theory Content → Laboratory Experiments → X-Activity
```

- Reordering is invalid
- Skipping intermediate sections is invalid if the section is required by LTPXC

---

### 5.4 Empty Unit Rule (MANDATORY)

A unit is **INVALID** if:

- The unit heading exists
- AND all sections permitted by LTPXC contain **zero topics/components**

At least **one valid topic, experiment, or component** must exist in any permitted section.

---

## 6. Topic and Content Semantics

### 6.1 Theory Topics (MANDATORY GRAMMAR)

Each theory topic **MUST** be defined as:

```
<Primary Topic> : <Details>
```

Rules:
- Exactly one colon is semantically significant
- Text before the first colon is the topic
- All text after the first colon is treated as opaque details
- Empty topics or empty details are invalid

---

### 6.2 Laboratory Experiments

- Laboratory content **MUST** be structured as:
  - One or more experiment blocks
  - Each experiment **MUST** have:
    - A title
    - A non-empty description

---

### 6.3 X-Activity Components

- X-Activity content **MUST** be structured as:
  - One or more component blocks
  - Each component **MUST** have:
    - A title
    - A non-empty description

---

## 7. Articulation Matrices (v1.3)

Articulation matrices define the mapping between Course Outcomes (COs) and Programme Outcomes (PO/PSO/SO). In DSL v1.3, these are defined using **Definition Lists** to ensure structural stability and ease of editing.

### 7.1 List-Based Articulation
Articulation mappings must be defined using a standard Markdown bulleted list. Each list item represents one Course Outcome and its associated mappings.

#### 7.1.1 Syntax Pattern
The syntax for each line is strict:
`- CO<n>: <Outcome_Type><Number>=<Value>, <Outcome_Type><Number>=<Value>, ...`

#### 7.1.2 Constraints
* **Target Identifier**: Must start with the CO label (e.g., `CO1:`) followed by a space.
* **Key-Value Pair**: Consists of the outcome name (e.g., `PO1`), an equals sign (`=`), and a value.
* **Allowed Values**: Must be exactly `1`, `2`, `3`, or `-` (where `-` denotes no articulation).
* **Separators**: Individual mappings within a single CO row must be separated by a comma.
* **Completeness**: While all columns defined in the Programme Context (e.g., PO1–PO11) should ideally be listed, any omitted key will default to `-` (no articulation).

### 7.2 Example
```markdown
## CO–NBA Programme Outcomes Mapping
- CO1: PO1=3, PO2=2, PO5=1, PO11=1
- CO2: PO1=2, PO2=3, PO3=2, PO5=1
- CO3: PO1=1, PO2=2, PO3=3, PO4=2, PO5=2
```
---

## 8. Error Semantics

- All violations **MUST raise `SyllabusError`**
- Validation is **fail-fast per syllabus file**
- For a given syllabus file, the compiler **MUST stop at the first violation**
- Across multiple syllabus files, the compiler **MAY continue processing**
  and report errors from each file independently
- Error aggregation across files is a **compiler behavior**, not a DSL violation
- Error messages **MUST**:
  - Identify the violated rule
  - Identify the course
  - Identify the unit (if applicable)
- The DSL specifies **what constitutes an error**, not **how many errors**
  a compiler implementation chooses to report across multiple files

A *compilation attempt* refers to the validation of a **single syllabus file**.
In batch compilation mode, multiple independent compilation attempts may be
performed within a single compiler invocation.


---

## 9. Versioning Rule

- This document defines **DSL v1.3**
- Any change to:
  - Structural constraints
  - Section ordering
  - Topic grammar
  - Credit or hour rules
  - Articulation semantics

**REQUIRES a new DSL version**.

Syllabi compiled under DSL v1.3 **MUST remain valid forever**.

---

## 10. Explicitly Out of Scope

The following are **not part of DSL v1.1**:

- Topic semantic normalization
- Duplicate topic detection
- Topic count limits per unit
- Cross-unit semantic analysis
- Pedagogical quality evaluation
