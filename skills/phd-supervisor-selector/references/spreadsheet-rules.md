# Supervisor Spreadsheet Rules

## Column Format Selection

### Decision Tree

When starting work, decide the column structure:

1. **User provided a template `.xlsx`?** → Use the template's exact column headers. Never rename or restructure them.
2. **No template, list includes US schools?** → Use simplified format WITH `美国USNEWS排名` column.
3. **No template, list is entirely non-US?** → Use simplified format WITHOUT `美国USNEWS排名` column.

### Main Columns (Simplified Format, Default)

- `导师`: supervisor name as shown on the profile.
- `Location`: country/region, e.g. `Hong Kong`, `Australia`, `United Kingdom`.
- `学校名字`: official English school name unless the user asks for Chinese.
- `QS排名`: current QS rank; use `QS 2026约XX` or `QS 2026待复核` if not verified.
- `美国USNEWS排名`: **only include this column when at least one US school is in the list.** Omit entirely for all-non-US lists.
- `Department`: department/school/center that owns the profile.
- `导师主页`: official profile page, team page, or official staff entry that visibly matches the person.
- `导师联系方式`: supervisor contact email. **Mandatory for domestic (China mainland) schools.** Fill with the supervisor's email address. For non-domestic schools, fill when available but not required.
- `博士申请信息`: official PhD/research degree/program application page.
- `其他导师信息`: same department/school staff list or official supervisor list.
- `备注`: short Chinese note based on profile content.
- `待确认导师`: quality gate column. AI sets to `新加待check` when creating new records; cleared manually after human review. Records with `新加待check` are invisible to students.

### Main Columns (Template Format)

When the user provides a template (typically `博士选导出选模版.xlsx`), match its headers exactly. The standard template has:

- `美国学校`: US school name — fill ONLY for US schools.
- `非美国学校`: Non-US school name — fill ONLY for non-US schools.
- `QS排名`: fill for all schools.
- `美国学校的Usnews排名`: fill ONLY for US schools; leave empty for non-US schools.

**Row-level rules for template format:**
- Each row belongs to exactly ONE school type (US or non-US).
- For US schools: fill `美国学校` + `QS排名` + `美国学校的Usnews排名`. Leave `非美国学校` empty.
- For non-US schools: fill `非美国学校` + `QS排名`. Leave `美国学校` and `美国学校的Usnews排名` empty.
- Both school types coexist in the same sheet; one column pair is empty per row.

### Column Detection on Existing Workbooks

When opening an existing workbook:
- Read the header row to detect which format is in use.
- Match by column header name, not by position.
- Do not assume the simplified format if a template format is detected.

### ⚠️ Column Offset Detection (序号列陷阱)

When the Excel has an `序号` column in the header but the data rows have no actual sequence numbers (the column is empty in the body), all subsequent data shifts left by one position. **This is a common error when importing from sheets that have header-only ordinal columns.**

**Detection steps:**
1. Parse the header row and note column positions
2. Read the first 3-5 data rows
3. Check if the `序号` column has values in the data rows
4. If `序号` is empty in all data rows → data is offset: column N in data maps to column N+1 in header

**Example:**
```
Header: [优先级, 序号, 学校, 学院/系, 导师姓名, 职称, 研究方向, ...]
Data:   [P0,     空,   NUS,  商学院,    Xiuping Li, 副教授, Consumer..., ...]
                     ↑ 实际是"学校"列的数据，不是"序号"
```

**Correction mapping:**
```python
# Offset detected: skip col 2 (序号), map data col 2 → header col 3 (学校)
# data_idx 0 → header col 1 (优先级)
# data_idx 1 → header col 3 (学校, skip 序号)
# data_idx 2 → header col 4 (学院/系)
# data_idx 3 → header col 5 (导师姓名)
# etc.
```

After confirming the offset pattern, apply it to ALL rows. Print a warning to the user about the detected offset.

## Homepage Link Rules

The supervisor homepage link must be openable and must visibly correspond to the supervisor. Never invent, infer, or keep a profile URL just because it follows a plausible pattern.

Accept:

- Official profile page with name and title.
- Official team page listing the person with title/email/team identity.
- Official staff list page only if individual profile pages do not exist and the page clearly lists the person.

Reject or move to `待确认`:

- 404 pages, security pages, search result pages, dynamic shells with no visible name, stale guessed URLs.
- A link that opens but does not mention the target person.
- A general school homepage pretending to be a supervisor homepage.

If the first profile URL is 404, blocked, stale, or mismatched, search Google/Bing with `supervisor name + university + department/profile`. Use the found URL only after opening it and confirming the page content matches the person. If no confirmed page is found, do not fill the row as a main-table supervisor.

For dynamic pages, use the browser if needed. Confirm visible name, title, department, research interests, or email.

If a profile has no public email but has a contact button, message form, or official page that can send a message, the profile can still be used. Note the contact route only when relevant.

## Remarks

Write `备注` from profile content, not generic claims. Use short Chinese phrases:

`职称；研究关键词（可带主页原文出处）；匹配度标识`

