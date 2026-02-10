from logging import fatal
from scripts.contracts import CourseExecutionContext
from scripts.utils import get_section_key

from scripts.patterns import (
    BLOCK_MATH_PATTERN, LATEX_ENV_PATTERN, UNIT_HEADING_PATTERN, THEORY_HEADER_PATTERN,
    HOURS_PATTERN, PRACTICAL_HEADER_PATTERN,
    XACT_HEADER_PATTERN, ACTIVITY_TITLE_PATTERN,
    DESCRIPTION_SUB_BULLET_PATTERN, UNIT_CO_MAP_PATTERN,
    CO_NUMBER_PATTERN, PC_EXPERIMENT_CO_PATTERN,
    CODE_BLOCK_PATTERN, BLOCKQUOTE_PATTERN, HTML_PATTERN,
    H3_PATTERN, H4_PATTERN, INVALID_HEADER_PATTERN,
    PARAGRAPH_PATTERN, TABLE_ROW_PATTERN, TABLE_SEPARATOR_PATTERN,
    BULLET_LINE_PATTERN, NUMBERED_LIST_PATTERN
)
from scripts.utils import extract_bullet_items, get_column_cells
import re


def _validate_activity_block(
    unit_block: str,
    header_pattern: re.Pattern,
    unit_no: int,
    label: str,
    ctx: CourseExecutionContext,
):
    match = header_pattern.search(unit_block)
    if not match:
        return 0, False  # hours, valid

    start = match.end()
    next_section = re.search(r"^####\s+", unit_block[start:], re.MULTILINE)
    block = unit_block[start : start + next_section.start()] if next_section else unit_block[start:]

    # Hours mandatory
    hour_match = HOURS_PATTERN.search(block)
    if not hour_match:
        ctx.log(
            "STAGE-4",
            f"{label.upper()}-HOURS-MISSING",
            f"Unit {unit_no} has {label} section but missing Hours.",
            fatal=True,
        )
        return 0, False

    hours = int(hour_match.group("hours"))

    # Title mandatory
    lines = block.splitlines()
    title_found = False

    for line in lines:
        if ACTIVITY_TITLE_PATTERN.match(line):
            title_found = True
            break

    if not title_found:
        ctx.log(
            "STAGE-4",
            f"{label.upper()}-TITLE-MISSING",
            f"Unit {unit_no} has {label} section but missing Title.",
            fatal=True,
        )
        return 0, False

    return hours, True

def _validate_syllabus_cos(co:str, ctx:CourseExecutionContext):
    if ctx.structure is None:
        return
    outcome_content = ctx.structure.explicit_sections["course_outcomes"]
    lines = outcome_content.splitlines()
    valid = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Bullet line
        if line.startswith("-"):
            valid.append(line)
            continue
    m = CO_NUMBER_PATTERN.match(co.strip())
    if not m:
        ctx.log(
            stage="STAGE-4",
            code="INVALID-CO-INTEGER",
            msg=f"Invalid CO token: {co}.",
            fatal=True,
        )
        return
    idx = int(m.group(1))
    upper = len(valid)
    if not (1 <= idx <= upper):
        ctx.log(
            "STAGE-4",
            "UNIT-CO-OUT-OF-RANGE",
            f"CO{idx} is invalid. Only CO1-CO{upper} are defined.",
            fatal=True,
        )
        return

