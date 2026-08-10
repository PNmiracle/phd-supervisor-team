---
name: phd-supervisor-selector
description: 博士导师筛选与表格管理工具。面向留学机构，为不同方向的学生快速建立可核验的导师列表。搜索各大学官方页面，判断导师是否具备 PhD 指导资格，填写表格各列。主力支持 Vika 在线表格直接 CRUD，Excel 作为可选回退模式。
agent_created: true
---

# PhD Supervisor Selector（博士导师筛选器）

## 概述

为博士申请者建立有据可查的导师列表。搜索各大学官方页面，判断导师是否具备 PhD 指导资格，填写表格各列，将不合格或高风险候选人排除在主表之外。

**主力模式：Vika（在线表格直接 CRUD）。Excel 作为可选回退模式。**

## Optional Companion Skill

**tavily-search-pro** — AI-powered search platform that acts as **L4 fallback** when L1-L3 access methods all fail (WAF blocks curl+browser+search). Provides:
- **extract**: Server-side page content extraction (bypasses Cloudflare/Incapsula WAF)
- **search**: Alternative search engine with clean, unencrypted result URLs
- **crawl/map**: Site structure discovery for blocked university sites
- **research**: Deep department analysis with citations

Requires `TAVILY_API_KEY` environment variable. If installed, search automatically escalates to Tavily when all other access methods are blocked. See `references/search-techniques.md` (L4 section) and `references/school-strategies.md` (L4 layer).

## 搜索编排（首先阅读）

开始搜索任务前，阅读 `references/search-orchestrator.md`。它定义了：

- **状态追踪**：续传中断的搜索，跳过已完成的学校
- **智能优先级**：按预期产出（P0-P3 层级）对学校排序
- **分阶段策略**：先快速扫描所有学校（Pass 1），再深入验证有希望的学校（Pass 2）

---

## 数据源检测

收到任务时，检测数据源：

1. **用户提供 Vika 分享链接**（如 `https://vika.cn/share/shrXXX/dstXXX/viwXXX`）：直接通过 Fusion API 操作 Vika 表格
2. **用户上传 `.xlsx` 文件**：操作本地电子表格
3. **用户同时提供**：优先 Vika 做 CRUD，Excel 做参考/填充源

---

## Excel 模式（可选）

当用户上传 `.xlsx` 文件而非 Vika 链接时，使用 Excel 模式。详见 `references/spreadsheet-rules.md`（列格式选择、列偏移检测、备注规则、质量检查）。

**默认输出列**：`导师`, `Location`, `学校名字`, `QS排名`, `美国USNEWS排名`, `Department`, `导师主页`, `导师联系方式`, `博士申请信息`, `其他导师信息`, `备注`

- `美国USNEWS排名`：仅当列表中有美国学校时包含此列
- `导师联系方式`：**国内学校必填**（导师 email），海外学校选填

---

## Vika 集成

**零依赖。** 所有操作使用 Python 3 标准库（`urllib` + `json`）——无需 `vika-cli`、npm 或第三方 SDK。仅需 API token 和任意 Python 3 安装。导入 Excel 时额外需要 `openpyxl`。

### 设置

1. 从 URL 解析：`datasheetId`（`dstXXX`）、`viewId`（`viwXXX`）
2. **Token 安全**：引导用户设置环境变量（不要在聊天中明文传递）：
   ```bash
   echo 'export VIKA_TOKEN=你的token' >> ~/.zshrc && source ~/.zshrc
   ```
3. Base URL: `https://api.vika.cn/fusion/v1`

### 操作前必做：过滤选导意向非空行

**每次执行增删改操作前，必须先获取所有记录并排除 `选导意向（点击选择）` 非空的行：**

```python
# 获取所有记录
result = vika("GET", "/records?maxRecords=200&fieldKey=name")
all_records = result["data"]["records"]

# 仅保留选导意向为空的行（这些是待编辑的行）
editable = [r for r in all_records if not r["fields"].get("选导意向（点击选择）")]

# 选导意向非空的行（这些是受保护的行，只能读取）
locked = [r for r in all_records if r["fields"].get("选导意向（点击选择）")]

# 所有增删改操作只针对 editable 列表中的 recordId
```

### 能力（记录级 CRUD）

| 操作 | 端点 | 备注 |
|------|------|------|
| 列出字段 | `GET /datasheets/{id}/fields` | 发现字段名和类型 |
| 列出记录 | `GET /datasheets/{id}/records?viewId=...&maxRecords=...` | 支持 filterByFormula、sort、分页 |
| 创建记录 | `POST /datasheets/{id}/records` | 每批最多 10 条，使用 `fieldKey: "name"` |
| 更新记录 | `PATCH /datasheets/{id}/records` | 发送 `{"records": [{"recordId":"xxx","fields":{...}}], "fieldKey": "name"}` |
| 删除记录 | `DELETE /datasheets/{id}/records?recordIds=recXXX` | recordIds 在 query parameter 中，非 request body |

### 关键限制

- **DELETE 请求格式**：recordIds 必须在 URL query parameter 中（`?recordIds=recXXX,recYYY`），不能在 request body 中。Helper 函数已自动处理此转换。
- MagicLookUp / OneWayLink 字段不可通过 API 写入。
- 每批最多 10 条记录，批次间加 0.3-0.5 秒延迟。

详细的 API 代码模板和操作指南见 `references/vika-guide.md`。

### 自然语言删除流程

当用户说"删除导师XXX"或"删除这条记录"时，按以下步骤操作：

1. **解析请求**：理解要删除什么（按导师名、按学校、按备注内容等）
2. **查找记录**：用 GET + filterByFormula 找到匹配的记录
   ```python
   # 按导师名查找
   filter_expr = urllib.parse.quote('{导师}="张三"')
   result = vika("GET", f"/records?filterByFormula={filter_expr}&maxRecords=200")
   records = result["data"]["records"]
   ```
3. **提取 recordIds**：从响应中提取 `recordId` 字段
4. **确认删除**：向用户展示找到的记录，确认是否删除
5. **执行删除**：使用正确格式调用 DELETE
   ```python
   # ✅ 正确格式
   vika("DELETE", "/records", {"records": [r["recordId"] for r in records]})
   ```
6. **验证结果**：删除后再次 GET 确认记录已移除

⚠️ **DELETE 格式陷阱**：必须发送 `{"records": ["recXXX"]}`，不能发送纯数组 `["recXXX"]`。

---

## 表格验证工作流（验证已有表格时触发）

当用户要求"验证表格信息""检查链接""确认 funding 是否属实"时，按以下工作流执行：

### 验证范围

1. **导师主页链接**：逐条 WebFetch 验证，确认是个人主页而非 404 伪装页/院系列表页/第三方平台
2. **博士申请信息链接**：WebFetch 验证可访问性
3. **其他导师信息链接**：WebFetch 验证可访问性
4. **备注信息**：方向匹配性、格式规范、排除 emoji 和主观判断词
5. **项目综合情况**：PhD 项目名称是否正确、stipend 金额是否与官网一致
6. **funding 预计情况**：NIH grant 类型/金额/时间线是否可验证、是否存在"中心总计"与"个人 funding"混淆

### 验证执行顺序

```
Step 1: 获取学生方向定义书 + 表格全部记录
    ↓
Step 2: 导师主页链接验证（逐条 WebFetch，禁止仅用 curl）
    ↓
Step 3: 博士申请信息 + 其他导师信息链接验证
    ↓
Step 4: 备注方向匹配性验证（对照方向定义书核心机制）
    ↓
Step 5: Stipend 金额核实（搜索每个学校官网最新数字）
    ↓
Step 6: NIH Grant 核实（NIH Reporter 交叉验证）
    ↓
Step 7: 生成问题清单 → 分级 → 修正 → 二次验证
```

### 问题分级

| 级别 | 描述 | 示例 |
|------|------|------|
| P0 - 严重 | 404 链接、错误 grant 类型、严重低估 stipend | 必须立即修正 |
| P1 - 重要 | 院系列表页代替个人主页、第三方平台链接 | 需找替代链接 |
| P2 - 轻微 | 备注格式问题、emoji、乱码 | 建议清理 |
| P3 - 提示 | 推测性数据未标注"约"、定性判断 | 建议补充标注 |

---

## 搜索工作流（Vika 和 Excel 通用）

1. 解析学生背景、研究方向、硬排除条件、目标地区/学校、排名限制
2. **检测表格格式**（见 `references/spreadsheet-rules.md`）：Vika 模式从 URL 解析 datasheetId；Excel 模式若用户提供模板则沿用其列结构
3. 优先搜索官方大学来源
4. **SPA/动态站点**：先查 `references/search-techniques.md` L0-SPA 策略（找替代来源而非死磕 SPA 壳）；若无替代来源再探测 JS bundle 中的 API 端点
5. 按内容验证每个导师主页
6. 使用 `references/selection-rules.md` 判断指导资格
   - **国内学校**：走「国内学校选导规则」子章节（招生目录优先 → A/B/C 分类 → 邮箱必填 → 主页要求）
7. 使用 `references/spreadsheet-rules.md` 填写表格
   - **国内学校**：额外遵守「国内学校表格规则」子章节（导师联系方式必填、主页来源要求、备注链接格式）
8. **写入后立即设置学校关联字段**（见「学校关联字段必填」规则）：确定学校→查找/创建主表记录→设置OneWayLink→验证Location/QS/国内学校层次已同步
9. **飞行前检查清单**（见下方「飞行前检查清单」）：写入前逐项检查 1-10，特别关注 6a/6b/6c（主页类型+硬排除+方向核心度），任一不过则跳过该导师
10. **小批次审核触发**：累计每写完 10 条新记录（或搜完一个学校的全部导师）→ 立即暂停搜索 → spawn 独立的 supervisor-auditor 做对抗审核 → 修 P0 → PASS 后继续
11. 没找到合适导师的学校记录排除原因

