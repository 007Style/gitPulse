#!/usr/bin/env bash
# package.sh — Build and package gitPulse into a distributable macOS zip
# Usage: ./package.sh [version]
#   version: optional override (default: latest git tag or "1.0.0")
# Requires: python3 and PyInstaller (pip3 install pyinstaller)
set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
BOLD=$'\e[1m'; DIM=$'\e[2m'; RESET=$'\e[0m'
GREEN=$'\e[32m'; YELLOW=$'\e[33m'; CYAN=$'\e[36m'; RED=$'\e[31m'

info()    { echo "${CYAN}▸${RESET} $*"; }
success() { echo "${GREEN}✔${RESET} $*"; }
warn()    { echo "${YELLOW}⚠${RESET} $*"; }
die()     { echo "${RED}✖${RESET} $*" >&2; exit 1; }

# ── Config ────────────────────────────────────────────────────────────────────
BINARY_NAME="gitPulse"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    VERSION="$1"
elif git -C "$SCRIPT_DIR" describe --tags 2>/dev/null | grep -qE '^v?[0-9]+\.[0-9]+\.[0-9]+'; then
    VERSION="$(git -C "$SCRIPT_DIR" describe --tags | sed 's/^v//; s/-[0-9]*-g[0-9a-f]*//')"
else
    VERSION="1.0.0"
    warn "No git tag found — using version ${VERSION}"
fi

ARCH="$(uname -m)"
OS="macos"
DIST_NAME="${BINARY_NAME}-${VERSION}-${OS}-${ARCH}"
DIST_DIR="${SCRIPT_DIR}/dist/${DIST_NAME}"
ZIP_PATH="${SCRIPT_DIR}/dist/${DIST_NAME}.zip"

echo ""
echo "${BOLD}  gitPulse — distributable packager${RESET}"
echo "${DIM}  version ${VERSION}  ·  ${OS}-${ARCH}${RESET}"
echo ""

# ── Step 1: Build ─────────────────────────────────────────────────────────────
python3 -m PyInstaller --version >/dev/null 2>&1 || die "PyInstaller not found. Run: pip3 install pyinstaller"

info "Building standalone binary (PyInstaller) …"
cd "$SCRIPT_DIR"
python3 -m PyInstaller --onefile --clean --noconfirm --strip \
    --name "$BINARY_NAME" \
    --distpath "${SCRIPT_DIR}/build/bin" \
    --workpath "${SCRIPT_DIR}/build/work" \
    --specpath "${SCRIPT_DIR}/build" \
    gitpulse.py >/dev/null 2>&1 || die "PyInstaller build failed"

BINARY_PATH="${SCRIPT_DIR}/build/bin/${BINARY_NAME}"
[[ -f "$BINARY_PATH" ]] || die "Binary not found at ${BINARY_PATH}"
success "Binary built: ${DIM}${BINARY_PATH}${RESET}"

# ── Step 2: Stage dist directory ─────────────────────────────────────────────
info "Staging dist directory …"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
cp "$BINARY_PATH"              "$DIST_DIR/${BINARY_NAME}"
cp "${SCRIPT_DIR}/gitpulse.py" "$DIST_DIR/gitpulse.py"
cp "${SCRIPT_DIR}/README.md"   "$DIST_DIR/README.md"
cp "${SCRIPT_DIR}/LICENSE"     "$DIST_DIR/LICENSE"

cat > "$DIST_DIR/install.sh" <<'INSTALLER'
#!/usr/bin/env bash
# install.sh — Install gitPulse so you can just type `gitPulse`
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="${SCRIPT_DIR}/gitPulse"
DEST_DIR="${1:-/usr/local/bin}"

[[ -f "$BINARY" ]] || { echo "Error: binary not found at ${BINARY}" >&2; exit 1; }

if [[ -d "$DEST_DIR" && -w "$DEST_DIR" ]]; then
    install -m 755 "$BINARY" "$DEST_DIR/gitPulse"
else
    echo "Installing to ${DEST_DIR} (requires sudo) …"
    sudo mkdir -p "$DEST_DIR"
    sudo install -m 755 "$BINARY" "$DEST_DIR/gitPulse"
fi

# Clear the Gatekeeper quarantine flag that macOS puts on downloaded files
xattr -d com.apple.quarantine "$DEST_DIR/gitPulse" 2>/dev/null || true

echo "✔ gitPulse installed to ${DEST_DIR}/gitPulse"
echo "  Run: gitPulse -r ~/code"
INSTALLER
chmod +x "$DIST_DIR/install.sh"
success "Staged: ${DIM}${DIST_DIR}${RESET}"

# ── Step 3: Zip ───────────────────────────────────────────────────────────────
info "Creating zip archive …"
rm -f "$ZIP_PATH"
cd "${SCRIPT_DIR}/dist"
zip -r --quiet "${DIST_NAME}.zip" "${DIST_NAME}/"
success "Package ready: ${GREEN}${BOLD}dist/${DIST_NAME}.zip${RESET}"

echo ""
echo "  ${BOLD}Binary${RESET}   $(du -sh "$DIST_DIR/${BINARY_NAME}" | cut -f1)   ${DIM}${DIST_DIR}/${BINARY_NAME}${RESET}"
echo "  ${BOLD}Archive${RESET}  $(du -sh "$ZIP_PATH" | cut -f1)   ${DIM}${ZIP_PATH}${RESET}"
echo ""
echo "${GREEN}${BOLD}  Done.${RESET} Recipients run ${BOLD}./install.sh${RESET} inside the archive to install."
echo ""
