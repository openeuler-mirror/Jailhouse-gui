# Commit 约定式提交规范（Conventional Commits v1.0.0）

本仓库提供 `commit-msg` 的两类校验：

- 约定式提交（Conventional Commits v1.0.0）：`.githooks/commit-msg.conventional`
- 本仓库门禁（例如必须 Signed-off-by/Tags）：`.githooks/commit-msg.gate`（见 `docs/GIT_LINT.md`）

Conventional Commits（官方规范，简体中文）：

```text
https://www.conventionalcommits.org/zh-hans/v1.0.0/
```

## 启用 Conventional Commits 校验（脚本）

在仓库根目录执行：

```bash
bash scripts/install-git-hooks-conventional.sh
```

该脚本会先执行 `bash scripts/install-git-hooks.sh`，然后配置为“只启用约定式提交校验”：

- `jh.hooks.commitmsg.gate=false`
- `jh.hooks.commitmsg.conventional=true`

如需手动切换：

```bash
git config --local jh.hooks.commitmsg.gate true|false
git config --local jh.hooks.commitmsg.conventional true|false
```

## 1) Subject（第一行，必填 / Conventional Commits Header）

格式：

```text
<type>: <description>
<type>(<scope>): <description>
<type>!: <description>                # breaking change
<type>(<scope>)!: <description>       # breaking change
```

提交说明应包含结构化元素，以向类库使用者表明其意图（与语义化版本对应关系）：

- `fix`: 修复 bug（对应语义化版本 PATCH）
- `feat`: 新增功能（对应语义化版本 MINOR）
- `BREAKING CHANGE:`（脚注）或 Header 中的 `!`：破坏性变更（对应语义化版本 MAJOR）

除 `fix`/`feat` 外，本仓库也允许常见类型（参考 commitlint Angular 约定）：

- `build`: 修改构建系统/依赖/外部接口等
- `chore`: 非业务性修改（工具/配置/杂项）
- `ci`: 修改持续集成流程
- `docs`: 修改文档
- `style`: 仅样式调整（缩进/空格/空行/格式化），不改功能逻辑
- `refactor`: 重构（不改功能逻辑）
- `perf`: 性能优化
- `test`: 测试相关变更
- `revert`: 回滚

字段说明：

- `<type>`：必填（名词），建议使用上面的类型集合（本仓库 hook 会校验）
- `<scope>`：可选（名词），建议使用模块/目录名（例如 `gui` / `rpc` / `generator`）
- `<description>`：必填，简短描述（语言不限制）

说明：如果你同时启用了门禁校验（`.githooks/commit-msg.gate`），还会额外限制 subject 长度、禁止 `WIP` 等，详见：`docs/GIT_LINT.md`。

示例：

```text
feat: add resource tree search
feat(gui): add resource tree search
fix(rpc): handle reconnect timeout
docs(readme): update build steps
refactor(model)!: change pci mmconfig schema
```

## 2) Body（可选）

如果你要写正文：**subject 后必须空一行**，再写正文。

```text
feat(gui): add resource tree search

Add a filter box to quickly locate nodes in large JHR files.
```

## 3) Footers / Trailers（可选）

Conventional Commits 把尾部元信息称为 footer（或 trailer）。如果你使用 footer：

- `subject` 与 `body/footer` 之间需要空一行（本仓库 hook 会校验）
- footer 建议使用 git trailer 的惯例（例如 `Token: value` / `Token #value`）
- 破坏性变更可以使用：
  - Header 的 `!`，或
  - footer 中的 `BREAKING CHANGE: <description>` / `BREAKING-CHANGE: <description>`

如果你同时启用了门禁校验（`.githooks/commit-msg.gate`），还会额外要求在提交消息末尾包含 `Tags/Tag` 与 `Signed-off-by` 等 trailers，详见：`docs/GIT_LINT.md`。

示例：

```text
feat(generator): add bundle export

Bundle export packs .cell/.dtb/images and a deploy manifest for one-click use.

Tags: generator, export
Signed-off-by: Your Name <you@example.com>
```

提示：trailer 之间顺序不强制。
