#!/bin/bash

# macOS one-click setup and launcher for the Fall Risk project.
# Double-click this file in Finder (or run: bash deploy/setup_and_run.command).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/full-version"
VENV_DIR="$PROJECT_ROOT/.venv-mac"

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

install_homebrew_if_needed() {
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

    # Homebrew's installer may ask the user to add brew to PATH. Load common locations now.
    if [[ -x /opt/homebrew/bin/brew ]]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
      eval "$(/usr/local/bin/brew shellenv)"
    fi
  else
    fail "请安装 Homebrew，或先自行安装 Python 3 和 Node.js 后重新运行。"
  fi
}

say "开始配置项目环境..."
cd "$PROJECT_ROOT"

install_homebrew_if_needed

if ! command_exists python3; then
  say "正在安装 Python 3..."
  brew install python
fi

if ! command_exists node; then
  say "正在安装 Node.js..."
  brew install node
fi

command_exists python3 || fail "找不到 python3。"
command_exists node || fail "找不到 node。"

say "创建 Python 虚拟环境并安装后端依赖..."
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install \
  "fastapi[standard]" uvicorn pyjwt pydantic sqlalchemy pandas \
  joblib lime numpy python-dotenv gradio aiosqlite "passlib[bcrypt]" \
  scikit-learn xgboost faker openpyxl reportlab

if ! command_exists pnpm; then
  say "正在安装 pnpm..."
  npm install --global pnpm
fi

[[ -d "$FRONTEND_DIR" ]] || fail "找不到前端目录：$FRONTEND_DIR"

say "安装前端依赖..."
cd "$FRONTEND_DIR"
pnpm install --dangerously-allow-all-builds
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

say "启动后端和前端..."

# Open each server in its own Terminal window so their logs remain visible.
osascript <<APPLESCRIPT
tell application "Terminal"
  activate
  do script "cd \"$PROJECT_ESCAPED\" && source \"$VENV_ESCAPED/bin/activate\" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
  do script "cd \"$FRONTEND_ESCAPED\" && pnpm dev"
end tell
APPLESCRIPT

# Give Vite a moment to start before opening the browser.
sleep 3
open "http://localhost:5173"

say "启动完成。"
echo "前端：http://localhost:5173"
echo "后端：http://127.0.0.1:8000/docs"
printf '\n按回车键关闭此窗口（不会停止已打开的服务）。'
read -r
