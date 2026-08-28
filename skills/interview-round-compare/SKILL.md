---
name: interview-round-compare
description: 手动对照同一公司同一岗位的一面与二面：比较两位面试官给出的工作内容、能力要求、服务项目是否一致。用户说「对照一面二面」「两轮面试官画像一不一致」「比一下 XX 岗位的一面和二面」时使用。不自动在 asr-pipeline 里触发。找不到某轮记录时报告缺失，不编造。
---

# Interview Round Compare

只在用户明确要求对照时运行。输入是已经存在的 Wiki 面试包，不是原始 ASR。

## 加载参考

写报告前读完 [references/compare-report.md](references/compare-report.md)。

## 输入

用户给出的 `company` + `position`。若只给其中一个，先补问。

可选：`round_a` / `round_b`（默认一面 vs 二面）；指定 Wiki 包路径时可跳过搜索。

## 检索

1. `obsidian search` 同时用公司名和岗位名。
2. 过滤 frontmatter：`type` 为 `interview-observer-analysis` 或 `interview-self-analysis` 或多视角评估，且 `company`、`position` 匹配。
3. 按 `round` 分组。优先读各包里的岗位画像表（观察者分析板块 3，或自我分析里的「面试官需求解码」）。
4. 零命中或只命中一轮：停止生成对照矩阵，列出已找到的笔记路径，请用户补另一轮或确认是否继续做单轮摘要。

不要用模糊同名岗位（如「HRBP」vs「HRBP实习生」）自动合并；不确定时列候选请用户选。

## 输出

一份对照报告，建议文件名：`<公司> <岗位>｜一面二面对照.md`。

固定三块：

1. 检索结果（用了哪些笔记）
2. 一致性矩阵：工作内容 / 能力要求 / 服务项目 / 组织阶段
3. 不一致项差异摘要（标红原则：能改变招聘校准或候选人准备策略的差异）

一致的部分也要写，避免只报差异造成「整岗都乱了」的错觉。

## 工作流

1. 抽出每一轮的岗位画像三列，保留证据时间戳。
2. 逐格判定：一致 / 部分一致 / 不一致 / 一轮缺失。
3. 对不一致格写：一面怎么说、二面怎么说、可能解释（考察深度不同 vs 真的画像冲突）、建议 Darren 向谁核实。
4. 结论先写能不能用同一张岗位画像继续招。

## 停止条件

- 用户其实想分析单场：转回 `interview-self-analysis` 或 `interview-observer-analysis`
- 材料仍是原始 ASR：先走 `asr-pipeline` 或 `interview-qa-extract`
