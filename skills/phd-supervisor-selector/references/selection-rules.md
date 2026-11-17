# Supervisor Selection Rules

## Evidence Priority

Use the strongest available evidence, in this order:

1. The PhD program publishes an eligible supervisor list; only choose names from that list.
2. The profile says the person supervises PhD/research students or is accepting doctoral students.
3. The profile has a `supervision`, `students`, `graduate supervision`, or similar section.
4. The CV/profile lists current or former PhD students.
5. The biography mentions PhD supervision, doctoral committees, or current/past doctoral students.
6. The title and employment type imply possible PhD supervision, with regional caution below.

If evidence is weak but the person is otherwise promising, move them to `排除或待确认` or mark the exact risk in `备注`.

## Selection Rounds

Use a staged judgement when explicit evidence is not available:

1. First pass: select only names from an official PhD supervisor list or profiles that clearly say the person can supervise PhD/research students.
2. Second pass: if no official list exists, prioritize people with a `supervision` section, supervised-student history, or biography evidence of doctoral supervision.
3. Third pass: only when the list is still thin, use title and region heuristics. In this pass, mark uncertainty plainly in `备注` or put the person in `排除或待确认`.

If several profiles in the same school share a pattern, use that pattern. For example, when only profiles with `available to supervise PhD students` appear among otherwise similar staff, select the marked profiles first.

## Region and Title Heuristics

When there is no explicit supervision evidence:

- United States, Hong Kong, Macau, and Europe except the UK/Ireland: normally require `Assistant Professor` or above. Do not select plain `Lecturer`.
- Singapore: normally require `Assistant Professor` or above unless a profile explicitly states doctoral supervision.
- UK and Ireland: `Lecturer` and `Senior Lecturer` may be acceptable when the school uses the UK system, but add a note if supervision eligibility is not explicit.
- Australia and New Zealand: `Lecturer` and `Senior Lecturer` may supervise in some universities. Check whether the profile or research degree page says they can supervise or are available for supervision.
- Other regions: `Lecturer` or above may be acceptable if the profile is research-active and the program allows it.
- Research fellow, research assistant professor, postdoc, or equivalent: include only if the profile or PhD page clearly indicates supervision/admission eligibility.

When only a title is visible and no other supervision evidence is available:

- United States, Hong Kong, Macau, and most of continental Europe: do not select `Lecturer`.
- Singapore: normally do not select `Lecturer`.
- UK and Ireland: `Lecturer` and `Senior Lecturer` can be considered, but note `需确认带博` when the page does not say it directly.
- Australia and New Zealand: `Lecturer` and `Senior Lecturer` can be considered only with supporting evidence or when no better match exists; note the supervision risk.
- For old UK-system titles used outside the UK, judge by the institution's actual rule and profile evidence rather than the title word alone.

## 🔴 国家黑名单：挪威、瑞典、葡萄牙，一律不看（2026-10-23 定调，2026-10-27 增补葡萄牙，2026-11-17 加固，焊死）

**用户原话**：

- 2026-10-23：「提到欧洲的时候除非是特意说明，绝对不看挪威和瑞典。」
- 2026-10-27：「现在加上葡萄牙。」
- 2026-11-17：「我看郭书睿还是选了瑞典呀？所以欧洲不要瑞典，挪威，葡萄牙还是没有起效啊」← 规则有漏洞，本版据此重写

**黑名单**：

| 国家 | 英文 | 常见学校（**看到这些校名就等于看到该国**） | 加入日期 |
|---|---|---|---|
| 挪威 | Norway / Norwegian | Oslo、Bergen、NTNU（Trondheim）、Tromsø、NMBU（Ås）、Stavanger、Agder、Nord | 2026-10-23 |
| 瑞典 | Sweden / Swedish | **Lund**、Uppsala、Stockholm、KTH、Chalmers、Gothenburg、Linköping、Umeå、Örebro、Karolinska、SLU、Malmö | 2026-10-23 |
| 葡萄牙 | Portugal / Portuguese | Lisbon、Porto、Coimbra、NOVA、ISCTE、Minho、Aveiro、Évora、Católica | 2026-10-27 |

> 📌 名单可增补：用户说「再加上 X」时，在表里加一行（含常见学校），并同步改本节标题、执行口径、以及 `rules-write.md` / `search-phase.md` / `search-orchestrator.md` / `SKILL.md` 的索引行。

