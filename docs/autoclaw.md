# AutoClaw 与 QQ 远程操作

AutoClaw 在本项目中只承担“远程操作入口”的角色。论文抓取、筛选、数据提交和 GitHub Pages 部署均由仓库中的 GitHub Actions 完成，AutoClaw 不应直接编辑 `data/`、运行筛选代码或接触 LLM API Key。

```text
QQ 私聊命令
    ↓
AutoClaw 严格解析白名单命令和日期
    ↓
<repo-root>/ops/autoclaw.ps1
    ↓
GitHub Actions: Update And Deploy Papers
    ↓
抓取、筛选、提交数据并部署 GitHub Pages
```

## 定时更新由谁负责

仓库工作流已经包含以下计划：

```yaml
schedule:
  - cron: "30 13 * * 1-5"
```

GitHub Actions cron 使用 UTC，因此它会在工作日北京时间 21:30 自动运行。自动更新不依赖本地电脑、AutoClaw 或 QQ Bot 在线。

不要再创建同一时间执行论文更新的 AutoClaw cron，否则可能重复触发工作流。旧任务可以在 AutoClaw 的计划任务页面删除，也可以使用 OpenClaw CLI：

```powershell
openclaw cron list
openclaw cron disable <job-id>  # 可恢复，推荐先使用
openclaw cron rm <job-id>       # 永久删除任务定义
```

不同 AutoClaw 安装方式可能需要指定 profile、Gateway URL 或凭据，具体以本机 `openclaw cron --help` 为准。不要手工编辑 `cron/jobs.json`，除非 Gateway 已停止并且已经备份文件。

如果只想在更新结束后收到 QQ 状态通知，可以单独安排一个 22:30 左右的“状态”任务；它只应调用 `ops/autoclaw.ps1 status`，不能再次触发更新。

## 首次准备

### 1. 准备本地仓库

将仓库克隆到运行 AutoClaw 的 Windows 电脑，并记录绝对路径：

```powershell
git clone https://github.com/Ning0713/ArXivADReader.git
Set-Location ArXivADReader
```

公开使用者应将脚本中的 `$repo`、`$siteUrl` 修改为自己的仓库和域名。个人路径、QQ 账号、Bot Token 和聊天记录不能提交到本仓库。

### 2. 安装并登录 GitHub CLI

```powershell
gh auth login -h github.com
gh api user --jq .login
gh workflow view update-and-deploy.yml --repo Ning0713/ArXivADReader
```

第二条命令必须返回正确的 GitHub 用户名。`gh auth status` 只能显示本地凭据记录；如果实际 API 返回 `401 Unauthorized`，应重新执行 `gh auth logout -h github.com` 和 `gh auth login -h github.com`。

GitHub CLI 凭据保存在运行 AutoClaw 的 Windows 用户账户中。不要将 GitHub Token 写入 Agent 提示词、`TOOLS.md`、仓库文件或 QQ 消息。

### 3. 先在 PowerShell 中直接测试脚本

将 `<repo-root>` 替换为仓库绝对路径：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "<repo-root>\ops\autoclaw.ps1" help

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "<repo-root>\ops\autoclaw.ps1" status
```

脚本本身使用纯 ASCII 英文参数，以兼容 Windows PowerShell 5.1。中文 QQ 指令由 AutoClaw 映射为固定英文参数：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "<repo-root>\ops\autoclaw.ps1" preview 2026-08-11
```

只有上述命令在本机正常后，才应接入 AutoClaw。

## AutoClaw Agent 配置

在负责 QQ 私聊的 Agent 指令中加入以下规则，并将 `<repo-root>` 替换为实际路径：

```text
你是 AutoDrive Papers 的远程操作入口。

只接受以下完整命令：
- 更新论文
- 更新论文 YYYY-MM-DD
- 补跑 YYYY-MM-DD
- 预览 YYYY-MM-DD
- 预览论文 YYYY-MM-DD
- 状态
- 帮助

日期必须完整匹配 YYYY-MM-DD，并且必须是有效日期。
任何额外文字、路径、管道符、重定向、分号、引号或其他 shell 内容都必须拒绝。

将中文命令映射为以下固定英文参数：
- 更新论文 -> update
- 补跑 -> retry
- 预览、预览论文 -> preview
- 状态 -> status
- 帮助 -> help

只允许调用：
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<repo-root>\ops\autoclaw.ps1" <固定英文参数> [日期]

不要直接修改仓库文件、data 目录、GitHub Secrets、AutoClaw 配置或系统计划任务。
不要把原始 QQ 文本直接拼接进 shell。
执行后把脚本的简要结果返回当前 QQ 私聊。
```

推荐在 Agent 层使用完整匹配，而不是“包含关键词”：

