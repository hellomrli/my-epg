# my-epg

EPG（电子节目指南）中转项目，每日自动从 [老张EPG](http://epg.51zmt.top:8000/) 拉取节目数据并推送到 GitHub，为 IPTV 提供节目单支持。

## 频道覆盖

- **央视**：CCTV1～CCTV17（共17个频道）
- **省级卫视**：东方卫视、北京卫视、江苏卫视、浙江卫视、湖南卫视等全国省级卫视
- **国际频道**：凤凰卫视、CGTN
- **4K 频道**：CCTV4K 等

> 广西省市级地方频道不在本项目范围内。

## EPG 地址

```
https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml
```

### 在播放列表中使用

```m3u
#EXTM3U x-tvg-url="https://raw.githubusercontent.com/hellomrli/my-epg/main/epg.xml"
#EXTINF:-1 tvg-id="1" tvg-logo="..." group-title="央视",CCTV1
http://example.com/stream.m3u8
```

## 数据更新

- 每天 **北京时间 06:00**（UTC 22:00）自动更新
- 下载失败时自动重试（最多3次，间隔递增）
- 有变化时才推送到 GitHub，无变化则跳过

## 本地使用

下载 `epg.xml` 后配合 IPTV 播放列表使用，支持大多数主流 IPTV 客户端（Perfect Player、IPTVnator、懒人视频等）。

## 致谢

EPG 数据来源：[老张EPG](http://epg.51zmt.top:8000/)
