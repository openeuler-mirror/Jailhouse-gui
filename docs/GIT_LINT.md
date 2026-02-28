# Git Lint 门禁（本仓库 Commit 整洁性保障）

目标：在本地提交阶段就拦住常见“脏提交”，降低 review 成本、减少线上踩坑。

本仓库使用 **repo-local git hooks**（`.githooks/`）实现门禁。

## 安装（一次性）

在仓库根目录执行：

```bash
bash scripts/install-git-hooks.sh
```

它会在当前仓库配置：

- `core.hooksPath = .githooks`

说明：这是 **本仓库本地配置**，不会影响你其他仓库。

## 按需启用（门禁 vs. 约定式提交）

`commit-msg` hook 内部分成两段校验脚本，可以分别启用：

- 门禁（本仓库治理策略，如必须 Signed-off-by/Tags）：`.githooks/commit-msg.gate`
- 约定式提交（Conventional Commits v1.0.0）：`.githooks/commit-msg.conventional`

门禁启用脚本（会先执行 `scripts/install-git-hooks.sh`，再只启用门禁校验）：

```bash
# 只启用“门禁”
bash scripts/install-git-hooks-gate.sh
```

约定式提交（Conventional Commits）的启用步骤移至：`docs/COMMIT_CONVENTION.md`。

也可以手动切换（更细粒度）：

```bash
git config --local jh.hooks.commitmsg.gate true|false
git config --local jh.hooks.commitmsg.conventional true|false
```

## 当前门禁项

`pre-commit`（提交前）：

- 对 staged 的 `*.py`：
  - 阻止提交 staged diff 中的 whitespace 问题（`git diff --check`）
  - 阻止提交包含 merge 冲突标记（`<<<<<<<`/`=======`/`>>>>>>>`）
  - 做语法检查（`python -m py_compile`）
- 阻止新增文件超过 10MiB（避免误提交大文件）

`commit-msg`（提交消息）：

- 门禁（`.githooks/commit-msg.gate`）：
  - subject 不能为空、不能以 `WIP` 开头、不能超过 72 字符、不能有行尾空格
  - trailers 必须位于提交消息末尾，且 trailers 前必须有一个空行
  - 必须包含 trailers：
    - `Signed-off-by: Name <email>`（默认要求与 `git config user.name/user.email` 匹配；可用 `JH_HOOKS_ALLOW_MISMATCH_SIGNOFF=1` 放宽）
    - `Tags: tag1, tag2` 或 `Tag: tag`
- 约定式提交（`.githooks/commit-msg.conventional`）规则说明见：`docs/COMMIT_CONVENTION.md`

实现说明：

- `commit-msg` 是一个 wrapper，会依次调用：
  - `.githooks/commit-msg.gate`（通用门禁）
  - `.githooks/commit-msg.conventional`（Conventional Commits v1.0.0 规范校验）

## 卸载

```bash
git config --local --unset core.hooksPath
```