### 规则一：这是**国家黑名单**，不依赖「欧洲」这个词出现

**不管范围词怎么写，黑名单国家一律排除。** 包括但不限于这些路径：

- 区域词：欧洲、欧陆、欧洲大陆、北欧、欧盟、Europe、continental Europe、EU、Nordic、Scandinavia
- **混合写法**：`澳欧`、`英欧`、`欧洲（不含英国）`、`欧陆不含英国`、`QS 50-200`
- **非欧洲路径**：`一带一路`（⚠️ 葡萄牙是海上丝路国家，实测风险）、欧盟项目、特定学科的国际合作网络、按 QS/排名带直接列全表
- 任何没出现「欧洲」两个字、但排名带或项目清单实际覆盖到该国的情形

### 规则二：「特意说明」的唯一认定标准（2026-11-17 加固——这是上次漏掉的洞）

**只有出现「国家名」或「该国具体学校名」才算特意说明。区域级词汇一律不算。**

| 用户/方向书的写法 | 算不算点名 | 动作 |
|---|---|---|
| 「挪威瑞典也可以」「含北欧」「加上葡萄牙」 | ✅ 算 | 放开该国 |
| 「加上 Lund」「看看 Uppsala」「Porto 也查一下」 | ✅ 算（点名了具体学校） | 放开那一所 |
| 「欧洲 QS 前 100」「澳欧 QS 50-200 可看」「欧陆不含英国」 | ❌ **不算** | 该国全部排除 |
| 「北欧 6 所」「欧洲开扫」「欧陆收口」 | ❌ **不算** | 该国全部排除 |
| 「QS 前 100」「排名带内都要」 | ❌ 不算 | 该国全部排除 |

> ⚠️ **2026-11-17 实测翻车点**：郭书睿任务的范围写「澳欧 QS 50-200 可看」，执行时被理解成「用户特意说明要看欧洲」→ 于是扫了 `Lund / Uppsala / Stockholm / Oslo / Copenhagen / Aarhus`，**两条瑞典 Lund 记录已写入表**（Mads Barbesgaard `recI83JNRI3Am`、Agnes Andersson `recYcZCLeRjEc`）。根因就是旧版规则没定义「特意说明」的边界，让区域词被当成了点名。
> **记住：「欧洲可看」≠「北欧可看」≠「瑞典可看」。**

### 规则三：续传时必须重新过滤 search-state 里的既有队列

`search-state/<学生>.md` 的「下一批队列 / 待做」清单**可能是规则生效前写下的**，里面有黑名单国家的学校照样会被执行。**每次从 state 续传、开工第一批之前，先拿黑名单把队列扫一遍**，命中的删掉，并在 state 里留一行「已按国家黑名单剔除：X / Y」。

> ⚠️ 郭书睿 state 里就写着「北欧 6：Lund/Copenhagen/Uppsala/Stockholm/Aarhus/Oslo」，直接被当成待办执行了。

### 未列入黑名单的欧洲国家照常处理

英国、爱尔兰、德国、荷兰、丹麦、芬兰、瑞士、奥地利、法国、意大利、西班牙、比利时等仍按用户给的排名带与方向要求正常搜索。

### 四个阶段的执行口径

| 阶段 | 动作 |
|---|---|
| 建名单 | 列候选校时直接剔除黑名单国家的**全部**学校，不派子代理、不抓取 |
| 续传 | 扫 `search-state` 的待做队列，剔除黑名单国家，state 里注明已剔除 |
| 写入 | 发现黑名单国家的导师一律**不写入**；已在表里的历史记录不属本条范围，但要在交付报告里单独列出并问用户是否处理 |
| 审核 | 表内出现黑名单国家的记录且用户从未点名 → 标为「范围外（默认排除）」并在报告里点出，不要静默放过也不要自作主张删除 |

**不确定时问用户**，不要自己推断「这次应该可以」。本条与用户其他地区要求叠加时，**以更严格的为准**。

## 🎓 默认排除顶尖名校（层级型排除，与地区无关）

**规则**：下表学校**默认不纳入搜索范围**——不搜索、不写入、不进候选池。除非用户**当次单独点名**。

