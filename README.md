# my-epg

为 IPTV 播放列表聚合多源 XMLTV 节目单，按频道 ID 对齐，并用备用源补齐节目时段。

[节目单](epg.xml) · [维护文档](docs/index.md) · [自动更新](https://github.com/hellomrli/my-epg/actions/workflows/epg_update.yml) · [配套播放列表](https://github.com/hellomrli/my-IPTV)

## 在播放器中使用

将下面的地址填入支持 XMLTV 的播放器的 EPG 设置：

```text
https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml
```

如果通过 M3U 指定节目单，在播放列表第一行使用：

```m3u
#EXTM3U x-tvg-url="https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml"
```

播放器会根据频道的 `tvg-id` 匹配节目。默认数据对应 [my-IPTV](https://github.com/hellomrli/my-IPTV)；其他播放列表需要先对齐 ID。

## 节目单如何更新

- 每天北京时间 06:00 运行自动更新，也可以在 Actions 手动触发。
- 同一源组按顺序尝试主站与镜像；不同组按优先级合并，高优先级先占时段，其他源补空档。
- 默认输出从北京时间当天零点起的 7 天窗口。实际天数取决于上游提供的数据。
- 只输出播放列表中的频道；没有节目数据的频道仍保留 XMLTV `channel` 节点。
- 自动任务最多尝试 3 次，校验 XML 和节目是否非空，通过后才提交变化。

频道覆盖和节目数量随上游变化。运行后的 `build_report.json` 会列出各源状态、每个频道的节目数和未匹配频道，适合排查缺失节目。

## 从源码生成

需要 Python 3，无第三方 Python 依赖。以下命令会访问配置中的上游源，并在仓库目录生成节目单和统计报告：

```bash
git clone https://github.com/hellomrli/my-epg.git
cd my-epg
python3 build_epg.py
```

成功后会出现 `epg.xml` 和 `build_report.json`。默认播放列表是 my-IPTV 的 `IPTV.m3u`；使用自己的列表时，传入实际路径：

```bash
python3 build_epg.py --playlist-file /path/to/IPTV.m3u --output epg.xml
```

命令参数、缓存行为和频道映射步骤见[维护文档](docs/index.md)。

## 数据与配置

| 文件 | 用途 |
|---|---|
| [sources.json](sources.json) | 上游源组、备用地址和合并优先级 |
| [channel_map.json](channel_map.json) | 固定频道 ID、别名和不匹配节目单的频道 |
| [build_epg.py](build_epg.py) | 下载、频道匹配、时段合并和 XMLTV 输出 |
| [apply_ids.py](apply_ids.py) | 将固定 ID 和 EPG 地址写入 M3U |
| [update_epg.sh](update_epg.sh) | 自动任务的重试、校验和 Git 提交步骤 |

## 来源与反馈

数据源包括 [老张 EPG](http://epg.51zmt.top:8000/)、[112114](https://epg.112114.xyz/)、[epg.pw](https://epg.pw/)、[kuke31/xmlgz](https://github.com/kuke31/xmlgz)、[CCSH/IPTV](https://github.com/CCSH/IPTV) 和 [taksssss/tv 镜像](https://gitee.com/taksssss/tv)。本项目做格式转换与聚合，节目数据版权归原始提供方，沿用原项目的个人使用说明。

报告缺失频道时，在 [Issues](https://github.com/hellomrli/my-epg/issues) 提供频道名、`tvg-id`、节目单日期及相关构建日志。仓库目前没有根目录许可证文件。
