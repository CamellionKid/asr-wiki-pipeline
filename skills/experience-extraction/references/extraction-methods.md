# 经验萃取方法

## 目录

- [卡片模板](#卡片模板)
- [基础框架](#基础框架)
- [外部信源清单](#外部信源清单)
- [检索协议](#检索协议)
- [与 Wiki 的衔接](#与-wiki-的衔接)

## 卡片模板

总览表：

| # | 知识点 | 一句话 | 使用场景 |
| --- | --- | --- | --- |
| 1 | [[#标题\|短名]] | 可执行的一句话 | 何时拿出这张卡 |

逐卡正文（六段式，段段要有实质内容）：

```markdown
## N. 标题

**场景**：面试/分享里的原始情境 + 题号/时间戳 `[F-S]`。

**原文转译**：当时怎么说、做到哪、权责是什么。不升维。

**提炼** `[M]`：
- 第一性原理或工作流步骤（编号）
- 与原文的差距（当时没做到哪一步）

**外部补充**：
- 框架/实证名称 + 来源 URL + `(as of YYYY-MM, source)`
- 为什么比原话更可执行
- 它的局限 / 不能替代原文的部分

**使用场景**：以后什么情况下直接套。

**反模式 / 边界**：什么时候不能套；小样本、无预算、无权限时怎么降级。

**双链**：相关概念卡、同一面试包其他笔记。
```

## 基础框架

先用这些，再决定要不要外搜。

### SECI（Nonaka）

隐性知识 → 社会化、外化、组合、内化。面试里出现「内训师 / 经验萃取 / 知识库」时优先考虑。外化步骤必须落到载体（案例卡、课纲、检查清单），不能停在「让专家分享」。

### After Action Review

四问：预期是什么、实际发生什么、为什么有差距、下次保留/改变什么。适合复盘类回答。

### Knowledge Harvesting

访谈绩优者 → 任务分解 → 决策点 → 工具与易错点 → 可教材料。适合「你们怎么做任职资格 / 怎么定义功能」。

### 第一性原理拆解

把做法拆回约束（目标、样本、预算、权限、时间），再重建最小可行机制。适合对方否定了大厂套模的场合。

### 领域工作流示例（按材料选用，不整表硬套）

- HR 任职资格：岗位族 → 关键任务 → 分级标准 → 小样本校准 → 试点
- HR 培训诊断：Can't do vs Won't do vs 制度问题
- 产品功能定义：问题证据 → 谁的任务 → 非目标 → 方案切片 → 验收
- 市场：ICP → 证据 → 信息结构 → 渠道假设

## 外部信源清单

每张卡片至少一个外部锚点。按领域查：

### HR / 组织

| 层级 | 信源 |
| --- | --- |
| 期刊 | Journal of Applied Psychology、Human Resource Management Journal、Personnel Psychology、Academy of Management 系列 |
| 行业研究 | HBR、MIT Sloan Management Review、SHRM、ATD、Gartner、Deloitte Human Capital Trends |
| 经典方法 | BEI / Critical Incident Technique（Flanagan）、Competency Modeling（McClelland / Spencer & Spencer）、Learning Agility（Korn Ferry）、9-Box Calibration、Addie / Kirkpatrick |
| 检索入口 | Google Scholar（`obsidian` 外用 WebSearch 发现后核对） |

### AI / 技术

| 层级 | 信源 |
| --- | --- |
| 论文 | arXiv、NeurIPS / ICML / ACL、Anthropic / OpenAI / DeepMind 研究博客 |
| 工程实践 | 官方文档、工程博客（Engineering Blog）、GitHub 仓库 README |
| GitHub 参考 | `borghei/claude-skills`（面试 loop、评分 rubric、debrief 引导）、`hsuanlolo/interview-feedback-copilot`（逐字引用核验、覆盖度图）、`dungnotnull/interview-question-designer-agent-skill`（BARS 锚点、加权维度、devil's-advocate 挑战） |

### 市场 / 商业

行业报告（Gartner / Forrester / IDC）、公司财报与公开信、一手访谈。

来源分级：期刊论文 > 行业研究 > 权威媒体 > 厂商博客 > 个人博客。用低分级来源时标注原因。

## 检索协议

1. 关键词组合：`<领域> <任务> playbook OR framework OR validation`，加方法人名或标准名。
2. WebSearch 发现 → 需要原文时按 web 决策树取（defuddle / WebFetch）。
3. GitHub 用 `topic:` + 方法名，优先 README 里有可运行步骤的仓库，而不是只有概念介绍的 Awesome 列表。
4. 每个锚点记录：

- 框架名
- URL（原样内联）
- as-of 日期
- 为什么比面试原话更可执行
- 不能替代原文的部分

5. 找不到写「未检索到更合适的外部框架」，不编造作者、年份、期刊或 URL。
6. 每卡至少一个锚点；一场面试的萃取文里，期刊/行业研究级来源应占多数，不许全是博客。

## 与 Wiki 的衔接

frontmatter 最低字段：

```yaml
type: interview-experience-extraction
origin_type: interview-analysis   # 会议分享用 talk-analysis
domain:
source: "[[01 一问一答]]"
source_id:   # 由 asr-pipeline / knowledge-compiler 分配
intake_mode: interview-pipeline
compile_status: compiled
```

经验萃取文是 Wiki 产物，不是 Raw。不要把 ASR 原文贴进卡片正文；用双链指回 Raw。
