#!/usr/bin/env python3
"""Compatibility entry point for the AI-layer sync workflow.

The implementation is kept at the repository root for backward compatibility;
this path is the canonical workflow entry point.
"""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "sync-ai-layer.py"), run_name="__main__")
