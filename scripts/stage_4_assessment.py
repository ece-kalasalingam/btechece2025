"""
STAGE 4: Assessment Strategy
Verbatim: Implements Section 7.1 (Table 6) of R2025 Regulations.
"""
from typing import List
from scripts.contracts import CourseMetadata, AssessmentStrategy, AssessmentComponent

def generate_assessment_strategy(metadata: CourseMetadata) -> AssessmentStrategy:
    """
    Determines CIA/ESE split based on R2025 Course Type.
    """
    t_code = metadata.course_type.value # e.g., "TC", "PC", "IC"
    
    # 1. Theory Course (TC) - Table 6, Row 1
    if t_code == "TC":
        return AssessmentStrategy(
            course_type_code="TC",
            cia_weight=40,
            ese_weight=60,
            components=[
                AssessmentComponent("Sessional Exams", 25),
                AssessmentComponent("Assignments/Quizzes", 10),
                AssessmentComponent("Attendance", 5)
            ]
        )

    # 2. Practical Course (PC) - Table 6, Row 2
    elif t_code == "PC":
        return AssessmentStrategy(
            course_type_code="PC",
            cia_weight=60,
            ese_weight=40,
            components=[
                AssessmentComponent("Lab Performance/Rubrics", 40),
                AssessmentComponent("Record/Observation", 10),
                AssessmentComponent("Internal Viva", 10)
            ]
        )

    # 3. Integrated Course (IC) - Table 6, Row 3
    elif t_code == "IC-T":
        # Usually 50/50 for Integrated
        return AssessmentStrategy(
            course_type_code="IC",
            cia_weight=50,
            ese_weight=50,
            components=[
                AssessmentComponent("Theory Sessionals", 20),
                AssessmentComponent("Lab Assessment", 20),
                AssessmentComponent("Integrated Project", 10)
            ]
        )
    elif t_code == "IC-P":
        # Usually 50/50 for Integrated
        return AssessmentStrategy(
            course_type_code="IC",
            cia_weight=50,
            ese_weight=50,
            components=[
                AssessmentComponent("Theory Sessionals", 20),
                AssessmentComponent("Lab Assessment", 20),
                AssessmentComponent("Integrated Project", 10)
            ]
        )
    
    # Default fallback for Skill Courses (SC)
    return AssessmentStrategy(t_code, 100, 0, [AssessmentComponent("Skill Demonstration", 100)])

def validate_assessment_compliance(metadata: CourseMetadata, strategy: AssessmentStrategy):
    # Check for X-Activity assessment
    if metadata.x > 0:
        has_pbl = any("PBL" in c.name or "X-Activity" in c.name for c in strategy.components)
        if not has_pbl:
            # We automatically inject it if it's missing but required by metadata
            strategy.components.append(AssessmentComponent("PBL/X-Activity", 10))
            # Adjust other components to keep total at CIA weight...