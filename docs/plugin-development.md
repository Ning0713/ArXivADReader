# 领域筛选插件与自动驾驶算法

领域插件决定“候选论文是否进入归档”以及“进入后使用哪些研究标签”。当前仓库使用 `plugins/autonomous_driving.py`，但流水线并不要求领域必须是自动驾驶；只要候选源覆盖目标领域，就可以替换为量子计算、机器人、遥感、医学影像或其他 arXiv 领域的插件。

```text
Axi 当日候选全集
    ↓
按 arXiv ID 去重
    ↓
plugin.evaluate(): 是否属于目标领域
    ↓
plugin.assign_tags(): 主标签 + 最多两个次标签
    ↓
可选 LLM: 边界样本复核、缺失翻译和摘要补全
    ↓
arXiv API: 补齐规范元数据
    ↓
data/ 与静态网站
```

## 插件接口

配置通过 `module:attribute` 引用模块级插件对象：

```yaml
filtering:
  plugin: "plugins.autonomous_driving:plugin"
  llm_review_min_score: 10
```

插件必须满足 `src/adpaper/filtering/base.py` 中的 `DomainPlugin`：

```python
class Plugin:
    slug: str
    version: str  # 推荐；写入每日 manifest，便于审计
    display_name: str
    tags: tuple[str, ...]
    arxiv_categories: tuple[str, ...]

    def evaluate(self, paper: Paper) -> RelevanceResult: ...
    def assign_tags(self, paper: Paper) -> TagAssignment: ...
```

字段含义：

| 字段 | 用途 |
| --- | --- |
| `slug` | 稳定的机器标识 |
| `version` | 记录当前规则版本，词表或阈值变化时应递增 |
| `display_name` | LLM 复核使用的目标领域名称 |
| `tags` | 页面侧栏、搜索和 LLM 可选标签的有序集合；至少一个 |
| `arxiv_categories` | Axi 不可用且明确启用 arXiv fallback 时的发现范围 |
| `evaluate()` | 返回是否纳入、分数、命中词和原因 |
| `assign_tags()` | 返回一个主标签和最多两个次标签 |

插件应当确定性运行并且不发起网络请求。模型调用属于可选 enrichment 层，不应写进插件。

## 当前自动驾驶筛选算法

当前实现的目标是“高召回 + 明确排除近似误命中”，而不是用单个关键词做二元搜索。

### 1. 文本归一化

算法把以下字段合并，并使用 Unicode `casefold()` 统一大小写：

- 英文标题；
- 中文标题；
- 英文摘要；
- 中文摘要；
- arXiv 分类。

英文和数字词使用字母数字边界匹配，避免短词命中更长单词；中文词使用子串匹配。

### 2. 信号词组

| 信号 | 示例 | 每个命中的分值 | 作用 |
| --- | --- | ---: | --- |
| 明确领域词 `explicit_terms` | autonomous driving、self-driving、自动驾驶 | 28 | 强纳入信号 |
| 专用数据集 `dataset_terms` | nuScenes、KITTI、Waymo、CARLA | 20 | 强纳入信号 |
| 道路上下文 `context_terms` | traffic、road、lane、pedestrian | 5 | 与技术词组合使用 |
| 技术任务 `technical_terms` | BEV、occupancy、LiDAR、trajectory prediction | 4 | 与道路上下文组合使用 |
| 标题专用词 `title_specific_terms` | 4D radar、camera-LiDAR、V2X | 不单独计分 | 标题命中时直接保留高召回 |
| 普通排除词 `excluded_terms` | medical、satellite、robot manipulation | 每词扣 15 | 缺少强驾驶证据时排除 |
| 标题硬排除词 `hard_excluded_title_terms` | microscopy、underwater、chemical laboratory | 固定扣 30 | 最高优先级排除 |

相关性分数为：

```text
score = min(
    100,
    28 × 明确领域词数量
  + 20 × 数据集词数量
  +  5 × 道路上下文数量
  +  4 × 技术任务数量
)
```

`ad_specific_terms` 只补充审计用的 `matched_terms`，不独立改变纳入结果。最终 JSON 会保留分数、命中词和原因，便于后续检查为什么一篇论文被选择。

### 3. 决策优先级

初始纳入条件满足任意一项即可：

- 命中明确自动驾驶词；
- 命中自动驾驶数据集或仿真环境；
- 标题命中自动驾驶专用技术；
- 同时具备非泛化道路上下文和技术任务，且分数达到 `minimum_weak_score=12`。

“autonomous”“driving”“vehicle”“car”等过于宽泛的词不会单独构成弱证据中的道路上下文。例如普通室内 BEV 场景不会因为出现 `BEV` 就被纳入。

之后应用排除规则：

1. 标题硬排除优先级最高，即使标题中出现 “self-driving” 也会排除化学实验室、显微镜、水下机器人等论文。
2. 普通排除词只有在缺少明确领域词、专用数据集和强道路上下文时才主导排除，避免误删真实驾驶论文。

这种顺序用于处理“Self-Driving Microscopy”“Autonomous UUV”“Robot Manipulation with BEV”等容易误命中的标题。

### 4. 标签算法

`assign_tags()` 为 15 个自动驾驶方向分别维护词表，例如：

- `BEV/Occupancy`：BEV、bird's-eye、occupancy；
- `多传感器融合`：sensor fusion、camera-LiDAR、camera-radar；
- `预测/规划`：trajectory、motion prediction、planner；
- `端到端驾驶`：end-to-end、driving policy；
- `VLM/VLA`：vision-language、VLM、VLA；
- `协同/V2X`：V2X、cooperative perception。

每个标签的分数等于命中的不同标签词数量。算法按分数降序排列；同分时使用 `tags` 中更靠前的标签，因此结果稳定可复现。第一名是主标签，第二和第三名是次标签。没有标签词命中时，自动驾驶插件回退到“感知”。

