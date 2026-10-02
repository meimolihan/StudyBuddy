#!/usr/bin/env bash
#
# studybuddy - 多功能Linux学习助手服务(webSSH&webSFTP) 安装脚本
# 将源码构建产物（server + web 前端）安装为 systemd 服务。
# 可重复执行，升级等同于重新安装（覆盖程序并重启服务，数据目录保留）。
#
# Usage:
#   交互式安装（将提示端口与数据目录）:
#     bash scripts/install.sh
#   参数静默安装（-p 端口 / -d 数据目录 / -s 源码目录）:
#     bash scripts/install.sh -p 8082 -d /var/lib/studybuddy /data/studybuddy.repo
#     bash scripts/install.sh -p 8082 -d /var/lib/studybuddy -s /tmp/studybuddy
#   预编译二进制安装（不需要 Node/git）:
#     bash scripts/install.sh -p 8082 -b
#     默认已优先使用二进制（auto）；不指定 -s 且本地无源码时自动下载预编译二进制
#   国内网络可用镜像仓库:
#     STUDYBUDDY_REPO=https://ghfast.top/https://github.com/meimolihan/studybuddy.git bash scripts/install.sh -y

set -euo pipefail

# ================== terminal colors ==================
list_color_init() {
    export gl_hui=$'\033[38;5;59m'
    export gl_hong=$'\033[38;5;9m'
    export gl_lv=$'\033[38;5;10m'
    export gl_huang=$'\033[38;5;11m'
    export gl_lan=$'\033[38;5;32m'
    export gl_bai=$'\033[38;5;15m'
    export gl_zi=$'\033[38;5;13m'
    export gl_bufan=$'\033[38;5;14m'
    export reset=$'\033[0m'
}
list_color_init

sep_line() {
  printf '%s' "$gl_bufan"
  printf '—%.0s' {1..32}
  printf '%s\n' "$reset"
}

section() {
  printf "  %s %s\n" "${gl_zi}▶${reset}" "$1"
}

ok() {
  printf "  %s %s\n" "${gl_lv}>>>${reset}" "$1"
}

skip() {
  printf "  %s %s\n" "${gl_hui}--${reset}" "$1"
}

print_banner() {
  local z="$gl_zi" r="$reset" b="$gl_bai" l="$gl_lan"
  printf '%s\n' \
    "" \
    "  ${z}┌─────────────────────────────────────────┐${r}" \
    "  ${z}│${r}   ${b}studybuddy${r}  ${l}学习助手服务 · 安装${r}     ${z}│${r}" \
    "  ${z}└─────────────────────────────────────────┘${r}" \
    ""
}

error() { printf "  %s %s\n" "${gl_hong}[错误]${reset}" "$1" >&2; exit 1; }

# ================== customize me ==================
APP_NAME="studybuddy"
DEFAULT_PORT=8082
APP_DIR="/var/lib/${APP_NAME}"
DEFAULT_DATA_DIR="${APP_DIR}/app/db"
CONFIG_FILE="/etc/${APP_NAME}.conf"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
CLI_BIN="/usr/local/bin/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-}")" && pwd)"
DEFAULT_SRC_DIR="${SCRIPT_DIR}/.."
MIN_NODE_MAJOR=18
GITHUB_REPO="https://github.com/meimolihan/studybuddy.git"
GITHUB_BIN_REPO="meimolihan/studybuddy"

# ================== GitHub 下载加速镜像 ==================
# 原始 GitHub 地址超时/失败时，按下列顺序依次尝试（末尾必须带斜杠）
GITHUB_MIRRORS=(
  "https://ghfast.top/"
  "https://ghproxy.net/"
  "https://gh.xxooo.cf/"
  "https://v6.gh-proxy.org/"
  "https://githubproxy.cc/"
)
# v6.gh-proxy.org 为纯 IPv6 代理：本机未配置 IPv6 地址时剔除，避免每次空等超时
if [ ! -s /proc/net/if_inet6 ]; then
  _no_v6=()
  for _m in "${GITHUB_MIRRORS[@]}"; do
    case "${_m}" in
      *v6.gh-proxy.org*) continue ;;
    esac
    _no_v6+=("${_m}")
  done
  GITHUB_MIRRORS=("${_no_v6[@]}")
fi

# 根据原始 GitHub URL 生成候选地址列表：原始地址优先，然后依次套用各镜像
make_url_candidates() {
  local github_url="$1"
  local p
  printf '%s\n' "$github_url"
  for p in "${GITHUB_MIRRORS[@]}"; do
    printf '%s\n' "${p}${github_url}"
  done
}
# ==========================================================

# 经 curl|bash 远程执行时，SCRIPT_DIR 指向 bash 抽取的临时目录，本地源码仓库
# 需按常见目录回退探测（当前目录 / 上一级目录 / 上级的上级），否则会误判"无本地源码"。
resolve_local_src() {
  local candidates=(
    "${SCRIPT_DIR:-}/.."
    "$(pwd)"
    "$(pwd)/.."
    "$(dirname "$(pwd)")"
    "$(dirname "$(dirname "$(pwd)")")"
  )
  for c in "${candidates[@]}"; do
    if [ -f "${c}/go.mod" ] || [ -d "${c}/cmd" ]; then
      printf '%s' "${c}"
      return 0
    fi
  done
  return 1
}