The first part should usually be title or eligibility status; the second part should be concrete research evidence (optionally with original quotes from the supervisor's homepage); the third part should be one of the three match identifiers. Keep it concise enough to read in a spreadsheet cell.

Allowed examples:

- `副教授；可持续供应链、产业协作、循环经济；比较匹配～`
- `教授；文物材料、科技考古、保护研究；可以备选一下～`
- `研究助理教授；遗产研究、澳门史、离散社群；需确认带博；可以备选一下～`
- `讲师；空间叙事、城市遗产、视觉文化；英国体系下可考虑；比较匹配～`
- `教授；环境风险、政策评估、气候金融；"research focuses on climate finance and policy evaluation"；建议多看看呢～`
- `Reader；胃肠癌政策评估、健康经济学；有监督经验但名额需确认；比较匹配～`

Avoid:

- `主页写明`, `公开资料`, `方向集中在`.
- `方向一优先`, `方向二备选`, `方向三优先`.
- Long explanations, copied profile blurbs, or unexplained English phrases when Chinese notes are requested.

Use careful risk labels instead of hard rejection language when the student may still want to inspect the person:

- `需确认带博`: promising profile but supervision eligibility is not explicit.
- `教学岗风险`: teaching/instruction/practice title or page focus.
- `研究岗风险`: research-only or fellow/postdoc profile without admission evidence.
- `更新偏旧`: no recent publications/projects/updates for roughly 3+ years.
- `方向相关但不完全贴合`: adjacent topic worth student review.
- `无合适导师`: school-level note when the school was searched but no usable person was found.

### 当学校匹配导师极少时（1-2位）

当某个学校符合学生方向的导师极少（仅1-2位）时，在备注末尾补充说明该系其他教师的主要方向，让学生有"已全面搜索"的信心。

正确写法：
- `教授；决策神经科学、风险与社会决策；该系教师主要研究临床/辅导实践方向，仅有一位与消费者决策相关。`
- `副教授；消费者判断与决策；该系以社会认知与神经犯罪学为主，仅此一位与消费者行为相关。`

要点：
1. 客观描述："该系教师主要研究XX方向"——陈述事实，不做评判
2. 给出数量："仅有一位与目标方向相关"——让学生知道已全面查看
3. 禁止主观：不要写"没有合适的"、"确实没有"、"不匹配"等评价性语言
4. **补充信息行只需填 `导师` 和 `备注`**：另起一行单独写入系/院的补充说明时，只填写导师名（如"XX大学XX系补充说明"）和备注内容，无需填写导师主页、博士申请信息、其他导师信息等字段。

这个补充说明可以放在备注末尾，用分号与前面的内容分隔。

## Extra Sheets

Add these sheets for researched lists:

- `说明与颜色图例`: color meaning, link rules, and note rules.
- `排除或待确认`: people/schools excluded or needing manual confirmation, with reason.
- `学校初筛` or region-specific screening sheet when scanning all schools in a region.

Highlight search batches or newly added rounds with distinct pale row fills. The legend must explain the fill colors.

## Quality Checks

Before final delivery:

1. Verify all main-table supervisor homepage links match the person, not just status code.
2. Verify PhD application and staff/supervisor list links are official and non-empty.
3. Search the workbook for banned note phrases.
4. Scan for formula errors if the workbook contains formulas.
5. **For mixed US/non-US lists**: verify no row has both `美国学校` and `非美国学校` filled. Verify US News ranking is only filled for US schools.
6. Render every worksheet or key range and visually check column widths, wrapping, row colors, and clipped text.
7. Keep existing user files unchanged; save a new workbook unless the user explicitly asks to overwrite.

## Common Edge Cases

- If one university has a supervisor PDF plus separate profile pages, use the PDF/list as eligibility evidence and the profile as `导师主页`.
- If a profile has no email but has a contact button or message link, note that the homepage can send messages.
- If a candidate has several research links, choose the one closest to the student's topic for `导师主页` and keep broader lab/department links in `其他导师信息`.
- If a school has no suitable candidate, do not invent one; add a school-level note explaining the mismatch.
- If a profile has several links, inspect the most topic-specific link first. For example, a lab/project page may show stronger fit than the general staff page, while the staff page may be better for identity verification.
- If a person appears relevant but outside the student's keywords, use a neutral note that invites review, such as `方向相关，可让学生判断兴趣`.
- If a candidate is likely unsuitable only because of title or supervision uncertainty, keep them out of the main table unless the user asked for borderline options.
- **When filling a template with mixed US/non-US schools**: sort rows so US schools are grouped together, non-US schools grouped together. This makes the empty cells less visually jarring.
- **When all schools are non-US in a template**: the `美国学校` and `美国学校的Usnews排名` columns remain in the header but all rows have them empty. This is correct behavior.

## 国内学校表格规则 (Domestic China School Column Rules)

国内（中国大陆）学校的导师记录在填写表格时，需额外遵守以下规则：

### 导师联系方式（必填）

`导师联系方式` 列为国内学校导师必填项。必须填入导师的 email 地址。

获取优先顺序：
1. 导师个人主页（标题栏/联系信息/页面底部）
2. 院系师资列表页
3. 百度学者、ResearchGate、学术论文通讯作者邮箱等其他来源

若通过非主页来源获取邮箱，须在备注中标注来源（如"邮箱来自百度学者"）。

### 导师主页（国内来源要求）

`导师主页` 必须使用 `.edu.cn` 域名的官方导师个人页面 URL。

若主页信息过少（仅有姓名+职称，无方向/论文/项目），：
- URL 仍填入 `导师主页` 列
- 备注中补充百度学者、百度百科、外部文章等链接

### 备注补充链接格式

备注中补充的外部链接需使用完整 URL，放在备注末尾，用分号与前文分隔：

```
教授；自然语言处理、知识图谱；百度学者 https://xueshu.baidu.com/...；可往NLP方向靠。
```
