#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my-epg 多源聚合脚本

从 sources.json 配置的多个 EPG 源抓取节目单，按频道名合并成一份 XMLTV。
- 同一组内按顺序 fallback（老张主站挂了自动用 gitee 镜像）
- 组与组之间按 priority 合并：高优先级源先占时段，低优先级源补空档
- 频道 id 以 IPTV.m3u 的 tvg-id 为准，空 id 用 channel_map.json 固定分配
- 只输出播放列表里存在的频道，控制文件体积

用法：
    python3 build_epg.py
    python3 build_epg.py --playlist-file ../my-IPTV/IPTV.m3u --output epg.xml
    python3 build_epg.py --source-cache /tmp/epg-cache --days 7
"""

import argparse
import gzip
import hashlib
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BJT = timezone(timedelta(hours=8))
DEFAULT_PLAYLIST = "https://raw.githubusercontent.com/hellomrli/my-IPTV/main/IPTV.m3u"
MIN_SEGMENT = timedelta(minutes=3)
MAX_DESC = 200
USER_AGENT = "my-epg/2.0 (+https://github.com/hellomrli/my-epg)"


def log(msg):
    print(f"[{datetime.now(BJT):%H:%M:%S}] {msg}", flush=True)


def norm(name):
    """频道名归一化：去空格/连字符/后缀，统一全角符号。"""
    s = (name or "").strip().lower()
    s = s.replace("（", "(").replace("）", ")").replace("＋", "+")
    s = s.replace("－", "-").replace("—", "-").replace("–", "-")
    s = re.sub(r"[\s\-_·・]", "", s)
    s = re.sub(r"(频道|电视台|电视)$", "", s)
    # CCTV-1 综合 / CCTV-16奥林匹克 这类带台名后缀的，归一到 cctv1 / cctv16；
    # 但欧洲、美洲、4K、8K 等是不同频道，不能归一。
    m = re.match(r"^cctv[-]?(\d{1,2})(\+?)(.*)$", s)
    if m:
        suffix = m.group(3)
        known = {
            "", "综合", "财经", "综艺", "体育", "电影", "国防军事", "电视剧",
            "纪录", "科教", "戏曲", "社会与法", "新闻", "少儿", "音乐",
            "奥林匹克", "农业农村", "体育赛事",
        }
        if suffix in known:
            return f"cctv{int(m.group(1))}{m.group(2)}"
    return s


def parse_dt(value):
    """解析 XMLTV 时间：20261024180000 +0800 / 20261024180000+0800。"""
    if not value:
        return None
    m = re.match(r"^\s*(\d{14})(?:\s*([+-]\d{4}))?", value)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
    except ValueError:
        return None
    off = m.group(2)
    if off:
        sign = 1 if off[0] == "+" else -1
        tz = timezone(sign * timedelta(hours=int(off[1:3]), minutes=int(off[3:5])))
    else:
        tz = BJT
    return dt.replace(tzinfo=tz).astimezone(BJT)


def fmt_dt(dt):
    return dt.astimezone(BJT).strftime("%Y%m%d%H%M%S") + " +0800"


def clean_text(value, limit=None):
    if not value:
        return ""
    s = re.sub(r"<[^>]+>", "", value)
    s = re.sub(r"\s+", " ", s).strip()
    if limit and len(s) > limit:
        s = s[:limit].rstrip() + "…"
    return s


def fetch(url, retries=2, timeout=90):
    last = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            if not data:
                raise ValueError("响应为空")
            return data
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise last


def read_source(url, cache_dir, name):
    if cache_dir:
        path = Path(cache_dir) / f"{name}.xml"
        if path.exists() and path.stat().st_size > 0:
            log(f"  使用缓存 {path}")
            return path.read_bytes()
    data = fetch(url)
    if cache_dir:
        path = Path(cache_dir) / f"{name}.xml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data


def parse_xmltv(data, name, window_start, window_end):
    """解析 XMLTV，只保留窗口内的节目，返回 channels / programmes / index。"""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"XML 解析失败: {exc}") from exc

    channels = {}
    for node in root.findall("channel"):
        cid = (node.get("id") or "").strip()
        names = [(d.text or "").strip() for d in node.findall("display-name")]
        names = [n for n in names if n]
        if cid and names:
            channels[cid] = names

    programmes = defaultdict(list)
    total = 0
    for node in root.findall("programme"):
        cid = node.get("channel")
        if cid not in channels:
            continue
        start = parse_dt(node.get("start"))
        stop = parse_dt(node.get("stop"))
        if not start or not stop or stop <= start:
            continue
        if stop <= window_start or start >= window_end:
            continue
        title = clean_text(node.findtext("title"))
        if not title:
            continue
        # 异常长的节目（超过 8 小时）截断，避免个别源数据错误撑大文件
        if stop - start > timedelta(hours=8):
            stop = start + timedelta(hours=8)
        desc = clean_text(node.findtext("desc"), MAX_DESC)
        category = clean_text(node.findtext("category"), 40)
        icon_node = node.find("icon")
        icon = (icon_node.get("src") or "").strip() if icon_node is not None else ""
        programmes[cid].append(
            {
                "start": start,
                "stop": stop,
                "title": title,
                "desc": desc,
                "category": category,
                "icon": icon,
            }
        )
        total += 1

    index = {}
    for cid, names in channels.items():
        weight = len(programmes.get(cid, []))
        for display in names:
            key = norm(display)
            if key and (key not in index or weight > index[key][1]):
                index[key] = (cid, weight)

    return {
        "name": name,
        "channels": channels,
        "programmes": programmes,
        "index": {k: v[0] for k, v in index.items()},
        "channel_count": len(channels),
        "programme_count": total,
    }


def load_group(group, cache_dir, window_start, window_end):
    errors = []
    for spec in group.get("sources", []):
        name = spec["name"]
        started = time.time()
        try:
            log(f"下载源 {name} ...")
            data = read_source(spec["url"], cache_dir, name)
            source = parse_xmltv(data, name, window_start, window_end)
            source["priority"] = group.get("priority", 100)
            source["url"] = spec["url"]
            source["bytes"] = len(data)
            source["elapsed"] = round(time.time() - started, 1)
            log(
                f"  {name} 成功：{source['channel_count']} 频道 / "
                f"{source['programme_count']} 条节目 / {len(data)/1024:.0f} KB"
            )
            return source, errors
        except Exception as exc:  # noqa: BLE001
            msg = f"{name}: {exc}"
            errors.append(msg)
            log(f"  {name} 失败：{exc}")
    return None, errors


def subtract(occupied, start, stop):
    """返回 [start, stop] 中未被 occupied 覆盖的片段。occupied 需有序且已合并。"""
    cursor = start
    pieces = []
    for a, b in occupied:
        if b <= cursor:
            continue
        if a >= stop:
            break
        if a > cursor:
            pieces.append((cursor, min(a, stop)))
        cursor = max(cursor, b)
        if cursor >= stop:
            break
    if cursor < stop:
        pieces.append((cursor, stop))
    return pieces


def add_interval(occupied, start, stop):
    occupied.append((start, stop))
    occupied.sort()
    merged = []
    for a, b in occupied:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def match_cid(source, names):
    for candidate in names:
        cid = source["index"].get(norm(candidate))
        if cid:
            return cid
    return None


def parse_m3u(text):
    channels = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("#EXTINF"):
            continue
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
        name = line.rsplit(",", 1)[-1].strip()
        if not name:
            continue
        channels.append(
            {
                "name": name,
                "id": attrs.get("tvg-id", "").strip(),
                "group": attrs.get("group-title", "").strip(),
                "logo": attrs.get("tvg-logo", "").strip(),
            }
        )
    return channels


def resolve_id(channel, fixed_ids):
    if channel["name"] in fixed_ids:
        return fixed_ids[channel["name"]]
    if channel["id"]:
        return channel["id"]
    return "ch-" + hashlib.sha1(channel["name"].encode("utf-8")).hexdigest()[:8]


def merge_group(names, sources, aliases, skip):
    occupied = []
    merged = []
    used = []
    for source in sorted(sources, key=lambda s: s["priority"]):
        progs = []
        seen = set()
        matched_names = []
        for name in names:
            if name in skip:
                continue
            candidates = [name] + aliases.get(name, [])
            cid = match_cid(source, candidates)
            if not cid:
                continue
            matched_names.append(name)
            for prog in source["programmes"].get(cid, []):
                key = (prog["start"], prog["stop"], prog["title"])
                if key in seen:
                    continue
                seen.add(key)
                progs.append(prog)
        if not progs:
            continue
        progs.sort(key=lambda p: p["start"])
        added = 0
        for prog in progs:
            start, stop = prog["start"], prog["stop"]
            for piece_start, piece_stop in subtract(occupied, start, stop):
                if piece_stop - piece_start < MIN_SEGMENT:
                    continue
                item = dict(prog)
                item["start"] = piece_start
                item["stop"] = piece_stop
                item["source"] = source["name"]
                merged.append(item)
                added += 1
            occupied = add_interval(occupied, start, stop)
        if added:
            used.append({"name": source["name"], "programmes": added})
    merged.sort(key=lambda p: p["start"])
    return merged, used


def write_xml(path, groups, source_meta):
    tv = ET.Element(
        "tv",
        {
            "generator-info-name": "my-epg multi-source",
            "generator-info-url": "https://github.com/hellomrli/my-epg",
            "source-info-name": "51zmt/112114/epg.pw/kuke31/CCSH",
        },
    )
    for gid, group in groups.items():
        channel = ET.SubElement(tv, "channel", id=gid)
        for name in group["names"]:
            ET.SubElement(channel, "display-name", lang="zh").text = name
    for gid, group in groups.items():
        for prog in group["programmes"]:
            node = ET.SubElement(
                tv,
                "programme",
                {
                    "start": fmt_dt(prog["start"]),
                    "stop": fmt_dt(prog["stop"]),
                    "channel": gid,
                },
            )
            ET.SubElement(node, "title", lang="zh").text = prog["title"]
            if prog.get("category"):
                ET.SubElement(node, "category", lang="zh").text = prog["category"]
            if prog.get("desc"):
                ET.SubElement(node, "desc", lang="zh").text = prog["desc"]

    xml = ET.tostring(tv, encoding="unicode")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        handle.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        handle.write(xml)
        handle.write("\n")
    return len(xml)


def main():
    parser = argparse.ArgumentParser(description="多源 EPG 聚合")
    parser.add_argument("--playlist", default=DEFAULT_PLAYLIST, help="播放列表 URL")
    parser.add_argument("--playlist-file", help="本地播放列表路径（优先于 --playlist）")
    parser.add_argument("--sources", default="sources.json", help="源配置")
    parser.add_argument("--map", default="channel_map.json", help="频道映射")
    parser.add_argument("--output", default="epg.xml", help="输出 XMLTV")
    parser.add_argument("--report", default="build_report.json", help="统计报告")
    parser.add_argument("--days", type=int, default=7, help="输出天数（默认 7）")
    parser.add_argument("--source-cache", help="源缓存目录（本地调试用）")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    sources_cfg = json.loads((base / args.sources).read_text(encoding="utf-8"))
    channel_map = json.loads((base / args.map).read_text(encoding="utf-8"))
    fixed_ids = channel_map.get("ids", {})
    aliases = channel_map.get("aliases", {})
    skip = set(channel_map.get("skip", []))

    if args.playlist_file:
        playlist_text = Path(args.playlist_file).read_text(encoding="utf-8")
        playlist_from = str(Path(args.playlist_file).resolve())
    else:
        log(f"下载播放列表 {args.playlist} ...")
        playlist_text = fetch(args.playlist).decode("utf-8-sig", errors="replace")
        playlist_from = args.playlist
    playlist = parse_m3u(playlist_text)
    if not playlist:
        log("播放列表为空，退出")
        return 1

    now = datetime.now(BJT)
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=max(1, args.days))

    log(f"播放列表：{len(playlist)} 个频道（{playlist_from}）")
    log(f"节目窗口：{window_start:%Y-%m-%d} ~ {window_end:%Y-%m-%d}")

    loaded = []
    source_report = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(load_group, group, args.source_cache, window_start, window_end): group
            for group in sources_cfg.get("groups", [])
        }
        for future in futures:
            group = futures[future]
            source, errors = future.result()
            if source:
                loaded.append(source)
                source_report.append(
                    {
                        "group": group.get("name"),
                        "source": source["name"],
                        "url": source["url"],
                        "ok": True,
                        "channels": source["channel_count"],
                        "programmes": source["programme_count"],
                        "bytes": source["bytes"],
                        "elapsed": source["elapsed"],
                    }
                )
            else:
                source_report.append(
                    {
                        "group": group.get("name"),
                        "source": None,
                        "ok": False,
                        "errors": errors,
                    }
                )

    if not loaded:
        log("所有 EPG 源均不可用，保留旧 epg.xml 不做覆盖")
        return 1

    groups = OrderedDict()
    for channel in playlist:
        gid = resolve_id(channel, fixed_ids)
        if gid not in groups:
            groups[gid] = {"names": [], "playlist_names": [], "programmes": [], "sources": []}
        groups[gid]["playlist_names"].append(channel["name"])
        if channel["name"] not in groups[gid]["names"]:
            groups[gid]["names"].append(channel["name"])

    channel_report = []
    with_programme = 0
    for gid, group in groups.items():
        progs, used = merge_group(group["names"], loaded, aliases, skip)
        group["programmes"] = progs
        group["sources"] = used
        if progs:
            with_programme += 1
        channel_report.append(
            {
                "name": group["names"][0],
                "names": group["names"],
                "id": gid,
                "programmes": len(progs),
                "sources": [u["name"] for u in used],
            }
        )

    size = write_xml(args.output, groups, source_report)
    total_programmes = sum(len(g["programmes"]) for g in groups.values())

    report = {
        "generated_at": now.isoformat(),
        "playlist": playlist_from,
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
        "summary": {
            "playlist_channels": len(playlist),
            "epg_channels": len(groups),
            "channels_with_programme": with_programme,
            "channels_without_programme": len(groups) - with_programme,
            "programmes": total_programmes,
            "output_bytes": size,
        },
        "sources": source_report,
        "channels": channel_report,
    }
    (base / args.report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log("=" * 56)
    log(f"输出 {args.output}：{len(groups)} 频道 / {total_programmes} 条节目 / {size/1024:.0f} KB")
    log(f"有节目频道：{with_programme}/{len(groups)}，无节目：{len(groups)-with_programme}")
    missing = [c["name"] for c in channel_report if not c["programmes"]]
    if missing:
        log("无节目：" + "、".join(missing))
    log(f"报告：{args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
