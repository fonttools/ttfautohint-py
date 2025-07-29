#!/bin/bash
set -e
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
FREETYPE2_PATCH="${SCRIPT_DIR}/freetype2.patch"
HARFBUZZ_PATCH="${SCRIPT_DIR}/harfbuzz.patch"
TTFAUTOHINT_PATCH="${SCRIPT_DIR}/ttfautohint.patch"

echo "Applying freetype2 patch..."
cd "${SCRIPT_DIR}/freetype2"
if ! git apply --check "${FREETYPE2_PATCH}" 2>/dev/null; then
    echo "  freetype2 patch already applied or not applicable"
else
    git apply "${FREETYPE2_PATCH}"
    echo "  freetype2 patch applied successfully"
fi

echo "Applying harfbuzz patch..."
cd "${SCRIPT_DIR}/harfbuzz"
if ! git apply --check "${HARFBUZZ_PATCH}" 2>/dev/null; then
    echo "  harfbuzz patch already applied or not applicable"
else
    git apply "${HARFBUZZ_PATCH}"
    echo "  harfbuzz patch applied successfully"
fi

echo "Applying ttfautohint patch..."
cd "${SCRIPT_DIR}/ttfautohint"
if ! git apply --check "${TTFAUTOHINT_PATCH}" 2>/dev/null; then
    echo "  ttfautohint patch already applied or not applicable"
else
    git apply "${TTFAUTOHINT_PATCH}"
    echo "  ttfautohint patch applied successfully"
fi

echo "All patches processed."
