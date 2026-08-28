---
name: asr-pipeline
description: ASR 知识管道主入口。接收 Raw 笔记或粘贴转写，先登记 51 Raw，再调用 asr-cleaner 只清洗不归档，询问方向后分流到自我面试、HR 旁观面试、会议分享（台上演讲/黑客松），或通用归档，并在 52 Wiki 生成文档包。用户说「处理这段 ASR」「面试 ASR」「黑客松转写」「台上分享做成 Wiki」时使用。不接收音频视频；一面二面对照用 interview-round-compare。
---

# ASR Pipeline

主调度器。把原始转写变成「51 Raw 原文 + 52 Wiki 文档包」。面试分析由子 Skill 完成；本 Skill 负责登记、清洗编排、询问、落盘、归档路由和 Daily Log。

```text
输入 → Raw 登记 → asr-cleaner（只清洗）→ 询问方向 → 子 Skill → Wiki 包 + 地图 → filing → Daily Log
```

## 加载参考

- 开始前读 [references/pipeline-flow.md](references/pipeline-flow.md)
- 写或重命名任何 Vault 笔记前读 [references/storage-rules.md](references/storage-rules.md)

子 Skill 按精确名称加载其 `SKILL.md` 并在本任务内执行。不要把「请再运行另一个 Skill」丢回给用户。

| 方向 | 调用链 |
| --- | --- |
| 自我面试 | `interview-qa-extract` → `interview-self-analysis` → `experience-extraction` |
| HR 旁观面试 | 问清岗位名 → `interview-qa-extract` → `interview-observer-analysis` → `experience-extraction` |
| 会议分享 | `talk-share-extract` → `experience-extraction`（输入 01 原文 + 横向分析，不跑面试三件套） |
| 其他 | `darren-archive` + `knowledge-compiler` 通用编译 |

`interview-round-compare` 不在本管道自动触发。

## 输入

只接受文字：

- Vault 里的 Raw 笔记路径或双链
- 对话粘贴的原始转写（先写入 `/tmp/asr-interview/intake/` 唯一文件）
- 可选：日期、公司、岗位、轮次、方向

收到音频/视频时停止，请用户先转写。

## 完成条件

1. Raw 笔记存在，含 YAML，正文未被改写
2. asr-cleaner 清洗稿与报告存在，`archive.requested=false`
3. 方向已由用户确认（不得猜测）
4. 对应 Wiki 文档包与 `<活动名>｜文档地图.md` 已写入
5. 已调用 filing/归档路由
6. 当日 Daily Log 含 RawRead 与 Wiki 双链
7. 已对 Wiki 包运行 `scripts/verify_pack.py --pack-dir <包目录> --cleaned <cleaned-transcript.md>`，七项全 PASS；有 FAIL 不算完成，结果贴进汇报

用户说「只清洗」时，完成 1–2 后停止。

## 工作流摘要

逐步操作、失败回退、manifest 字段见 pipeline-flow.md。此处只列不可省略的门闩。

1. **Raw 登记**：粘贴文本则 `obsidian create` 进 51 Raw；已有笔记则只补 YAML、规范命名、frontmatter 双链。禁止改 ASR 正文。
2. **清洗**：加载 `asr-cleaner`，明确「只清洗、不要归档」。复用其 `/tmp/asr-life-log/<pipeline-id>/handoff.json`。不要调用 `asr-life-log`。
3. **询问**：保存方向（自我面试 / HR 旁观面试 / 会议分享 / 其他）。旁观面试必须再问岗位名。会议分享再确认活动名。用户已声明「会议/黑客松/台上分享」时不要再问面试分支。
4. **分流**：把 `pipeline.json`、清洗稿路径、问答将要使用的路径传给子 Skill；不要只在对话里贴长文。
5. **Wiki 包**：按 storage-rules 在 52 Wiki 创建包文件夹和文档地图，链回 Raw 与各产物。写完后对包运行 `scripts/verify_pack.py --pack-dir <包目录> --cleaned <cleaned-transcript.md>`，FAIL 则回头修，不算完成。
6. **Filing**：调用 `file-classification-johnny-decimal`（Vault 内会转到 `darren-archive`）。领域未定时先放 `51.07 Raw 输入待分类` 对应的 Wiki 暂存策略见 storage-rules。
7. **Daily Log**：追加 RawRead 与 Wiki 地图双链。

## 敏感数据

旁观面试默认按含候选人个人数据处。未获「确认归档」前：分析可做，Wiki 中对姓名与可识别前雇主做最小化；`pipeline.json` 的 `safety.sensitive_data` 如实登记。自我面试按 Darren 本人材料处理。

## Vault 写入

所有笔记读写用 `obsidian` CLI。不要用通用文件工具直写 Vault。临时清洗产物留在 `/tmp`，不要把清洗稿回写进 51 Raw。

## 停止条件

日期冲突、方向未答、asr-cleaner gate 失败、或用户改口只要对照多轮时，保留已有产物并说明卡在哪一步。
