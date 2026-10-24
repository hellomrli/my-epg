#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 channel_map.json 里的固定 tvg-id 写回 IPTV.m3u。

用法：
    python3 apply_ids.py --playlist ../my-IPTV/IPTV.m3u --output /tmp/IPTV.m3u
    python3 apply_ids.py --playlist ../my-IPTV/IPTV.m3u --tvg-url \
        https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml
"""

import argparse
import json
import re
from pathlib import Path

TVG_ID_RE = re.compile(r'tvg-id="[^"]*"')
TVG_URL_RE = re.compile(r'x-tvg-url="[^"]*"')


def channel_name(line):
    return line.rsplit(",", 1)[-1].strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", default="IPTV.m3u")
    parser.add_argument("--map", default="channel_map.json")
    parser.add_argument("--output")
    parser.add_argument("--tvg-url", help="同时改写 #EXTM3U 的 x-tvg-url")
    args = parser.parse_args()

    mapping = json.loads(Path(args.map).read_text(encoding="utf-8"))
    fixed = mapping.get("ids", {})
    lines = Path(args.playlist).read_text(encoding="utf-8").splitlines()

    changed = 0
    empty_after = 0
    output = []
    for line in lines:
        if line.startswith("#EXTM3U") and args.tvg_url:
            if TVG_URL_RE.search(line):
                line = TVG_URL_RE.sub(f'x-tvg-url="{args.tvg_url}"', line, count=1)
            else:
                line = line.replace("#EXTM3U", f'#EXTM3U x-tvg-url="{args.tvg_url}"', 1)
        elif line.startswith("#EXTINF"):
            name = channel_name(line)
            new_id = fixed.get(name)
            if new_id:
                if TVG_ID_RE.search(line):
                    line = TVG_ID_RE.sub(f'tvg-id="{new_id}"', line, count=1)
                else:
                    line = re.sub(r"(#EXTINF:[^\s]+)", rf'\1 tvg-id="{new_id}"', line, count=1)
                changed += 1
            m = TVG_ID_RE.search(line)
            if not m or m.group(0) == 'tvg-id=""':
                empty_after += 1
        output.append(line)

    target = Path(args.output or args.playlist)
    target.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")
    print(f"写入 {target}：修改 {changed} 个 tvg-id，仍为空 {empty_after} 个")


if __name__ == "__main__":
    main()
