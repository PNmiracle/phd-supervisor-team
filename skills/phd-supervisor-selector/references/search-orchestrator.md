# Search Orchestrator

Session-aware search coordination with state tracking, smart prioritization, and standardized sub-agent dispatch. Read this before starting ANY search task.

## 1. Check for Existing State (FIRST STEP)

Before searching any school, check for a state file:

```bash
# Path: {SKILL_DIR}/search-state/{student_name}.md
# {SKILL_DIR} = the directory containing this skill's SKILL.md file.
# For most agents: ~/.workbuddy/skills/phd-supervisor-selector/
cat "{SKILL_DIR}/search-state/{student_name}.md" 2>/dev/null
```

If the file exists, resume from the recorded state. If not, create one and track progress as you go.

### State File Format

```markdown
# Search State: {student_name}
Updated: {ISO timestamp}

## School Status

| School | Status | Strategy Used | Candidates Found | Notes |
|--------|--------|---------------|------------------|-------|
| UAL - Chelsea | completed | API + browser | 3 | Pure portal, API worked |
| RCA | completed | curl + browser | 5 | Staff page direct parse |
| University of Leeds | in_progress | search engine | 2 | Curl blocked, using fallback |
| University of Edinburgh | pending | - | - | - |
| Kingston University | blocked | - | 0 | Staff page 404, DNS issues |

## Known 404 URLs (do not re-check)
- https://www.kingston.ac.uk/staff/profiles/design/
- https://www.southampton.ac.uk/art/research/staff.page

## Successful Strategies (also update school-strategies.md)
> After discovering a working strategy for a school, record it BOTH here AND in `references/school-strategies.md` for long-term reuse across different students.

> 💡 **Before trying access methods from scratch, check `references/school-strategies.md` first.** It records which access layer (L1/L2/L3) and architecture each school uses. L1 = direct curl, L2 = API mining, L3 = search engine fallback. The layer tells you the path; the keywords depend on the student's discipline. It records which architecture each school uses (Pure Portal, Vue SPA, Static HTML, etc.) and which access method worked. If the school is in the registry, use the recorded strategy. If not, record your findings after the search.

- Pure portal API: https://pure.ual.ac.uk/portal/en/persons/?format=json
- Vue SPA faculty list: pattern found in app.js → /api/faculty/page
- Simple HTML parse: worktribe.com staff profiles

## Last Search Context
- Target directions: {user's research directions}
- QS range: {min}-{max}
- Regions: {UK, Australia, ...}
- Hard exclusions: {list}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not yet searched |
| `in_progress` | Currently searching |
| `completed` | Fully searched, results added to table |
| `completed_dry` | Fully searched, no matching candidates found |
| `blocked` | All access methods failed, documented in 排除表 |
| `skipped` | Not in scope (wrong region, no relevant dept, etc.) |

## 2. Smart School Prioritization (BEFORE searching)

Before diving into individual schools, spend 2 minutes sorting the target school list by expected yield:

### Priority Tiers

分层逻辑是**目标院系的规模和匹配概率**，不是学校排名。同一个学校对不同学生可能在不同层。

| Tier | Criteria | How to identify |
|------|----------|----------------|
| **P0 — Gold Mines** | 目标院系大（30+ 教师）、研究方向与学生高度重叠 | 院系有独立博士项目 + 多位教师做学生方向 |
| **P1 — Likely Hits** | 目标院系中等规模（10-30 教师），有部分匹配教师 | 院系存在且有博士项目，部分教师方向相关 |
| **P2 — Possible** | 院系存在但规模小或方向交叉为主 | 仅 2-5 位教师与学生方向沾边 |
| **P3 — Long Shots** | 无独立目标院系，需跨院系寻找 | 学生方向需要创造性匹配（如工业工程→机械工程自动化方向） |

### Prioritization Heuristics

1. **Department size matters**: A school with a 50-person target faculty is worth 10x more effort than one with 3 loosely related staff.
2. **Advisor experience bias**: If the student's previous successful matches came from a certain type of school (e.g., UK research-intensive, AU Group of Eight), prioritize similar schools.
3. **Cache advantage**: Schools with known working strategies (from state file) go first — they'll be fastest.
4. **User urgency**: If user says "先搜英国", don't start with Australia.

### Action

Before searching, output a quick priority matrix:

```
Search Priority (预计 20 所):
P0: 目标院系最大的 4-5 所 — 先攻
P1: 院系中等、部分匹配的 5-6 所 — 第二波
P2: 院系小或方向交叉的 5-6 所 — 第三波
P3: 需跨院系寻找的 — 最后扫尾
```

Then search P0 first, report results, advance to P1.

## 3. Phased Search Strategy (Token-Efficient)

Do NOT deep-search every school in one go. Use a two-pass approach:

### Pass 1: Quick Scan (all P0+P1 schools, ~30 min)
- Light touch: check if relevant department EXISTS
- Use: curl, API, or browser — whichever is fastest
- Output: binary yes/no per school
- Skip: schools with no relevant department

### Pass 2: Deep Verify (only schools that passed Pass 1)
- For each school with a relevant department: full discovery pipeline
- Use: API → filter → verify personal pages → fill table
- Parallelize: 3-5 schools at a time via sub-agents

This prevents wasting 20 minutes deep-searching a school that turns out to have no relevant department.

## 4. Standardized Sub-Agent Dispatch

When spawning sub-agents, use this template:

```
Task: Search {school_name} for PhD supervisors in {direction}

