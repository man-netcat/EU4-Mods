#!/usr/bin/env python3
"""
EU4 Dynamic Tags Generator - Main Entry Point

This module provides the main entry point for the EU4 Dynamic Tags Generator.
All the actual implementation is in the src/ folder for better organization.
"""

import os

from src.generator import build_modules
from src.defines.paths import MODULES_ROOT


def main():
    """Main entry point for the EU4 Dynamic Tags Generator."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build_modules(MODULES_ROOT)


if __name__ == "__main__":
    main()
