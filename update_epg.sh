#!/bin/bash
#
# EPG 中转脚本
# 每天定时从 51zmt 拉取 EPG，推送到 GitHub
# 失败时自动重试（最多3次，每次间隔递增）
#

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

LOG() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

RETRY=0
MAX_RETRIES=3
DELAY_BASE=30  # 秒

while true; do
    RETRY=$((RETRY + 1))
    LOG "第 ${RETRY} 次尝试下载 EPG..."

    # 下载 EPG（跟随重定向，302 -> exml.51zmt.top）
    if wget -O epg.xml \
            --timeout=60 \
            --tries=1 \
            -q \
            "http://epg.51zmt.top:8000/e.xml"; then

        FILE_SIZE=$(wc -c < epg.xml)
        if [ "$FILE_SIZE" -gt 50000 ]; then
            LOG "下载成功 (${FILE_SIZE} bytes)"
            break
        else
            LOG "文件太小 (${FILE_SIZE} bytes)，视为失败"
        fi
    else
        LOG "下载失败"
    fi

    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        LOG "已达最大重试次数 ${MAX_RETRIES}，放弃"
        exit 1
    fi

    DELAY=$((DELAY_BASE * RETRY))
    LOG "${DELAY} 秒后重试..."
    sleep "$DELAY"
done

# 提交推送
cd "$REPO_DIR"
git config --local user.email "action@github.com"
git config --local user.name "GitHub Action"

if git diff --quiet epg.xml; then
    LOG "EPG 无变化，跳过提交"
else
    git add epg.xml
    git commit -m "Update EPG: $(date -u '+%Y-%m-%d %H:%M UTC')"
    git push
    LOG "推送完成"
fi
