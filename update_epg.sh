#!/usr/bin/env bash
#
# my-epg 每日构建脚本
# 多源聚合 + 组内 fallback，任意单一源失效都不会中断
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

LOG() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

PLAYLIST="${PLAYLIST:-https://raw.githubusercontent.com/hellomrli/my-IPTV/main/IPTV.m3u}"

for attempt in 1 2 3; do
    LOG "第 ${attempt} 次构建 EPG..."
    if python3 build_epg.py \
        --playlist "$PLAYLIST" \
        --output epg.xml \
        --report build_report.json; then
        break
    fi
    if [ "$attempt" -ge 3 ]; then
        LOG "构建失败，保留旧 epg.xml 不提交"
        exit 1
    fi
    DELAY=$((attempt * 15))
    LOG "${DELAY} 秒后重试..."
    sleep "$DELAY"
done

# 输出合法性校验：必须是可解析的 XMLTV，且频道/节目非空
python3 - <<'PY'
import xml.etree.ElementTree as ET
root = ET.parse("epg.xml").getroot()
channels = len(root.findall("channel"))
programmes = len(root.findall("programme"))
assert channels > 0, "epg.xml 没有 channel"
assert programmes > 0, "epg.xml 没有 programme"
print(f"校验通过: {channels} channels / {programmes} programmes")
PY

git config --local user.email "action@github.com"
git config --local user.name "GitHub Action"

if git diff --quiet -- epg.xml; then
    LOG "EPG 无变化，跳过提交"
else
    git add epg.xml
    git commit -m "Update EPG: $(date -u '+%Y-%m-%d %H:%M UTC')"
    git push
    LOG "推送完成"
fi
