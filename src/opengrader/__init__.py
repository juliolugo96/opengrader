"""OpenGrader's public package interface."""

from opengrader.config import AssignmentConfig, TestConfig, load_assignment
from opengrader.grader import grade_assignment

__all__ = ["AssignmentConfig", "TestConfig", "grade_assignment", "load_assignment"]
__version__ = "0.2.0"
