"""Compliance rule engine for the HK corridor egress demo."""

from .rules import CheckResult, run_checks

__all__ = ["CheckResult", "run_checks"]