---

## 搜索标准

- **搜索引擎为主要策略**查找个人导师资料。搜 `"[导师名] [大学] professor"` 获取真实 URL——不要猜测 URL
  - **国内学校**：使用百度搜索而非 Google。搜索 `"[导师名] [学校名] 教授"` 或 `"[导师名] [学校名] 博士导师"`
- 优先官方大学页面而非个人网站
- **禁止 URL 猜测**：不要通过命名规则构造 URL（失败率约 90%）
- **SPA/JS 渲染页面**：不接受 200 空壳。**优先尝试 L0-SPA 策略**（找替代来源：个人网站、ResearchGate、研究中心页面），不要死磕 SPA 壳。详见 `references/search-techniques.md` L0-SPA 节和 `references/school-strategies.md` 各学校策略
- **并行搜索**：使用 WorkBuddy Agent 工具对不同的学校/域名进行并行检查。给每个 Agent 清晰的独立任务

### 浏览器验证替代方案

WorkBuddy 不能打开真实浏览器，但可以通过以下方式验证：
1. **WebFetch** 工具获取页面实际内容验证
2. **WebSearch** 搜索 `"[Name] [University] professor"` 发现真实 URL
3. **DDG HTML 搜索**：`https://html.duckduckgo.com/html/?q=...` 返回纯 HTML

### 链接验证标准（验证已有表格时强制执行）

**❌ 禁止仅依赖 HTTP 状态码（curl/urllib）判断链接有效性。**

原因：
- 美国大学网站对 404 常返回 **200 + "Page Not Found" 页面内容**
- 旧 URL 路径废弃后可能重定向到院系统一搜索页，状态码仍是 200
- 必须通过 **WebFetch 读取实际页面内容** 才能判断真假

**✅ 正确做法：逐条 WebFetch 验证**

对每个导师主页 URL，必须：
1. **用 WebFetch 获取页面完整内容**
2. **检查页面是否包含导师姓名**（防止 404 伪装页）
3. **判断页面类型**：
   - ✅ **真正个人主页**：含 CV、Publication、Research、Contact、Biography 等专属信息
   - ⚠️ **实验室主页**：多人共用，需标注并在备注中补充个人页链接
   - ❌ **院系教师目录页**：全院教师列表，该导师只是其中一条
   - ❌ **第三方平台**：出版商简介、ORCID、LinkedIn、ResearchGate 等
   - ❌ **404 伪装页**：状态码 200 但内容显示 Not Found / 搜索页

### 导师主页类型前置过滤（搜索阶段强制执行 — 写入前硬门，不可跳过）

**在决定把导师写入表格前，必须先判断导师主页类型和研究方向是否属于硬排除项。这是写入前的硬门（pre-write gate），不是写入后的审计项（post-write audit）。跳过此步骤直接写入 = 偷懒，审核官会整批退回。**

**复盘教训（2026-08-10 优录-刘同学案例）**：7 条 P0 全部是因为写入前没执行此硬门——第三方平台页、医生预约页、CRM 聚合页、`__trashed` URL、线虫模型、纯生信、癌症主线。这些本应在搜索阶段就跳过，却一路漏到最终审核才被发现，浪费了 11% 的工作量。

#### 硬门 A：导师主页类型过滤

以下类型的页面直接跳过，不入表：

| 页面类型 | 判断标准 | 示例 |
|---------|---------|------|
| **第三方平台** | 域名非学校官方（`.edu` 或学校官方子域） | Loop.frontiersin.org、DovePress、ResearchGate、ORCID、Google Scholar、X-MOL、Aminer |
| **医生预约/诊所页** | 页面结构是医生 profile（含预约、就诊信息），无 Publications/Research Lab 板块 | NYU Langone `/doctors/...`、医院医师介绍页 |
| **CRM/中心聚合页** | 页面是研究中心/CRM 系统首页，非个人专属页 | USF `healthscholars.usf.edu/crm`、中心 landing page |
| **院系列表页** | 页面是全系教师列表，该导师只是其中一行 | `psych.zju.edu.cn/27612/list.htm` |
| **SPA 空壳** | 200 状态码但内容 < 1KB 或返回相同字节数的通用 HTML | 无实际内容的 JS 渲染壳 |

**判断方法**：
1. 用 WebFetch 打开候选 URL
2. 检查页面内容是否包含**导师姓名 + 职称 + 研究方向/论文列表**（至少两项）
3. 检查域名是否属于学校官方（`.edu`、学校官方子域、或学校官网明确列出的教师目录子域）
4. 第三方平台、医生预约页、CRM 聚合页 → **直接放弃该导师，不入表**

**例外**：SPA 壳但学校官方域名，且通过 WebSearch 能找到**替代可抓取来源**（如个人网站、实验室 WordPress 页）→ 用替代来源作为导师主页 URL。

#### 硬门 B：研究方向硬排除

以下研究方向属于**通用硬排除项**（与具体学生无关，所有学生一律排除），在搜索阶段发现即跳过，不入表：

| 硬排除项 | 判断标准 | 典型案例 |
|---------|---------|---------|
| **线虫/果蝇/酵母模式生物** | 实验室主线使用 C. elegans / Drosophila / Yeast 作为核心模式动物 | 心衰线虫模型、果蝇神经发育——即使涉及目标疾病，模式生物层级不对 |
| **纯计算生物学（>70% dry lab）** | 研究以生信分析、突变谱解析、计算建模为主，无 wet lab | 纯突变谱分析、纯数据库挖掘——即使方向关键词沾边 |
| **癌症生物学为主线** | 实验室主线是肿瘤/白血病/癌症机制，目标方向只是副业 | 白血病干细胞为主、iPSC 只是工具——即使有 iPSC 关键词 |

**判断方法**：
1. 打开导师主页，阅读 Research Interests / Publication 列表
2. 目标方向关键词在主页/论文中出现频率是否 >50%（核心方向 vs "研究方向之一"）
3. 如果方向定义书有额外的学生专属排除项，一并对照

**注意**：方向定义书中的学生专属排除项由各学生任务单独提供，不写入此通用规则。但 auditor 审核时必须拿到方向定义书原文，独立对照。

---

- **OSU**: `medicine.osu.edu/find-faculty/...` 路径常废弃，faculty 页面迁移到 `mcdb.osu.edu/people/...` 或其他子域名
- **CWRU/CCF**: `lerner.ccf.org/cvme/faculty/...` 可能改为 `my.clevelandclinic.org/staff/...`
- **TAMU**: 部分 faculty 页面在子域名如 `genetics.tamu.edu` 而非主站
- **USF**: `healthscholars.usf.edu` 子域名页面结构不稳定
- **旧 URL 返回 200 但内容为空**：curl 无法识别，必须 WebFetch

---

## 深度发现管线

1. **全面扫描**——通过 API 获取所有教师数据，按目标院系筛选
2. **过滤**——检查剩余教师的学位、专业、研究关键词
3. **优先级排序**——按与学生方向的匹配度排名
4. **验证**——通过 WebFetch 打开个人页面，确认研究内容
5. **扩展**——仅在用户明确要求时重新检查之前 404 的链接

---

---
## 导师转校处理流程（2026-08-07 新增）

若发现导师已从当前学校转到新学校，且新学校在选校范围内有合适的 PhD 项目，则**全面更新以下字段**：

1. **学校名字**：改为新学校的 recordId
2. **导师主页**：更新为新学校的官方 profile URL
3. **导师联系方式**：更新为新学校的邮箱
4. **Department**：更新为新学校的院系/职位
5. **所在PhD项目**：更新为新学校的 PhD 项目名称
6. **博士申请信息**：更新为新学校 PhD 项目 URL
7. **项目综合情况**：改为新学校的项目情况（Stipend/录取难度/业界出路等）
8. **有机化学前置要求** + **官方说明**：更新为新学校的官网依据
9. **备注**：标注转校信息（何时从何处转来），若新职位行政任务重（如 DVC Research）需标注"套磁前确认带生意愿"

**示例**：Mike Ryan 2026年3月从 Monash DVC Research 转到 Sydney DVC Research → 学校从 Monash (QS 31) 更新为 Sydney (QS 28)，主页、邮箱、PhD项目等全部更新。

---
## funding 预计情况：三段式格式（强制执行）

**【28年funding预估风险】和【funding预计情况】两列必须按三段式填写：**

| 段落 | 标题格式 | 内容 |
|------|---------|------|
| 第一段 | `【过往资助历史】` | 该PI历史上获得的主要资助、资助机构、持续时间 |
| 第二段 | `【现有在研资助】` | 当前活跃的资助项目、金额规模、到期时间、实验室现状 |
| 第三段 | `【2028年预测】` | 学生进入博士第二年（2028年）时的资金支持预判、风险点、续约概率 |

**禁止**只写零散描述不按三段式组织。格式要求：每段以`【】`中文标题开头，段落间用 `\n` 分隔。

## 项目综合情况字段结构

`项目综合情况` 列需覆盖四项，用 `【】` 标签分隔：
- `【项目】`：PhD项目名称 + 项目实力 + 方向覆盖 + 产业联系
- `【录取难度】`：直接判断高/中等偏高/中等/中等偏低/低
- `【funding】`：奖学金类型 + 金额（搜索官网核实最新数据）+ 覆盖年限
- `【毕业业界可能性】`：毕业生去向 + 产业/临床转化前景

**禁止**写录取率等推测性数字（标注为"约"或留空）。

**默认使用中文填写备注**，即使 Excel 源数据的研究方向为英文也需翻译为中文关键词。格式：`职称；研究方向（中文关键词）；风险/注意事项。`

### 🎯 语气要求：像面对面和学生说话

备注是给申请学生看的，语气要自然、有"人味"，像坐在旁边帮 ta 梳理信息的口吻。