is_valid_src() {
  [ -f "$1/go.mod" ] || [ -d "$1/cmd" ]
}
# ==================================================

PORT=""
DATA_DIR=""
SRC_DIR=""
SRC_DIR_EXPLICIT=0
BINARY_MODE="auto"
INSTALL_YES=0

# ---- bootstrap: support `bash -c "$(curl ...)" -p ... -d ...` ----
case "$0" in
  -*) set -- "$0" "$@" ;;
esac

# ---- parse command-line args (silent install) ----
while [ "$#" -gt 0 ]; do
  case "$1" in
    -p|--port)
      shift
      [ -n "${1:-}" ] || error "缺少 -p/--port 的值"
      PORT="$1"
      ;;
    -d|--data)
      shift
      [ -n "${1:-}" ] || error "缺少 -d/--data 的值"
      DATA_DIR="$1"
      ;;
    -s|--src)
      shift
      [ -n "${1:-}" ] || error "缺少 -s/--src 的值"
      SRC_DIR="$1"
      SRC_DIR_EXPLICIT=1
      ;;
    -b|--binary)
      BINARY_MODE="force"
      ;;
    -y|--yes)
      INSTALL_YES=1
      ;;
    -h|--help)
      printf "%s\n" "${gl_lan}studybuddy${reset} - ${gl_bai}多功能Linux学习助手服务(webSSH&webSFTP) 安装脚本${reset}"
      printf "  %-13s %s\n" "${gl_bai}用法:${reset}" "bash scripts/install.sh [-p PORT] [-d DATA_DIR] [-s SRC] [-b] [-y]"
      printf "  %-13s %s\n" "${gl_bai}-p, --port${reset}" "监听端口（默认 ${gl_lan}${DEFAULT_PORT}${reset}）"
      printf "  %-13s %s\n" "${gl_bai}-d, --data${reset}" "数据目录（默认 ${gl_lan}${DEFAULT_DATA_DIR}${reset}）"
      printf "  %-13s %s\n" "${gl_bai}-s, --src${reset}" "源码仓库路径（默认 ${gl_lan}${DEFAULT_SRC_DIR}${reset}）"
      printf "  %-13s %s\n" "${gl_bai}-b, --binary${reset}" "强制使用预编译二进制安装（无需 Node.js/git）"
      printf "  %-13s %s\n" "${gl_bai}-y, --yes${reset}" "免交互，未指定项全部使用默认值"
      printf "  %-13s %s\n" "${gl_bai}-h, --help${reset}" "显示本帮助"
      printf "%s\n" "${gl_hui}指定任意参数即进入静默安装；不带参数则为交互式安装。${reset}"
      printf "%s\n" "${gl_hui}默认优先下载 GitHub Releases 预编译二进制（无需 Node/npm/git）；可用 STUDYBUDDY_VERSION 指定版本号（默认 latest）。${reset}"
      printf "%s\n" "${gl_hui}未指定 -b 且本地存在源码仓库（含 -s 显式指定）时，仍按源码编译安装。${reset}"
      printf "%s\n" "${gl_hui}国内网络可设 STUDYBUDDY_REPO 自定义仓库或镜像地址，如 STUDYBUDDY_REPO=https://ghfast.top/https://github.com/meimolihan/studybuddy.git${reset}"
      printf "%s\n" "${gl_hui}首次运行的用户名/密码为随机生成，请查看服务日志：journalctl -u studybuddy -n 50${reset}"
      exit 0
      ;;
    *)
      error "未知参数: $1（使用 -h 查看帮助）"
      ;;
  esac
  shift
done

# ---- firewall: automatically open the listen port ----
FW_OPENED="n"
open_firewall_port() {
  local PORT="$1"
  if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
    if ! firewall-cmd --query-port="${PORT}/tcp" >/dev/null 2>&1; then
      firewall-cmd --permanent --add-port="${PORT}/tcp" >/dev/null 2>&1 || true
      firewall-cmd --reload >/dev/null 2>&1 || true
    fi
    ok "已通过 ${gl_bai}firewalld${reset} 开放端口 ${gl_lan}${PORT}/tcp${reset}"
    FW_OPENED="y"
    return 0
  fi

  if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
    if ! ufw status 2>/dev/null | grep -q "${PORT}/tcp"; then
      ufw allow "${PORT}/tcp" >/dev/null 2>&1 || true
    fi
    ok "已通过 ${gl_bai}ufw${reset} 开放端口 ${gl_lan}${PORT}/tcp${reset}"
    FW_OPENED="y"
    return 0
  fi

  if command -v iptables >/dev/null 2>&1; then
    if iptables -C INPUT -p tcp --dport "${PORT}" -j ACCEPT >/dev/null 2>&1; then
      ok "端口 ${gl_lan}${PORT}/tcp${reset} 已在 iptables 中放行"
      FW_OPENED="y"
      return 0
    fi
    if iptables -L INPUT -n 2>/dev/null | grep -qE 'policy (DROP|REJECT)|REJECT|DROP'; then
      if iptables -I INPUT -p tcp --dport "${PORT}" -j ACCEPT >/dev/null 2>&1; then
        ok "已通过 ${gl_bai}iptables${reset} 开放端口 ${gl_lan}${PORT}/tcp${reset}"
        FW_OPENED="y"
        return 0
      fi
    fi
  fi
  printf "  %s %s\n" "${gl_huang}[提示]${reset}" "未检测到活跃的防火墙（firewalld/ufw/iptables），跳过端口开放。"
}

