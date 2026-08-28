# ASR Pipeline 流程与交接

## 目录

- [运行目录](#运行目录)
- [pipeline.json](#pipelinejson)
- [步骤](#步骤)
- [调用子 Skill](#调用子-skill)
- [失败回退](#失败回退)

## 运行目录

```text
/tmp/asr-interview/<pipeline-id>/
├── pipeline.json
├── intake/                  # 粘贴文本的唯一种子，不覆盖
└── wiki-preview/            # 落 Vault 前的正文草稿
```

`pipeline_id` 优先复用 asr-cleaner 的 `asr-<YYYYMMDD>-<源 SHA-256 前 12 位>`。尚未清洗时用同一公式，源文件为 Raw 正文或 intake 文件。

asr-cleaner 产物仍在：

```text
/tmp/asr-life-log/<pipeline-id>/
├── handoff.json
├── raw-transcript.txt
├── cleaned-transcript.md
└── cleaning-report.md
```

不要复制整段转录进 JSON。

## pipeline.json

```json
{
  "schema_version": 1,
  "pipeline_id": "asr-20260827-0123456789ab",
  "record_date": "2026-08-27",
  "direction": "self | observer | talk | other | unset",
  "company": null,
  "position": null,
  "round": null,
  "domain": null,
  "raw_note_path": null,
  "asr_handoff_path": null,
  "cleaned_text_path": null,
  "report_path": null,
  "qa_path": null,
  "wiki_pack_dir": null,
  "artifacts": [],
  "safety": {
    "sensitive_data": "none | candidate | employee | mixed",
    "archive_confirmed": false
  },
  "cleaning": {
    "archive_requested": false,
    "status": "pending"
  }
}
```

主 Skill 创建并更新这一份文件。子 Skill 只读路径字段，不另起状态文件。

## 步骤

### Step 0 接收输入

- 粘贴文本：写入 `intake/` 下带时间戳的新文件，再以此为 source。
- Vault 笔记：`obsidian read`。若无 YAML，按 storage-rules 前置 YAML，不改正文。
- `record_date`：用户明确日期 > 文本内可靠日期 > 当前 Asia/Shanghai 日期。冲突则问。

### Step 1 Raw 登记

按 storage-rules 命名并放入 51 Raw。不确定领域 → `51.07 Raw 输入待分类`。HR 面试原文 → `51.01.01 录音转写（Transcripts）`。

创建 `pipeline.json`。

### Step 2 asr-cleaner

加载已注册的 `asr-cleaner`，并在创建 manifest 时强制 `--no-archive`：

```bash
python3 "<asr-cleaner>/scripts/handoff_contract.py" create \
  --input-type raw_transcript \
  --source-path "/absolute/path/to/source.txt" \
  --record-date YYYY-MM-DD \
  --language zh \
  --no-archive
```

然后按 `asr-cleaner` SKILL.md 做忠实清洗，调用 `mark-cleaned`。确认 `handoff.json` 里 `archive.requested=false`。回填 `cleaned_text_path`、`report_path`、`asr_handoff_path`。

不要调用 `asr-life-log`。清洗失败则停止，不询问方向装成已分析。

### Step 3 询问方向

必须等待用户回答。选项：

1. 自我面试（我是候选人）
2. HR 旁观面试（我作为 HR 参与或旁听）
3. 会议分享（台上演讲、黑客松、meetup，有主持和作品/议题场次）
4. 其他方向（课程、marketing、通用知识等）

旁观面试接着问岗位名称。自我面试若岗位/公司/轮次仍缺，也问，因为命名和 Wiki 包依赖它们。

### Step 4 子 Skill

把路径写入 `pipeline.json` 再调用。执行顺序见主 SKILL.md 表格。

每个子 Skill 返回 Markdown 正文 + 建议文件名。主 Skill 写入 `wiki-preview/`，确认无 Raw 正文污染后再 `obsidian create`。

### Step 5 Wiki 包与地图

按 storage-rules 建包。`<活动名>｜文档地图.md` 最后写，保证链接目标已存在。文档地图不加 NN 序号。随后运行 `scripts/verify_pack.py --pack-dir <包目录> --cleaned <cleaned_text_path>`，FAIL 不算完成。

### Step 6 Filing

调用 `file-classification-johnny-decimal`。Vault 笔记应被路由到 `darren-archive`。不要在本 Skill 里复制一套 Johnny Decimal 规则。

### Step 7 Daily Log

```markdown
- [x] RawRead [[<Raw 笔记名>]]
- [x] Wiki [[<活动名>｜文档地图]]
```

若有 `source_id`，再补一行 Wiki 摘要双链。

## 调用子 Skill

1. 用当前运行时的 Skill 加载机制按精确名称调用。
2. 若不支持嵌套调用：读取该 Skill 的 `SKILL.md` 与需要的 references，在本任务内完整执行。
3. 调用时传递 `pipeline.json` 路径、`cleaned_text_path`、`qa_path`（若已有）。
4. `experience-extraction` 需要问答或分析已存在；不要对未切分的清洗稿直接萃取。从 `pipeline.json` 的 `qa_path` 读 01 原文，不从纪要读。
5. 方向为 `talk` 时调用 `talk-share-extract`（它自己产出会议版 01 一问一答或全文转写）。01 落盘后必须把该文件的绝对路径回填进 `pipeline.json` 的 `qa_path`，再把 **01 原文 + 横向分析** 交给 `experience-extraction`。禁止调用 `interview-qa-extract`。
6. 方向为 other 时禁止调用面试三件套和会议纪要套件。

## 失败回退

| 失败点 | 行为 |
| --- | --- |
| 媒体输入 | 停止，不创建管道 |
| Raw 已存在且正文将被改写 | 停止 |
| asr-cleaner 未给出清洗稿 | 保留 Raw，报告清洗错误 |
| 方向未回答 | 保留 Raw 与清洗稿，不写分析 |
| 子 Skill 中途失败 | 保留已完成产物，文档地图只链已存在文件 |
| filing 失败 | 笔记已在 Wiki 暂存路径则报告路径，不假装已分类 |
| Daily Log 失败 | 仍报告 Wiki 路径，并标明日志未回写 |
