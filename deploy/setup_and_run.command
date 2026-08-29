#!/bin/bash

# macOS one-click setup and launcher for the Fall Risk project.
# Double-click this file in Finder (or run: bash deploy/setup_and_run.command).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/full-version"
VENV_DIR="$PROJECT_ROOT/.venv-mac"
PNPM_TOOLS_DIR="$PROJECT_ROOT/.pnpm-tools"

say() {
  printf '\n%s\n' "$1"
}

fail() {
  printf '\n错误：%s\n' "$1" >&2
  printf '按回车键关闭窗口。'
  read -r
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

load_homebrew_path() {
  # Finder-launched .command files often do not inherit the user's shell PATH.
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

install_homebrew_if_needed() {
  load_homebrew_path

  if command_exists brew; then
    return
  fi

  say "未检测到 Homebrew。它用于在 macOS 上安装 Python 和 Node.js。"
  printf '是否现在安装 Homebrew？需要联网，并可能要求输入 macOS 密码。[Y/n] '
  read -r answer
  answer="${answer:-Y}"
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || \
      fail "Homebrew 安装失败，请先手动安装后重新运行。"

    # Homebrew's installer may ask the user to add brew to PATH. Load it now.
    load_homebrew_path
  else
    fail "请安装 Homebrew，或先自行安装 Python 3 和 Node.js 后重新运行。"
  fi
}

python_is_supported() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    >/dev/null 2>&1
}

find_compatible_python() {
  local candidate
  local candidates=(
    "/opt/homebrew/bin/python3.13"
    "/opt/homebrew/bin/python3.12"
    "/opt/homebrew/bin/python3.11"
    "/opt/homebrew/bin/python3.10"
    "/usr/local/bin/python3.13"
    "/usr/local/bin/python3.12"
    "/usr/local/bin/python3.11"
    "/usr/local/bin/python3.10"
    "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
  )

  if command_exists python3; then
    candidates+=("$(command -v python3)")
  fi

  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]] && python_is_supported "$candidate"; then
      PYTHON_BIN="$candidate"
      return 0
    fi
  done

  return 1
}

run_pnpm() {
  if [[ "$PNPM_USE_COREPACK" == true ]]; then
    "$PNPM_BIN" pnpm "$@"
  else
    "$PNPM_BIN" "$@"
  fi
}

say "开始配置项目环境..."
cd "$PROJECT_ROOT"

install_homebrew_if_needed

PYTHON_BIN=""
if ! find_compatible_python; then
  say "正在安装兼容的 Python 3.12..."
  brew install python@3.12 || fail "Python 3.12 安装失败。"
  PYTHON_BIN="$(brew --prefix python@3.12)/bin/python3.12"
fi

if ! command_exists node; then
  say "正在安装 Node.js..."
  brew install node
fi

[[ -x "$PYTHON_BIN" ]] || fail "找不到 Python 3.10 或更高版本。"
command_exists node || fail "找不到 node。"

say "创建 Python 虚拟环境并安装后端依赖..."
if [[ -x "$VENV_DIR/bin/python" ]] && ! python_is_supported "$VENV_DIR/bin/python"; then
  say "检测到旧版 Python 虚拟环境，正在重新创建..."
  rm -rf "$VENV_DIR"
fi
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install \
  "fastapi[standard]" uvicorn pyjwt pydantic "sqlalchemy[asyncio]" pandas \
  joblib lime numpy python-dotenv gradio aiosqlite "passlib[bcrypt]" \
  "scikit-learn==1.7.2" xgboost faker openpyxl reportlab

# Do not install pnpm globally: /usr/local is commonly not writable on macOS.
PNPM_BIN=""
PNPM_USE_COREPACK=false
if command_exists pnpm; then
  PNPM_BIN="$(command -v pnpm)"
elif command_exists corepack; then
  say "正在通过 Corepack 准备 pnpm（不需要管理员权限）..."
  PNPM_BIN="$(command -v corepack)"
  PNPM_USE_COREPACK=true
  run_pnpm --version >/dev/null || fail "Corepack 无法准备 pnpm，请检查网络连接。"
else
  say "正在项目目录中安装 pnpm（不需要管理员权限）..."
  npm install --prefix "$PNPM_TOOLS_DIR" pnpm@11 || fail "pnpm 安装失败，请检查网络连接。"
  PNPM_BIN="$PNPM_TOOLS_DIR/node_modules/.bin/pnpm"
fi

[[ -d "$FRONTEND_DIR" ]] || fail "找不到前端目录：$FRONTEND_DIR"

say "安装前端依赖..."
cd "$FRONTEND_DIR"
run_pnpm install --dangerously-allow-all-builds
cd "$PROJECT_ROOT"

# Escape a value for use inside an AppleScript double-quoted string.
applescript_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '%s' "$value"
}

PROJECT_ESCAPED="$(applescript_escape "$PROJECT_ROOT")"
VENV_ESCAPED="$(applescript_escape "$VENV_DIR")"
FRONTEND_ESCAPED="$(applescript_escape "$FRONTEND_DIR")"
PNPM_BIN_ESCAPED="$(applescript_escape "$PNPM_BIN")"
PNPM_TERMINAL_PREFIX=""
if [[ "$PNPM_USE_COREPACK" == true ]]; then
  PNPM_TERMINAL_PREFIX=" pnpm"
fi

say "启动后端和前端..."

# Open each server in its own Terminal window so their logs remain visible.
osascript <<APPLESCRIPT
tell application "Terminal"
  activate
  do script "cd \"$PROJECT_ESCAPED\" && source \"$VENV_ESCAPED/bin/activate\" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
  do script "cd \"$FRONTEND_ESCAPED\" && \"$PNPM_BIN_ESCAPED\"$PNPM_TERMINAL_PREFIX dev --host 127.0.0.1"
end tell
APPLESCRIPT

# Wait until both servers are really reachable; do not report success too early.
backend_ready=false
frontend_ready=false
say "等待后端和前端启动..."
for attempt in {1..90}; do
  if curl --silent --fail --output /dev/null http://127.0.0.1:8000/openapi.json; then
    backend_ready=true
  fi
  if curl --silent --fail --output /dev/null http://127.0.0.1:5173; then
    frontend_ready=true
  fi
  if [[ "$backend_ready" == true && "$frontend_ready" == true ]]; then
    break
  fi
  sleep 1
done

[[ "$backend_ready" == true ]] || fail "后端未能在 90 秒内启动，请查看新打开的后端 Terminal 窗口。"
[[ "$frontend_ready" == true ]] || fail "前端未能在 90 秒内启动，请查看新打开的前端 Terminal 窗口。"

open "http://127.0.0.1:5173"

say "启动完成。"
echo "前端：http://127.0.0.1:5173"
echo "后端：http://127.0.0.1:8000/docs"
printf '\n按回车键关闭此窗口（不会停止已打开的服务）。'
read -r