def _validate_syllabus_theory_grammar(content: str, ctx: CourseExecutionContext):
    if ctx is None:
        return
    total_theory_hours = 0
    total_practical_hours = 0
    total_x_hours = 0
    units_with_px = 0
    course_type = ctx.metadata["course_type"] if ctx and ctx.metadata else None
    expected_theory_hours = None
    if ctx.metadata:
        expected_theory_hours = 15 * (ctx.metadata["l"] + ctx.metadata["t"])
        expected_p_hours = 15 * ctx.metadata["p"]
        expected_x_hours = 15 * ctx.metadata["x"]

    matches = list(UNIT_HEADING_PATTERN.finditer(content))
    unit_numbers = [int(m.group("number")) for m in matches]
    
    expected_sequence = [1, 2, 3, 4, 5]
    if unit_numbers != expected_sequence:
        error_code = "INSUFFICIENT-UNITS" if len(unit_numbers) != 5 else "INVALID-UNIT-SEQUENCE"
        ctx.log(
            stage="STAGE-4",
            code=error_code,
            msg=f"Exactly 5 units required in sequence 1-5; found {unit_numbers}.",
            fatal=True,
        )
        return

    for i, unit_match in enumerate(matches):
        start = unit_match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        unit_block = content[start:end]
        
        # Theory header must exist
        theory_match = THEORY_HEADER_PATTERN.search(unit_block)
        if not theory_match:
            ctx.log(
                stage="STAGE-4",
                code="THEORY-HEADER-MISSING",
                msg=f"Unit {unit_numbers[i]} is missing 'Theory' section.",
                fatal=True,
            )
            return
        pre_theory = unit_block[:theory_match.start()]
        co_match = UNIT_CO_MAP_PATTERN.search(pre_theory)
        if not co_match:
            ctx.log(
                "STAGE-4",
                "UNIT-CO-MAPPING-MISSING",
                (
                    f"Unit {unit_numbers[i]} must declare CO mapping "
                    f"using '- COs: COx, COy' before the Theory section."
                ),
                fatal=True,
            )
            return
        if len(UNIT_CO_MAP_PATTERN.findall(pre_theory)) > 1:
            ctx.log(
                "STAGE-4",
                "MULTIPLE-UNIT-CO-MAPPINGS",
                f"Unit {unit_numbers[i]} must contain exactly ONE CO mapping line.",
                fatal=True,
            )
            return
        raw = co_match.group(1)
        cos = [c.strip().upper() for c in raw.split(",")]

        seen = set()
        duplicates = set()

        for co in cos:
            _validate_syllabus_cos(co, ctx)
            if co in seen:
                duplicates.add(co)
            seen.add(co)

        if duplicates:
            ctx.log(
                "STAGE-4",
                "DUPLICATE-UNIT-CO-MAPPING",
                (
                    f"Unit {unit_numbers[i]} maps duplicate COs: "
                    f"{', '.join(sorted(duplicates))}. "
                    "Each CO must appear only once per unit."
                ),
                fatal=True,
            )
            return
        theory_start = theory_match.end()
        # Theory hours must exist
        next_subsection = re.search(r"^####\s+", unit_block[theory_start:], re.MULTILINE)
        theory_block = (
            unit_block[theory_start : theory_start + next_subsection.start()]
            if next_subsection
            else unit_block[theory_start:]
        )
        hour_match = HOURS_PATTERN.search(theory_block)
        
        if not hour_match:
            ctx.log(
                stage="STAGE-4",
                code="THEORY-HOURS-MISSING",
                msg=f"Unit {unit_numbers[i]} is missing Theory hours.",
                fatal=True,
            )
            return

        total_theory_hours += int(hour_match.group("hours"))
        bullet_items = extract_bullet_items(theory_block)

        valid_topics = []

        for item in bullet_items:
            # Must contain a title and subtopics separated by colon
            # --- Exclude Hours bullet explicitly ---
            if HOURS_PATTERN.match(item):
                continue
            if ":" not in item:
                continue

            title, subtopics = item.split(":", 1)

            # Reject empty title or empty subtopics
            if not title.strip():
                continue
            if not subtopics.strip():
                continue

            valid_topics.append(item)

        topic_count = len(valid_topics)
        
        if topic_count < 4 or topic_count > 8:
            ctx.log(
                stage="STAGE-4",
                code="INVALID-TOPIC-COUNT",
                msg=(
                    f"Unit {unit_numbers[i]} must contain 4-8 valid Theory topics "
                    f"(bulleted with title and subtopics). Found {topic_count}."
                ),
                fatal=True,
            )
            return
        
        p_hours, p_valid = _validate_activity_block(
            unit_block,
            PRACTICAL_HEADER_PATTERN,
            unit_numbers[i],
            "Practical",
            ctx,
        )

        x_hours, x_valid = _validate_activity_block(
            unit_block,
            XACT_HEADER_PATTERN,
            unit_numbers[i],
            "X-Activities",
            ctx,
        )

        if p_valid or x_valid:
            units_with_px += 1

        total_practical_hours += p_hours
        total_x_hours += x_hours
    if units_with_px < 1 and course_type in {"IC-T", "IC-P"}:
        ctx.log(
            "STAGE-4",
            "NO-PRACTICAL-OR-X",
            "At least one unit must contain a valid Practical or X-Activity component for IC-T/IC-P courses.",
            fatal=True,
        )
        return
    if units_with_px > 0 and course_type in {"TC"}:
        ctx.log(
            "STAGE-4",
            "UNWANTED PRACTICAL-OR-X",
            "No unit must contain a Practical or X-Activity component for TC courses.",
            fatal=True,
        )
        return
    
    if total_theory_hours != expected_theory_hours:
        ctx.log(
            stage="STAGE-4",
            code="THEORY-HOURS-MISMATCH",
            msg=(
                f"Total Theory hours = {total_theory_hours}, "
                f"expected {expected_theory_hours} (15 x (L+T))."
            ),
            fatal=True,
        )
    if total_practical_hours != expected_p_hours:
        ctx.log(
            "STAGE-4",
            "PRACTICAL-HOURS-MISMATCH",
            f"Total Practical hours = {total_practical_hours}, expected {expected_p_hours}.",
            fatal=True,
        )

    if total_x_hours != expected_x_hours:
        ctx.log(
            "STAGE-4",
            "X-ACTIVITY-HOURS-MISMATCH",
            f"Total X-Activity hours = {total_x_hours}, expected {expected_x_hours}.",
            fatal=True,
        )    