- **不要**写"符合XX方向""匹配XX方向""老师的XX和你的XX很相关"——太机械，像机器打分
- **不要**写任何评价性连接语（如"很契合""直接对话""很有交集"）——备注只陈述事实
- **不要**堆砌术语关键词——写完要读一遍，想象你是说给一个紧张的申请者听的
- **要**写短句，多用"，"和"；"，少用长定语句
- 信息量要保持，但语气要松弛——是"帮你梳理"不是"给你打分"

### 备注格式：三段式

每条备注严格按三段式书写，用分号分隔：

**导师职称 + 研究方向（可带导师主页中的原文出处）+ 匹配度标识**

| 段落 | 内容 | 说明 |
|------|------|------|
| 第一段 | 导师职称 | 教授/副教授/助理教授/讲师等 |
| 第二段 | 研究方向 | 从导师主页中找原文依据再写研究方向（没有依据不写）；可摘录主页原文作为出处（如 `"research focuses on consumer judgment and decision-making"`） |
| 第三段 | 匹配度标识 | 仅两极标注，见下表 |

**匹配度标识（只在拿不准的时候写）**：

**唯一允许的标识**：方向有一定交叉但非核心对应，或资历/职称偏早期，有点沾边但拿不准 → 写 `可以备选一下呢～` 或 `可以往xx方向靠～`。

**其他所有情况（包括方向直接相关、有合理发表记录、特别推荐的顶尖人选）——不写任何匹配度标识，不写任何评价性连接语（如"很契合""能搭上""直接对话"）。备注只保留职称 + 研究方向，句号结尾即可。**

**禁止事项**：
- 禁止在备注里使用任何 emoji 符号（🔥👍👀⭐✅❌ 等）
- 禁止使用 `建议多看看呢～` 标识（已废弃，所有正面推荐语都不写）
- 禁止使用主观评价用语如 `高度相关`、`比较相关`、`很匹配`、`完美匹配`、`强匹配`、`弱相关`
- 禁止使用 `比较匹配～` 标识（已废弃，中间档不写）
- 禁止写评价性连接语如 `老师的XX和你的XX很相关`、`很契合`、`直接对话`、`很有交集`、`能搭上`
- 描述事实，不做评判

**正确示例**：
- `副教授；做消费者判断与决策、跨期选择。`
- `教授；做文化遗产和建筑史；可以往遗产保护方向靠；可以备选一下呢～`
- `助理教授；消费者决策、道德决策、自我概念清晰度；MIT PhD。`

### 🗣️ 第二人称规则（强制执行）

**所有备注必须以"你"称呼学生，不用"学生"二字。**

- ✅ `研究方向涵盖青少年心理健康与学校支持体系`
- ✅ `涉及跨文化适应与学生发展领域`
- ✅ `可以往你感兴趣的学校心理支持方向靠`
- ❌ ~~`和学生的青少年心理健康方向很契合`~~
- ❌ ~~`和学生发展及跨文化适配方向很契合`~~

**批量替换规则**：
- 所有 `学生` → `你` 或 `你的`（按语境）
- 所有 `和学生` → `和你的`
- 所有 `为学生` → `为你`

### 📛 方向编号禁止规则

**禁止在备注里写"方向1""方向2""方向3"等编号。必须写出具体的学术研究方向名称。**

- ❌ ~~`方向1核心匹配`~~
- ❌ ~~`方向1+2精准匹配`~~
- ❌ ~~`方向2方向对口`~~
- ✅ `研究方向涵盖青少年心理健康与学校支持体系`
- ✅ `涉及跨文化适应与学生发展领域`
- ✅ `在青少年心理健康与学校支持体系的视角下研究家庭干预`

方向编号 → 方向名称映射（按各学生的实际研究方向填写）：
- 方向1 → 青少年心理健康与支持体系
- 方向2 → 跨文化适应与学生发展
- 方向3 → 社会工作与青少年支持

### 🧹 AI 生成内容清理（写备注后强制执行）

**每次写完或批量修改备注后，必须执行以下清理操作：**

1. **移除所有 ⚠️ 及之后的内容**：备注中任何 `⚠️` 字符及其在同一语义段落后的内容都要删除。`⚠️` 会让学生感到不安，且看起来"太像 AI 写的"。

2. **移除所有 Emoji**：备注中不得出现任何 emoji 字符。使用以下 Unicode 范围过滤：
   - 表情符号（U+1F300–U+1F9FF）
   - 杂项符号（U+2600–U+27BF）
   - 装饰符号（U+2702–U+27B0）
   - 补充符号（U+1F900–U+1F9FF）
   - Dingbats（U+2700–U+27BF）
   - 交通/地图符号（U+1F680–U+1F6FF）

3. **清理后检查**：备注应只保留纯文字 + 中文标点，干净、自然、像人说的话。

**处理方式：** 可以在 Python 中用 Unicode 码点范围过滤，或逐字符检查 `unicodedata.category()`。

### 当学校匹配导师极少时（1-2位）

**在备注末尾补充说明该系其他教师的主要方向**，让学生有"已全面搜索"的信心。使用客观描述，不要写"确实没有"等主观判断。

正确示例：
- `教授；决策神经科学、风险与社会决策、无创脑刺激；这个系老师主要做临床和辅导实践方向，这一位的决策方向是唯一交叉点。`
- `副教授；消费者判断与决策；这个系以社会认知和神经犯罪学为主，就这一位做消费者行为相关；可以备选一下呢～`

要点：
- 说明"这个系老师主要做XX方向"——客观陈述事实
- 说明"只有这一位和XX搭边"——给出数量，让学生有"全面看过了"的感觉
- 不要写"没有合适的"、"确实没有"等主观评价

**补充信息行写入规则**：当需要另起一行单独写入系/院的补充说明（如某系无匹配导师）时，只需填写 `导师` 和 `备注` 两个字段，无需填写导师主页、博士申请信息等其他字段。

---

## 操作权限（CRITICAL — 所有操作前首先检查）

### 🚫 表格隔离：只操作用户指定的那张表

用户每次提供 Vika 分享链接时，从 URL 解析 `datasheetId`（`dstXXX`）。**本轮所有 CRUD 操作仅限于用户本次传入的这张表**。

**绝对禁止：**
- 操作用户未明确指定的其他 datasheet（即使 API token 有权限）
- 操作关联的学校主表（OneWayLink/MagicLookUp 引用的表）
- 通过 API 修改关联表的任何字段
- 在用户未给链接时自行假设或复用之前的 datasheetId

### 🚫 范围外记录保护：非目标范围记录禁止删除（2026-08-05 新增，CRITICAL）

**用户目标范围之外、但已存在于表格中的历史记录（如其他国家的学校、不在本轮目标州/排名范围内的学校），默认保留，禁止删除。**

删除操作是**高危且不可逆**的（Vika API 删除后无回收站恢复接口，只能网页端「时光机」整表回滚）。因此：

**绝对禁止：**
- 因"不在本轮目标范围"而主动删除已有记录（即使该记录可编辑、选导意向为空）
- 因"与当前学生需求不匹配"而批量清理历史记录
- 未经用户明确确认执行任何 DELETE 操作

**唯一允许删除的情形（全部满足才可删）：**
1. 用户在本轮任务中**明确点名**要求删除某条记录（如"删除导师XXX"），且已向用户展示待删记录并获确认
2. 质量维护场景：验证确认导师**已离任/页面永久 404/官方目录已无此人**（离任导师检测规则），且该记录不是本轮新增

**范围外记录的正确处理方式：**
- 保留原样不动；如需提示可在交付报告中向用户说明"表内存在 XX 条范围外历史记录，未做处理"
- 若用户明确要求清理，先列出将删除的记录清单，**等用户确认后再执行**

**删除流程铁律：任何 DELETE 调用前，必须在操作记录中留下理由（用户点名/离任验证），并在回传结果中逐条列出被删记录。**

### 🚫 选导意向保护：已填写=不可触碰

当 Vika 表中 `选导意向（点击选择）` 字段有值（非空/非 null）时：
- **禁止修改**该行的任何字段
- **禁止删除**该行
- **禁止覆盖**该行的备注、研究方向、导师主页等字段
- **仅可读取**，不可写入

这些是学生已经审阅并反馈过的记录，任何修改都会造成数据损失。

**操作前必须：**
1. 先 GET 所有记录
2. 过滤掉 `选导意向（点击选择）` 非空的行
3. 仅对 `选导意向` 为空的行执行增删改操作

### 📋 当前活跃表（由用户传入）

表的链接和 datasheetId 随每次任务由用户提供，不固定。首次操作时从链接解析并确认。

---

## 关键规则（CRITICAL）

### Stipend 与 Funding 核实规则（验证已有表格时强制执行）

#### Stipend 金额必须逐校核实官网

**禁止未经核实直接填写或接受 stipend 数字。** 表格中常见的 stipend 数据存在系统性偏差，必须搜索每个学校 PhD 项目的官网确认最新数字。

**常见学校官方 stipend 参考（2025-2026 学年）**：

| 学校/项目 | 常见错误数据 | 官方数据 | 偏差 |
|----------|------------|---------|------|
| CWRU BSTP | ~$37K+/yr | **$38,000** | 轻微低估 |
| OSU BSGP | ~$34K/yr | **$33,980** | 基本准确 |
| UB PPBS | ~$32K/yr | **$31,000-$35,000**（来源不一）| 在范围内 |
| TAMU Medical Sciences (Medical Physiology) | ~$32K/yr | **$35,000** | **-$3,000** |
| TAMU Genetics | ~$32K/yr | **$32,000** | 准确 |
| USF Medical Sciences | ~$30K/yr | **$37,000** | **-$7,000（严重）** |
| Rochester GDSC/CMPP | ~$35K/yr | **$35,100** | 基本准确 |
| UW-Madison CMB | $37K+/yr | **$37,000** | 基本准确 |

