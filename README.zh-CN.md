# task-tree skill

「任务树 + 演进路径 = 可溯源的活文档」的可移植实现。

## 目录里有什么

```
task-tree/
  .claude-plugin/              插件清单、市场清单、图标
  SKILL.md                     方法与使用说明（Claude 自动读取）
  scripts/build_task_tree.py   通用生成器：tree.json → Obsidian
  templates/tree.json          完整示例（个人网站上线）
  templates/config.json        Obsidian 库路径配置示例
  schema/tree.schema.json      数据模型 Schema
  examples/small-task.json     轻量示例（1 分支 3 节点）
  tests/                       集成测试
  evals/                       真实评测提示
```

依赖：Python 3.10+ 标准库。无网络、无第三方包。

## 安装

插件市场（推荐）：

```text
/plugin install task-tree --marketplace dylanshi-cloud/task-tree
```

手动复制：把整个 `task-tree/` 文件夹放到目标机器的 `~/.claude/skills/task-tree/`。
   - macOS / Linux：`~/.claude/skills/`
   - Windows：`C:\Users\<你>\.claude\skills\`
2. 告诉 Claude 新库的位置（任选其一）：
   - 环境变量：`TASK_TREE_VAULT=/path/to/ObsidianVault`
   - 配置文件：`~/.config/task-tree/config.json`（Windows：`%USERPROFILE%\.config\task-tree\config.json`）
     ```json
     { "vault": "/Users/you/Desktop/Claude记忆" }
     ```
   - 临时参数：`--vault /path/to/vault`
3. 自检：
   ```bash
   python3 ~/.claude/skills/task-tree/scripts/build_task_tree.py \
     --tree ~/.claude/skills/task-tree/templates/tree.json \
     --vault /tmp/task-tree-test \
     --history /tmp/task-tree-test-history.json --no-open
   ```
   应生成 13 篇笔记 + 1 个画布 + 1 个生长 SVG。用 Obsidian 打开 `/tmp/task-tree-test` 检查画布。
   跑测试：`cd ~/.claude/skills/task-tree && python3 -m unittest discover -s tests -v`。

> 换机器时只需要这个文件夹；不需要 V11 项目、不需要记忆库、不需要任何本机脚本。

## 让它在所有任务里自动生效

在目标机器的 `~/.claude/CLAUDE.md` 加入：

```markdown
## 任务树（所有产出型任务默认）

- 三步：先澄清意图再动手 → 拆子任务 → 确认后推进。
- 凡要产出文件、分析、决策、代码/模型/文档改动的任务，一律建树；纯问答不建。
- 开工先问清「为什么做 / 给谁用 / 什么算成功 / 不做什么」，复述确认后再拆。
- 每个任务一棵树：`.task-tree/<任务slug>/tree.json`（单任务项目可用 `.task-tree/tree.json`）。
- `roles` 写谁负责什么，节点 `owner` 写 Claude / 用户 / 外部，用于生成协同视图。
- 用 task-tree skill 生成 Obsidian 只读镜像；只改 tree.json，不手改页面。
- 每轮收口跑一次生成器；聊天只报「本轮变化 / 下一步 / 待拍板」，不复述页面细节。
- 状态与拍板只认这一份源；目标变更追加 calibration，不覆盖历史。
```

Claude 看到多步骤任务时会自动调用本 skill；也可以直接说「用任务树」。

## 一个任务怎么开始

1. 在任务工作目录建 `.task-tree/<任务slug>/tree.json`，从 `templates/tree.json` 复制后改写；单任务项目可省略 slug。
2. 把 `program`、`title`、`mission` 先写对；`nodes` 可以后补。
3. 生成一次，确认画布与根页结构。
4. 之后每轮改 `tree.json` → 重跑生成器；有变化时「生长页」会列出本轮新增/迁移，并追加一条快照。
   生成器会自动在 Obsidian 打开本任务画布，并打印任务目录与 `obsidian://` 链接；不想自动打开就加 `--no-open`。
5. 历史快照默认落在 `tree.json` 同目录的 `<名字>_history.json`；想换位置用 `--history`。
6. 每个任务的生成器都会更新 `<库>/50 任务树/任务总览.md`，跨任务先看总览再进生长页。

## 与 V11 专用生成器的关系

V11 已有自己的状态机（`v11_elements.json` / `decisions.json`），项目内的
`agent/scripts/build_task_tree.py` 负责把这些数据适配成树。
**通用 skill 不依赖 V11**；新项目直接用通用生成器，`nodes` 写在 `tree.json` 里。

## 打包给别人

```bash
cd ~/.claude/skills
zip -r task-tree-skill.zip task-tree
```

对方解压到自己的 `~/.claude/skills/` 即可。也可以放进任何 Git 仓库或网盘同步。
