# LLM 配置与密钥安全

AutoDrive Papers 可以选择使用 OpenAI-compatible LLM 完成边界论文复核、缺失翻译和摘要补全。LLM 不是必需依赖：未设置 API Key 时，程序会自动跳过 LLM，规则筛选、标签、站点构建和部署仍可正常运行。

真实密钥只能保存在运行环境中，不能写入 Git 仓库、生成后的静态站点或浏览器端代码。

## 配置项

| 名称 | 是否必需 | 是否敏感 | 默认值 | 用途 |
| --- | --- | --- | --- | --- |
| `LLM_API_KEY` | 启用 LLM 时必需 | 是 | 无 | 调用模型服务的凭据 |
| `LLM_BASE_URL` | 使用非默认服务时必需 | 通常否 | `https://api.openai.com/v1` | OpenAI-compatible API 根地址 |
| `LLM_MODEL` | 使用非默认模型时必需 | 通常否 | `gpt-4o-mini` | 服务商提供的模型标识 |

接口必须兼容 OpenAI Chat Completions。`LLM_BASE_URL` 应填写 API 根地址，例如 `https://provider.example/v1`，不要附加 `/chat/completions`。模型名称必须与服务商实际提供的名称一致。

## GitHub Actions 配置

如果只通过 GitHub Actions 定时更新网站，本地计算机不需要保存 API Key。以下操作需要仓库管理员权限。

1. 打开自己的 GitHub 仓库主页。
2. 进入 `Settings`。
3. 在左侧选择 `Secrets and variables`，然后选择 `Actions`。
4. 打开 `Secrets` 或 `Repository secrets` 区域。
5. 点击 `New repository secret`。
6. 名称填写 `LLM_API_KEY`，值填写服务商提供的真实 API Key，然后点击 `Add secret`。
7. 如果使用仓库默认的接口地址和模型，到此即可完成配置。
8. 如果使用其他 OpenAI-compatible 服务，再分别创建 `LLM_BASE_URL` 和 `LLM_MODEL` 两个 Repository Secret。

填写 Secret 值时不要添加引号、PowerShell 的 `$env:` 前缀或多余空格。保存后 GitHub 只显示 Secret 名称和更新时间，无法再次查看原值；需要更换时使用 `Update` 写入新值。

当前工作流使用以下名称读取 Secrets，名称必须完全一致：

```yaml
LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
LLM_BASE_URL: ${{ secrets.LLM_BASE_URL }}
LLM_MODEL: ${{ secrets.LLM_MODEL }}
```

GitHub 设置页面虽然名为 `Secrets and variables`，但 `LLM_API_KEY` 必须存放在 **Secrets**，不能存放在 Variables。当前工作流也从 `secrets.*` 读取接口地址和模型名称；为了无需修改工作流，建议将三个值都按上述方式创建为 Repository Secret。

Secrets 只注入到 `Update and classify` 步骤，不会写入 GitHub Pages 静态文件。Fork 不会继承上游仓库的 Secrets，每位使用者都需要在自己的仓库中配置自己的 Key。GitHub 默认也不会把仓库 Secrets 提供给来自 Fork 的 Pull Request 工作流。

### 验证远程配置

1. 打开仓库的 `Actions` 页面。
2. 选择 `Update And Deploy Papers` 工作流。
3. 点击 `Run workflow`。
4. 为避免测试时提交数据，将 `dry_run` 设置为 `true`。
5. 如果测试一个已经归档的日期，同时将 `force` 设置为 `true`，否则程序会直接返回 `unchanged` 而不调用 LLM。
6. 运行后确认 `Update and classify` 步骤完成，并检查日志中没有输出凭据或请求头。

LLM 在本项目中采用容错模式：接口不可用时会回退到规则筛选，因此一次工作流成功不一定能证明模型请求成功。正式更新后，可以在新生成的论文数据中查看 `classifier` 是否出现 `rules+llm`，并检查新增翻译或摘要。某一天没有出现该标记，也可能只是当日没有需要 LLM 处理的样本。

## 本地临时配置

只有在本地执行更新并希望启用 LLM 时，才需要在本地设置 API Key。推荐使用当前 PowerShell 会话的临时环境变量，避免把真实密钥写入命令历史：

```powershell
$secureKey = Read-Host "LLM API Key" -AsSecureString
$env:LLM_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
Remove-Variable secureKey

# 使用默认 OpenAI 配置时不需要设置下面两项
$env:LLM_BASE_URL = "https://provider.example/v1"
$env:LLM_MODEL = "provider-model-name"

python -m adpaper update --date today
```

只检查变量是否存在，不要把值打印到终端：

```powershell
if ($env:LLM_API_KEY) { "LLM_API_KEY is set" } else { "LLM_API_KEY is not set" }
```

使用结束后清除当前会话中的变量，或直接关闭终端：

```powershell
Remove-Item Env:LLM_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:LLM_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:LLM_MODEL -ErrorAction SilentlyContinue
```

仓库已忽略 `.env` 和 `.env.*`，只跟踪不含密钥的 `.env.example`。但是项目不会自动加载 `.env` 文件，因此无需为了正常运行创建或提交 `.env`。如果使用第三方环境管理工具加载 `.env`，仍需确认该文件保持未跟踪状态。

## 提交前检查

允许提交的内容包括公开的接口示例、模型默认值和空白变量名。以下内容不得提交：

- 真实 API Key、访问令牌或完整 Authorization 请求头；
- 填有真实值的 `.env`、YAML、JSON 或脚本；
- 包含密钥的终端输出、Actions 日志、截图或调试文件；
- 将密钥嵌入 `site/`、HTML、JavaScript 或其他浏览器可下载文件的代码；
- 个人聊天记录、QQ Bot 凭据或本地工作区内容。

提交前至少执行：

```powershell
git status --short
git diff --cached
git ls-files ".env" ".env.*"
```

最后一条命令正常情况下只能列出 `.env.example`。`.gitignore` 只能阻止新的未跟踪文件被加入；如果敏感文件曾被强制添加或已经提交，之后再加入忽略规则并不能删除历史记录。

公开仓库还应在 GitHub 的 `Settings` / `Code security and analysis` 中启用可用的 Secret scanning 和 Push protection。API Key 最好专门为本项目创建，并在服务商后台设置额度、速率限制和账单提醒。

## API Key 泄漏处理

如果真实 Key 曾出现在提交、日志、Issue、截图或网页中，应按以下顺序处理：

1. 立即在模型服务商后台撤销或轮换旧 Key。仅删除文件或提交不能使旧 Key 失效。
2. 检查服务商的调用记录、消费额度和异常来源。
3. 从当前代码、Actions 日志、Artifacts、Issue 或网页中移除敏感内容。
4. 使用新 Key 更新 GitHub Repository Secret 和需要使用它的本地环境。
5. 如果 Key 进入 Git 历史，再评估使用 `git filter-repo` 等工具清理历史并协调强制推送；无论是否清理历史，都必须先撤销旧 Key。
6. 安全问题应通过仓库的 Security Advisory 私下报告，不要在公开 Issue 中粘贴密钥。

GPG 签名只能证明提交者身份和提交完整性，不能保护已经写入提交内容的 API Key。密钥安全仍依赖环境变量、GitHub Secrets、最小权限和及时轮换。
