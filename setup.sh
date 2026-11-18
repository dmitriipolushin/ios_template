#!/bin/bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────
# iOS Template Setup Script
#
# Usage:
#   ./setup.sh
#   ./setup.sh --name "My App" --bundle-id com.yourcompany.myapp
#
# What it does:
#   1. Asks for app name and bundle ID (or uses flags)
#   2. Renames all "AppName" references in code and config
#   3. Sets up Secrets.plist from template
#   4. Installs xcodegen if missing
#   5. Generates .xcodeproj
#   6. Removes this script (it's a one-time setup)
# ──────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Parse arguments ──────────────────────────────────────────

APP_NAME=""
BUNDLE_ID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --name) APP_NAME="$2"; shift 2 ;;
        --bundle-id) BUNDLE_ID="$2"; shift 2 ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
    esac
done

# ── Interactive prompts (if flags not provided) ──────────────

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     iOS Template Setup               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

if [[ -z "$APP_NAME" ]]; then
    read -rp "$(echo -e "${GREEN}App name${NC} (e.g. My Cool App): ")" APP_NAME
fi

if [[ -z "$APP_NAME" ]]; then
    echo -e "${RED}App name is required.${NC}"
    exit 1
fi

# Derive identifiers from app name
# "My Cool App" → "MyCoolApp" (code identifier)
# "My Cool App" → "my-cool-app" (slug for bundle ID suggestion)
CODE_NAME=$(echo "$APP_NAME" | sed 's/[^a-zA-Z0-9 ]//g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1' | tr -d ' ')
SLUG=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')

if [[ -z "$BUNDLE_ID" ]]; then
    SUGGESTED="com.yourcompany.${SLUG//-/}"
    read -rp "$(echo -e "${GREEN}Bundle ID${NC} [${SUGGESTED}]: ")" BUNDLE_ID
    BUNDLE_ID="${BUNDLE_ID:-$SUGGESTED}"
fi

# Extract prefix from bundle ID (everything before last segment)
BUNDLE_PREFIX=$(echo "$BUNDLE_ID" | rev | cut -d. -f2- | rev)

echo ""
echo -e "  App name:    ${YELLOW}${APP_NAME}${NC}"
echo -e "  Code name:   ${YELLOW}${CODE_NAME}${NC}"
echo -e "  Bundle ID:   ${YELLOW}${BUNDLE_ID}${NC}"
echo -e "  Prefix:      ${YELLOW}${BUNDLE_PREFIX}${NC}"
echo ""
read -rp "$(echo -e "${GREEN}Proceed? (Y/n)${NC} ")" CONFIRM
if [[ "${CONFIRM,,}" == "n" ]]; then
    echo "Aborted."
    exit 0
fi

echo ""

# ── Step 1: Rename in project.yml ────────────────────────────

echo -e "${BLUE}[1/6]${NC} Updating project.yml..."

sed -i '' "s/name: AppName/name: ${CODE_NAME}/" project.yml
sed -i '' "s/bundleIdPrefix: com.example/bundleIdPrefix: ${BUNDLE_PREFIX}/" project.yml
sed -i '' "s/  AppName:/  ${CODE_NAME}:/" project.yml
sed -i '' "s/PRODUCT_BUNDLE_IDENTIFIER: com.example.appname/PRODUCT_BUNDLE_IDENTIFIER: ${BUNDLE_ID}/" project.yml
sed -i '' "s/INFOPLIST_KEY_CFBundleDisplayName: \"App Name\"/INFOPLIST_KEY_CFBundleDisplayName: \"${APP_NAME}\"/" project.yml
sed -i '' "s/AppNameTests/${CODE_NAME}Tests/g" project.yml

echo -e "  ${GREEN}✓${NC} project.yml updated"

# ── Step 2: Rename in Swift files ────────────────────────────

echo -e "${BLUE}[2/6]${NC} Renaming in Swift source files..."

# Rename struct/class references in Swift files
find App/ -name "*.swift" -type f -exec sed -i '' "s/AppNameApp/${CODE_NAME}App/g" {} +
find App/ -name "*.swift" -type f -exec sed -i '' "s/\"AppName\"/\"${APP_NAME}\"/g" {} +

# Rename the @main file itself
if [[ -f "App/App/AppNameApp.swift" ]]; then
    mv "App/App/AppNameApp.swift" "App/App/${CODE_NAME}App.swift"
    echo -e "  ${GREEN}✓${NC} Renamed AppNameApp.swift → ${CODE_NAME}App.swift"