[ "$(id -u)" != "0" ] && error "请以 root 身份运行（例如 sudo bash scripts/install.sh）"

print_banner
sep_line
section "安装信息"
printf "  %-14s %s\n" "${gl_lan}系统${reset}" "$(uname -s) $(uname -m)"
printf "  %-14s %s\n" "${gl_lan}程序${reset}" "${gl_bai}${APP_NAME}${reset}"
sep_line

# ---- Node 运行时检查（仅源码安装需要）----
check_node_runtime() {
  if ! command -v node >/dev/null 2>&1; then
    error "未检测到 Node.js，请先安装（要求 >= v${MIN_NODE_MAJOR}），例如：apt install nodejs npm / 或使用 nvm/官方安装包"
  fi
  NODE_MAJOR="$(node -e 'console.log(process.versions.node.split(".")[0])' 2>/dev/null || echo 0)"
  if [ "${NODE_MAJOR}" -lt "${MIN_NODE_MAJOR}" ]; then
    error "Node.js 版本过低（当前 $(node -v)），要求 >= v${MIN_NODE_MAJOR}"
  fi
  NPM_CMD="$(command -v npm || true)"
  if [ -z "${NPM_CMD}" ]; then
    error "未检测到 npm，Node.js 安装异常，请检查安装。"
  fi
  INSTALL_TOOL="npm"
  if command -v yarn >/dev/null 2>&1; then
    INSTALL_TOOL="yarn"
  fi
  ok "Node.js $(node -v) / 包管理器 ${gl_bai}${INSTALL_TOOL}${reset}"
}

# ---- 安装方式判定：二进制优先，可回退源码 ----
INSTALL_METHOD="source"
BIN_PATH="${APP_DIR}/studybuddy"
BIN_VER=""
local_src="$(resolve_local_src)" || true
if [ "${BINARY_MODE}" = "force" ]; then
  INSTALL_METHOD="binary"
elif [ "${SRC_DIR_EXPLICIT}" = "1" ]; then
  INSTALL_METHOD="source"
elif [ -n "${local_src}" ] && is_valid_src "${local_src}"; then
  INSTALL_METHOD="source"
elif [ -z "${PORT}" ] && [ "${INSTALL_YES}" != "1" ] && [ -t 0 ]; then
  read -r -p "${gl_bai}安装方式${reset}: ${gl_hui}[1] 预编译二进制(无需Node) [2] 源码编译 [默认: 1]${reset} " METHOD_CHOICE
  case "${METHOD_CHOICE}" in
    2|2*) INSTALL_METHOD="source" ;;
    *) INSTALL_METHOD="binary" ;;
  esac
else
  INSTALL_METHOD="binary"
fi

if [ "${INSTALL_METHOD}" = "binary" ]; then
  ok "安装方式：${gl_lan}预编译二进制${reset}（单文件，无需 Node.js/npm/git）"
else
  ok "安装方式：${gl_lan}源码编译${reset}"
  check_node_runtime
fi

