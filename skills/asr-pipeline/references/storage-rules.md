# Raw / Wiki 存储规则

## 目录

- [Raw 命名与 YAML](#raw-命名与-yaml)
- [Raw 落点](#raw-落点)
- [Wiki 包](#wiki-包)
- [文档地图](#文档地图)
- [Daily Log 与双链](#daily-log-与双链)

## Raw 命名与 YAML

文件名：

```text
<公司或来源>-<岗位或主题>-<轮次>-<日期> ASR原始转写.md
```

未知段用 `未命名`，问清后 `obsidian move` 重命名。不要为了改名而改正文。

YAML（前置到原文之前；已有 frontmatter 则只补缺字段）：

```yaml
title:
date: YYYY-MM-DD
type: asr-raw
domain: HR | AI | Philosophy | Market Intelligence | Investment | Common | Cross-domain
interview_role: self | observer | NA
event_type: talk | hackathon | meetup | workshop | NA
event_name:
company:
position:
round:
pipeline_id:
compile_status: raw
source_id:
tags:
  - kb/layer/raw
  - kb/type/transcript
related: []
```

`interview_role` 在询问方向前可为 `NA`。询问后再 `obsidian property:set`。

禁止：改写 ASR 正文、把清洗稿覆盖进 Raw、删除用户已有的 YAML 字段。

## Raw 落点

先定 layer=Raw，再定 domain（沿用 knowledge-compiler 的 domain-routing 含义）。

| 情况 | 目录 |
| --- | --- |
| 新进 ASR（待清洗） | `51-60 知识编译系统（Vault）/51 原始资料（Raw）/51.08 ASR（Raw）/ASR-待清洗` |
| 已补 YAML、已清洗交接的 ASR | `51-60 知识编译系统（Vault）/51 原始资料（Raw）/51.08 ASR（Raw）/ASR-清洗完成` |
| HR 领域已编译转写（可选） | `51-60 知识编译系统（Vault）/51 原始资料（Raw）/51.01 人力资源（HR）/51.01.01 录音转写（Transcripts）` |
| 领域未定 | `51-60 知识编译系统（Vault）/51 原始资料（Raw）/51.07 Raw 输入待分类` |

本管道默认把原始转写留在 `51.08 ASR（Raw）`：待清洗进 `ASR-待清洗`，YAML 与命名补齐后 `obsidian move` 到 `ASR-清洗完成`。不要把清洗稿覆盖进 Raw 正文。HR 面试不要仅为了归类而复制一份到 51.01.01，除非 filing 明确要求。

## Wiki 包

一次转译一个包，文件夹名：

```text
<公司或来源>-<岗位或主题>-<轮次>-<日期>
```

默认父目录（domain 已定）：

| domain | 父目录 |
| --- | --- |
| HR | `52 编译产物（Wiki）/52.01 人力资源（HR）/52.01.05 语音转录总结` |
| AI | `52 编译产物（Wiki）/52.02 人工智能（AI）/52.02.06 语音转录总结` |
| Philosophy | `52 编译产物（Wiki）/52.03 哲学（Philosophy）/52.03.06 语音转录总结` |
| Market Intelligence | `52 编译产物（Wiki）/52.06 市场营销与市场洞察（Market Intelligence）/52.06.03 摘要（Summaries）` |
| 未定 | 先在 52 对应暂存不可用时，仍创建包并立即调用 filing，不要长期留在 Raw |

包内文件（「文件」列只写角色名；落盘时一律用「<活动名>｜<角色>」格式，如 `01 HR Max 黑客松 2026-08-15｜一问一答.md`，见下方命名规则）：

| 角色 | 谁产生 | 何时 |
| --- | --- | --- |
| 文档地图 | asr-pipeline | 全部产物写完后 |
| 一问一答 | interview-qa-extract | 自我 / 旁观 |
| 逐题评分 | interview-self-analysis | 仅自我 |
| 多视角评估（SSC·BP·COE） | interview-self-analysis | 仅自我 |
| 面试官分析 | interview-observer-analysis | 仅旁观 |
| 一问一答 / 全文转写 | talk-share-extract | 会议分享（原文完整重排；有问答出一问一答，否则全文转写） |
| 议程与发言人 | talk-share-extract | 会议分享 |
| 分享纪要 | talk-share-extract | 会议分享 |
| 现场问答 | talk-share-extract | 会议分享（索引，原文在 01） |
| 横向分析 | talk-share-extract | 会议分享（跨场次主题综合，核心产物） |
| 经验萃取 | experience-extraction | 自我 / 旁观 / 会议分享（会议按主题出深卡） |

其他方向不建面试包或会议包；按 knowledge-compiler 的摘要/概念规则写单篇 Wiki。HR 会议包与面试包一样进 `52.01.05 语音转录总结`。

Wiki 笔记 YAML 最低字段：`type`、`date`、`domain`、`company`、`position`、`round`、`pipeline_id`、`source`（指 Raw）、`origin_type: interview-analysis`。经验萃取再加 `source_id`。分配新号前先读 `52.01.01 索引（Indexes）/HR-Sources.md`（HR 域）或对应域注册表，取最大已用号 +1；不要靠全库 grep 防撞，也不要复用表中已有的 SRC-HR-NNNN。

## 文档地图

`<活动名>｜文档地图.md` 用紧凑列表，固定字段顺序（文档地图不加 NN 序号）：

```markdown
# <公司/活动名> <岗位> <轮次>｜文档地图

- 原始转写 · [[<Raw 名>]] · 加入：YYYY-MM-DD
- 一问一答 · [[<活动名>｜一问一答]]
- 逐题评分 · [[<活动名>｜逐题评分]]
- 多视角评估 · [[<活动名>｜多视角评估（SSC·BP·COE）]]
- 经验萃取 · [[<活动名>｜经验萃取]]
```

旁观分支把逐题评分 / 多视角两行换成 `面试官分析 · [[<活动名>｜面试官分析]]`。会议分享换成：一问一答或全文转写、议程、纪要、现场问答、横向分析（同样带活动名前缀）。不存在的文件不要预链。地图文件名用活动名，避免重名。`obsidian move` 的目标路径必须带 `.md`，否则会丢掉扩展名。

地图 YAML：`type: interview-pack-moc`（会议包用 `talk-pack-moc`），`related` 列出包内全部笔记和 Raw。**包内文件名一律用「NN <活动名>｜<文件角色>」格式**（NN 为两位序号，如 `01 HRBP 运营团队（长沙）一面｜一问一答.md`；文档地图不加序号）。序号保证包内排序，活动名前缀保证跨包唯一——短名会在第二个包出现时撞名，导致双链误解析。

历史包例外（规则生效前已落盘，除非用户要求不要批量改）：

- 首个历史包（苏州科达）保留短文件名，作为 `[[01 一问一答]]` 等短链的唯一解析目标，不要再创建无前缀短名文件。
- HRMax 黑客松 2026-08-15：该包 01 仍是议程、无全文层，属规则生效前产物；除非用户要求补 01 全文，否则不要顺延改名。

## Daily Log 与双链

写完后：

```markdown
- [x] RawRead [[<Raw 名>]]
- [x] Wiki [[<地图名>]]
```

并 `obsidian backlinks` / `obsidian links` 抽查 Raw 与地图。最短文件名能解析即可，不要手写已过期的长路径前缀。