def _count_valid_practical_activities(block: str, unit_no: int, ctx):
    lines = block.splitlines()

    activities = 0
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Match activity title
        m = ACTIVITY_TITLE_PATTERN.match(line)
        if not m:
            i += 1
            continue

        title = m.group(1).strip()
        if not title:
            ctx.log(
                "STAGE-4",
                "PRACTICAL-TITLE-EMPTY",
                f"Unit {unit_no} has a Practical activity with empty Title.",
                fatal=True,
            )
            return 0

        # Expect at least one Description sub-bullet
        j = i + 1
        desc_found = False

        while j < len(lines):
            sub = lines[j].rstrip()

            # Sub-bullet (indented)
            if DESCRIPTION_SUB_BULLET_PATTERN.match(sub):
                desc_found = True
                break

            # Stop if next activity starts
            if ACTIVITY_TITLE_PATTERN.match(sub):
                break

            # Stop if new section starts
            if sub.startswith("####"):
                break

            j += 1

        if not desc_found:
            ctx.log(
                "STAGE-4",
                "PRACTICAL-DESCRIPTION-MISSING",
                f"Practical activity '{title}' in Unit {unit_no} is missing Description.",
                fatal=True,
            )
            return 0

        activities += 1
        i = j
    return activities

def _count_pc_practical_activities_and_hours(block: str, ctx: CourseExecutionContext):
    lines = block.splitlines()
    activities = 0
    total_hours = 0
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        m = ACTIVITY_TITLE_PATTERN.match(line)
        if not m:
            i += 1
            continue

        title = m.group(1).strip()
        if not title:
            ctx.log(
                "STAGE-4",
                "PC-EXPERIMENT-TITLE-EMPTY",
                "Experiment title cannot be empty.",
                fatal=True,
            )
            return 0, 0

        found_desc = False
        found_hours = False
        found_cos = False
        exp_hours = 0
        cos_seen = set()

        j = i + 1
        while j < len(lines):
            sub = lines[j].rstrip()

            if ACTIVITY_TITLE_PATTERN.match(sub) or sub.startswith("####"):
                break

            # Hours
            if HOURS_PATTERN.match(sub):
                exp_hours = int(HOURS_PATTERN.match(sub).group("hours"))
                found_hours = True

            # COs
            elif PC_EXPERIMENT_CO_PATTERN.match(sub):
                found_cos = True
                raw = PC_EXPERIMENT_CO_PATTERN.match(sub).group(1)
                cos = [c.strip().upper() for c in raw.split(",")]

                for co in cos:
                    _validate_syllabus_cos(co, ctx)
                    if co in cos_seen:
                        ctx.log(
                            "STAGE-4",
                            "DUPLICATE-PC-EXPERIMENT-CO",
                            f"Duplicate CO '{co}' in experiment '{title}'.",
                            fatal=True,
                        )
                        return 0, 0
                    cos_seen.add(co)

            # Description
            elif DESCRIPTION_SUB_BULLET_PATTERN.match(sub):
                found_desc = True

            j += 1

        if not found_hours or not found_desc or not found_cos:
            missing = []
            if not found_hours:
                missing.append("Hours")
            if not found_cos:
                missing.append("COs")
            if not found_desc:
                missing.append("Description")

            ctx.log(
                "STAGE-4",
                "PC-EXPERIMENT-INCOMPLETE",
                (
                    f"Experiment '{title}' is missing: "
                    f"{', '.join(missing)}."
                ),
                fatal=True,
            )
            return 0, 0

        activities += 1
        total_hours += exp_hours
        i = j

    return activities, total_hours

