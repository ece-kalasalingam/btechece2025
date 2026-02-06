# scripts/stage_5.py
from scripts.contracts import CourseExecutionContext, CanonicalCourse, CourseMeta

def run_course_assembly(ctx: CourseExecutionContext):
    if not ctx.is_eligible or ctx.metadata is None or ctx.structure is None:
        return
    meta_obj = CourseMeta(
        course_title=ctx.metadata.get("course_title", "UNTITLED"),
        course_category=ctx.metadata.get("course_category", "UNKNOWN"),
        course_type=ctx.metadata.get("course_type", "UNKNOWN"),
        l=ctx.metadata.get("l", 0), t=ctx.metadata.get("t", 0),
        p=ctx.metadata.get("p", 0), x=ctx.metadata.get("x", 0),
        c=ctx.metadata.get("c", 0.0),
        prerequisite=ctx.metadata.get("prerequisite"),
        corequisite=ctx.metadata.get("corequisite"),
        course_author=ctx.metadata.get("course_author", "Department Curriculum Committee"),
        bos_date=ctx.metadata.get("bos_date", "N/A"),
        course_revision=ctx.metadata    .get("course_revision", "1.0"), # User provided 'Version' in MD
        document_version=ctx.metadata.get("document_version", "1"), # Git commit count
        document_date=ctx.metadata.get("document_date", "N/A"),     # Git date
        document_git_hash=ctx.metadata.get("document_git_hash", "N/A"), # Git Hash
        course_level=ctx.metadata.get("course_level", 1)
    )
    ctx.metadata = None  # Clear metadata to save memory

    ctx.course = CanonicalCourse(
        course_code=ctx.course_code,
        course_meta=meta_obj,
        description=ctx.structure.explicit_sections.get("course_description", ""),
        units=ctx.extracted_data.get("units", []),
        outcomes=ctx.extracted_data.get("outcomes", []),
        articulation=ctx.structure.explicit_sections.get("articulation_matrix"),
        # Key updated to match SECTION_TITLE_MAP in patterns.py
        assessment=ctx.structure.explicit_sections.get("assessment_schemes"),
        rubrics=ctx.structure.explicit_sections.get("rubrics"),
    )