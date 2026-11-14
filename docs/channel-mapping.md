# 对齐频道

XMLTV 的 `channel id` 必须与 M3U 中的 `tvg-id` 一致。按以下步骤修正自己的列表，或为新频道配置稳定 ID。

## 将固定 ID 写入播放列表

在仓库根目录运行，替换 `--playlist` 为实际 M3U 路径。使用 `--output` 先生成副本，便于核对：

```bash
python3 apply_ids.py \
  --playlist /path/to/IPTV.m3u \
  --output /tmp/IPTV-with-epg.m3u \
  --tvg-url https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml
```

脚本根据 [channel_map.json](../channel_map.json) 的固定映射写入 `tvg-id`，并更新首行的 `x-tvg-url`。省略 `--output` 会改写输入文件。它只修正配置中已有的映射，不会给所有未知频道自动补 ID。

## 新增或修正频道

1. 在 `ids` 中给频道分配稳定 ID。已知源 ID 可沿用；地方台和轮播频道使用 `gx-*`、`hot-*` 等项目 ID。
2. 若源中的名称与 M3U 不同，在 `aliases` 中补上实际别名。
3. 如果频道没有固定节目表，将名称加入 `skip`。这些频道仍输出 `channel` 节点，只跳过节目匹配。
4. 运行 `apply_ids.py` 更新 M3U，再使用同一列表运行 `build_epg.py`。
5. 在 `build_report.json` 的 `channels` 中核对 ID、节目数和数据来源。

例如，配置已经用 `广西综艺` 作为 `广西综艺旅游` 的源名称别名。已有 ID 修正包括 `CCTV16 → 1864`、`金鹰纪实 → 1324`、`凤凰卫视香港台 → phoenix-hk`。

生成脚本对未指定 ID 的频道还有哈希兜底；长期维护时仍应配置稳定 ID，避免名称变化影响匹配。

## 对齐 4K 与高清版本

配置中以下频道共用节目单 ID，并用别名连接到高清频道：

| 播放列表频道 | 匹配节目单 |
|---|---|
| CCTV-16 4K | CCTV16 |
| 北京卫视4K | 北京卫视 |
| 广东卫视4K | 广东卫视 |
| 河北4K | 河北卫视 |

这种处理合并的是节目安排，不改变播放流的清晰度。

## 频道存在但节目为空

先检查频道是否在 `skip` 中，再检查报告的源错误和频道匹配结果。部分地方台尚无可用公开节目数据；购物、自办或轮播频道也可能没有固定节目表。不要仅因节目为空删除频道，也不要为它填入其他频道的节目。

返回[文档索引](index.md)，或查看[节目合并规则](merging.md)。