# ---- 下载并部署预编译二进制（standalone 面板 + CLI，内置前端）----
install_binary() {
  local arch="" name="" tag="${STUDYBUDDY_VERSION:-latest}" url_path="" tmp="" hdr="" magic="" url=""
  case "$(uname -m)" in
    x86_64|amd64) arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    *)
      printf "  %s\n" "${gl_huang}[警告]${reset} 架构 $(uname -m) 无预编译二进制（仅 amd64/arm64），请使用源码安装。"
      return 1
      ;;
  esac
  name="studybuddy_linux_${arch}"
  if [ "${tag}" = "latest" ]; then
    url_path="releases/latest/download/${name}"
  else
    case "${tag}" in v*) ;; *) tag="v${tag}" ;; esac
    url_path="releases/download/${tag}/${name}"
  fi
  BIN_VER="${tag}"
  ok "下载预编译二进制 ${gl_bai}${name}${reset}（版本 ${gl_lan}${tag}${reset}）"

  if command -v curl >/dev/null 2>&1; then
    DL_CURL="y"
  elif command -v wget >/dev/null 2>&1; then
    DL_CURL="n"
  else
    printf "  %s\n" "${gl_huang}[警告]${reset} 未检测到 curl/wget，无法下载二进制。"
    return 1
  fi

  tmp="$(mktemp)"
  hdr="${tmp}.hdr"

  # 候选地址：原始 GitHub + 各镜像（顺序由 GITHUB_MIRRORS 决定）
  local candidates=()
  mapfile -t candidates < <(make_url_candidates "https://github.com/${GITHUB_BIN_REPO}/${url_path}")

  for url in "${candidates[@]}"; do
    skip "尝试下载 ${gl_bai}${url}${reset}"
    # 换链接 = 换源，清掉旧文件，避免残留文件污染判断
    rm -f "${tmp}" "${hdr}"
    DL_FAIL="n"
    if [ "${DL_CURL}" = "y" ]; then
      if command -v timeout >/dev/null 2>&1; then
        timeout 120 curl -fsSL --connect-timeout 10 --max-time 120 \
          -o "${tmp}" -D "${hdr}" "${url}" 2>/dev/null || DL_FAIL="y"
      else
        curl -fsSL --connect-timeout 10 --max-time 120 \
          -o "${tmp}" -D "${hdr}" "${url}" 2>/dev/null || DL_FAIL="y"
      fi
    else
      wget -qO "${tmp}" --timeout=120 --tries=1 "${url}" 2>/dev/null || DL_FAIL="y"
    fi

    if [ "${DL_FAIL}" = "y" ] || [ ! -s "${tmp}" ]; then
      printf "  %s\n" "${gl_huang}[警告]${reset}" "下载失败：${url}"
      continue
    fi

    # 大小核对：镜像/Cache 可能返回被截断的残缺文件（curl 认为传输正常）
    if [ "${DL_CURL}" = "y" ] && [ -f "${hdr}" ]; then
      expected="$(grep -i '^content-length:' "${hdr}" | tail -n 1 | tr -d '\r' | awk '{print $2}')"
      actual="$(stat -c%s "${tmp}" 2>/dev/null || echo 0)"
      if [ -n "${expected}" ] && [ "${actual}" != "${expected}" ]; then
        printf "  %s\n" "${gl_huang}[警告]${reset} 文件不完整（${actual}/${expected} 字节），跳过该源。"
        continue
      fi
    fi

    magic="$(head -c4 "${tmp}" | od -An -tx1 | tr -d ' \n')"
    if [ "${magic}" != "7f454c46" ]; then
      printf "  %s\n" "${gl_huang}[警告]${reset} 下载内容不是可执行程序，跳过该源。"
      continue
    fi

    # 运行自检：损坏/截断的 yao-pkg 快照在执行 version 时会报 Pkg 错误
    chmod +x "${tmp}"
    if ! "${tmp}" version >/dev/null 2>&1; then
      printf "  %s\n" "${gl_huang}[警告]${reset} 二进制自检失败（损坏或非 yao-pkg 快照），跳过该源。"
      continue
    fi

    mkdir -p "${APP_DIR}"
    cp -f "${tmp}" "${BIN_PATH}"
    chmod +x "${BIN_PATH}"
    rm -f "${tmp}" "${hdr}"
    ok "二进制已安装至 ${gl_bai}${BIN_PATH}${reset}"

    # 二进制部署同样下发运维脚本（面板"备份/还原"依赖），失败仅告警不阻断安装
    mkdir -p "${APP_DIR}/scripts" 2>/dev/null || true
    local script_name="" raw_url=""
    for script_name in studybuddy_backup.sh studybuddy_recover.sh; do
      local raw_candidates=()
      mapfile -t raw_candidates < <(make_url_candidates "https://github.com/${GITHUB_BIN_REPO}/raw/main/scripts/${script_name}")
      for raw_url in "${raw_candidates[@]}"; do
        DL_OK="n"
        if [ "${DL_CURL}" = "y" ]; then
          curl -fsSL --connect-timeout 10 --max-time 60 "${raw_url}" > "${APP_DIR}/scripts/${script_name}" 2>/dev/null && DL_OK="y"
        else
          wget -qO "${APP_DIR}/scripts/${script_name}" --timeout=60 --tries=1 "${raw_url}" 2>/dev/null && DL_OK="y"
        fi
        if [ "${DL_OK}" = "y" ] && [ -s "${APP_DIR}/scripts/${script_name}" ] \
          && grep -q '^#!/bin/bash' "${APP_DIR}/scripts/${script_name}"; then
          chmod +x "${APP_DIR}/scripts/${script_name}"
          ok "已下发运维脚本 ${gl_bai}${script_name}${reset}"
          break
        fi
        rm -f "${APP_DIR}/scripts/${script_name}"
      done
    done
    return 0
  done
  rm -f "${tmp}" "${hdr}"
  printf "  %s\n" "${gl_huang}[警告]${reset} 所有源均下载失败/校验未通过，回退源码安装。"
  return 1
}

# ---- silent install detection ----
SILENT="n"
if [ -n "${PORT}" ]; then
  case "${PORT}" in
    ''|*[!0-9]*) error "PORT 无效（需为 1‑65535 的数字）: ${PORT}" ;;
    *) [ "${PORT}" -ge 1 ] && [ "${PORT}" -le 65535 ] || error "PORT 超出范围（1‑65535）: ${PORT}" ;;
  esac
  SILENT="y"
fi
if [ -n "${DATA_DIR}" ]; then
  SILENT="y"
fi
if [ -n "${SRC_DIR}" ]; then
  SILENT="y"
fi
if [ ! -t 0 ]; then
  SILENT="y"
fi

