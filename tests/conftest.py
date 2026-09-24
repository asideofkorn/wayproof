"""Shared fixtures for the repository regression suite."""

import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def generated_site(tmp_path_factory):
    """Build the canonical static site once for every test session."""
    from scripts import build_site

    output = tmp_path_factory.mktemp("generated-site")
    original_cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        stats = build_site.build(output)
    finally:
        os.chdir(original_cwd)
    return output, stats