**关键教训**：
- USF Medical Sciences 的 stipend 被系统性严重低估（$30K vs 实际 $37K）
- TAMU 不同 track（Medical Physiology vs Genetics）stipend 不同，不能统一填写
- 不同来源（学校官网、研究生院、具体项目页面）的 stipend 数字可能不一致，需标注来源

#### NIH Grant 必须通过 NIH Reporter 交叉验证

**对表格中提到的具体 NIH grant，必须到 reporter.nih.gov 核实**：
- Grant 类型（R01 / R35 MIRA / K99/R00 / T32 / K08 等）
- 具体金额和资助周期
- PI 姓名是否与导师一致
- 项目编号是否可查

**常见错误模式**：
- 将 K08 过渡性资助描述为已转为 R01（实际可能未获独立 R01）
- 将合作 grant 误认为个人独立 grant
- 将"中心总计 funding"与"个人 funding"混为一谈
- 将 K99/R00 的资助金额误标为 R01 级别

#### Funding 字段中的推测性数据必须标注

以下数据类型属于**推测性估算**，学校官网通常不公布具体数字，必须标注为"约"或"估算"：
- PhD 录取率（"~15-20%"）
- 国际生比例（"~30%"）
- 未来 funding 预估（"2028 年预计..."）
- startup 金额范围（"$800K-$1.2M"）

**禁止将推测性数据作为事实陈述。**

---

### SPA 壳返回 200 ≠ 链接有效
200 状态码 + SPA 壳（响应相同内容，所有不同 URL 返回相同字节数）→ **不能确认导师存在**。立即切换到 **L0-SPA 策略**：通过 WebSearch 找替代来源（个人网站、ResearchGate、研究中心页面），不要在 SPA 壳上浪费尝试。详见 `references/search-techniques.md` L0-SPA 节。

**经典案例（2026-07-13）**：CUHK STA 的 `/people/faculty/{name}/` 所有 URL 返回完全相同的 114KB 首页 HTML（SPA 壳），浏览器 JS 加载后才显示个人内容。正确格式是 `/peoples/{slug}/`（静态 HTML，可直接验证研究方向）。详见 `references/school-strategies.md` CUHK 章节。

**经典案例（2026-07-23）**：HKUST(GZ) 的 `facultyprofiles.hkust-gz.edu.cn` 全站 SPA，所有页面返回完全相同的 1522 字节 HTML 壳。URL 格式从 `?name=XXX` 查询参数改为 `/faculty-personal-page/NAME/shortname` 路径格式，但两种格式的 SPA 行为一致。自动化工具无法区分旧 URL 失效和新 URL 有效——200 ≠ 内容正确，必须浏览器人工确认。DSA 学域的替代来源为 `dsa.hkust-gz.edu.cn/blog/YYYY/MM/DD/name-slug`（WordPress 格式，可直接抓取内容）。

### CUHK(SZ) 特殊规则：教师 URL ID 不稳定（2026-07-23 验证）

CUHK(SZ) 数据科学学院的 `sds.cuhk.edu.cn/teacher/XXX` 的 ID 不是稳定标识符。2026 年 7 月的大规模重组中，同一学院的教授被分散到多个子域名和路径格式：

| 变化类型 | 示例 | 旧 URL | 新 URL |
|----------|------|--------|--------|
| teacher ID 变更 | 李爽 | `/teacher/273` | `/teacher/472` |
| 路径格式切换 | 王子卓 | `/teacher/254` | `/node/59` |
| 跨子域名迁移 | 罗智泉 | `sds.cuhk.edu.cn/teacher/478` | `sse.cuhk.edu.cn/teacher/184` |
| 个人网站 | 丁宏强 | `sds.cuhk.edu.cn/teacher/378` | `myweb.cuhk.edu.cn/chrisding/Home/Index` |

**关键规则**：

1. **每次会话重新搜索**：不信任上次存储的 teacher ID，使用 WebSearch 搜索 `"[导师名] sds.cuhk.edu.cn teacher"` 找新 ID
2. **不能按旧 ID 推断新 ID**：ID 变更无明显规律（不是简单递增/递减）
3. **多种 URL 格式并存**：同一学院同时存在 `/teacher/XXX`、`/node/XXX`、`myweb.cuhk.edu.cn`、`gklbdc.cuhk.edu.cn`、`sse.cuhk.edu.cn`、`mscfe.cuhk.edu.cn` 等多种格式，每种都需独立搜索验证
4. **Python SSL 握手失败 ≠ 链接失效**：`sds.cuhk.edu.cn` 在 Python urllib 中报 `SSLV3_ALERT_HANDSHAKE_FAILURE`，但 WebFetch 和浏览器可以正常访问。先用 WebFetch 测，再判死

### 导师主页必须是个人 URL

禁止使用通用院系列表页。每位导师必须有自己唯一的个人主页 URL。

**找不到合格个人主页的导师不得写入 Vika 表**（强制规则）：

禁止用以下 URL 代替个人主页：
- 院系师资列表页（如 `psych.zju.edu.cn/27612/list.htm`）
- 实验室成员列表页（如 `www.nakakolab.iis.u-tokyo.ac.jp/member/nakano_e.html`）
- 第三方平台（如 x-mol.com、百度百科、ResearchGate、**ORCID.org**、Google Scholar、aminer.cn）
- 学校/学院首页
- 返回 200 但内容为空或显示"该页面暂未开放"的占位页（如浙大 person.zju.edu.cn 的 577 字节 SPA 壳）

**特别强调**：ORCID（orcid.org）是研究者 ID 注册平台，不是个人主页。即使 ORCID 页面包含研究者的论文列表和简介，也**绝对不能**作为导师主页 URL 使用。ORCID 是学术身份标识系统，不是机构官方个人页面。

**验证标准**：用 WebFetch 或 curl 打开 URL，必须能看到导师的姓名、职称、研究方向等个人信息。如果页面没有导师个人内容，视为无效。

**处理**：找不到合格个人主页 → 不写入 Vika。宁可缺，不可用错误链接凑数。

### 禁止在备注中使用 ✅
✅ 标记是临时验证备注，不是研究事实。⚠️ 仅在页面真的被封锁时用作最后手段。

### 禁止在备注中写入报名/联系方式
不要写 "预计2026年入学"、"需发简历至xxx" 等内容。

### 禁止在备注中写入方向偏向
不要写 "方向偏X"、"没有非常符合的老师" 等主观评价。

### 禁止猜测 URL

**永远不要通过命名规则构造 URL。** 大学网站经常重组，URL 路径会变。必须通过以下方式获取 URL：
1. WebSearch 搜索 `"[Name] [University] professor"` 找个人页面
2. WebSearch 搜索 `"[University] [Department] faculty staff listing"` 找系列表页
3. **WebFetch 逐条验证**——200 状态码不代表内容正确（可能是 SPA 壳或 404 软页面）

**「其他导师信息」字段的特殊规则**：这些是系级教职员列表页 URL。每次会话开始、或用户说"检查链接"时，必须对每个 Department 的列表页 URL 逐一 WebFetch 验证。不要依赖 `references/school-strategies.md` 中记录的 URL——它们可能在你上次访问后已经变了。

**教训（2026-07-07）**：12 个「其他导师信息」链接中 4 个已失效（NUS × 2, NTU × 1, CityU × 1），都是因为大学重组了网站结构。

#### 大规模 404 复盘（2026-07-14）

黄肇启选导任务中，60 条记录的 `博士申请信息` 和 `其他导师信息` 出现大面积 404。复盘发现三个根因：

**根因 1：URL 猜测（占 90%+）**

所有出错的 URL 都是在写表时按路径命名规则直接构造的，没有经过 WebSearch 搜索验证。典型的猜测模式 vs 真实路径：

| 字段 | 猜测的路径 | 真实路径 |
|------|-----------|---------|
| HKU SAAS 博士申请 | `/programmes/research-postgraduate` | `/programme/rpg/mphil-phd` |
| HKU Nursing 博士申请 | `/education/postgraduate/` | `/education/doctor-of-philosophy-programme` |
| CUHK SPHPC 博士申请 | `/programmes/` | `/mphil-phd-programme/` |
| HKUST ECE 博士申请 | `/pg/` | `/admissions/postgraduate` |
| HKUST LifeSci 博士申请 | `/programmes/` | 在 `prog-crs.hkust.edu.hk` 子域名 |
| HKU BS 博士申请 | `/programmes/research-postgraduate/` | `phd.hkubs.hku.hk/admissions/...` |
| PolyU Nursing 博士申请 | `/sn/study/` | `/study/pg/rpg/2026/sn` |
| HKU SAAS 院系列表 | `/staff` | `/staff_teaching.php` |
| HKUST CSE 院系列表 | `/people/faculty/` | `/admin/people/faculty/` |
| HKUST LifeSci 院系列表 | `/people/` | `/faculty-members/` |
| HKUST ECE 院系列表 | `/people/` | 无系级列表页，用 `facultyprofiles.hkust.edu.hk` |
| HKUST Math 院系列表 | `/people/faculty/` | 无系级列表页，用 `facultyprofiles.hkust.edu.hk` |

**核心教训**：博士申请信息页和院系列表页的 URL 结构在各校各系之间**没有统一规律**。`/programmes/`、`/people/`、`/staff`、`/pg/`、`/study/` 这些常见路径在大量真实站点上都是 404。**必须先 WebSearch 搜索到真实页面，再把 URL 写进表里，一步都不能省。**

**根因 2：大学网站持续重组**

CUHK SPHPC 的院系列表页从 `/people/` 迁移到了 `/academic-staff/`，原有 URL 直接 404。这类重组是常态，不是偶发事件。

**根因 3：CityU WAF 干扰诊断**

CityU 全站 Incapsula WAF 会使自动化工具看到的返回码异常（403/404/超时/空壳），容易和真正 404 混淆。必须区分"WAF 拦截"和"真 404"——前者是所有 CityU URL 的系统性问题，后者是 URL 本身失效。

**防范措施（写入前强制执行）**：