section "配置参数"
# port prompt
if [ -z "${PORT}" ]; then
  if [ "$INSTALL_YES" = "1" ] || [ ! -t 0 ]; then
    PORT="${DEFAULT_PORT}"
  else
    while :; do
      read -r -p "${gl_bai}请输入监听端口${reset} ${gl_hui}[默认: ${DEFAULT_PORT}]${reset}: " PORT
      PORT="${PORT:-$DEFAULT_PORT}"
      case "$PORT" in
        ''|*[!0-9]*) printf "  %s\n" "${gl_huang}端口无效，请重新输入。${reset}" ;;
        *)
          if [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ]; then break; fi
          printf "  %s\n" "${gl_huang}端口超出范围（1‑65535），请重新输入。${reset}"
          ;;
      esac
    done
  fi
else
  printf "  %-14s %s\n" "${gl_lan}监听端口${reset}" "${gl_bai}${PORT}${reset}（参数指定）"
fi
PORT="${PORT:-$DEFAULT_PORT}"

# data dir prompt
if [ -z "${DATA_DIR}" ]; then
  if [ "$INSTALL_YES" = "1" ] || [ ! -t 0 ]; then
    DATA_DIR="${DEFAULT_DATA_DIR}"
  else
    read -r -p "${gl_bai}请输入数据目录${reset} ${gl_hui}[默认: ${DEFAULT_DATA_DIR}]${reset}: " DATA_DIR
    DATA_DIR="${DATA_DIR:-$DEFAULT_DATA_DIR}"
  fi
else
  printf "  %-14s %s\n" "${gl_lan}数据目录${reset}" "${gl_bai}${DATA_DIR}${reset}（参数指定）"
fi

# 数据目录不得与安装目录相同，否则 app/db 软链将自引用（环形），自动纠正为 app/db
if [ "${DATA_DIR}" = "${APP_DIR}" ] || [ "${DATA_DIR}" = "${APP_DIR}/" ]; then
  printf "  %s\n" "${gl_huang}[提示]${reset} 数据目录不能与安装目录相同，已自动使用 ${gl_bai}${APP_DIR}/app/db${reset}"
  DATA_DIR="${APP_DIR}/app/db"
fi
DATA_DIR="${DATA_DIR:-$DEFAULT_DATA_DIR}"

# source repo / binary install
if [ "${INSTALL_METHOD}" = "binary" ]; then
  if ! install_binary; then
    if [ "${BINARY_MODE}" = "force" ]; then
      error "二进制安装失败（-b 强制二进制模式），可用 -s 指定源码目录重新安装"
    fi
    printf "  %s\n" "${gl_huang}[警告]${reset} 预编译二进制获取失败，回退为源码编译安装。"
    INSTALL_METHOD="source"
    check_node_runtime
  fi
fi

if [ "${INSTALL_METHOD}" = "source" ]; then
  SRC_DIR="${SRC_DIR:-$DEFAULT_SRC_DIR}"
  if ! is_valid_src "${SRC_DIR}"; then
    if [ "${SRC_DIR_EXPLICIT}" != "1" ]; then
      DISCOVERED_SRC="$(resolve_local_src)" || true
      if [ -n "${DISCOVERED_SRC:-}" ]; then
        ok "已从仓库目录发现本地源码 ${gl_bai}${DISCOVERED_SRC}${reset}"
        SRC_DIR="${DISCOVERED_SRC}"
      fi
    fi
  fi
  if ! is_valid_src "${SRC_DIR}"; then
    if [ "${SRC_DIR_EXPLICIT}" = "1" ]; then
      error "未找到源码仓库 ${SRC_DIR}（-s 显式指定，需包含 server/ 与 web/ 目录）"
    fi
    ok "本地无源码仓库，尝试获取源码（可用环境变量 STUDYBUDDY_REPO 自定义仓库地址）"
    TMP_ROOT="$(mktemp -d)"
    TMP_SRC="${TMP_ROOT}/studybuddy"

    # 候选仓库源：自定义 > 原始 GitHub > 各镜像
    REPO_CANDIDATES=()
    [ -n "${STUDYBUDDY_REPO:-}" ] && REPO_CANDIDATES+=("${STUDYBUDDY_REPO}")
    while IFS= read -r u; do
      REPO_CANDIDATES+=("$u")
    done < <(make_url_candidates "${GITHUB_REPO}")

    FETCHED="n"
    if command -v timeout >/dev/null 2>&1; then CLONE_TIMEOUT="timeout 90"; else CLONE_TIMEOUT=""; fi

    if command -v git >/dev/null 2>&1; then
      for repo in "${REPO_CANDIDATES[@]}"; do
        [ -n "${repo}" ] || continue
        skip "尝试 git clone ${gl_bai}${repo}${reset}"
        if ${CLONE_TIMEOUT} git clone --depth=1 "${repo}" "${TMP_SRC}" 2>"${TMP_ROOT}/clone.err"; then
          FETCHED="y"
          break
        fi
        printf "  %s %s\n" "${gl_huang}[警告]${reset}" "克隆失败：$(tail -n 1 "${TMP_ROOT}/clone.err" 2>/dev/null)"
        rm -rf "${TMP_SRC}"
      done
    else
      printf "  %s %s\n" "${gl_huang}[警告]${reset}" "未检测到 git，跳过 git clone，改用源码压缩包"
    fi

    # 回退：下载源码压缩包并解压（无需 git，走与脚本下载一致的加速线路）
    if [ "${FETCHED}" != "y" ]; then
      ARCHIVE_URLS=()
      while IFS= read -r u; do
        ARCHIVE_URLS+=("$u")
      done < <(make_url_candidates "https://github.com/meimolihan/studybuddy/archive/refs/heads/main.tar.gz")
      # 兜底：codeload 直链
      ARCHIVE_URLS+=("https://codeload.github.com/meimolihan/studybuddy/tar.gz/refs/heads/main")

      if command -v curl >/dev/null 2>&1; then
        DL_CMD="curl -fsSL --connect-timeout 10 --max-time 120"
      elif command -v wget >/dev/null 2>&1; then
        DL_CMD="wget -qO- --timeout=120 --tries=1"
      else
        DL_CMD=""
      fi
      for url in "${ARCHIVE_URLS[@]}"; do
        [ -n "${url}" ] || continue
        [ -n "${DL_CMD}" ] || break
        skip "尝试下载源码包 ${gl_bai}${url}${reset}"
        TMP_TGZ="${TMP_ROOT}/src.tar.gz"
        if ${DL_CMD} "${url}" > "${TMP_TGZ}" 2>/dev/null \
          && tar -xzf "${TMP_TGZ}" -C "${TMP_ROOT}" 2>/dev/null; then
          EXTRACTED="$(find "${TMP_ROOT}" -maxdepth 1 -type d -name 'studybuddy-*' -print -quit 2>/dev/null)"
          if [ -n "${EXTRACTED}" ]; then
            mv "${EXTRACTED}" "${TMP_SRC}"
            FETCHED="y"
            break
          fi
        fi
        printf "  %s %s\n" "${gl_huang}[警告]${reset}" "下载失败：${url}"
        rm -f "${TMP_TGZ}"
      done
    fi

    [ "${FETCHED}" = "y" ] || error "获取源码仓库失败，请检查服务器网络，或使用 -s 指定本地源码目录"
    SRC_DIR="${TMP_SRC}"
    ok "已获取源码仓库"
  fi
