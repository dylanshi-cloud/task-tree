---
name: task-tree
description: 任务树 + 演进路径的活文档法。所有产出型任务（写文件、做分析、做决策、改代码/模型/文档）开工时默认使用：先过五步算法，再问清为什么做、给谁用、什么算成功，拆分支与节点，用 Obsidian 画布和只读笔记展示延伸、进展、协同与修正，随时可溯源。Use when starting any task that produces files, analysis or decisions, and when asked for a task tree, project plan, living document, traceable prompt tree, growth view, or "why/who/success" breakdown.
---

# 任务树协作法

## 执行算法（先过这一关）

所有产出型任务，顺序不可跳：**去愚 → 删除 → 优化 → 加速 → 自动化**；前一步没做完，不进入下一步。

1. **去愚**：要求落到人、场景、判据；问去掉会怎样、谁用、不做损失什么；模糊词改可判定。
2. **删除**：先删流程、步骤、零件、文档、字段；默认不该存在，没被迫加回来说明删得不够。安全/法规/验收红线不删。
3. **优化**：只优化删完仍必要的；减少步骤、接口、依赖、等待。
4. **加速**：缩短反馈周期，一轮只推一个关键节点；方向未验证不提速，不靠加班掩盖错误。
5. **自动化**：手工验证稳定、前四步完成后才自动化；不自动化坏流程。

拆树时同步记录：删除项进 `deleted`，验证过的自动化进 `automation`；确认回执固定多一行「这一版删掉了什么 / 哪一步还不该自动化」。汇报先删后增，只增不减不算过算法关。

把「任务树 + 演进路径」做成可溯源的活文档：**单一真相 + 只读镜像 + 校准机制**。

## 何时用

**默认用于所有产出型任务**：写文件、做分析、做决策、改代码/模型/文档。小任务只建 1 个分支、≤3 个节点；纯问答、一次查询、无产物闲聊不建。

## 三步协议

### 1. 先澄清意图再动手

按顺序问，不跳步：

1. **为什么做**：追问到「不做会怎样」。
2. **给谁用**：第一读者、场景、最在意什么；第二读者是谁。
3. **什么算成功**：3–7 条可判定判据；每条问「怎么验证、谁认账」。
4. **不做什么**：非目标与红线；没有「不做」，范围一定膨胀。
5. **约束**：时间、钱、不可逆项、已有资产。

怎么问：

- 一次只澄清一层；每轮 2–4 个互斥选项，各附代价；下一问依赖上一答。
- 先问目的，不问参数。用户说方案时，先问「它解决什么」。
- 抽象词变可判定项：对「科技感/简单/便宜/好用」追问「做到什么程度算够」。
- 用户说「你定」就取默认并标「建议暂定」；参数问到 60% 就往下走。

够了的判据：能复述目标且用户不改关键词；能预测用户对 3 个没问过的取舍；每条成功判据都有证据形式，每条非目标都能挡住一个具体请求。

**确认回执**（拆树前发）：

> 目标：… / 对象：… / 成功：… / 不做：… / 暂定：…
> 这一版删掉什么：… / 哪一步还不该自动化：…

用户确认或修正后才拆分支。

### 2. 拆子任务：根 → 分支 → 节点

- 根：使命、对象、成功判据、非目标、角色。
- 删除 pass：先问每个流程/步骤/文档/字段「去掉会怎样」；删除项写进 `deleted`；安全红线、法规证据、验收判据不删。
- 分支：3–9 个互不重叠的专业面，每个写「为什么存在、服务哪条成功判据」。
- 节点：可独立验收的交付物，必须有 `judge` 与 `next`；`next` 标明算法步骤。
- 一个节点只属于一个分支；跨分支依赖写成文字，不建平行树。

### 3. 确认后推进

- 一次只推一个关键节点，有产物 + 验收判据才切换；新想法进 parking list，不临时加分支。
- 状态、拍板、数字变化先写 `tree.json`，再重生成页面。
- 目标变更与方案迭代分开记：`calibrations.kind` 用「目标 / 方案 / 范围」。
- 收口：更新 `state`、`next`、`evidence`、`decision_ids`，补 `deleted` / `automation`，必要时加 `log`，重跑一次生成器。
- 聊天只报「本轮变化 / 下一步 / 待拍板」；有删除时先说删了什么。

## 数据模型

唯一真相是一棵 `tree.json`。完整示例见 `templates/tree.json`，字段见 `schema/tree.schema.json`，最小示例见 `examples/small-task.json`。

```json
{
  "program": "短名",
  "title": "任务树标题",
  "roles": [{"who": "Claude", "does": "..."}, {"who": "用户", "does": "..."}],
  "mission": {"why": "", "who": "", "non_goals": [], "success": [{"id": "S1", "text": "", "nodes": ["A1"]}]},
  "branches": {"A": {"name": "", "why": "", "serves": ["S1"]}},
  "nodes": [{"id": "A1", "branch": "A", "title": "", "state": "open", "owner": "Claude", "judge": "", "next": "", "evidence": []}],
  "decisions": [], "calibrations": [], "drift_checks": [],
  "deleted": [], "automation": [], "current": "A1", "log": []
}
```

- `state` 只用 `done | partial | open | decide | blocked | later`；`done` 必须有证据。
- 每条成功判据至少挂一个节点；挂不上的节点说明它不该存在。
- `owner` 不写时：`decide` → 用户，`blocked` → 外部，其余 → Claude。
- `deleted` 只记真删掉的；`automation` 只记手工验证过、稳定且前四步完成的。
- 旧数字进 `drift_checks`；扫描到冲突先改源。

## 生成与验收

```bash
python3 ~/.claude/skills/task-tree/scripts/build_task_tree.py \
  --tree .task-tree/tree.json \
  --vault "<Obsidian 库根目录>"
```

- `--vault` 省略时读 `$TASK_TREE_VAULT` → `~/.config/task-tree/config.json` → 常见库路径。
- 默认生成后打开画布；`--no-open` 关闭，`--dry` 只看计划，`--history` 改快照位置。
- 输出 `<vault>/50 任务树/<program>/`：根页、分支页（节点内联）、演进页、生长 SVG、画布；单分支三节点共 5 个文件。
- 同时更新 `50 任务树/任务总览.md`。页面只读；生成器只删带 `generator: task-tree skill` 标记的旧文件。
- 生成前校验 `program`、节点 id、`branch`、`state`；有错退出并指出位置。
- 改生成器或模板后跑 `python3 -m unittest discover -s tests -v`（12 个集成测试，无第三方依赖）。

## 维护

- 只改 `tree.json` 或上游数据源；不手改生成页，冲突先修源。
- 一个任务一棵树；不另起看板、周报或第二份状态文件。
- 任务结束冻结树；下一件新任务另建一棵。
- V11 复用项目适配器：`~/v10/载人电动飞行器/agent/scripts/build_task_tree.py`；新项目直接用通用生成器。
- 安装、插件市场与跨机器复制见 `README.md`；改完跑 `claude plugin validate .`。
