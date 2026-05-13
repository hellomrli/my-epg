#!/usr/bin/env python3
"""
Download and merge EPG for user's specific IPTV channels.
Primary: 51zmt (老张EPG) - fresh, updated daily
Backup: 112114 GitHub mirror - older data, full channel list
"""

import urllib.request
import gzip
import os
import xml.etree.ElementTree as ET
from datetime import datetime

SOURCES = [
    ("51zmt", "http://epg.51zmt.top:8000/e.xml"),
    ("112114", "https://raw.githubusercontent.com/sparkssssssssss/epg/main/pp.xml"),
]

# Playlist channel names -> EPG display-names (first match wins)
CHANNEL_ALIASES = {
    # CCTV
    "CCTV1": ["CCTV1"], "CCTV2": ["CCTV2"], "CCTV3": ["CCTV3"], "CCTV4": ["CCTV4"],
    "CCTV5": ["CCTV5"], "CCTV5+": ["CCTV5+"], "CCTV6": ["CCTV6"], "CCTV7": ["CCTV7"],
    "CCTV8": ["CCTV8"], "CCTV9": ["CCTV9"], "CCTV10": ["CCTV10"],
    "CCTV11": ["CCTV11"], "CCTV12": ["CCTV12"], "CCTV13": ["CCTV13"],
    "CCTV14": ["CCTV14"], "CCTV15": ["CCTV15"], "CCTV16": ["CCTV16"], "CCTV17": ["CCTV17"],
    # Provincial satellite
    "东方卫视": ["东方卫视"], "北京卫视": ["北京卫视"], "江苏卫视": ["江苏卫视"],
    "浙江卫视": ["浙江卫视"], "湖南卫视": ["湖南卫视"], "安徽卫视": ["安徽卫视"],
    "深圳卫视": ["深圳卫视"], "广东卫视": ["广东卫视"], "山东卫视": ["山东卫视"],
    "湖北卫视": ["湖北卫视"], "四川卫视": ["四川卫视"], "重庆卫视": ["重庆卫视"],
    "天津卫视": ["天津卫视"], "吉林卫视": ["吉林卫视"], "辽宁卫视": ["辽宁卫视"],
    "云南卫视": ["云南卫视"], "贵州卫视": ["贵州卫视"], "河南卫视": ["河南卫视"],
    "河北卫视": ["河北卫视"], "山西卫视": ["山西卫视"], "江西卫视": ["江西卫视"],
    "黑龙江卫视": ["黑龙江卫视"], "甘肃卫视": ["甘肃卫视"], "青海卫视": ["青海卫视"],
    "海南卫视": ["海南卫视"],
    "东南卫视": ["东南卫视"], "广西卫视": ["广西卫视"],
    "三沙卫视": ["三沙卫视"],
    # CGTN
    "CGTN": ["CGTN"],
    # Phoenix (51zmt uses simplified names)
    "凤凰卫视中文台": ["凤凰中文"],
    "凤凰卫视资讯台": ["凤凰资讯"],
    "凤凰卫视香港台": ["凤凰香港"],
    # 4K
    "CCTV4K": ["CCTV4K"],
    "咪咕4K": ["咪咕4K"],
    # Extra provincial
    "陕西卫视": ["陕西卫视"], "宁夏卫视": ["宁夏卫视"],
    "内蒙古卫视": ["内蒙古卫视"], "新疆卫视": ["新疆卫视"],
    "西藏卫视": ["西藏卫视"], "兵团卫视": ["兵团卫视"],
    "CETV1": ["CETV1"], "CETV2": ["CETV2"], "CETV4": ["CETV4"],
    "卡酷动画": ["卡酷卡通"], "金鹰卡通": ["金鹰卡通"], "金鹰纪实": ["金鹰纪实"],
    "哈哈炫动": ["哈哈炫动"],
    "厦门卫视": ["厦门卫视"], "康巴卫视": ["康巴卫视"],
    "北京纪实": ["北京纪实高清"],
}


def download(url):
    """Download and decode content."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        if raw and raw[0] in (0x1f, 0x78):
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")


def main():
    print(f"=== EPG Update {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    name_to_id = {}  # display_name -> channel_id
    all_progs = {}   # (channel_id, start, title) -> prog dict

    for source_name, url in SOURCES:
        print(f"Downloading {source_name}...")
        try:
            xml = download(url)
        except Exception as e:
            print(f"  Failed: {e}")
            continue

        try:
            root = ET.fromstring(xml)
        except ET.ParseError as e:
            print(f"  Parse error: {e}")
            continue

        # Build name -> channel_id mapping
        for ch in root.iter("channel"):
            ch_id = ch.get("id", "")
            for dn in ch.iter("display-name"):
                dn_text = dn.text
                if dn_text and dn_text not in name_to_id:
                    name_to_id[dn_text] = ch_id
        print(f"  {len(name_to_id)} channels")

        # Also build id -> display_name
        id_to_display = {v: k for k, v in name_to_id.items()}

        # Collect programmes for channels we care about
        for prog in root.iter("programme"):
            ch_ref = prog.get("channel", "")
            display = id_to_display.get(ch_ref, "")
            if display not in CHANNEL_ALIASES:
                continue
            start = prog.get("start", "")
            stop = prog.get("stop", "")
            title_els = list(prog.iter("title"))
            title = str(title_els[0].text) if title_els and title_els[0].text else "未知节目"
            key = (ch_ref, start, title)
            if key not in all_progs:
                all_progs[key] = {"ch_ref": ch_ref, "start": start, "stop": stop, "title": title}

        print(f"  {len(all_progs)} programmes so far")

    print(f"\nTotal: {len(all_progs)} programmes across {len(set(p['ch_ref'] for p in all_progs.values()))} channels")

    # Build output XML
    root = ET.Element("tv")
    root.set("generator-info-name", "my-epg merged EPG")
    root.set("info-url", "https://github.com/hellomrli/my-epg")
    root.set("source-info-name", "merged: 51zmt + 112114")

    # Add channel entries (in playlist order)
    for playlist_ch, aliases in CHANNEL_ALIASES.items():
        matched_name = None
        for alias in aliases:
            if alias in name_to_id:
                matched_name = alias
                break
        if matched_name:
            ch_el = ET.SubElement(root, "channel")
            ch_el.set("id", name_to_id[matched_name])
            dn_el = ET.SubElement(ch_el, "display-name")
            dn_el.set("lang", "zh")
            dn_el.text = matched_name

    # Add programmes sorted by channel and start time
    for prog in sorted(all_progs.values(), key=lambda p: (p["ch_ref"], p["start"])):
        p_el = ET.SubElement(root, "programme")
        p_el.set("channel", prog["ch_ref"])
        p_el.set("start", prog["start"])
        p_el.set("stop", prog["stop"])
        t_el = ET.SubElement(p_el, "title")
        t_el.set("lang", "zh")
        t_el.text = prog["title"]

    output = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with open("epg.xml", "wb") as f:
        f.write(output)

    print(f"Wrote epg.xml ({len(output):,} bytes)")

    # Coverage report
    found = sum(1 for _, aliases in CHANNEL_ALIASES.items()
                if any(a in name_to_id for a in aliases))
    missing = [c for c, aliases in CHANNEL_ALIASES.items()
               if not any(a in name_to_id for a in aliases)]
    print(f"Coverage: {found}/{len(CHANNEL_ALIASES)} channels")
    if missing:
        print(f"Missing channels: {missing}")


if __name__ == "__main__":
    main()