### 5. LLM 与规则插件的关系

LLM 不是主筛选器。流水线先执行确定性插件，然后仅在以下情况调用 LLM：

- 规则没有纳入，但分数达到 `filtering.llm_review_min_score`，属于边界样本；
- 论文缺少中文标题或中文摘要，需要补全内容。

LLM 可以把边界样本补充纳入，但不会把规则已经纳入的论文删除，因此保持高召回。LLM 还可以在插件的 `tags` 范围内重分配标签。

LLM 提示词会读取当前插件的 `display_name` 和 `tags`，不再写死自动驾驶。更换插件后，无需修改 `src/adpaper/llm.py`。

## 更换为其他领域

可以更换，但不能只替换几个关键词后直接沿用现有数据。推荐在 Fork 或新仓库中完成以下步骤。

### 1. 创建新插件

例如创建 `plugins/quantum_computing.py`：

```python
from dataclasses import dataclass

from adpaper.models import Paper, RelevanceResult, TagAssignment


@dataclass(slots=True)
class QuantumComputingPlugin:
    slug: str = "quantum-computing"
    version: str = "quantum-computing-v1"
    display_name: str = "量子计算"
    arxiv_categories: tuple[str, ...] = ("quant-ph", "cs.ET")
    tags: tuple[str, ...] = (
        "量子算法",
        "量子纠错",
        "量子网络",
        "量子硬件",
    )

    def evaluate(self, paper: Paper) -> RelevanceResult:
        text = " ".join((paper.title, paper.abstract, *paper.categories)).casefold()
        matched = [
            term
            for term in ("quantum computing", "quantum circuit", "qubit")
            if term in text
        ]
        excluded = "quantum dot" in text and not matched
        return RelevanceResult(
            include=bool(matched) and not excluded,
            score=min(100, len(matched) * 30),
            matched_terms=matched,
            reasons=["命中量子计算术语"] if matched else [],
        )

    def assign_tags(self, paper: Paper) -> TagAssignment:
        text = f"{paper.title} {paper.abstract}".casefold()
        if "error correction" in text:
            return TagAssignment("量子纠错")
        if "network" in text:
            return TagAssignment("量子网络")
        return TagAssignment("量子算法")


plugin = QuantumComputingPlugin()
```

示例只展示接口，不代表生产级量子领域词表。实际插件应像自动驾驶插件一样加入明确词、上下文组合、近似误命中排除和测试样本。

### 2. 修改配置

```yaml
filtering:
  plugin: "plugins.quantum_computing:plugin"
  llm_review_min_score: 10
```

`module:attribute` 两部分都必须正确，且模块必须能从仓库根目录导入。

### 3. 修改站点品牌

至少更新 `config/config.yml` 中的：

```yaml
site:
  title: "Quantum Papers"
  subtitle: "Daily Quantum Computing Research Digest"
  domain: "your-domain.example"
```

Fork 使用者还应修改 `sources.user_agent`、README、CNAME/DNS、仓库链接和项目介绍。模板的页面 description 会自动读取 `site.subtitle`。

### 4. 使用全新的历史数据

不要在同一份 `data/` 中混合自动驾驶历史和新领域数据。已有日期默认返回 `unchanged`，直接换插件只会让旧日期仍保留自动驾驶论文、新日期开始出现另一个领域。

推荐方式是：

1. 在新的 Fork 或分支中保留代码；
2. 有意识地移除原项目的 `data/daily/`、`data/papers/` 和生成索引；
3. 用新插件从目标起始日期重新生成数据；
4. 检查后再发布新站点。

删除历史数据是项目迁移操作，应在独立分支中完成并保留 Git 历史，不要在原自动驾驶站点上直接执行。

### 5. 检查候选源覆盖范围

插件只能筛选候选源已经提供的论文，不能发现完全不在候选集合中的内容。

- 默认来源是 Axi 当日页面；目标领域必须出现在该页面候选中。
- 只有显式传入 `--allow-arxiv-discovery` 时，Axi 失败才使用 arXiv 分类回退。
- 回退分类由插件的 `arxiv_categories` 决定，例如量子领域使用 `quant-ph`，而不是自动驾驶默认的 `cs.CV/cs.RO/cs.AI/cs.LG`。
- 如果目标领域需要 PubMed、Semantic Scholar 或其他来源，应新增 Source 实现，不能只改插件。

### 6. 添加领域测试

每次修改插件至少应覆盖：

- 明确属于目标领域的正样本；
- 与目标领域词汇相似但实际无关的负样本；
- 通用方法词但缺少领域上下文的样本；
- 领域专用数据集或术语样本；
- 标签主次顺序；
- 中英文关键词。

```powershell
ruff check .
pytest -q
python -m adpaper validate
python -m adpaper build
```

### 7. 先预览再发布

```powershell
python -m adpaper update --date 2026-08-12 --force --dry-run
```

或通过 QQ：

```text
预览 2026-08-12
```

重点检查 `candidate_count`、`selected_count`、warnings 和 Actions 中的 LLM HTTP 状态。预览不提交数据，也不创建 Pages 部署记录。确认结果后再正式更新或补跑。

## 设计约束

- 规则优先保持确定性、可测试和可审计。
- 插件不进行网络请求，也不读取 API Key。
- 高召回不能依赖无限扩张的宽泛词；必须配合上下文和负样本。
- 标签必须来自插件声明的 `tags`，最多一个主标签和两个次标签。
- 修改规则或词表后递增 `version`，便于日后追踪每日数据使用的筛选版本。
- 新领域的开源贡献应同时提交插件、正负测试和文档，不接受只有大段关键词但没有误命中验证的规则。
