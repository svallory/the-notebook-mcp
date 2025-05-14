# Pre-commit Hook Setup

This project uses Git hooks to run `ruff format` before each commit, ensuring consistent code formatting.

## Automatic Setup

The pre-commit hook is automatically set up when you install the dev dependencies:

```bash
# Using pip
pip install -e ".[dev]"

# Using uv
uv pip install -e ".[dev]"
```

Then enable the pre-commit hook:

```bash
pre-commit install
```

## Manual Setup

If the automatic setup doesn't work, you can set up the hook manually:

1. Create the pre-commit hook file:

```bash
mkdir -p .git/hooks
```

2. Create a `.git/hooks/pre-commit` file with the following content:

```bash
#!/bin/sh

# Run ruff format before commit
echo "Running ruff format..."
uv run ruff format

# If there are any staged changes after running format, add them to the commit
git diff --name-only --cached | grep '\.py$' | xargs -I{} git add {}

# Return success
exit 0
```

3. Make the hook executable:

```bash
chmod +x .git/hooks/pre-commit
```

## Testing the Hook

To test if the hook is working:

```bash
# Make some change to a Python file
# Stage the change
git add .

# Try to commit
git commit -m "Test pre-commit hook"
```

You should see "Running ruff format..." in the output, and the code should be formatted before the commit is finalized. 