fi

if command -v systemctl >/dev/null 2>&1; then
  USE_SYSTEMD="y"
else
  USE_SYSTEMD="n"
  printf "  %s\n" "${gl_huang}[警告]${reset} 未检测到 systemd（容器或受限环境）。"
  printf "  %s\n" "${gl_hui}    已回退为后台运行模式，重启或崩溃后服务不会自动恢复。${reset}"
fi

sep_line
section "安装程序"
ok "正在安装 ${gl_bai}${APP_NAME}${reset} 程序 ${gl_hong}.${gl_huang}.${gl_lv}.${gl_bai}"

if [ "${INSTALL_METHOD}" = "binary" ]; then
  ok "使用预编译二进制：${gl_bai}${BIN_PATH}${reset}（版本 ${gl_lan}${BIN_VER}${reset}）"
else
  # 1) 拷贝 server 源码到安装目录
  mkdir -p "${APP_DIR}"
  rm -f "${APP_DIR}/app/db"
  cp -rf "${SRC_DIR}/server/." "${APP_DIR}/"
  rm -f "${APP_DIR}/.env"
  ok "已拷贝服务端源码至 ${gl_bai}${APP_DIR}${reset}"

  # 1.1) 拷贝运维脚本（备份/还原脚本供面板"服务管理"调用，也便于手动执行）
  if [ -d "${SRC_DIR}/scripts" ]; then
    mkdir -p "${APP_DIR}/scripts"
    cp -rf "${SRC_DIR}/scripts/." "${APP_DIR}/scripts/"
    chmod +x "${APP_DIR}"/scripts/*.sh 2>/dev/null || true
    ok "已部署运维脚本至 ${gl_bai}${APP_DIR}/scripts${reset}"
  fi

  # 2) 安装服务端生产依赖
  ok "正在安装服务端依赖（${INSTALL_TOOL}） ${gl_hong}.${gl_huang}.${gl_lv}.${gl_bai}"
  if [ "${INSTALL_TOOL}" = "yarn" ]; then
    ( cd "${APP_DIR}" && yarn install --production --non-interactive >/dev/null )
  else
    ( cd "${APP_DIR}" && npm install --omit=dev --no-audit --no-fund >/dev/null )
  fi
  ok "服务端依赖安装完成"

  # 3) 构建 web 前端
  ok "正在构建 web 前端 ${gl_hong}.${gl_huang}.${gl_lv}.${gl_bai}"
  if [ "${INSTALL_TOOL}" = "yarn" ]; then
    ( cd "${SRC_DIR}/web" && yarn install --non-interactive >/dev/null && yarn build >/dev/null )
  else
    ( cd "${SRC_DIR}/web" && npm install --no-audit --no-fund >/dev/null && npm run build >/dev/null )
  fi
  mkdir -p "${APP_DIR}/app/static"
  cp -rf "${SRC_DIR}/web/dist/." "${APP_DIR}/app/static/"
  ok "前端构建完成，已部署至 ${gl_bai}${APP_DIR}/app/static${reset}"
fi

# 4) 数据目录 & 软链接（数据与程序分离，便于备份/还原）
mkdir -p "${APP_DIR}/app"
rm -rf "${APP_DIR}/app/db"
mkdir -p "${DATA_DIR}"
if [ "${DATA_DIR}" != "${APP_DIR}/app/db" ]; then
  ln -s "${DATA_DIR}" "${APP_DIR}/app/db"
fi
chmod 700 "${DATA_DIR}"
ok "数据目录 ${gl_lan}${DATA_DIR}${reset} 已就绪（app/db $( [ "${DATA_DIR}" = "${APP_DIR}/app/db" ] && echo "即为数据目录" || echo "软链至数据目录" )）"

# 5) 安装记录
mkdir -p "$(dirname "${CONFIG_FILE}")"
if [ "${INSTALL_METHOD}" = "binary" ]; then
  cat > "${CONFIG_FILE}" <<EOF
# ${APP_NAME} 安装记录（由 install.sh 生成，请勿手动修改）
APP_DIR=${APP_DIR}
PORT=${PORT}
DATA_DIR=${DATA_DIR}
BACKUP_DIR=${APP_DIR}/backup
INSTALL_METHOD=binary
BIN_PATH=${BIN_PATH}
VERSION=${BIN_VER}
EOF
else
  cat > "${CONFIG_FILE}" <<EOF
# ${APP_NAME} 安装记录（由 install.sh 生成，请勿手动修改）
APP_DIR=${APP_DIR}
PORT=${PORT}
DATA_DIR=${DATA_DIR}
BACKUP_DIR=${APP_DIR}/backup
INSTALL_METHOD=source
NODE_BIN=$(command -v node)
EOF
fi
chmod 0644 "${CONFIG_FILE}"
ok "已写入安装记录 ${gl_bai}${CONFIG_FILE}${reset}"

# 6) 安装内置 CLI 命令
mkdir -p "$(dirname "${CLI_BIN}")"
if [ "${INSTALL_METHOD}" = "binary" ]; then
  rm -f "${CLI_BIN}"
  ln -s "${BIN_PATH}" "${CLI_BIN}"
else
  cat > "${CLI_BIN}" <<CLI
#!/bin/sh
exec "$(command -v node)" "${APP_DIR}/bin/studybuddy.js" "\$@"
CLI
  chmod +x "${CLI_BIN}"
fi
ok "已安装命令 ${gl_bai}${CLI_BIN}${reset}（运行 ${gl_bai}${APP_NAME} help${reset} 查看用法）"

sep_line
section "启动服务"
if [ "${USE_SYSTEMD}" = "y" ]; then
  if [ "${INSTALL_METHOD}" = "binary" ]; then
    EXEC_START="${BIN_PATH}"
  else
    EXEC_START="$(command -v node) ${APP_DIR}/index.js"
  fi
  cat > "${SERVICE_FILE}" <<UNIT
[Unit]
Description=${APP_NAME} - 多功能Linux学习助手服务(webSSH&webSFTP)
After=network-online.target local-fs.target
Wants=network-online.target

[Service]
Type=simple
# KillMode=process：systemctl stop 只终止主 node 进程，不波及面板 spawn 的备份/还原脚本
KillMode=process
ExecStart=${EXEC_START}
WorkingDirectory=${APP_DIR}
Environment=HTTP_PORT=${PORT}
Environment=DEBUG=true
Environment=GUACD_HOST=127.0.0.1
Environment=GUACD_PORT=4822
Environment=TZ=Asia/Shanghai
Restart=on-failure
RestartSec=3
# 面板 stop 缓慢时快速收敛，避免备份/还原时 systemctl stop 长时间阻塞
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
UNIT

  systemctl daemon-reload
  systemctl enable "${APP_NAME}" >/dev/null 2>&1 || true
  systemctl restart "${APP_NAME}"
  sleep 3
  if systemctl is-active "${APP_NAME}" >/dev/null 2>&1; then
    ok "${gl_bai}${APP_NAME}${reset} 服务已启动。"
    systemctl status "${APP_NAME}" --no-pager || true
  else
    printf "  %s\n" "${gl_hong}[错误]${reset} 服务启动失败，请检查：${gl_bai}journalctl -u ${APP_NAME} -n 50${reset}" >&2
    exit 1
  fi
else
  if [ "${INSTALL_METHOD}" = "binary" ]; then
    PROC_PATTERN="${BIN_PATH}"
    RUN_CMD=("${BIN_PATH}")
  else
    PROC_PATTERN="${APP_DIR}/index.js"
    RUN_CMD=(node "${APP_DIR}/index.js")
  fi
  if command -v pgrep >/dev/null 2>&1 && pgrep -f "${PROC_PATTERN}" >/dev/null 2>&1; then
    printf "  %s\n" "${gl_huang}[警告]${reset} 检测到 ${APP_NAME} 进程可能已在运行"
  else
    env HTTP_PORT="${PORT}" \
        DEBUG=true \
        GUACD_HOST=127.0.0.1 \
        GUACD_PORT=4822 \
        nohup "${RUN_CMD[@]}" >> "${DATA_DIR}/${APP_NAME}.log" 2>&1 &
    ok "${APP_NAME} 已在后台启动，pid: ${gl_bai}$!${reset}"
  fi
fi

# 提取并打印首次初始化生成的随机账号密码（数据目录已存在时不会重新生成）
print_initial_credentials() {
  local user="" pass="" creds="" keydb="${DATA_DIR}/key.db"
  # 权威来源：直接从数据库读取（避免 journal 残留多次安装的历史凭据，导致打印错误账号）
  if [ -f "${keydb}" ]; then
    user="$(grep -o '"user":"[^"]*"' "${keydb}" 2>/dev/null | head -n 1 | cut -d'"' -f4)"
    pass="$(grep -o '"initPassword":"[^"]*"' "${keydb}" 2>/dev/null | head -n 1 | cut -d'"' -f4)"
  fi
  if [ -z "${user}" ] && [ -z "${pass}" ]; then
    # 兜底：无 initPassword 字段的旧版本数据库，回退日志提取
    if [ "${USE_SYSTEMD}" = "y" ]; then
      command -v journalctl >/dev/null 2>&1 && \
        creds="$(journalctl -u "${APP_NAME}" --no-pager -n 300 2>/dev/null | grep -E '用户名:|密码:' | tail -n 2)"
    fi
    if [ -z "${creds}" ] && [ -f "${DATA_DIR}/${APP_NAME}.log" ]; then
      creds="$(grep -E '用户名:|密码:' "${DATA_DIR}/${APP_NAME}.log" 2>/dev/null | tail -n 2)"
    fi
    user="$(printf '%s\n' "${creds}" | sed -n 's/.*用户名:[[:space:]]*//p' | tail -n 1 | sed 's/[[:space:]║]*$//' | tr -d '\r')"
    pass="$(printf '%s\n' "${creds}" | sed -n 's/.*密码:[[:space:]]*//p' | tail -n 1 | sed 's/[[:space:]║]*$//' | tr -d '\r')"
  fi
  [ -n "${user}" ] && [ -n "${pass}" ] || return 1
  printf "  %s\n" "${gl_lv}✔ 首次登录凭据（请登录后立即修改）${reset}"
  printf "  %-14s %s\n" "${gl_lan}用户名${reset}" "${gl_bai}${user}${reset}"
  printf "  %-14s %s\n" "${gl_lan}密码${reset}" "${gl_bai}${pass}${reset}"
  return 0
}