fi

echo -e "  ${GREEN}✓${NC} Swift files updated"

# ── Step 3: Setup Secrets.plist ──────────────────────────────

echo -e "${BLUE}[3/6]${NC} Setting up Secrets.plist..."

if [[ -f "App/Resources/Secrets.plist" ]]; then
    echo -e "  ${YELLOW}⚠${NC}  Secrets.plist already exists, skipping"
else
    if [[ -f "Secrets.plist.example" ]]; then
        cp Secrets.plist.example App/Resources/Secrets.plist
        echo -e "  ${GREEN}✓${NC} Copied Secrets.plist.example → App/Resources/Secrets.plist"
        echo -e "  ${YELLOW}→${NC}  Fill in your API keys in App/Resources/Secrets.plist"
    else
        echo -e "  ${YELLOW}⚠${NC}  No Secrets.plist.example found, skipping"
    fi
fi

# ── Step 4: Install XcodeGen ─────────────────────────────────

echo -e "${BLUE}[4/6]${NC} Checking XcodeGen..."

if command -v xcodegen &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} XcodeGen already installed ($(xcodegen --version 2>/dev/null || echo 'unknown version'))"
else
    echo -e "  ${YELLOW}→${NC}  Installing XcodeGen via Homebrew..."
    if command -v brew &>/dev/null; then
        brew install xcodegen
        echo -e "  ${GREEN}✓${NC} XcodeGen installed"
    else
        echo -e "  ${RED}✗${NC}  Homebrew not found. Install XcodeGen manually:"
        echo "     brew install xcodegen"
        echo "     Then run: xcodegen generate"
    fi
fi

# ── Step 5: Generate Xcode project ──────────────────────────

echo -e "${BLUE}[5/6]${NC} Generating Xcode project..."

if command -v xcodegen &>/dev/null; then
    xcodegen generate 2>&1 | head -5
    echo -e "  ${GREEN}✓${NC} .xcodeproj generated"
else
    echo -e "  ${YELLOW}⚠${NC}  Skipped (XcodeGen not available). Run 'xcodegen generate' manually."
fi

# ── Step 6: Install Maestro ──────────────────────────────────

echo -e "${BLUE}[6/7]${NC} Checking Maestro..."

if command -v maestro &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Maestro already installed ($(maestro --version 2>/dev/null || echo 'unknown'))"
else
    echo -e "  ${YELLOW}→${NC}  Installing Maestro CLI..."
    if java -version &>/dev/null 2>&1; then
        curl -fsSL "https://get.maestro.mobile.dev" | bash
        echo -e "  ${GREEN}✓${NC} Maestro installed"
    else
        echo -e "  ${YELLOW}⚠${NC}  Java 17+ required for Maestro. Install manually:"
        echo "     brew install openjdk@17"
        echo "     curl -fsSL \"https://get.maestro.mobile.dev\" | bash"
    fi
fi

# ── Step 7: Initialize git (if not already) ──────────────────

echo -e "${BLUE}[7/7]${NC} Git setup..."

if [[ -d ".git" ]]; then
    echo -e "  ${GREEN}✓${NC} Git repo already initialized"
else
    git init -q
    echo -e "  ${GREEN}✓${NC} Git repo initialized"
fi

# ── Done ─────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Setup complete!                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Fill in API keys in ${YELLOW}App/Resources/Secrets.plist${NC}"
echo -e "  2. Set Adapty key in ${YELLOW}App/Services/Subscription/AdaptyManager.swift${NC}"
echo -e "  3. Open ${YELLOW}${CODE_NAME}.xcodeproj${NC} in Xcode"
echo -e "  4. Select your team in Signing & Capabilities"
echo -e "  5. Build & run!"
echo ""
echo -e "  ${BLUE}Tip:${NC} Use Claude Code skills for development:"
echo -e "    /speckit.specify  — create feature spec"
echo -e "    /ios-implement    — implement from spec"
echo -e "    /ios-qa           — static QA (144 checks)"
echo -e "    /ios-maestro      — E2E testing with Maestro"
echo -e "    /ios-review       — code review"
echo -e "    /imagine          — generate images"
echo ""

# Self-destruct — this script is one-time
read -rp "$(echo -e "${YELLOW}Remove setup.sh? (Y/n)${NC} ")" REMOVE_SELF
if [[ "${REMOVE_SELF,,}" != "n" ]]; then
    rm -- "$0"
    echo -e "${GREEN}✓${NC} setup.sh removed"
fi