School: {full_school_name}
Target Department: {department_name(s)}
Student Directions: {list of directions with keywords}
Hard Exclusions: {list}

Steps:
1. Navigate to {school_url} — locate the staff/faculty directory for {department}
2. If directory found: extract all relevant staff names, titles, profile URLs
3. For each potential match: open profile page, check:
   - Research interests match student directions?
   - Evidence of PhD supervision?
   - Not excluded by title (teaching-only, emeritus, etc.)
4. Report back in this format:

FOUND:
- Name | Title | Profile URL | Research Keywords | PhD Supervision Evidence | Match Notes

NOT FOUND / BLOCKED:
- Reason (no department, all blocked, no matches, etc.)

Report back ONLY the structured list above. Do not narrate your process.
```

### Parallel Coordination

- Spawn ALL sub-agents for a tier at once
- Do your own verification work while they run
- Collect results, deduplicate, and fill the table
- Mark school status in the state file immediately


### Verification Gate (before writing ANY record)

For each candidate found, before filling the spreadsheet:

```
1. Take the name → Google "{name}" "{university}" professor
2. Click the search result → verify the page contains the person's name + research info
3. Use the verified URL for 导师主页
4. If search fails or page is blocked → mark ⚠️, include the search query
```

**Never construct URLs from patterns.** Even if you found the person via a staff directory, verify their individual profile URL via search engine. URL formats change; search engines always have the live URL.

## 5. State Update Protocol

After completing each school, update the state file immediately:

```bash
# After searching University of Leeds:
# Update status: completed, candidates: 3, strategy: curl + browser
```

If the search is interrupted, the state file IS the resume point. Next session reads it and continues where you left off.

## 6. Incremental Update (Future Sessions)

When the same student comes back for a "refresh" search:

1. Read the state file — all previously `completed` schools are already done
2. ONLY search `pending` or `blocked` schools
3. For `completed` schools, only re-check if:
   - More than 3 months since last search
   - User explicitly requests re-check
   - Known site migration or new academic year signal
4. For `blocked` schools: try ONE new approach (different domain, search engine), then leave blocked if still fails



## 8. Post-Search Learning Loop (CRITICAL)

After completing EACH school, before moving to the next:

```
1. Update school-strategies.md ← what architecture? what method worked? what failed?
2. Update state file ← mark school status, candidate count
3. (If new strategy discovered) Note it in "Successful Strategies" section above
```

This 30-second step compounds: every search makes every future search faster.

### State persistence

- **Per school**: update the state file and `school-strategies.md` immediately after completing the school
- **End of session**: ensure all state files are saved. (Optional: if the skill directory is a git repo, commit changes. Do not auto-commit without user confirmation.)

## 7. Optimization Principles

- **Check school-strategies.md first**: Before accessing a school, look it up in the registry. Known architecture → known approach → no wasted attempts.
- **Cache aggressively**: Store working API endpoints, URL patterns, department names
- **Fail fast**: If 3 attempts to access a school fail, mark `blocked` and move on. Come back at the end.
- **Batch writes**: Fill the spreadsheet in batches of 5-10, not one by one
- **Report progress**: After each P-tier completion, tell user: "P0 done: found 12 candidates across 4 schools. Starting P1."
- **Token budget awareness**: Each school deep-search costs ~5000-15000 tokens. Prioritization ensures tokens go to high-yield schools first.