| 地区 | 学校 | 排除原因 |
|---|---|---|
| 🇬🇧 英国 | University of Oxford、University of Cambridge | 申请门槛极高 |
| 🇺🇸 美国 | Stanford、MIT、Harvard + 美国 Top 15（US News） | 同上 |

**三种情形**：

| 用户说法 | 动作 |
|---|---|
| 「QS 前 xxx」「英国 QS 前 100」这类**范围描述** | 自动跳过下表学校，不需要额外确认 |
| **单独点名**某校（如「加上剑桥」） | 只纳入被点名的那一所，其余照常排除 |
| **明确说不要排除**（「顶尖的也可以试试」「牛剑也加上」） | 该批次全部放开 |

**与地区默认排除的区别**：本条按**学校层级**排除，与地区无关；挪威/瑞典/葡萄牙那条按**国家**排除。两条可能同时命中——例如「欧洲 QS 前 100」→ 既要跳过牛剑，也要跳过挪瑞葡。

**三阶段执行口径**：同地区默认排除——搜索列候选校时剔除、写入时不写、审核时发现标「范围外（默认排除）」并在报告里点出。

### ⚠️ 2026-11-17 复盘：这条规则在 2026-10-07 瘦身后失效了一个多月

- 瘦身（提交 `879f026`，SKILL.md 274KB → 25.7KB）把原 `### 排除顶尖名校（默认规则）` 从 **SKILL.md 正文**搬进了 `rules-write.md` §8。
- 但 `rules-write.md` 的定位是「**任何写入动作之前**必读、可整读」——**搜索阶段建候选校名单时根本不加载它**。而搜索阶段真正会读的 `search-phase.md` 和 SKILL.md「写入前硬门速查」里都没有这条。
- 结果：搜索阶段加载的任何文件都不含这条规则 → 牛津、剑桥被重新纳入候选，直到用户发现才反馈。
- **教训（重要）**：一条**作用于搜索阶段**的规则，必须落在搜索阶段会读的文件里（`search-phase.md` 或 SKILL.md 常驻速查）。搬进「写入前必读」文件 = 在该阶段不可见，等于规则失效。**以后任何瘦身/搬迁，都要核对规则的「生效阶段」与「文件加载时机」是否仍然匹配。**
- 对照：2026-10-23 新增的挪威/瑞典/葡萄牙规则因为同时写进了 `search-phase.md` 与 SKILL.md 速查，所以搜索阶段能正常生效。

## Usually Acceptable Titles

`Chair Professor`, `Professor`, `Associate Professor`, `Assistant Professor`, `Reader`, and equivalent full-time research/teaching-and-research faculty titles.

`Distinguished Professor` and `Honorary Professor` can be included only if the page also supports current supervision or the fit is exceptional.

## Usually Exclude

Exclude from the main table unless strong contrary evidence exists:

- `Adjunct Professor`, `Visiting Professor`, `Emeritus Professor`. **Do not include emeritus/retired professors. Delete them immediately if found.**
- `Teaching Professor`, `Professor of Instruction`, `Professor of Practice`, `Industry Professor`.
- `Clinical Professor`, `Practical Professor`, studio/practice-only faculty.
- Research-only staff, postdocs, fellows, and lab staff without doctoral supervision evidence.
- Very junior profiles with only 1-3 papers and no other research evidence.
- **Age/heavily senior profiles**: anyone clearly over ~70 or whose career timeline suggests full retirement. Do not include; delete if already in table.
- Inactive profiles: no recent publications, projects, or updates for roughly 3+ years, especially for senior scholars.
- Profiles where the person looks mainly teaching, instruction, industry practice, or professional-service oriented rather than research active.
- People whose title or page suggests they cannot independently supervise doctoral students, unless the PhD page explicitly says they can.
- Obvious mismatch with the student's hard exclusions.

## Fit Judgement

Fit can be strong even when keywords are indirect, if the supervisor's research methods, objects, or field can support the student's project.

**When to use `可以备选一下呢～` / `可以往XX方向靠～`** (only when both conditions are met):
- Bottom line: supervisor's research does NOT touch anything the student absolutely won't consider
- Trigger: research partially matches the student's direction but also diverges, worth letting the student consider

Direction-fit phrases (`和你的XX方向能搭上`/`有交叉`/`比较对口`) are also allowed as objective overlap descriptions — use `你`, not `学生`. They can be used alone or combined with the backup marker.