对于 `博士申请信息` 和 `其他导师信息` 两个字段，**写入每条记录前**必须：
1. 用 WebSearch 搜索 `"[学校] [院系] PhD research postgraduate admission"` 或 `"[学校] [院系] faculty academic staff"`
2. 打开搜索结果中的真实页面
3. 确认 URL 可访问（非 404、非 SPA 壳）
4. 把验证过的 URL 填入字段
5. **批量写入后，对所有非 CityU 的 URL 逐条 curl/WebFetch 验证**

### CityU（港城）特殊规则：WAF 防护 + 双域名策略

#### WAF 防护（2026-07-13 验证；2026-08-04 修正）

CityU 全站部署了 **Incapsula WAF**，会拦截所有来自自动化工具（curl、Python urllib、WebFetch）的请求。这不是链接失效，而是反爬机制。

| 域名 | 自动化访问现象 | 浏览器访问 |
|------|-------------|-----------|
| `cityu.edu.hk/stfprofile/` | 200 返回 Incapsula JS 挑战页（200-1000 字节） | ✅ 正常 |
| `scholars.cityu.edu.hk` | **403 Forbidden** | ✅ 正常 |

**关键认知**：
- 自动化审计脚本检测 CityU 链接时，**可能全部报死链**（或 SPA 壳），这是一个已知的系统性问题
- **⚠️ 403 ≠ 必然有效（2026-08-04 修正）**：scholars 返回 403 有两种可能——① 正常教授的页面被 WAF 拦截（有效）；② **离任/已离职教授的页面已删除**（WebFetch 穿透 WAF 后显示 "The page does not exist"）。**必须用 WebFetch 穿透验证**，不能一律当作 WAF 正常现象放过
- 链接有效性必须由人在浏览器中逐条确认，或 WebFetch 穿透 WAF 看真实内容
- 不要因为 WAF 拦截就删除有效的 CityU 导师链接，但也**不要因为 403 就假设链接有效**——交叉验证（见下方「离任导师检测」）

**离任导师检测（2026-08-04 沉淀，Maurice Benayoun 案例）**：

判断 CityU 导师是否已离任，三步交叉验证：

1. **WebFetch 穿透 WAF**：`WebFetch("https://scholars.cityu.edu.hk/en/persons/xxx")` — 若返回 "The page does not exist" / "Page not found"，该学者主页已删除，高度怀疑离任
2. **查 CityU 学术人员目录**：`https://www.cityu.edu.hk/zh-hk/directories/people/academic?page=N` — 若标注 **Visiting Professor** / **Adjunct Professor**，通常是离任后保留的挂名身份
3. **查系级现任教职员列表**：如 `https://www.scm.cityu.edu.hk/people` — 若现任教授/副教授/客座/兼任各分组均无此人，基本确认离任

**辅助手段**：WebSearch 搜 `"[导师名] [原校] 教授"` 看是否已转到其他学校（如南京大学官网注明"原香港城市大学创意媒体学院教授（2012年至2024年）"）。已离任导师**不进入主表**，已写入的需删除。

#### 链接格式策略

CityU 有两种导师主页 URL 格式：

1. **stfprofile 格式**（推荐优先使用）：`https://www.cityu.edu.hk/stfprofile/xxx.htm`
   - 部分旧版教授页面使用此格式
   - 自动化访问返回 Incapsula JS 挑战页（约 200-1000 字节）

2. **scholars 格式**：`https://scholars.cityu.edu.hk/en/persons/xxx/`
   - Pure Portal 全校统一入口，信息更完整
   - 自动化访问返回 403；**离任教授此页面会变成真实 404（穿透 WAF 可见）**

**选择策略**：两种格式都可以用，stfprofile 优先级更高（因为至少不返回 403）。scholars 格式写入后必须 WebFetch 穿透验证内容（能显示教授姓名/职称/院系才算有效）。

#### 写入后复验规则

由于 WAF 的存在，"写入后复验"规则做以下调整：

1. 写入 Vika 后，用 WebFetch 或 urllib 快速检查
2. **预期结果**：stfprofile 返回 200 + 约 200-1000 字节（JS 挑战）；scholars 返回 403
3. 以上两种结果**不能直接判定链接有效**——必须 WebFetch 穿透 WAF 确认页面有该导师姓名/职称/院系内容（穿透后显示 "The page does not exist" 即已失效）
4. **删除记录条件**：Google 搜索找不到该导师、系页面已删除、浏览器确认 404、或**官方目录已无此人（离任）**
5. **交付前**：提示用户在浏览器中抽查 CityU 链接（特别是 scholars 格式的）

### 排除退休/名誉教授
不添加 Emeritus、退休、约 70 岁以上、或不在当前教职员目录中的导师。

### 禁止修改已填写选导意向的记录（见上方「操作权限」）

当 Vika 表中 `选导意向（点击选择）` 非空时，该行即被锁定——不得修改、删除或覆盖。详见「操作权限 → 选导意向保护」。

### 禁止向 MagicLookUp 或计算字段写入
QS排名、Location、美国USNEWS排名等字段通过 API 只读。

### 新增记录去重

写入新记录前，检查是否已存在于已有选导意向的记录中。

#### Unicode 规范化去重（2026-08-07 沉淀）

不同来源对名字的拼写可能存在变音符号差异（如 `Jaffre` vs `Jaffré`），简单字符串精确匹配会漏检。**写入前必须使用 Unicode NFKD 规范化去除重音后再比对：**

```python
import unicodedata

def normalize_name(name):
    nfkd = unicodedata.normalize('NFKD', name)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()
```

**去重流程**：
1. 拉取表中所有已有记录，按 `normalize_name()` 分组
2. 对每个新导师，用 `normalize_name()` 查是否已有同名记录
3. 若已有→**跳过**不写入，或先合并信息到已有记录再删除重复（如果已有记录字段空缺）
4. 删除重复时，优先保留**选导意向非空**（已确认）的记录，删除选导意向为空的记录
5. **DELETE 格式**：`DELETE /records?recordIds=recXXX,recYYY`，不带 Content-Type header

### 🏫 学校关联字段必填（强制执行 — CRITICAL）

**每条新导师记录写入后，必须立即设置学校关联字段（OneWayLink），让 Location / QS排名 / 美国USNEWS排名 / 国内学校层次 通过 MagicLookUp 自动同步。**

这是最容易遗漏但影响最大的步骤。学校关联字段决定整行的 Location、QS、USNEWS、国内学校层次等信息，不填等于记录残缺。

#### 第一步：识别新学生 / 老学生（强制执行，不可跳过）

每张选导表的 OneWayLink 字段指向的学校主表不同。必须先从字段定义读取 `foreignDatasheetId` 来判断学生类型：

```python
r = vika('GET', f'/datasheets/{datasheet_id}/fields')

link_fields = []
for f in r['data']['fields']:
    if f['type'] == 'OneWayLink':
        link_fields.append({
            'field_id': f['id'],
            'field_name': f['name'],
            'main_table_id': f['property']['foreignDatasheetId'],
        })
```

**根据 `foreignDatasheetId` 的值自动识别**：

| foreignDatasheetId | 学生类型 | 主表模式 |
|---------------------|----------|----------|
| `dstMNzQU9Aa58DpgW3` | **新学生** | 统一主表（一张表管全球） |
| `dstNvlYbmD2BTMCB0r` | **老学生** | QS 主表（非美国学校） |
| `dstd7iuffLGUbSnavd` | **老学生** | US 主表（美国学校） |

新老学生的后续操作流程不同，下面分别说明。

---

#### 第二步-A：新学生模式（统一主表 `dstMNzQU9Aa58DpgW3`）

约 2200 条记录，统一管理全球所有学校。**只有一个 OneWayLink 字段**（如「学校名字」），链接到同一张主表。

字段结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `学校全称` | Text | 完整英文/中文校名 |
| `学校中文名` | Text | 中文名称 |
| `学校英文缩写` | Text | 如 SYSU、CUC |
| `2026年QS排名` | Number | 2026 QS 综合排名（无排名留空） |
| `2027年QS排名` | Number | 2027 QS 综合排名 |
| `2025年QS排名` | Number | 历史参考 |
| `2025年USNews排名` | Number | 美国学校专用 |
| `国家/地区` | SingleSelect | 含 China (Mainland)、United States 等 |
| `所在大洲` | SingleSelect | Asia、Europe、Americas 等 |
| `国内学校层次` | SingleSelect | 985 / 211 / 双非 / 双一流 / 专业院校 |
| `国内学校所在省份` | SingleSelect | 如广东省、北京市、江苏省 |
| `美国学校所在州` | SingleSelect | 美国学校专用（如 加利福尼亚州） |

**创建学校记录**（新学生）：

```python
# 国内学校示例
data = {'records': [{'fields': {
    '学校全称': '广州大学',
    '学校中文名': '广州大学',
    '学校英文缩写': 'GU',
    '国家/地区': 'China (Mainland)',
    '所在大洲': 'Asia',
    '国内学校层次': '双一流',
    '国内学校所在省份': '广东省',
}}], 'fieldKey': 'name'}
resp = vika('POST', f'/datasheets/{main_table_id}/records', data)
school_rid = resp['data']['records'][0]['recordId']

# 关联
data = {'records': [{
    'recordId': supervisor_rid,
    'fields': {link_field_name: [school_rid]}
}], 'fieldKey': 'name'}
vika('PATCH', f'/datasheets/{datasheet_id}/records', data)
```

SingleSelect 字段直接传字符串值即可，API 自动匹配选项。

---

#### 第二步-B：老学生模式（双主表）

两张独立的学校主表，选导表通常有**两个 OneWayLink 字段**：

| 关联字段 | 链接到 | 适用情况 |
|----------|--------|----------|
| `非美国地区学校` | QS 主表（`dstNvlYbmD2BTMCB0r`，~1651 条） | 非美国学校 |
| `美国地区学校` | US 主表（`dstd7iuffLGUbSnavd`，~439 条） | 美国学校 |

