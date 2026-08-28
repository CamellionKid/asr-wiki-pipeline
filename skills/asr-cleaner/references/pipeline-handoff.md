# ASR 清洗到生活日志的交接契约

把 hook 视为可验证的管道检查点，不依赖某个 Agent 是否“记得继续”。每批已转写文字使用独立的 `pipeline_id`、运行目录和 JSON manifest。

## 运行目录与稳定标识

默认运行目录：

```text
/tmp/asr-life-log/<pipeline-id>/
├── handoff.json
├── raw-transcript.txt         # 用户提供的原始转写，保持不变
├── cleaned-transcript.md      # 忠实清洗稿，不做语义压缩
└── cleaning-report.md
```

`pipeline_id` 使用 `asr-<YYYYMMDD>-<源文件 SHA-256 前 12 位>`。相同来源在同一记录日期重试时得到相同 ID，用于防止重复追加。

本契约只接受 `raw_transcript`。音频或视频必须在进入本管道前由用户侧完成转写；本地管道不提供媒体转写。

## Manifest 最小结构

```json
{
  "schema_version": 1,
  "pipeline_id": "asr-20260825-0123456789ab",
  "record_date": "2026-08-25",
  "source": {
    "type": "raw_transcript",
    "path": "/absolute/path/raw-transcript.txt",
    "sha256": "...",
    "language": "zh"
  },
  "transcription": {
    "status": "provided",
    "transcript_path": "/absolute/path/raw-transcript.txt"
  },
  "cleaning": {
    "status": "completed_with_uncertainty",
    "cleaned_text_path": "/tmp/.../cleaned-transcript.md",
    "report_path": "/tmp/.../cleaning-report.md",
    "pending_items": ["[名词待确认: ...]"],
    "category_hints": ["动作层", "判断层"]
  },
  "safety": {
    "sensitive_data": "none",
    "archive_confirmed": false
  },
  "archive": {
    "requested": true,
    "status": "pending",
    "target_path": null,
    "daily_log_path": null
  }
}
```

Manifest 只传状态和路径，不复制整段转录，避免上下文截断与 JSON 转义问题。下游必须从 `cleaned_text_path` 读取正文，从 `report_path` 读取噪声和待确认项。

## 生命周期 hooks

| Hook | 通过条件 | 失败行为 |
|---|---|---|
| `on_input_received` | 输入为文字、记录日期和源文件已确定；已创建 manifest | 收到媒体或日期有歧义时停止并说明 |
| `after_cleaning` | 清洗稿和报告均存在；敏感数据状态已检查 | 产物不完整时不调用下游 |
| `before_life_log` | validator 返回 `valid: true`，且 `archive.requested=true` | 保留产物并报告阻塞项 |
| `after_life_log` | 目标笔记和 Daily Log 存在；批次 marker 与双链可验证 | 将 archive 标为 `failed`，不得宣称归档成功 |

## CLI 契约

从 `asr-cleaner` Skill 根目录运行：

```bash
# 1. 创建 manifest；输出 JSON 中包含 manifest_path
python3 scripts/handoff_contract.py create \
  --input-type raw_transcript \
  --source-path "/absolute/path/raw-transcript.txt" \
  --record-date 2026-08-25 \
  --language zh

# 2. 清洗完成后登记产物
python3 scripts/handoff_contract.py mark-cleaned \
  --manifest "/tmp/asr-life-log/<pipeline-id>/handoff.json" \
  --cleaned-text-path "/tmp/.../cleaned-transcript.md" \
  --report-path "/tmp/.../cleaning-report.md" \
  --sensitive-data none \
  --category-hint 动作层 \
  --category-hint 判断层

# 3. 调用 asr-life-log 前做硬校验
python3 scripts/handoff_contract.py validate \
  --manifest "/tmp/asr-life-log/<pipeline-id>/handoff.json" \
  --stage before-life-log

# 4. asr-life-log 写入并验证后回填结果
python3 scripts/handoff_contract.py complete \
  --manifest "/tmp/asr-life-log/<pipeline-id>/handoff.json" \
  --status completed \
  --target-path "/absolute/path/YYYY-MM-DD 生活记录.md" \
  --daily-log-path "/absolute/path/YYYY-MM-DD.md"

python3 scripts/handoff_contract.py validate \
  --manifest "/tmp/asr-life-log/<pipeline-id>/handoff.json" \
  --stage after-life-log
```

检测到候选人、员工或其他敏感个人数据时，使用相应的 `--sensitive-data`；只有获得明确归档确认后才能加入 `--archive-confirmed`。

## Skill 调用规则

1. 清洗完成并通过 gate 后，通过当前运行时注册的 Skill 加载机制，以精确名称调用 `asr-life-log`。
2. 若运行时不支持嵌套 Skill 调用，读取该运行时已注册入口所指向的 `asr-life-log/SKILL.md`，在当前任务内继续执行；不要只把“下一步请运行另一个 Skill”留给用户。
3. 调用时同时传递 manifest 路径、清洗稿路径和清洗报告路径。不要依赖对话上下文隐式交接正文。
4. `asr-life-log` 回填同一个 manifest。不要创建第二份状态文件。

## 幂等 marker

`asr-life-log` 必须把以下 Obsidian 隐藏注释写入当日生活记录：

```markdown
%% asr-pipeline:<pipeline-id> %%
```

写入前先搜索 marker：

- 已存在：不重复追加，归档状态记为 `noop`，继续验证 Daily Log 双链。
- 不存在：写入本批内容与 marker，归档状态记为 `completed`。
