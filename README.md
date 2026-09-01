# AutoDrive Papers

自动驾驶领域的公开论文日报与静态归档站点：<https://adpaper.ning0713.top>

本项目每天读取 [paper.axi404.top](https://paper.axi404.top/) 的当日论文全集，使用可替换的自动驾驶筛选插件保留高召回的相关论文，并用 arXiv API 校验和补齐元数据。生成结果发布到 GitHub Pages，不需要个人服务器、邮件服务或数据库。

## 功能

- 按日期归档自动驾驶相关论文，数量不设上限。
- 中英文标题/摘要、arXiv、PDF 和翻译链接。
- 自动驾驶细分标签：感知、BEV、传感器融合、端到端、VLM/VLA、规划等。
- 浏览器本地收藏清单，跨日期页面持久化。
- 在任意日期页面搜索全站历史论文，支持标签和关键词。
- 响应式分类侧栏与回到顶部按钮。
- GitHub Actions 定时更新、校验和部署。
- AutoClaw/QQ 白名单命令：更新、补跑、预览和状态查询。

## 本地运行

需要 Python 3.11 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m adpaper validate
python -m adpaper build
```

构建结果位于 `site/`，可用任意静态 HTTP 服务器预览：

```powershell
python -m http.server 8000 -d site
```

执行一次线上更新（需要网络）：

```powershell
python -m adpaper update --date today
```

默认以 Axi 页面为候选来源。只有明确传入 `--allow-arxiv-discovery` 时，Axi 不可用才会使用 arXiv 分类查询回退。

## 配置与插件

默认配置在 `config/config.yml`。LLM 增强是可选的，使用 OpenAI-compatible 接口；未设置 `LLM_API_KEY` 时会自动跳过，规则筛选、标签和站点构建仍可独立运行。真实密钥不得写入配置文件或提交到 Git。

本地临时环境变量、GitHub Actions Repository Secrets、验证步骤和泄漏处理方法见 [LLM 配置与密钥安全](docs/llm-configuration.md)。

插件接口位于 `src/adpaper/filtering/base.py`。插件同时定义相关性算法、标签、领域名称和 arXiv 回退分类，因此可以替换为其他研究领域；更换时还必须隔离历史数据并更新站点品牌。当前自动驾驶评分、排除规则、标签算法和完整换域步骤见 [领域筛选插件与自动驾驶算法](docs/plugin-development.md)。

## 历史迁移

不会把 AutoClaw 的 C 盘工作区加入运行时依赖。一次性迁移时传入旧工作区：

```powershell
python -m adpaper migrate --legacy-root "C:\path\to\legacy-workspace"
```

迁移工具优先重新抓取 Axi 的结构化日期页面，失败时使用本地 JSON/历史记录，并将报告写入 `data/migration-report.json`。原始 HTML/TXT 快照不会提交到仓库。

## GitHub Pages 部署

1. 在仓库 Settings / Pages 中选择 GitHub Actions。
2. 添加 DNS：`adpaper.ning0713.top` 的 CNAME 指向 `Ning0713.github.io`。
3. 等待 HTTPS 证书签发。
4. 在 Actions 中手动运行 `Update And Deploy Papers` 验证一次。

工作流默认在工作日北京时间 08:00（UTC 00:00）运行。启用 AI 时，将真实 API Key 配置为 GitHub Actions Repository Secret，具体步骤见 [LLM 配置与密钥安全](docs/llm-configuration.md)。

## AutoClaw/QQ

AutoClaw 只应调用仓库里的 `ops/autoclaw.ps1`，不直接修改数据或执行任意 shell：

```text
更新论文
补跑 2026-08-10
预览 2026-08-10
状态
帮助
```

GitHub Actions 已在工作日北京时间 08:00 自动更新，不需要重复创建 AutoClaw 论文 cron。AutoClaw 只用于人工远程更新、补跑、无写入预览和状态查询。首次配置、QQ 白名单、操作流程、取消 cron 和故障排查见 [AutoClaw 与 QQ 远程操作](docs/autoclaw.md)。

## 数据来源与许可

论文元数据链接到 [arXiv](https://arxiv.org/)，每日候选页面参考 [Axi404/ArxivReader](https://github.com/Axi404/ArxivReader)。本项目独立于 Axi404，也不托管论文 PDF。

Axi404/ArxivReader 采用 MIT 许可证；其版权和许可证保留在 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本项目代码采用 MIT 许可证，详见 [LICENSE](LICENSE)。
