#!/bin/bash

echo "🧹 Starting code formatting..."

# Define target folders and files to format
TARGETS="src/ scripts/ hooks/ main.py"

echo "📁 Formatting targets: $TARGETS"
echo ""

# Remove unused imports and variables (non-intrusive but effective)
echo "1️⃣ Removing unused imports and variables..."
autoflake -r --in-place --remove-unused-variables --remove-all-unused-imports --ignore-init-module-imports $TARGETS

# Fix punctuation, capitalization, etc. in docstrings
echo "2️⃣ Formatting docstrings..."
docformatter -r -i --wrap-summaries=88 --wrap-descriptions=88 --make-summary-multi-line $TARGETS

# Automatically sort imports
echo "3️⃣ Sorting import statements..."
isort $TARGETS

# Automatically format (handle long lines, function arguments, f-strings, etc.)
echo "4️⃣ Formatting code..."
black $TARGETS

# Finally, static check (non-fixing)
echo "5️⃣ Static code analysis..."
flake8 $TARGETS

echo ""
echo "✅ Code formatting complete!"
echo "📊 Processed targets: $TARGETS"