Correct usage:
- `教授；做心血管药物流行病学，但也有老年用药安全的研究方向；和你的药流方向能搭上，可以备选一下呢～`
- `副教授；做药物经济学和卫生技术评估，也有糖尿病慢病管理方向；可以往慢病预测模型方向靠～`

**Never use verdict labels** like `建议多看看`、`比较匹配`、`高度相关`、`很匹配`、`完美匹配`、`匹配度最高`、`匹配面最广`、`很契合`、`直接对话`、`很有交集`、`核心人选` — these are forbidden machine-scoring language. The remark should contain title, research direction, and optionally a direction-fit phrase or backup marker when the trigger condition is met. Let the student judge fit from the research description.

Do not overfit by title alone. Check publications, projects, current research, supervised students, and program requirements where possible.

## Remarks Evidence

Prefer remarks grounded in one of these evidence types:

- Direct keyword overlap with the student's direction, such as field terms, methods, materials, regions, populations, or theoretical frames.
- The supervisor's publications, projects, biography, grants, or supervised students match the student's topic even when the profile keywords are broader.
- Adjacent but potentially useful fit that should be shown to the student for judgement, such as related management, media, heritage, environment, health, finance, spatial, or cross-cultural work.
- Direction fit is good but supervision status is uncertain; say so briefly instead of overstating eligibility.

When writing a positive note, include the reason, not just a verdict. When the fit is only adjacent, use language like `可让学生判断兴趣`, `方向相关但不完全贴合`, or a short domain-specific risk.

## Direction Balance Review (审查已有导师表时必做)

当用户要求"审查现有导师的匹配度"或"重新选一下"时，不仅要逐条判断匹配度，还必须检查**整张表的方向分布是否与学生的实际工作方向一致**。

### 步骤

1. **明确学生的核心工作方向**：从备注、对话上下文、学生背景中提取。注意区分"学生感兴趣的多个方向"和"学生当前实际在做的主要方向"。
2. **逐条分类现有导师**：按方向归为三类：
   - **A 类 — 强匹配**：直接属于学生当前主要工作方向的院系/研究领域
   - **B 类 — 有交叉**：研究方向与学生工作方向有方法学或应用层面的交叉
   - **C 类 — 偏离**：研究方向与学生当前工作方向基本无关
3. **统计分布**：如果 C 类占比超过 40%，或 A 类占比低于 30%，向用户报告方向失衡问题
4. **提出方案**：建议删除 C 类，补充 A 类方向的新导师，使 A 类占比达到 50% 以上

### 注意事项

- 学生的"兴趣方向"和"实际工作方向"可能不同。以**实际工作方向**为主轴判断匹配度
- 同一个学生可能有多个方向，需要确认哪个是当前主要工作
- 不要只看导师所在系名，要看具体研究内容（同系不同方向的导师匹配度可能差很大）

## School-Level Screening

If a school is in the user's list but no suitable person is found, record it in a screening sheet with a specific reason. This is mandatory for user-specified school scopes: every searched school with no suitable supervisor must be logged in `学校初筛` or `排除或待确认` with the school name, search status, and concrete reason.

- No relevant department or PhD route found.
- Relevant department exists but all profiles are practice/teaching/technical-heavy rather than research-active.
- Staff page is dynamic or blocked and no individual page can be verified.
- The PhD route lacks funding or does not admit research students.
- No supervisor list, but other staff links may deserve a future manual pass.
- A relevant person exists but has no clear PhD supervision evidence, stale publications, or a title that is risky in that region.
- The school has a relevant PhD program, but the available staff are only loosely related to the student's direction.

Keep these notes factual and brief.

## 国内学校选导规则 (Domestic China School Rules)

以下规则适用于中国大陆高校的博士导师筛选。与海外学校共同存在时，国内学校走这套逻辑，海外学校走原有通用逻辑。

### 规则一：招生目录优先

首先查看目标学校/学院官网是否已发布**2027年博士研究生招生简章及招生目录**。

- **已公布 2027 招生目录**：仅可选择招生目录中列出的导师。目录以外任何导师（无论名气大小）均不可选。
- **未公布 2027 招生目录**：进入规则二的招生可能性判断。
- 2027 招生目录 vs 2026/2025 招生目录：如果 2027 未出但 2026 已出，不可直接用 2026 替代——进入规则二。但可将 2026 目录中连续多年出现的导师标记为"往年连续招生"作为辅助参考。

