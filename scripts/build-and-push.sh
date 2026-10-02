#!/bin/bash
#
# StudyBuddy (学习助手) - 发布脚本（触发 GitHub Actions 单一发布流水线）
# 不在本地编译任何产物：仅更新版本号、推送代码、打 v 开头 tag。
# 推送后由 GitHub Actions 的 .github/workflows/release.yml 链式自动完成：
#   [1] 编译 linux amd64/arm64 静态二进制（Go，CGO_ENABLED=0）
#   [2] 创建 GitHub Release 并附带 studybuddy_linux_amd64 / studybuddy_linux_arm64
#   [3] 构建推送 Docker 镜像：Docker Hub + GHCR
#   [4] 同步仓库到 CNB 镜像仓库
#
# Usage:
#   TAG(必填) 形如 v0.0.1; --yes 免交互; -m "备注" 可选发版说明
#     bash scripts/build-and-push.sh v0.0.1 --yes -m "第一个测试版"
set -euo pipefail

info() { echo -e "${gl_lv}>>> $*${reset}"; }
warn() { echo -e "${gl_huang}!!! $*${reset}"; }
error() { echo -e "${gl_hong}ERROR: $*${reset}"; exit 1; }

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

# 拉取本次 tag 触发的 workflow run：tag push 后 Actions 尚未注册新 run，
# 直接 --limit 1 取最新会取到上一次的陈旧记录。
# 这里按 tag 过滤并轮询等待，且用 headSha 校验确实是本次 push 的 run。
get_gh_run_info() {
    local workflow="$1"
    local tag="$2"
    local expect_sha
    expect_sha=$(git rev-parse HEAD 2>/dev/null) || expect_sha=""

    local tries=0
    local max_tries=18
    local run_json=""
    local sha=""
    while (( tries < max_tries )); do
        run_json=$(gh run list --workflow="${workflow}" --limit 1 --branch "${tag}" \
            --json status,displayTitle,headBranch,event,databaseId,startedAt,headSha 2>/dev/null) || run_json=""
        if [[ -n "$run_json" && "$run_json" != "[]" ]]; then
            sha=$(echo "$run_json" | jq -r '.[0].headSha')
            if [[ -z "$expect_sha" || "$sha" == "$expect_sha" ]]; then
                echo "$run_json"
                return 0
            fi
        fi
        tries=$((tries + 1))
        if (( tries < max_tries )); then
            sleep 5
        fi
    done
    return 1
}

calc_elapsed() {
    local start_iso="$1"
    local start_ts
    start_ts=$(date -d "${start_iso}" +%s 2>/dev/null)
    if [[ -z "$start_ts" ]]; then
        echo "时间解析失败"
        return
    fi
    local now_ts=$(date +%s)
    local diff=$(( now_ts - start_ts ))

    if (( diff < 60 )); then
        echo "${diff} 秒"
    elif (( diff < 3600 )); then
        echo "$((diff / 60)) 分 $((diff % 60)) 秒"
    else
        echo "$((diff / 3600)) 时 $(((diff % 3600)/60)) 分"
    fi
}

