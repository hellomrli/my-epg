# my-epg

多源 EPG（电子节目指南）聚合项目，为 [my-IPTV](https://github.com/hellomrli/my-IPTV) 的播放列表提供节目单。

旧版只从老张 EPG 拉一份 `e.xml`，频道少、单点故障。现在改为**多源抓取 + 按频道合并 + 源失效自动切换**：即使老张的源再次挂掉，也会自动用 gitee 镜像、112114、epg.pw 等源顶上。

## EPG 地址

```text
https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml
```

在 m3u 里使用：

```m3u
#EXTM3U x-tvg-url="https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml"
```

## 当前覆盖

以 `my-IPTV` 的 124 条频道为基准（4 组 4K 频道与高清频道共用 EPG id）：

| 项目 | 数量 |
|---|---|
| 播放列表频道 | 124 条 |
| EPG 频道节点 | 120 个 |
| 有节目单的频道 | 101 个 |
| 暂无节目单 | 19 个 |

已覆盖：央视 1–17、CCTV4K、全部省级卫视、凤凰中文/资讯/香港、广西省级 4 台、广西 8 个地市台（柳州、玉林、北海、百色、来宾、防城港、崇左、钦州）、精彩热播/睛彩/黑莓/哒啵等运营商轮播频道。

**暂无公开 EPG 的频道**（13 个广西地市台 + 6 个无节目单频道）：

- 南宁新闻综合、南宁影视娱乐、南宁文旅生活
- 柳州科教
- 桂林新闻综合、桂林科教旅游、桂林公共频道
- 贵港新闻综合、贵港科教生活
- 梧州新闻综合、梧州教育生活
- 贺州综合、河池新闻综合
- 广西乐思购、广西移动、咪咕4K、绝对巨星C罗、绝对巨星梅西、世界杯经典回顾

前 13 个是城市台，公开 EPG 源（51zmt / 112114 / epg.pw / erw）均未收录，只有运营商内部 EPG 才有；后 6 个是购物/自办/轮播频道，本身没有固定节目表。这些频道仍会在 `epg.xml` 里保留 `channel` 节点，播放器显示“暂无节目信息”，不会报错。

4K 频道采用高清频道的节目单：`CCTV-16 4K` 用 CCTV16，`北京卫视4K`/`广东卫视4K`/`河北4K` 分别用北京卫视/广东卫视/河北卫视。

## 数据源

| 优先级 | 源 | 说明 | 覆盖 |
|---|---|---|---|
| 10 | [老张EPG e1](http://epg.51zmt.top:8000/e1.xml.gz) | 央视/卫视/数字付费/省级地方台，含节目详情，约 2 天 | 176 频道 |
| 10 备用 | [gitee 镜像](https://gitee.com/taksssss/tv/raw/main/epg/51zmte1.xml.gz) | 老张主站失效时自动切换 | 同上 |
| 20 | [112114](https://epg.112114.xyz/pp.xml) | 聚合源，含部分广西地市台，当天数据 | 约 540 频道 |
| 20 备用 | [gitee 镜像](https://gitee.com/taksssss/tv/raw/main/epg/112114.xml.gz) | 112114 主站失效时使用 | 同上 |
| 30 | [epg.pw 中国区](https://epg.pw/xmltv/epg_CN.xml.gz) | 提供未来 7 天，用于补齐后几天 | 约 700 频道 |
| 40 | [kuke31/xmlgz](https://raw.githubusercontent.com/kuke31/xmlgz/main/all.xml.gz) | erw 免费版，含睛彩/黑莓/哒啵等轮播频道 | 约 500 频道 |
| 50 | [CCSH/IPTV](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml.gz) | 频道 id 体系与 51zmt 一致，最后兜底 | 约 395 频道 |

合并规则：

1. 同一组内按顺序尝试，第一个成功的源生效（老张挂了自动用 gitee 镜像）。
2. 组与组之间按优先级合并：高优先级源先占时段，低优先级源只补空档，不会重复。
3. 只输出播放列表里存在的频道，控制文件体积（当前约 1.8 MB / 7 天）。

## 目录结构

```text
.
├── build_epg.py            # 多源抓取、合并、输出 XMLTV
├── apply_ids.py            # 把固定 tvg-id 写回 IPTV.m3u
├── sources.json            # 源配置（增删源改这里）
├── channel_map.json        # 频道 id / 别名 / 跳过名单
├── update_epg.sh           # 每日构建脚本（含校验、提交）
├── epg.xml                 # 生成的节目单
└── .github/workflows/
    └── epg_update.yml      # 每天北京时间 06:00 自动更新
```

## 本地运行

```bash
# 直接抓远程播放列表并生成
python3 build_epg.py

# 用本地播放列表 + 本地源缓存调试（不联网）
python3 build_epg.py \
  --playlist-file ../my-IPTV/IPTV.m3u \
  --source-cache /tmp/epg-cache

# 只看统计
cat build_report.json
```

`--source-cache` 目录按源名缓存 `.xml`，存在时直接读缓存，方便反复调试合并逻辑。

## 频道 id 对齐

`epg.xml` 的 `channel id` 与 `IPTV.m3u` 的 `tvg-id` 必须一致。目前：

- 央视/卫视沿用 51zmt 的数字 id（`CCTV1=1`、`湖南卫视=27`…）。
- 广西省级台用 51zmt 的 `892/893/895/897`。
- 广西地市台和轮播频道用 `gx-*` / `hot-*` 固定 id。
- 4K 频道与高清频道共用 id。

修正过的旧 id：

| 频道 | 旧 id | 新 id |
|---|---|---|
| CCTV16 | 7249 | 1864 |
| 金鹰纪实 | 2025 | 1324 |
| 凤凰卫视香港台 | 143 | phoenix-hk |

如果 `IPTV.m3u` 重新从上游同步后 id 丢失，运行：

```bash
python3 apply_ids.py \
  --playlist ../my-IPTV/IPTV.m3u \
  --tvg-url https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml
```

## 新增频道

1. 在 `channel_map.json` 的 `ids` 里给新频道分配一个稳定 id（没有就先用 `ch-` 哈希兜底）。
2. 如果各源里的叫法和播放列表不一致，在 `aliases` 里加别名，例如：

```json
"广西综艺旅游": ["广西综艺", "广西综艺旅游"]
```

3. 确认不需要节目单的频道放进 `skip`，避免每天做无意义的匹配。
4. 本地跑一次 `build_epg.py`，看 `build_report.json` 里该频道是否拿到节目。

## 数据更新

- 每天北京时间 **06:00**（UTC 22:00）自动构建。
- 构建失败会重试 3 次；全部失败时保留旧 `epg.xml`，不会把空文件推上去。
- 只有 `epg.xml` 有变化时才提交。

## 致谢

EPG 数据来源：[老张EPG](http://epg.51zmt.top:8000/)、[112114](https://epg.112114.xyz/)、[epg.pw](https://epg.pw/)、[kuke31/xmlgz](https://github.com/kuke31/xmlgz)、[CCSH/IPTV](https://github.com/CCSH/IPTV)、[taksssss/tv](https://gitee.com/taksssss/tv) 镜像。

本项目仅做格式转换与聚合，节目数据版权归原始提供方所有，仅供个人使用。