搜索招生目录时，优先搜索：
- `[学校名] 2027年博士研究生招生专业目录`
- `[学校名] [院系名] 2027年博士招生`
- `[学校名] 研究生院 2027年博士招生简章`

### 规则二：招生可能性分类（A/B/C 三级）

当 2027 招生目录未公布时，根据导师的招生稳定性分为三级：

**A 级 — 稳定招生。直接选择。**
- 学术大牛，有在研国家级重大/重点项目（如国自然重点、973/863、国家重点研发计划等）
- 历年几乎每年都在招生目录上，招生记录连续
- 判断依据：个人主页/实验室页面显示在研项目、近两年有博士招生公告、往年招生目录连续出现
- 备注可标注"往年连续招生"或"有在研重大项目"

**B 级 — 间接招生。可以选择。**
- 普通教授/副教授，每 1-2 年招一次博士生
- 有在研项目但非重大项目，近三年有博士招生记录
- 判断依据：个人主页显示在研课题、近三年招生目录中有出现但不连续
- 备注可标注招生频率（如"近三年招生 2 次"）

**C 级 — 波动招生。不选择（除非有特殊推荐理由并注明）。**
- 年纪过大（约 60 岁以上且近两年无博士生招生记录）
- 即使是大牛，但已多年（3 年以上）未出现在招生目录中
- 更偏向行政事务（如院长/副校长/党委书记等）而非一线教学研究，近三年无博士生指导记录
- 判断依据：个人主页多年未更新、近三年招生目录未出现、以行政头衔为主

C 级如确有特殊推荐理由（如方向极度契合且该方向无其他导师可选），可保留但必须在备注开头明确标注 `C级波动招生，特殊推荐理由：XXX`。

### 规则三：导师联系方式（邮箱必填）

国内学校的每一位导师，必须将 **email** 填入 `导师联系方式` 列。

- 优先从导师个人主页获取（标题栏、联系信息区、页面底部）
- 若无主页或主页无邮箱，从院系师资列表页获取
- 若以上均无，通过百度学者、ResearchGate、学术论文通讯作者邮箱等其他来源查找——并在备注中标注邮箱来源
- 禁止在该列填写非邮箱内容（如网址、电话等）

### 规则四：导师主页要求

国内学校导师的 `导师主页` 必须使用**国内官网学校的导师个人主页 URL**。

- **URL 必须是完整的原始链接**（`https://` 开头），**禁止**使用重命名的纯文本占位符（如"XXX个人主页""暂未找到"等）。即使暂时找不到，也必须填入一个有效的 URL 或留空后标注，不允许用文本替代 URL
- 优先使用学校官网的教师个人页面（通常包含研究方向、论文、项目等）
- 若无个人主页，或主页信息过少（仅含姓名+职称，无研究方向/论文/项目等实质性内容），则该主页 URL 仍填入 `导师主页` 列
- 同时必须在备注中补充其他效度较高的专业平台链接：
  - 百度学者（百度学术）个人页面
  - 百度百科词条
  - 外部文章/采访链接（含有导师研究方向说明的新闻稿、学术报道等）
  - 论文作者页面（如知网作者页、万方学者页等）
- **佐证规则**：若通过并行搜索多个页面（如百度学者+论文+新闻）推论出导师研究方向符合学生方向，而该信息在导师主页上无法看到，则必须将对应的外部链接放在备注中作为佐证

备注中的补充信息格式示例：
- `教授；自然语言处理、知识图谱、大模型应用；主页信息较少，百度学者页 https://xueshu.baidu.com/... 显示主要方向为 NLP。`
- `副教授；文化遗产保护、建筑史；无个人主页，百度百科 https://baike.baidu.com/... 显示研究方向为古建筑保护。`

### 国内学校搜索优先级

1. 首先搜索学校官网（`.edu.cn` 域名）的招生目录和导师页面
2. 若官网无法访问或无相关信息，使用百度搜索 `[导师名] [学校名] 教授` 或 `[导师名] [学校名] 博士导师`
3. 辅助来源：百度学者、百度百科、知网、万方、学校研究生院公告
