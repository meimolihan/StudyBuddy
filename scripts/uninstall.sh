#!/usr/bin/env bash
#
# StudyBuddy (学习助手) - 小学生刷题自测 Web 系统 卸载脚本
# 停止并移除 systemd 服务 / 后台进程，删除程序目录，可选删除数据与教材目录。
#
# Usage: bash scripts/uninstall.sh [-y] [--purge|--keep-data] [-q]

set -e

APP_NAME="studybuddy"
APP_DISPLAY="StudyBuddy"
APP_DIR="/var/lib/StudyBuddy"
DEFAULT_PORT=8080
CONFIG_FILE="/etc/studybuddy.conf"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
CLI_BIN="/usr/local/bin/${APP_NAME}"

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
    "  ${z}│${r}   ${b}StudyBuddy${r}  ${l}学习助手 · 卸载${r}        ${z}│${r}" \
    "  ${z}└─────────────────────────────────────────┘${r}" \
    ""
}

error() { printf "  %s %s\n" "${gl_hong}[错误]${reset}" "$1" >&2; exit 1; }
[ "$(id -u)" != "0" ] && error "请以 root 身份运行（sudo bash scripts/uninstall.sh）"

UNINSTALL_YES=0
DELETE_DATA=0
KEEP_DATA=0
QUIET=0

usage() {
  printf '%s\n' \
    "用法: bash scripts/uninstall.sh [选项]" \
    "" \
    "选项:" \
    "  -y, --yes        免确认，自动同意卸载" \
    "      --purge      卸载时同时删除数据目录（data/、archive/、content/ 与全部程序文件）" \
    "      --keep-data  卸载时保留数据目录" \
    "  -q, --quiet      静默模式，仅输出关键信息" \
    "  -h, --help       显示帮助" \
    "" \
    "示例:" \
    "  bash scripts/uninstall.sh -y               免确认卸载，保留数据目录" \
    "  bash scripts/uninstall.sh -y --purge       免确认卸载，并删除数据目录"
  exit 0
}

# ---- bootstrap: support `bash -c "$(curl ...)" -y --purge` ----
case "$0" in
  -*) set -- "$0" "$@" ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes) UNINSTALL_YES=1; shift ;;
    --purge|--delete-data) DELETE_DATA=1; shift ;;
    --keep-data) KEEP_DATA=1; shift ;;
    -q|--quiet) QUIET=1; shift ;;
    -h|--help) usage ;;
    *) error "未知参数: $1，使用 -h 查看帮助" ;;
  esac
done

[ "$QUIET" = "1" ] && {
  sep_line() { :; }
  section() { :; }
  ok() { :; }
  skip() { :; }
}

PORT="$DEFAULT_PORT"
read_config() {
  [ -f "$CONFIG_FILE" ] || return 0
  while IFS='=' read -r KEY VALUE; do
    KEY=$(printf '%s' "$KEY" | tr -d ' ')
    VALUE=$(printf '%s' "$VALUE" | tr -d '\r')
    case "$KEY" in
      APP_DIR) [ -n "$VALUE" ] && APP_DIR="$VALUE" ;;
      PORT) [ -n "$VALUE" ] && PORT="$VALUE" ;;
    esac
  done < "$CONFIG_FILE"
}

find_studybuddy_pids() {
  local d pid cmdline
  for d in /proc/[0-9]*; do
    [ -d "$d" ] || continue
    pid="${d#/proc/}"
    [ "$pid" = "$$" ] && continue
    # 用命令行匹配安装目录下的二进制，避免误杀其他进程
    cmdline=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null) || continue
    case "$cmdline" in
      *"${APP_DIR}/${APP_NAME}"*) echo "$pid" ;;
    esac
  done
}

close_firewall_port() {
  local PORT="$1"
  [ -z "$PORT" ] && return 0

  # 1. firewalld
  if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
    firewall-cmd --permanent --remove-port="${PORT}/tcp" >/dev/null 2>&1 || true
    firewall-cmd --reload >/dev/null 2>&1 || true
    ok "已通过 ${gl_bai}firewalld${reset} 关闭端口 ${gl_lan}${PORT}/tcp${reset}"
  # 2. ufw
  elif command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw delete allow "${PORT}/tcp" >/dev/null 2>&1 || true
    ok "已通过 ${gl_bai}ufw${reset} 关闭端口 ${gl_lan}${PORT}/tcp${reset}"
  # 3. iptables
  elif command -v iptables >/dev/null 2>&1; then
    if iptables -D INPUT -p tcp --dport "${PORT}" -j ACCEPT >/dev/null 2>&1; then
      ok "已通过 ${gl_bai}iptables${reset} 关闭端口 ${gl_lan}${PORT}/tcp${reset}"
    fi
  fi
}

[ "$QUIET" = "1" ] || print_banner
sep_line
section "卸载确认"
if [ "$UNINSTALL_YES" = "1" ]; then
  ok "开始卸载 ${APP_DISPLAY} ..."