def _validate_pc_experiments_only(content: str, ctx: CourseExecutionContext):
    # 1. UNIT headings forbidden
    if UNIT_HEADING_PATTERN.search(content):
        ctx.log(
            "STAGE-4",
            "PC-UNIT-NOT-ALLOWED",
            "Practical Course must not contain UNIT sections.",
            fatal=True,
        )
        return

    # 2. #### Experiments must exist
    exp_match = PRACTICAL_HEADER_PATTERN.search(content)
    if not exp_match:
        ctx.log(
            "STAGE-4",
            "PC-EXPERIMENTS-MISSING",
            "Practical Course must contain a '#### Experiments' section.",
            fatal=True,
        )
        return

    # Extract Experiments block
    start = exp_match.end()
    next_section = re.search(r"^####\s+", content[start:], re.MULTILINE)
    exp_block = content[start : start + next_section.start()] if next_section else content[start:]

    # 3. Validate activities
    activities, total_hours = _count_pc_practical_activities_and_hours(exp_block, ctx)
    if activities < 1:
        ctx.log(
            "STAGE-4",
            "PC-NO-ACTIVITIES",
            "Practical Course must contain at least one valid experiment.",
            fatal=True,
        )
        return

    # 4. Hours reconciliation
    if ctx.metadata:
        expected = 15 * ctx.metadata["p"]
        if total_hours != expected:
            ctx.log(
                "STAGE-4",
                "PC-HOURS-MISMATCH",
                f"Total Practical hours = {total_hours}, expected {expected}.",
                fatal=True,
            )

def _validate_exempted_syllabus_markdown(content: str, ctx: CourseExecutionContext):
    lines = content.splitlines()
    i = 0
    # Re-organized loop for clarity
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 1. Critical Failures (Forbidden Syntax)
        if any(p.search(line) for p in [CODE_BLOCK_PATTERN, BLOCKQUOTE_PATTERN, HTML_PATTERN,  BLOCK_MATH_PATTERN, LATEX_ENV_PATTERN,]):
            ctx.log("STAGE-4", "UNSUPPORTED-MARKDOWN", f"Forbidden syntax: {stripped}", fatal=True)
            return

        # 2. Header Validation
        if INVALID_HEADER_PATTERN.match(line):
            ctx.log("STAGE-4", "INVALID-HEADER-LEVEL", f"Headers must be H3 or H4: {stripped}", fatal=True)
            return
        
        if H3_PATTERN.match(line) or H4_PATTERN.match(line):
            if "|" in stripped:
                ctx.log("STAGE-4", "INVALID-HEADER-CONTENT",
                        f"Headers must not contain table pipes: {stripped}", fatal=True)
                return
            i += 1
            continue


        # 3. Complex Structures (Tables)
        # ✅ Table Validation Logic
        if (
                TABLE_ROW_PATTERN.match(line)
                and i + 1 < len(lines)
                and TABLE_SEPARATOR_PATTERN.match(lines[i + 1])
            ):

            # 2. Establish column count from the header
            col_count = len(get_column_cells(line))
            
            # 3. Validate separator has the same number of columns
            if len(get_column_cells(lines[i + 1])) != col_count:
                ctx.log(
                    "STAGE-4",
                    "TABLE-COLUMN-MISMATCH",
                    "Header and separator column counts do not match.",
                    fatal=True,
                )
                return

            # 4. Validate all subsequent data rows
            j = i + 2
            while j < len(lines) and TABLE_ROW_PATTERN.match(lines[j]):
                row_content = lines[j]

                # Error if it's a duplicate separator
                if TABLE_SEPARATOR_PATTERN.match(row_content):
                    ctx.log("STAGE-4", "INVALID-TABLE", "Duplicate or misplaced separator row.", fatal=True)
                    return
                
                # Check column count
                cells = get_column_cells(row_content)
                if len(cells) != col_count:
                    ctx.log("STAGE-4", "TABLE-COLUMN-MISMATCH", f"Row {j+1} does not match header column count.", fatal=True)
                    return

                # --- NEW: CRITICAL CONTENT VALIDATION ---
                for cell in cells:
                    # Check for unbalanced math mode (the cause of your error)
                    if cell.count("$") % 2 != 0:
                        ctx.log("STAGE-4", "INVALID-TABLE-CONTENT", 
                                f"Unbalanced '$' in row {j+1}. Math mode must be closed within the same cell.", fatal=True)
                        return
                    
                    # Check for literal ampersands that aren't math
                    if "&" in cell and "$" not in cell:
                        ctx.log("STAGE-4", "INVALID-TABLE-CONTENT", 
                                f"Literal '&' found in row {j+1}. Use math mode or remove it.", fatal=True)
                        return

                j += 1

            i = j  # Move index to the end of the table
            continue

        # 4. Allowed Content (The "Whitelist")
        if any(p.match(line) for p in [BULLET_LINE_PATTERN, NUMBERED_LIST_PATTERN, PARAGRAPH_PATTERN]):
            i += 1
            continue

        # 5. Fallback - If the code reaches here, it's something truly weird (e.g., "!!! Note")
        ctx.log("STAGE-4", "INVALID-MARKDOWN-LINE", f"Unhandled line: {stripped}", fatal=True)
        return
    