beautify_gh_run() {
    local workflow="${1:-}"
    local tag="${2:-}"
    # 本机未安装 gh CLI 时快速跳过（可用 GitHub 网页或 API 查看流水线）
    if ! command -v gh >/dev/null 2>&1; then
        echo -e ""
        echo -e "${gl_huang}>>> 未检测到 gh CLI，跳过流水线状态查询。可手动查看：${reset}"
        echo -e "${gl_lv}https://github.com/meimolihan/StudyBuddy/actions${reset}"
        return 0
    fi
    echo -e ""
    echo -e "${gl_zi}>>> GitHub Actions 流水线信息${gl_bai}"
    echo -e "${gl_bufan}————————————————————————————————————————————————${gl_bai}"

    json_data=$(get_gh_run_info "${workflow}" "${tag}")
    if [[ -z "$json_data" || "$json_data" == "[]" ]]; then
        echo -e "${gl_hong}[错误] 未获取到本次(${tag})流水线运行记录${reset}"
        echo -e "${gl_bai}可能原因：GitHub Actions 尚未注册该 run，可稍后用以下命令手动查看：${reset}"
        echo -e "${gl_lv}gh run list --workflow=${workflow} --branch ${tag}${reset}"
        echo -e "${gl_bufan}————————————————————————————————————————————————${gl_bai}"
        return 1
    fi

    status=$(echo "$json_data" | jq -r '.[0].status')
    title=$(echo "$json_data" | jq -r '.[0].displayTitle')
    event=$(echo "$json_data" | jq -r '.[0].event')
    run_id=$(echo "$json_data" | jq -r '.[0].databaseId')
    started_at=$(echo "$json_data" | jq -r '.[0].startedAt')

    elapsed=$(calc_elapsed "$started_at")

    case "$status" in
        in_progress)
            status_text="${gl_huang}运行中${reset}"
            ;;
        completed)
            conclusion=$(gh run view "$run_id" --json conclusion | jq -r '.conclusion')
            case "$conclusion" in
                success) status_text="${gl_lv}成功${reset}";;
                failure) status_text="${gl_hong}失败${reset}";;
                cancelled) status_text="${gl_hui}已取消${reset}";;
                skipped) status_text="${gl_huang}已跳过${reset}";;
                *) status_text="${gl_huang}已完成(${conclusion})${reset}";;
            esac
            ;;
        *)
            status_text="${gl_hui}${status}${reset}"
            ;;
    esac

    printf "%-14s%s\n" "${gl_hui}[工作流]：${reset}" "${gl_lan}${workflow}${reset}"
    printf "%-14s%s\n" "${gl_hui}[运行状态]：${reset}" "$status_text"
    printf "%-14s%s\n" "${gl_hui}[提交标题]：${reset}" "${gl_huang}$title${reset}"
    printf "%-14s%s\n" "${gl_hui}[触发事件]：${reset}" "${gl_bai}$event${reset}"
    printf "%-14s%s\n" "${gl_hui}[Run ID]：${reset}" "${gl_bufan}$run_id${reset}"
    printf "%-14s%s\n" "${gl_hui}[已耗时]：${reset}" "${gl_bai}$elapsed${reset}"

    echo -e "${gl_bufan}————————————————————————————————————————————————${gl_bai}"
    echo -e ""
    echo -e "${gl_huang}>>> 快捷操作命令${gl_bai}"
    echo -e "${gl_bufan}————————————————————————————————————————————————${gl_bai}"
    echo -e "${gl_lv}实时跟踪流水线：${reset}gh run watch $run_id"
    echo -e "${gl_lv}查看详细信息：${reset}gh run view $run_id"
    echo -e "${gl_lv}查看完整日志：${reset}gh run view $run_id --log"
    echo -e "${gl_lv}查看失败日志：${reset}gh run view $run_id --log-failed"
    echo -e "${gl_lv}取消本次构建：${reset}gh run cancel $run_id"
    echo -e "${gl_lv}重新运行流水线：${reset}gh run rerun $run_id"
    echo -e "${gl_bufan}————————————————————————————————————————————————${gl_bai}"
}

YES_MODE=0
TAG=""
MSG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes) YES_MODE=1; shift ;;
        -m|--message)
            shift
            [ -n "${1:-}" ] || error "缺少 -m/--message 的备注内容"
            MSG="$1"
            shift
            ;;
        *) TAG="$1"; shift ;;
    esac
done

[[ -z "${TAG}" ]] && error "缺少TAG参数，示例: $0 v0.0.1 --yes"

cd "$(dirname "$0")/.."

