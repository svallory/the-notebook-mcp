#!/bin/bash
# Wrapper script to run pytest with required environment variables set.

# Set the environment variable to silence the jupyter_client warning
export JUPYTER_PLATFORM_DIRS=1

# Run pytest, passing along any arguments provided to this script
python -m pytest "$@" 