```text
^更新论文(?:\s+(?:today|\d{4}-\d{2}-\d{2}))?$
^补跑\s+(?:today|\d{4}-\d{2}-\d{2})$
^(?:预览|预览论文)\s+(?:today|\d{4}-\d{2}-\d{2})$
^状态$
^帮助$
```

正则通过后仍应由 `ops/autoclaw.ps1` 再次验证日期。两层验证用于防止任意 QQ 文本进入 PowerShell。

## 可用 QQ 命令

| QQ 命令 | 脚本参数 | 行为 | 修改数据 | 部署网站 |
| --- | --- | --- | --- | --- |
| `更新论文` | `update` | 更新今天；日期已存在时返回 unchanged | 可能 | 可能 |
| `更新论文 2026-08-12` | `update 2026-08-12` | 更新指定日期，不覆盖已存在日期 | 可能 | 可能 |
| `补跑 2026-08-10` | `retry 2026-08-10` | 使用 `force=true` 重新抓取并覆盖该日清单 | 是 | 是 |
| `预览 2026-08-12` | `preview 2026-08-12` | 完整抓取、规则筛选和可选 LLM 复核 | 否 | 否 |
| `状态` | `status` | 返回最近 5 次工作流状态并检查站点 HTTP | 否 | 否 |
| `帮助` | `help` | 返回白名单命令 | 否 | 否 |

`预览` 不提交数据，也不会创建 GitHub Pages 部署记录，但仍会访问 Axi、arXiv 和已配置的 LLM，因此可能消耗 API 配额。脚本输出 `dispatched` 只表示 GitHub 已接受任务，不表示工作流已经完成；随后发送“状态”查看结果。

正式的定时、更新或补跑工作流会在同一次运行中生成并推送 `data/`，然后直接上传已构建的 Pages 产物并部署。这是因为使用 GitHub Actions 内置 `GITHUB_TOKEN` 推送的数据提交不会再次触发 `push` 工作流。预览和无数据变化的运行不会创建 Pages 部署记录。

## 常用操作流程

### 日常自动更新

无需向 QQ 发送命令。GitHub Actions 会在工作日北京时间 21:30 自动运行。22:00 以后发送：

```text
状态
```

### 当天提前手动更新

```text
更新论文
```

如果当天已经存在归档，命令不会强制覆盖。需要重新筛选时使用补跑。

### 补齐或重新生成某一天

先无写入预览：

```text
预览 2026-08-10
```

确认候选数和筛选结果合理后：

```text
补跑 2026-08-10
```

补跑会真实修改 `data/` 并触发网站部署，不能把任意未知日期直接映射成补跑命令。

### 修改插件后的验证

1. 在代码分支中修改插件并完成测试。
2. 合并到 `main` 后发送 `预览 YYYY-MM-DD`。
3. 检查 Actions 日志中的 `candidate_count`、`selected_count` 和 warnings。
4. 结果符合预期后再发送 `补跑 YYYY-MM-DD`。

## 故障排查

### GitHub 返回 401

```powershell
gh api user --jq .login
gh auth logout -h github.com
gh auth login -h github.com
```

必须在运行 AutoClaw 的同一个 Windows 用户账户中完成登录。

### 工作流长时间 queued

这是 GitHub runner 排队，不要连续重复发送更新或补跑。使用“状态”查看同一个运行，或直接打开 Actions 页面。

`status` 使用项目要求的 Python 标准库检查站点 HTTP 状态。正常结果应包含 `site_http=200`；如果 AutoClaw 找不到 `python`，应先把 Python 3.11+ 加入该 Windows 用户的 `PATH`。

### arXiv 返回 429

这是 arXiv 元数据接口限流，不等于 LLM 配置失败。Axi 候选仍可完成预览，工作流会把 arXiv 警告写入 `warnings`。

### LLM 是否实际调用成功

Actions 日志中的 Secrets 应显示为 `***`。模型请求只有在 `/chat/completions` 返回 `HTTP 200` 时才能证明调用成功。工作流整体成功并不足以证明 LLM 成功，因为项目会在 LLM 不可用时回退到规则筛选。

## 安全边界

- AutoClaw 只调用版本库中的固定脚本，不执行 QQ 用户提供的任意命令。
- 不允许 QQ 指令修改代码、Secrets、DNS、Git 历史、计划任务或本机文件。
- 不向群聊开放管理命令；建议仅绑定所有者私聊会话。
- 不把 QQ Bot Token、Gateway Token、GitHub Token、LLM Key 或本地聊天历史提交到 Git。
- Fork 使用者必须改成自己的仓库、域名、GitHub Secrets 和 QQ Bot 配置。
- 代码修改应通过正常开发、测试、GPG 签名和代码审查完成，而不是通过 QQ 文本生成任意 shell。
