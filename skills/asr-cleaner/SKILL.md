---
name: asr-cleaner
description: 已转写录音文字的统一处理入口：接收用户提供的原始 ASR 文本或文本文件，做可追溯的忠实清洗，并通过显式 handoff 自动调用 asr-life-log 分类归档到 Obsidian。用户说「清洗 ASR」「整理这段转写并归档」「帮我清洗这段录音文字」时使用。只接受文字，不接收或转写音频/视频；若文本已清洗或已语义压缩且只需归档，可直接使用 asr-life-log。
---

# ASR 清洗 → 生活日志统一入口

把用户已经转写好的录音文字处理成可追溯的生活日志。将 `asr-cleaner` 作为公开入口，编排忠实清洗和 `asr-life-log` 归档；不要让用户在 A、B 两个 Skill 之间手工搬运文本。

## 输入与完成条件

只接受：

- 对话内粘贴的原始 ASR 转录文字
- 本地原始 ASR 文本文件
- 可选的记录日期、语言和“只清洗、不归档”指令

音频或视频不是本 Skill 的输入。收到媒体文件时停止，并请用户先提供已经转写好的文字；不要调用本地或远程媒体转写服务。

默认完成条件：

1. 保留用户提供的原始转录。
2. 生成忠实清洗稿与清洗报告。
3. 自动调用 `asr-life-log`，写入当日生活记录并回填 Daily Log 双链。
4. 验证目标笔记、批次 marker、双链和 handoff 终态。

若用户明确说“只清洗”“不要归档”，完成第 1-2 项后停止，并把 manifest 的 `archive.requested` 设为 `false`。

## 职责边界

| 模块 | 唯一职责 |
|---|---|
| `asr-cleaner` | 已转写文字的忠实清洗、待确认标记、清洗报告、handoff 与管道编排 |
| `asr-life-log` | 语义压缩、分类整理、Obsidian 归档和双链验证 |

**清洗不等于语义压缩。** 清洗稿必须保留可追溯的事实、时间、说话人不确定性和原意；分类摘要由 `asr-life-log` 完成。

## 核心工作流

```text
用户提供的原始 ASR 文字 -> 忠实清洗 -> handoff gate -> asr-life-log -> 验证
```

### Step 0：接收文字并初始化 handoff

1. 确认输入是文字。对对话内文本先原样写入 `/tmp/asr-life-log/intake/` 下的唯一临时文件，再以该文件为 source；不要覆盖同名 intake。
2. 确定 `record_date`：用户明确日期 > 文本内可靠日期 > 当前 Asia/Shanghai 日期。跨日或日期证据冲突时先询问，不静默猜测。
3. 按 [references/pipeline-handoff.md](references/pipeline-handoff.md) 调用 `scripts/handoff_contract.py create --input-type raw_transcript`，创建 `/tmp/asr-life-log/<pipeline-id>/handoff.json`。
4. 不覆盖已存在的同一批次 manifest；把同一 `pipeline_id` 视为重试。

### Step 1：加载用户画像与系统记忆

按 [references/background-query.md](references/background-query.md) 检索系统级 `AGENTS.md` / `agent.md`、MCP 长期记忆及用户画像，构建专有名词纠错候选字典。记忆与画像仅提供纠错候选，不是录音事实来源，也不能单独证明说话人身份。

若记忆源或 MCP 不可用时直接进入降级模式：保留原词并标注 `[名词待确认: 原文]`，不要阻塞非敏感内容的清洗。

### Step 2：执行忠实清洗

按 [references/cleaning-rules.md](references/cleaning-rules.md) 逐类处理重复转写、语言错检、专有名词、说话人混杂、环境噪声、断句和填充词。

必须：

- 保留输入已有的时间戳或可恢复时段信息。
- 把不确定项显式留在清洗稿和报告中。
- 不把“未提到”改写成“没有”，不补写动机、结论或身份。
- 不为缩短篇幅删除有效事实；不要在本阶段写分类摘要。

### Step 3：生成清洗产物与分类提示

在本次运行目录写入：

- `cleaned-transcript.md`：完整、忠实、可追溯的清洗稿。
- `cleaning-report.md`：原始/清洗后字数、字数保留率、七类噪声统计、待确认项和降级信息。没有上游置信度时写“未提供”，不要臆造分数。
- manifest 中的 `category_hints`：仅记录动作层/判断层/背景层/元层候选，不修改清洗稿，不替代下游分类。

检查是否包含候选人、员工或其他敏感个人数据。通过 `mark-cleaned --sensitive-data ...` 明确登记；存在敏感数据时，未获用户明确归档确认不得使用 `--archive-confirmed`。

### Step 4：执行 before_life_log hook

按交接契约运行：

```bash
python3 scripts/handoff_contract.py validate \
  --manifest "/tmp/asr-life-log/<pipeline-id>/handoff.json" \
  --stage before-life-log
```

只有返回 `valid: true` 且 `archive.requested=true` 才能继续。失败时保留全部产物，报告具体 gate 错误，不要声称已归档。

### Step 5：显式调用 asr-life-log

1. 通过当前运行时注册的 Skill 加载机制，以精确名称调用 `asr-life-log`。
2. 传递同一个 manifest 路径、`cleaned_text_path` 和 `report_path`；不要只传对话里的正文。
3. 若运行时不支持嵌套 Skill 调用，读取已注册 `asr-life-log` 入口的 `SKILL.md` 并在当前任务内完整执行。不要把下一步留给用户。
4. `asr-life-log` 不得重复执行 ASR 清洗，只做语义压缩、分类、归档和验证。

### Step 6：执行 after_life_log hook

让 `asr-life-log` 回填同一个 manifest 后，运行 `validate --stage after-life-log`。只有以下项目全部通过才报告成功：

- 生活记录目标文件存在。
- 目标文件含 `%% asr-pipeline:<pipeline-id> %%`。
- Daily Log 存在指向生活记录的双链。
- `archive.status` 为 `completed` 或 `noop`。

## 边界

- 不接收或转写音频、视频；只处理用户提供的文字。
- 不删除、移动或覆盖用户提供的原始转录。
- 不在清洗阶段做最终分类、事实推断或语义摘要。
- 不静默修复低置信度名词、说话人或语言错检片段。
- 不把临时清洗产物写入 Vault；持久归档只由 `asr-life-log` 执行。
- 不把候选人或员工个人数据写入 Vault，除非用户明确确认本次归档。
- 不把“调用下游成功”当成“归档成功”；必须通过 after hook。