else
  while :; do
    read -r -p "${gl_huang}卸载将停止并移除 ${APP_DISPLAY} 服务与程序，是否继续？${gl_bai}[y/N]${reset}: " CONFIRM
    case "$CONFIRM" in
      y|Y|yes|YES)
        ok "开始卸载 ${APP_DISPLAY} ..."
        break
        ;;
      n|N|no|NO|"")
        printf "  %s\n" "${gl_huang}已取消卸载。${reset}"
        exit 0
        ;;
      *)
        printf "  %s\n" "${gl_huang}输入无效，请输入 y 或 n。${reset}"
        ;;
    esac
  done
fi

read_config

# 从 service 文件回退读取安装参数（config 缺失时）
if [ -f "$SERVICE_FILE" ]; then
  _SVC_PORT=$(grep -oE 'STUDYBUDDY_PORT=[0-9]+' "$SERVICE_FILE" | head -n1 | cut -d= -f2)
  [ -n "$_SVC_PORT" ] && PORT="$_SVC_PORT"
  _SVC_DIR=$(grep -oE 'WorkingDirectory=[^ ]+' "$SERVICE_FILE" | head -n1 | cut -d= -f2)
  [ -n "$_SVC_DIR" ] && APP_DIR="$_SVC_DIR"
fi

sep_line
section "停止服务"
if command -v systemctl >/dev/null 2>&1 && [ -f "$SERVICE_FILE" ]; then
  ok "正在停止并移除 systemd 服务 ${gl_bai}${APP_NAME}${reset} ..."
  systemctl stop "${APP_NAME}" 2>/dev/null || true
  systemctl disable "${APP_NAME}" 2>/dev/null || true
  rm -f "$SERVICE_FILE"
  systemctl daemon-reload 2>/dev/null || true
else
  skip "未发现 systemd 服务，跳过。"
fi

sep_line
section "停止进程"
PIDS=$(find_studybuddy_pids)
if [ -n "$PIDS" ]; then
  ok "正在停止 ${APP_DISPLAY} 进程: ${gl_bai}$PIDS${reset} ..."
  for PID in $PIDS; do
    [ -d "/proc/$PID" ] || continue
    kill "$PID" 2>/dev/null || true
  done
  sleep 1
  for PID in $PIDS; do
    [ -d "/proc/$PID" ] || continue
    kill -9 "$PID" 2>/dev/null || true
  done
else
  skip "未发现运行中的 ${APP_DISPLAY} 进程，跳过。"
fi

sep_line
section "删除程序与命令"
if [ -n "$APP_DIR" ] && [ -d "$APP_DIR" ]; then
  # 程序本体（二进制 + 运维脚本）必删；数据/教材/归档按选项处理
  rm -f "${APP_DIR}/${APP_NAME}"
  rm -rf "${APP_DIR}/scripts"
  ok "已删除程序文件 ${gl_bai}${APP_DIR}/${APP_NAME}${reset}"
else
  skip "未找到程序目录 ${gl_bai}${APP_DIR}${reset}，跳过。"
fi
if [ -f "$CLI_BIN" ] || [ -L "$CLI_BIN" ]; then
  rm -f "$CLI_BIN"
  ok "已删除命令 ${gl_bai}${CLI_BIN}${reset}"
else
  skip "未找到命令 ${gl_bai}${CLI_BIN}${reset}，跳过。"
fi

sep_line
section "删除数据目录"
if [ -n "$APP_DIR" ] && [ -d "$APP_DIR" ]; then
  ok "检测到数据目录: ${gl_bai}${APP_DIR}/data、${APP_DIR}/archive、${APP_DIR}/content${reset}"
  if [ "$KEEP_DATA" = "1" ]; then
    skip "已保留数据目录"
  elif [ "$DELETE_DATA" = "1" ]; then
    rm -rf "$APP_DIR"
    ok "已删除安装与数据目录 ${gl_bai}${APP_DIR}${reset}"
  elif [ -t 0 ]; then
    read -r -p "${gl_huang}是否删除全部数据目录（data/、archive/、content/，含账号数据库与归档试卷）？${gl_bai}[Y/n]${reset}: " DEL_DATA
    case "$DEL_DATA" in
      n|N|no|NO)
        skip "已保留数据目录 ${gl_bai}${APP_DIR}/data 等${reset}"
        ;;
      *)
        rm -rf "$APP_DIR"
        ok "已删除安装与数据目录 ${gl_bai}${APP_DIR}${reset}"
        ;;
    esac
  else
    skip "非交互模式下默认保留数据目录 ${gl_bai}${APP_DIR}/data 等${reset}"
  fi
else
  skip "未找到数据目录，跳过。"
fi

sep_line
section "删除安装记录"
if [ -f "$CONFIG_FILE" ]; then
  rm -f "$CONFIG_FILE"
  ok "已删除安装记录 ${gl_bai}$CONFIG_FILE${reset}"
else
  skip "未找到安装记录 ${gl_bai}$CONFIG_FILE${reset}，跳过。"
fi

sep_line
section "关闭防火墙"
close_firewall_port "$PORT"

sep_line
printf "  %s\n" "${gl_lv}✔ ${APP_DISPLAY} 已卸载完成${reset}"
printf "  %s\n" "${gl_hui}如需重新安装，请再次运行 scripts/install.sh 安装脚本。${reset}"
sep_line