**QS 主表字段**（老学生）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `学校` | Text | 英文校名 |
| `排名` | Number | QS 综合排名 |
| `Location` | SingleSelect | 国家/地区 |
| `地区` | SingleSelect | 大洲 |

**US 主表字段**（老学生）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `学校` | Text | 英文校名 |
| `排名` | Number | US News 排名 |
| `所在州` | SingleSelect | 美国所在州 |

**⚠️ 老学生 US 主表无 Location 字段**：`dstd7iuffLGUbSnavd` 只有 `学校`/`排名`/`所在州`，没有 `Location` 字段。设置 `美国地区学校` 后 MagicLookUp 不会自动填充 Location。

**解决方案**：同时设置 `非美国地区学校` 指向一个已有 Location=United States 的学校（如 MIT、Stanford），用作 Location 来源。此时记录会同时有两个链接。

**创建学校记录**（老学生）：

```python
# QS 主表
data = {'records': [{'fields': {
    '学校': 'Ghent University',
    '排名': 159,
    'Location': 'Belgium',
    '地区': 'Europe',
}}], 'fieldKey': 'name'}
vika('POST', f'/datasheets/dstNvlYbmD2BTMCB0r/records', data)

# US 主表
data = {'records': [{'fields': {
    '学校': 'Harvard University',
    '排名': 3,
    '所在州': '马萨诸塞州',
}}], 'fieldKey': 'name'}
vika('POST', f'/datasheets/dstd7iuffLGUbSnavd/records', data)
```

#### 第三步：在主表中查找学校（⚠️ 多层模糊搜索 → 搜不到就停，禁止自建）

> **教训（2026-07-20）**：主表实际有 2200+ 条学校记录，`pageSize=200` 只返回第一页。
> 不翻页会误判学校不存在 → 创建重复 → 后续维护混乱。
> **必须用 `pageNum` 翻页直到 `len(records) >= total`，确认遍历全部记录后再判断。**

> **教训（2026-07-24）**：精确匹配 `"University of Exeter"` 搜不到主表中的 `"The University of Exeter"`（少了 The）。
> 搜索必须分多层：精确 → 模糊 → 缩写 → 多候选确认 → 搜不到就停。
> **绝对禁止在主表 POST 新建学校。** 搜不到就告诉用户去补，等用户补完再继续。

**搜索策略（四层，逐层兜底）：**

| 层 | 策略 | 适用场景 | 搜到多个怎么办 |
|----|------|----------|---------------|
| L1 | 精确匹配 `学校全称` / `学校中文名` | 已知完整名 | 不会多（精确匹配唯一） |
| L2 | 大小写不敏感子串匹配 `lower(学校全称)` in `lower(target)` OR `lower(target)` in `lower(学校全称)` | The/University 等前缀差异 | **列出所有候选让用户选** |
| L3 | 匹配 `学校英文缩写`（如 UW-Madison、Exeter） | 名称差异较大时 | **列出所有候选让用户选** |
| L4 | 搜不到 | 学校确实不在主表 | **停下来告诉用户，绝不 POST** |

> **美国学校特别注意**：L2 子串匹配可能搜出多个同名分校（如 "University of California" 匹配到 UC Berkeley、UC Davis、UCLA 等）。当候选 > 1 时，必须列出全名 + recordId 让用户确认。

```python
def find_school_by_name(main_table_id, school_name, mode='new'):
    """翻页遍历全部主表记录，分层查找学校。搜不到返回None让用户自己补。"""
    name_field = '学校全称' if mode == 'new' else '学校'
    all_records = []
    page = 1
    while True:
        r = vika('GET', f'/datasheets/{main_table_id}/records?pageSize=500&pageNum={page}&cellFormat=string')
        all_records.extend(r['data']['records'])
        total = r['data']['total']
        if len(r['data']['records']) < 500 or page * 500 >= total:
            break
        page += 1
    
    # L1: 精确匹配
    for rec in all_records:
        if rec['fields'].get(name_field) == school_name:
            return [rec['recordId']]  # 返回单个候选的列表
        if mode == 'new' and rec['fields'].get('学校中文名') == school_name:
            return [rec['recordId']]
    
    # L2: 大小写不敏感子串匹配
    target_lower = school_name.lower()
    candidates = []
    for rec in all_records:
        full = (rec['fields'].get(name_field) or '').lower()
        cn = (rec['fields'].get('学校中文名') or '').lower()
        if target_lower in full or full in target_lower or target_lower in cn or cn in target_lower:
            candidates.append(rec)
    
    if candidates:
        # 去重（可能有中文名和英文名指向同一条）
        seen = set()
        unique = []
        for rec in candidates:
            if rec['recordId'] not in seen:
                seen.add(rec['recordId'])
                unique.append(rec)
        if len(unique) == 1:
            return [unique[0]['recordId']]
        else:
            # 多个候选 → 必须让用户选
            return [(r['recordId'], r['fields'].get(name_field, '?')) for r in unique]
    
    # L3: 英文缩写匹配
    candidates = []
    for rec in all_records:
        abbr = (rec['fields'].get('学校英文缩写') or '').lower()
        if abbr and abbr in target_lower:
            candidates.append(rec)
    if candidates:
        return [(r['recordId'], r['fields'].get(name_field, '?')) for r in candidates]
    
    # L4: 搜不到 → 停下来
    return None  # 告诉用户：学校不在主表，请手动添加后再继续
```

**使用方式**：
```python
result = find_school_by_name(main_table_id, "University of Exeter", mode='new')
if result is None:
    # 搜不到 → 告诉用户，停止操作
    print("学校 'University of Exeter' 不在主表中，请先在主表手动添加。")
elif isinstance(result[0], tuple):
    # 多个候选 → 让用户选
    print(f"搜到 {len(result)} 个匹配：")
    for rid, name in result:
        print(f"  {rid}: {name}")
else:
    # 唯一匹配 → 直接用
    school_rid = result[0]
```

#### 第四步：搜不到学校时 — 停下来，不要自建 🚫

第三步搜不到学校时，**绝对不要在主表 POST 新建**。改为：

1. 把导师记录先写入选导表（不含学校关联）
2. 告诉用户："XX 学校不在主表中，请手动添加"
3. 等用户补完学校后，再设置 OneWayLink

**禁止事项（新增）**：
- 🚫 **绝对禁止**对主表执行 POST/PATCH/DELETE 操作（即使 API token 有权限）
- 🚫 **绝对禁止**用 `vika('POST', f'/datasheets/{main_table_id}/...')` 在任何路径下创建学校
- 🚫 **绝对禁止**在搜不到学校时自己去建——正确做法是停下来告诉用户

#### 第五步：设置导师记录的 OneWayLink

```python
data = {'records': [{
    'recordId': supervisor_rid,
    'fields': {link_field_name: [school_rid]}
}], 'fieldKey': 'name'}
vika('PATCH', f'/datasheets/{datasheet_id}/records', data)
```

#### 第六步：验证

Patch 后重新 GET 记录，确认 `Location`、`QS排名`、`国内学校层次` / `美国USNEWS排名` 等已通过 MagicLookUp 自动填充。

**禁止事项**：
- 禁止假设学生类型（必须从 `foreignDatasheetId` 动态识别新/老学生）
- 禁止新老学生混用字段名（新学生用 `学校全称`/`2026年QS排名`，老学生用 `学校`/`排名`）
- 禁止在不创建主表记录的情况下直接设置 OneWayLink（会导致幽灵链接）
- 禁止在未翻页遍历全部主表记录前就判断"学校不存在"并创建
- 禁止 OneWayLink 值写成字符串而非数组
- 🚫 **禁止对主表执行任何写操作**（POST/PATCH/DELETE）。搜不到学校就告诉用户，不自己建

**常见错误**：
- 不识别学生类型 → 用错字段名 → API 报错或写入无效字段
- OneWayLink 值写成字符串而非数组 → API 报错 → 链接未生效
- 翻页不全就判断学校不存在 → 创建重复记录 → 主表数据混乱

### 国内学校搜索（不使用 Google）
国内（中国大陆）学校的导师搜索**不使用 Google**，改用百度搜索：
- `[导师名] [学校名] 教授`
- `[导师名] [学校名] 博士导师`
- 辅助来源：百度学者、百度百科、知网、万方

所有国内学校导师必须遵守 `references/selection-rules.md` 中的「国内学校选导规则」。

---

## 飞行前检查清单（添加导师前强制执行）

```
[ ] 1. 搜索引擎搜索: "[Name] [University] professor"
[ ] 2. 打开个人页面: 确认姓名、职称、院系
[ ] 3. 检查研究: 阅读 Research Interests 部分
[ ] 4. 检查活跃状态: 非 Emeritus/Retired/Visiting
[ ] 5. 匹配方向: 研究关键词与学生方向对比
[ ] 6. 个人 URL: 验证是个人页面而非通用列表页
[ ] 6a. 主页类型检查: 非第三方平台/医生预约页/CRM聚合页/SPA空壳 → 否则直接跳过
[ ] 6b. 硬排除检查: 研究主线非线虫/果蝇/酵母模式生物、非纯计算(>70% dry lab)、非癌症生物学为主线 → 否则直接跳过，不入表
[ ] 6c. 方向核心度: 该方向是实验室主攻方向（非"研究方向之一"），在导师主页/论文中出现频率 >50%
[ ] 7. 写入记录: 所有检查通过后再写入
[ ] 8. 获取学校主表 ID: GET /datasheets/{id}/fields → 找 OneWayLink 字段的 property.foreignDatasheetId
[ ] 9. 设置学校关联: 写入后立即设置 OneWayLink → 验证 Location/QS/国内学校层次 已同步
[ ] 10. 批次审核触发: 累计每写完 10 条新记录 → 立即暂停搜索，spawn supervisor-auditor 做对抗审核
```