# ===================== CNB 同名仓库检测与自动创建 =====================
ensure_cnb_repo() {
    local token="${CNB_ACCESS_TOKEN:-}"
    if [ -z "${token}" ] && [ -f "${HOME}/.cnb_token" ]; then
        token=$(<"${HOME}/.cnb_token")
    fi
    if [ -z "${token}" ]; then
        warn "未配置 CNB_ACCESS_TOKEN 或 ~/.cnb_token，跳过 CNB 仓库检测"
        return 0
    fi
    local origin repo cname code
    origin=$(git config --get remote.origin.url 2>/dev/null || true)
    repo=$(basename "${origin}" .git 2>/dev/null || true)
    [ -z "${repo}" ] && repo=$(basename "$(pwd)" 2>/dev/null || true)
    cname="cnb.cool/meimolihan/${repo}"
    if GIT_TERMINAL_PROMPT=0 git ls-remote "https://cnb:${token}@${cname}.git" >/dev/null 2>&1; then
        info "CNB 同名仓库已存在：${cname}，跳过创建"
        return 0
    fi
    info "CNB 仓库不存在：${cname}，正在自动创建 ..."
    code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "https://api.cnb.cool/meimolihan/-/repos" \
        -H "Authorization: Bearer ${token}" \
        -H "Accept: application/vnd.cnb.api+json" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"${repo}\",\"visibility\":\"public\"}")
    if [ "${code}" = "201" ] || [ "${code}" = "200" ]; then
        info "CNB 仓库创建成功：${cname}（HTTP ${code}）"
    else
        warn "CNB 仓库创建返回 HTTP ${code}（可能已存在或权限不足），继续发布"
    fi
}
ensure_cnb_repo
TARGET_VER="${TAG#v}"
[[ "${TARGET_VER}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || error "TAG 格式错误，示例: v0.0.1"

# ===================== 重复Tag/Release自动清理 =====================
info "检查远端是否存在 Release ${TAG}"
if command -v gh >/dev/null 2>&1 && gh release view "${TAG}" >/dev/null 2>&1; then
    warn "发现已存在Release ${TAG}，准备删除Release并清理tag"
    gh release delete "${TAG}" -y --cleanup-tag
fi

info "清理本地&远端Git tag: ${TAG}"
git tag -d "${TAG}" 2>/dev/null || true
git push origin --delete "${TAG}" 2>/dev/null || true

# ===================== 版本号 bump =====================
info "执行版本号更新 ${TARGET_VER}"

# StudyBuddy 的版本载体为仓库根目录 VERSION 文件（单行语义化版本号），
# 发布流水线会把它经 -ldflags "-X main.version=${TAG}" 注入二进制。
printf '%s\n' "${TARGET_VER}" > VERSION

info "版本号确认:"
grep -n . VERSION | sed 's/^/  VERSION: /'

# ===================== 写发版备注 =====================
info "写入发版备注 RELEASE_NOTES.md"
{
  if [ -n "${MSG}" ]; then
    printf '%s\n' "${MSG}"
    printf '\n'
  fi
  printf '```bash\n'
  printf 'docker pull mobufan/studybuddy:latest\n'
  printf '```\n'
  printf '```bash\n'
  printf 'docker pull mobufan/studybuddy:%s\n' "${TAG}"
  printf '```\n'
  printf '\n'
  printf '```bash\n'
  printf 'docker pull ghcr.io/meimolihan/studybuddy:latest\n'
  printf '```\n'
  printf '```bash\n'
  printf 'docker pull ghcr.io/meimolihan/studybuddy:%s\n' "${TAG}"
  printf '```\n'
  printf '\n'
  printf '## 二进制安装\n'
  printf '```bash\n'
  printf 'bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/install.sh)" -p 8080 -d /var/lib/StudyBuddy\n'
  printf '```\n'
  printf '\n'
  printf '## 二进制卸载\n'
  printf '```bash\n'
  printf 'bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/uninstall.sh)" -y --purge\n'
  printf '```\n'
} > RELEASE_NOTES.md

# ===================== Git 提交 & Tag =====================
info "提交版本变更"
git add .
git commit -m "chore: bump version to ${TARGET_VER}" || info "无版本文件变更，跳过提交"
git push origin main

git tag "${TAG}"
git push origin "${TAG}"
info "✅ 已推送 tag ${TAG}，将自动执行发布流水线（release.yml）"

info "查看发布结果: gh release view ${TAG}"
info "查看镜像: docker pull mobufan/studybuddy:${TAG}"

beautify_gh_run "release.yml" "${TAG}" || true
