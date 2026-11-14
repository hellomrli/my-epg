# 维护节目单

本页用于在已有仓库中生成 XMLTV、替换上游源或排查构建结果。命令在仓库根目录运行，需要 Python 3。

## 生成并检查结果

使用默认配置生成节目单：

```bash
python3 build_epg.py --output epg.xml --report build_report.json --days 7
```

检查 `build_report.json` 的 `summary`、`sources` 和 `channels`。`channels_without_programme` 表示没有节目数据的频道数量；它与播放器无法播放频道是不同的问题。

如果使用本地 M3U，将实际文件路径传给 `--playlist-file`。该选项优先于 `--playlist`：

```bash
python3 build_epg.py --playlist-file /path/to/IPTV.m3u --output epg.xml
```

所有参数可通过帮助查看：

```bash
python3 build_epg.py --help
```

## 使用源缓存复查合并

首次带上缓存参数运行，会下载上游并按源名写入 `.xml` 文件：

```bash
python3 build_epg.py --source-cache /tmp/epg-cache
```

之后可将本地播放列表和缓存一起用于复查：

```bash
python3 build_epg.py \
  --playlist-file /path/to/IPTV.m3u \
  --source-cache /tmp/epg-cache \
  --output /tmp/epg-preview.xml \
  --report /tmp/epg-preview-report.json
```

有效缓存存在时直接读取；缺少缓存或组内备用源没有缓存时，脚本仍可能联网。`--source-cache` 是缓存选项，不能将它当成离线开关。删除对应源的缓存文件后，下次会重新下载该源。

## 配置主站与备用源

编辑 [sources.json](../sources.json) 的 `groups`。每组包含 `name`、`priority` 和有序的 `sources` 列表；每个源需要稳定的 `name` 和 XML/XML.GZ 地址。

1. 将首选地址放在组内首位，镜像放在后面。
2. 为组设置优先级，数值越小越优先。
3. 重新构建，检查报告中每组实际采用的 `source`。

默认源组是老张 EPG、112114、epg.pw 中国区、kuke31 和 CCSH。主站、镜像与精确 URL 以配置文件为准。

## 自动任务失败

[更新工作流](../.github/workflows/epg_update.yml) 每天 UTC 22:00、即北京时间次日 06:00 执行 [update_epg.sh](../update_epg.sh)。脚本最多运行 3 次构建，之后检查 XML 是否可解析、频道和节目是否非空。

所有源不可用时，生成脚本退出并保留已有节目单。自动任务校验失败时不发布本轮数据；校验通过且 `epg.xml` 有变化才提交。`update_epg.sh` 包含 Git 提交和推送，单纯调试时使用 `build_epg.py`。

频道 ID 或名称没有匹配上时，继续查看[对齐频道](channel-mapping.md)。