---

## 常见错误速查表

| 错误 | 示例 | 正确做法 |
|------|------|---------|
| 猜测 URL | 拼 `/programmes/research-postgraduate`、`/people/faculty/`、`/pg/` 等 | WebSearch 搜索真实页面 URL |
| 批量写入「博士申请信息」时未逐个验证 | 42 条新记录全空，填表时按命名规则拼写 | 每条 URL 写入前必须 WebSearch → 打开验证 → 再填入 |
| 依赖上次会话的院系列表 URL | CUHK SPHPC `/people/` 已变更为 `/academic-staff/` | 每次会话重新 WebFetch 验证 |
| SPA 壳当有效 | 200 响应但无内容（HKUST Math `~macyang` 86B） | 交叉验证姓名和内容，换替代 URL |
| CityU WAF 404 当真实 404 | CityU MKT/EF 系页面返回 404（WAF 拦截） | 浏览器人工确认，区分 WAF 和真 404 |
| 老学生主表有 100 条硬限制（旧表） | 旧 QS/US 主表写入 >100 条时静默丢弃 | 不重新验证 GET；主表只增不删 |
| CDU/CDU 等小型大学研究人员页 404 | RD3 确认有效后 RD4 再查变 404 | 交付前逐条复验所有链接，不信任上一轮验证结果 |
| 备注中 SPA 标注和匹配标识混在同一段 | `Macquarie为SPA系统需浏览器验证；可以备选一下呢～` | SPA 标注放在第二段末尾，第三段仅放匹配标识 |
| CUHK(SZ) teacher ID 跨会话失效 | 上次存的 `/teacher/254` 已变 `/node/59`、`/teacher/273`→`/teacher/472` | 每次会话重新 WebSearch 搜新 ID，不信任历史 URL |
| HKUST(GZ) SPA 全站 1522B 壳 | 新旧 URL 格式均返回相同字节数，自动化无法判定有效性 | 标记 SPA，提示浏览器确认；同步搜索 DSA 博客替代来源 |
| Python SSL 失败当 404 | `sds.cuhk.edu.cn` Python urllib 报 handshake failure | 换 WebFetch 验证，不直接判死 |
| Vika URL 字段 PATCH 静默失败 | `fieldKey="name"` 返回 200 但 URL 未更新 | 必须 `fieldKey="id"` + 字段 ID |
| PATCH 后回读键名错误 | GET 返回字段名键，用 field ID 读永远 None | PATCH 前后各拉字段列表，回读用字段名 |
| CityU scholars 403 一律当有效（2026-08-04） | Maurice Benayoun 案例：scholars 403 是 WAF 壳，穿透后实为 "The page does not exist"（导师已离任） | 403 必须 WebFetch 穿透看真实内容；交叉验证 CityU 学术目录（Visiting/Adjunct 标注）+ 系级教职员列表；已离任导师删除记录 |
| 并发 curl 共享临时文件 | 多个线程写同一 /tmp 文件，title 互相污染（状态码仍可靠） | 每个 URL 用独立临时文件；对 title 异常/200 无 title 的页面用 WebFetch 单独确认 |
| 备注用「学生」称呼申请者 | `明确接受PhD学生` 违反第二人称规则 | 改为 `明确接受PhD申请`，所有备注以「你」称呼申请者 |
| **curl 200 当链接有效（美国学校 404 伪装页）** | OSU `medicine.osu.edu/find-faculty/...` 返回 200 但内容显示 "Not Found" | **必须 WebFetch 读内容**，状态码 200 ≠ 页面真实存在 |
| **院系列表页当个人主页** | 全院教师列表页只有姓名+职称，无 CV/Publications | 个人主页必须含专属研究内容；列表页不可接受 |
| **第三方平台当个人主页** | DovePress 编辑简介、ORCID、ResearchGate | 禁止用第三方平台代替大学官方个人主页 |
| **Stipend 系统性低估** | USF 写 `$30K/yr` 实际 `$37K`；TAMU Medical Sciences 写 `$32K` 实际 `$35K` | 每条记录写入前搜索学校官网 stipend 页面核实 |
| **K08 误认为 R01** | "NIH K08→R01(2017-2022)" 中 R01 查无实据 | NIH Reporter 交叉验证 grant 类型、金额、时间线 |
| **中心总计与个人 funding 混淆** | "CRM总计>$20M" 被误认为导师个人 funding | 明确区分"中心总计"与"个人独立 grant" |
| **推测性数据未标注** | "录取率~15-20%""2028年预计" 作为事实陈述 | 标注为"估算""约"，说明无官方来源 |
| **选导顾问自审自填（确认偏误）** | 优录-刘同学案例：同一会话反复复查"没问题"，换新对话框 auditor 查出 7 条 P0 | 批次审核必须 spawn 独立 auditor，不复用选导顾问上下文 |
| **长对话疲劳放过** | 几十轮后对"看起来还行"的记录直接放行，`__trashed` 发现了但 WebFetch 能打开就判有效 | 同一会话处理 30+ 条后开新会话；auditor 有罪推定，主动找理由拒绝 |
| **方向定义书转述失真** | 选导顾问把"干细胞+心血管"转述成"干细胞"，auditor 信了转述，iPSC 副业当核心 | auditor 必须亲自读方向定义书原文，不信任任何人的摘要 |
| **硬排除项漏检** | 线虫模型/纯生信/癌症主线一路漏到最终审核才发现，删除 7 条 = 11% 工作量浪费 | 飞行前清单 6b 硬排除检查是写入前硬门，不是写入后审计项 |

---

## 链接修复工作流（用户说"链接打不开/404"时触发）

当用户反馈已有表格中某学校/学院的导师链接大面积失效时，按以下步骤系统修复：

### 步骤 0：批量拉取全部 URL（2026-08-04 沉淀）

不要只修用户点名的那几条，先全量审计：

1. GET 全部记录，提取三个 URL 字段（`导师主页` / `博士申请信息` / `其他导师信息`）去重
2. 批量 curl 检查状态码 + 字节数 + title（用**独立临时文件**，不要并发共享同一文件——共享文件会污染 title 读取，但状态码仍可靠）
3. 按学校分组整理结果，区分：真 404 / SPA 壳 / WAF 拦截 / 疑似正常
4. 对存疑的（200 但无 title、403、SPA 壳、标题异常）逐一 WebFetch 穿透验证内容

### 步骤 1：诊断区分失效类型

用 curl/WebFetch 逐一检查每个链接的状态，区分三类情况：

| 类型 | 症状 | 说明 |
|------|------|------|
| 真 404 | HTTP 404 + 页面标题含"404" | URL 确实失效，需搜索新链接 |
| SPA 壳 | 200 + 所有 URL 返回相同字节数 + 无实际教授信息 | 站点是 JavaScript 渲染，自动化无法判断 |
| WAF/SSL 拦 | 403 / SSL 握手失败 / 超时 | 防护机制干扰，需换工具验证（**注意：403 也可能是离任教授页面已删除，必须 WebFetch 穿透看真实内容，见 CityU 章节**） |

### 步骤 2：按学校搜索新 URL

不要逐个导师搜，先搜学校的教师目录页找全员新链接格式，再针对性补充搜索：

```python
# 批量搜索语法示例
for name in broken_professors:
    WebSearch(f'"{name}" sds.cuhk.edu.cn teacher OR node')
```

**CUHK(SZ) 搜索技巧**：
- 搜 `"[导师名] sds.cuhk.edu.cn teacher"` 找标准 teacher 页
- 搜 `"[导师名] cuhk.edu.cn"` 发现跨子域名迁移（myweb/gklbdc/sse/mscfe）
- 搜 `"[导师名] sds.cuhk.edu.cn node"` 发现 node 格式页面

**HKUST(GZ) 搜索技巧**：
- 搜 `"dsa.hkust-gz.edu.cn [导师名] faculty blog"` 找 WordPress 格式替代页
- `facultyprofiles.hkust-gz.edu.cn` 是纯 SPA，自动化只能确认 200，无法确认内容
- 若 DSA 博客有个人页则优先使用（可自动化验证内容）

**各校 2026 年改版经验（2026-08-04 沉淀）**：

| 学校 | 变化 | 新旧格式 |
|------|------|---------|
| PolyU Scholars Hub | slug 全面变更，旧 slug 404 | 旧 `persons/christina-wong-wing-yan` → 新 `persons/christina-wong`；`chloe-ki`→`chung-wha-ki`；`magnum-lam`→`man-lok-lam-2`；`minjung-cho`→`min-jung-cho`；`haze-ng`→UUID 格式 `c4fd5adc-...`。**规律：搜 `"[导师名] polyu scholars hub"` 或从 `polyu.edu.hk/sft/people/academic-staff` 列表页抓个人页链接** |
| HKUST HUMA | 路径重组 | 博士申请 `programmes/research-postgraduate` → `teaching/pg/phd`；院系列表 `people` → `about/faculty` |
| HKU Art History | 加 index.php 前缀 | `people/xxx` → `index.php/people/xxx` |
| HKUBS | 人名用英文全名 slug | `people/wan-wen/` → `people/echo-wen-wan/`（万雯的英文名是 Echo Wen Wan） |
| CUHK | 系页面下线后迁移研究门户 | `arch.cuhk.edu.hk/en/people/faculty-members/xxx` → `research.cuhk.edu.hk/en/persons/xxx` |

### 步骤 3：写入前逐条 WebFetch 验证

每个候选 URL 必须用 WebFetch 打开，验证能显示：
- ✅ 导师姓名、职称
- ✅ 研究方向
- ✅ 院系归属

出现以下任一情况即判定无效：
- ❌ 404 / 页面未找到
- ❌ 只有导航栏/空壳（SPA）
- ❌ 显示的是其他不相关人员

### 步骤 4：Vika PATCH 修复