# 取第一个IPv4
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "${IP}" ] && IP="<服务器IP>"

open_firewall_port "${PORT}"

if [ "${FW_OPENED}" = "y" ]; then
  FW_STATUS="${gl_lv}已开放 ${PORT}/tcp${reset}"
else
  FW_STATUS="${gl_huang}未检测到活跃防火墙，已跳过${reset}"
fi

if [ "${INSTALL_METHOD}" = "binary" ]; then
  METHOD_LABEL="预编译二进制 v${BIN_VER#v}"
else
  METHOD_LABEL="源码编译"
fi
sep_line
if [ "${USE_SYSTEMD}" = "y" ]; then
  printf "  %s\n" "${gl_lv}✔ ${APP_NAME} 安装成功！${reset}"
  printf "  %-14s %s\n" "${gl_lan}访问地址${reset}" "${gl_bai}http://${IP}:${PORT}${reset}"
  printf "  %-14s %s\n" "${gl_lan}数据目录${reset}" "${gl_bai}${DATA_DIR}${reset}"
  printf "  %-14s %s\n" "${gl_lan}程序目录${reset}" "${gl_bai}${APP_DIR}${reset}"
  printf "  %-14s %s\n" "${gl_lan}安装方式${reset}" "${gl_bai}${METHOD_LABEL}${reset}"
  printf "  %-14s %s\n" "${gl_lan}防火墙状态${reset}" "$FW_STATUS"
  printf "  %-14s %s\n" "${gl_lan}运行模式${reset}" "${gl_bai}systemd 服务${reset}"
  printf "  %-14s %s\n" "${gl_lan}服务命令${reset}" "${gl_hui}systemctl status ${APP_NAME}${reset}"
  printf "  %-14s %s\n" "${gl_lan}升级方式${reset}" "${gl_hui}重新执行 scripts/install.sh（数据自动保留）${reset}"
