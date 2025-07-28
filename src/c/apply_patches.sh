#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
FREETYPE2_PATCH="${SCRIPT_DIR}/freetype2.patch"
HARFBUZZ_PATCH="${SCRIPT_DIR}/harfbuzz.patch"

cd "${SCRIPT_DIR}/freetype2"
git apply "${FREETYPE2_PATCH}"

cd "${SCRIPT_DIR}/harfbuzz"
git apply "${HARFBUZZ_PATCH}"