```python
# URL 字段 PATCH 必须 fieldKey="id"
fields = vika("GET", "/fields")
homepage_fid = next(f["id"] for f in fields["data"]["fields"] if '导师主页' in f['name'])

updates = [{"recordId": rid, "fields": {homepage_fid: new_url}} for rid, new_url in fixes.items()]

for i in range(0, len(updates), 10):
    vika("PATCH", "/records", {"records": updates[i:i+10], "fieldKey": "id"})
```

### 步骤 5：PATCH 后回读验证

```python
# 回读时必须用字段名（不是 field ID）
verified = vika("GET", f"/records?recordIds={','.join(fixed_ids)}")
for r in verified['data']['records']:
    # ✅ 正确：用字段名读取
    url = r['fields'].get('导师主页', '')
    # ❌ 错误：用 field ID 读取 → 永远 None
    # url = r['fields'].get(homepage_fid, '')
```
| CUHK(SZ) teacher ID 跨会话失效 | 上次存的 `/teacher/254` 已变 `/node/59`、`/teacher/273` 变 `/teacher/472` | 每次会话重新 WebSearch 搜索新 ID，不信任旧 ID |
| HKUST(GZ) SPA 全站 1522B 壳 | 新旧 URL 格式均返回相同字节数，自动化无法判定有效性 | 标记为 SPA，提示用户浏览器确认；同步搜索 DSA 博客替代来源 |
| Python SSL 失败当链接失效 | `sds.cuhk.edu.cn` Python urllib 报 handshake failure | 换 WebFetch 验证，不直接判 404 |
| Vika URL 字段 PATCH 静默失败 | `fieldKey="name"` 写入 URL 字段返回 200 但未更新 | 必须用 `fieldKey="id"` + 字段 ID（非字段名） |
| PATCH 后回读用错键名 | GET 返回字段名键，但用 field ID 去读永远 None | PATCH 前后各拉一次字段列表，回读用当前字段名 |
| 精确匹配搜不到学校就自建 | 搜 "University of Exeter" 搜不到 "The University of Exeter" → 在主表 POST 创建重复 | 必须用 L1→L2→L3 分层搜索，L2 用不区分大小写子串匹配；搜不到就告诉用户，绝不自建 |
| 对主表执行写入操作 | POST 到主表新建学校、或 PATCH 修改主表记录 | 🚫 主表是只读参考数据源，任何写操作都是禁止的 |

---

## 小批次强制审核（搜索阶段强制执行）

**不要等所有学校搜完再统一审核。每写完 10 条新记录，必须立即 spawn supervisor-auditor 做对抗审核。**

### 审核触发条件

| 场景 | 操作 |
|------|------|
| 写完 10 条新记录 | 立即停，spawn supervisor-auditor（独立 spawn，见下方「独立审核原则」） |
| 搜完一个学校的全部导师 | 即使不足 10 条，也 spawn auditor |
| auditor 返回 P0 | 修正后再继续搜索，不积压 |
| 选导顾问同一会话已处理 30+ 条 | 建议用户为新批次开新会话（长对话疲劳防范） |

### 修正后二次验证

收到 auditor 的 P0 清单后：
1. 对 P0 记录立即修正（换链接/改备注/删除）
2. 修正后重新 spawn auditor 验证同一批
3. 确认 PASS 后再进入下一轮搜索

### 独立审核原则（CRITICAL — 防止确认偏误和长对话疲劳）

**复盘教训（2026-08-10 优录-刘同学案例）**：同一个选导顾问在长对话中反复复查自己的产出，始终认为"没问题"；换一个新对话框让 auditor 独立审核，立即查出 7 条 P0。根因是：自己审自己填的东西，天然查不出"该不该留"的问题；长对话几十轮后对同一批记录产生"看过了"的疲劳性放过。

**因此，批次审核必须遵守以下原则：**

| 原则 | 要求 | 为什么 |
|------|------|--------|
| **独立 spawn** | 每次批次审核必须 spawn 一个**全新的** supervisor-auditor agent，不能复用选导顾问的上下文 | 选导顾问在填表过程中已经形成了"这些导师都合适"的先入为主，带着这个心态审核等于不审 |
| **新鲜视角** | auditor 拿到的只有：学生方向定义书原文 + 本批 10 条记录数据，没有选导顾问的判断过程和理由 | 让 auditor 独立判断"这条该不该留"，而不是"选导顾问的判断对不对" |
| **方向定义书独立验证** | auditor 必须亲自阅读学生方向定义书的**原文**，不能只看选导顾问转述的摘要 | 选导顾问在转述时可能无意识地缩小了方向范围（如把"干细胞+心血管"转述成"干细胞"），导致方向核心度判断失准 |
| **审核心态：有罪推定** | auditor 的立场是"每条记录默认有 P0，除非能证明它没有"。不是"默认没问题，除非发现问题" | 确认偏误让人倾向于"找到理由就放行"；有罪推定强制 auditor 主动找理由拒绝 |
| **长对话疲劳防范** | 若选导顾问在同一会话中已处理 30+ 条记录，必须建议用户为新批次开一个新会话 | 30 轮后注意力下降，对"看起来还行"的记录容易直接放过——优录-刘同学案例正是如此 |

### auditor 指令模板（升级版）

每次 spawn supervisor-auditor 时，传递以下指令：

```
你是一名选导审计官。你的立场是"有罪推定"——每条记录默认有 P0，除非你能证明它没有。

你将收到：
1. 学生方向定义书原文（你自己读，不信任任何人的转述）
2. 本批 X 条新记录数据

审核规则（逐条检查，一项不通过即标记 P0）：

A. 链接类型检查：
   - 导师主页必须是大学官方页面（.edu 或学校官方子域）
   - 排除：第三方平台（Loop/DovePress/ResearchGate/ORCID）、医生预约页、CRM聚合页、院系列表页、SPA空壳
   - 你要主动找理由判定不合格，而不是找理由放行

B. 方向核心度检查（必须独立读方向定义书）：
   - 你自己阅读学生方向定义书原文，不信任选导顾问的摘要
   - 该导师的研究方向是实验室主攻方向，还是只是"研究方向之一"？
   - 硬排除：线虫/果蝇/酵母模式生物？纯计算(>70% dry lab)？癌症生物学为主线？
   - 如果方向定义书写明了排除项，你必须逐条对照

C. URL 健康检查：
   - URL 不含 __trashed、_legacy、_old
   - 非 302 跳转到搜索页/列表页
   - WebFetch 能读取到导师姓名+职称+研究方向（非 WAF 挑战页）

D. 排除规则执行审计：
   - 选导顾问是否执行了飞行前清单的 6b（硬排除检查）和 6c（方向核心度）？
   - 如果备注里出现"可以备选一下"但方向明显不核心 → P0（选导顾问在偷懒放行）

输出格式：
- 逐条输出检查结果（A/B/C/D 各项 PASS 或 FAIL + 原因）
- 汇总：P0 清单（记录编号 + 原因 + 修正建议）
- 无 P0 则输出 "PASS — 本批 X 条记录全部通过强制验证清单"
```

---

## 写入后审计（强制执行）

每次批量写入 Vika 后，运行审计脚本：

```bash
python3 scripts/audit.py [DATASHEET_ID] [VIKA_TOKEN]
```

审计检查：
1. 交叉链接（URL 域名与 Department 不匹配）
2. 备注格式（缺少；分隔符、缺少句号）
3. 备注中是否有垃圾内容
4. 缺少必填字段（导师主页、博士申请信息、其他导师信息）
5. **国内学校**：检查 `导师联系方式` 是否为空，是否为有效 email 格式

## 链接健康审计（用户报"链接404/badcase"时，2026-08-04 新增）

先全量审计再针对性修复，不要只修用户点名的几条：

```bash
python3 scripts/link-audit.py [DATASHEET_ID] [VIKA_TOKEN]
```

脚本输出：每个 URL 状态码/字节数/title（独立临时文件避免并发污染）→ 按类型汇总 →
待 WebFetch 穿透验证的存疑项清单（403 / 200 无 title / 疑似 WAF 壳）。

**关键判断规则**：
- `403`（尤其 CityU scholars）：**不能当作 WAF 正常现象直接放过**，必须 WebFetch 穿透看真实内容——
  正常教授页面穿透后可见姓名/职称；离任教授穿透后显示 "The page does not exist" → 删除记录
- `200 + 小字节无 title`：疑似 WAF JS 挑战壳，WebFetch 确认内容
- 修复流程：搜索替代 URL → 逐条 WebFetch 验证 → `fieldKey="id"` PATCH → 回读验证
- 各校 2026 年 URL 改版格式见「链接修复工作流 → 步骤 2」表格

---

## 协作流程（"开始学生" / "结束学生"）

当用户说**"开始学生"**（或"提交更新"、"同步并提交"等）时，自动执行 pull -> branch -> commit -> push -> PR 全流程。当用户说**"结束学生"**时，先提取本轮搜索经验更新策略库，再自动执行同步流程。

**完整执行步骤见 `references/collaboration-workflow.md`。** 触发后按该文档的 11 步流程执行，无需用户懂 git。

---

## 参考文献

- 决定候选人能否进入主表前，阅读 `references/selection-rules.md`
  - **国内学校**：重点阅读文档末尾的「国内学校选导规则」（招生目录优先、A/B/C 分类、邮箱必填）
- 创建/编辑/验证表格前，阅读 `references/spreadsheet-rules.md`
  - **国内学校**：重点阅读文档末尾的「国内学校表格规则」（导师联系方式列、主页来源、备注链接格式）
- 开始搜索前，阅读 `references/search-orchestrator.md`
- 访问学校前，检查 `references/school-strategies.md`
- SPA/API 发现技巧，见 `references/search-techniques.md`
- Vika 完整 CRUD 操作 + API 代码模板，见 `references/vika-guide.md`
- 协作流程（开始学生/结束学生），见 `references/collaboration-workflow.md`