else
  printf "  %s\n" "${gl_lv}✔ ${APP_NAME} 安装成功！${reset} ${gl_huang}（后台运行模式）${reset}"
  printf "  %-14s %s\n" "${gl_lan}访问地址${reset}" "${gl_bai}http://${IP}:${PORT}${reset}"
  printf "  %-14s %s\n" "${gl_lan}数据目录${reset}" "${gl_bai}${DATA_DIR}${reset}"
  printf "  %-14s %s\n" "${gl_lan}程序目录${reset}" "${gl_bai}${APP_DIR}${reset}"
  printf "  %-14s %s\n" "${gl_lan}安装方式${reset}" "${gl_bai}${METHOD_LABEL}${reset}"
  printf "  %s\n" "  ${gl_huang}注意：${reset}后台运行模式在系统重启后不会自动恢复。"
fi

# 等待服务完成数据库初始化后再读取凭据
[ "${USE_SYSTEMD}" = "y" ] || sleep 2
skip "读取首次登录凭据 ..."
if ! print_initial_credentials; then
  printf "%s\n" "  ${gl_huang}注意：${reset}未读取到初始化凭据（数据目录已存在时不会重新生成），可查看日志：${gl_bai}journalctl -u ${APP_NAME} -n 50${reset}"
fi
sep_line