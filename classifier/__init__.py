"""
Staxx Task Classifier — Public package interface.

Usage::

    from classifier import classify, ClassifierInput, TaskClassification

    result = classify({"messages": [...], "model": "gpt-4o"})
    print(result.task_type, result.confidence)
"""

from classifier.engine import classify
from classifier.schemas import ClassifierInput, TaskClassification

__all__ = ["classify", "ClassifierInput", "TaskClassification"]
