# Search Techniques for PhD Supervisor Discovery

Practical techniques for discovering supervisor profiles, bypassing website limitations, and scaling verification efficiently.

## SPA Workaround — Alternative Academic Identity Sources (L0)

When a university's staff profile portal is a pure SPA that returns empty HTML shells (<5KB, status 200), do NOT waste time trying to crack it. Instead, find the scholar's academic footprint on alternative platforms.

### The Alternative Source Strategy

Scholars maintain academic identities on multiple platforms — most are server-rendered:

| Source | Reliability | Access Method | What You Get | Real Examples |
|--------|-------------|---------------|-------------|---------------|
| Personal academic website | **High** | WebFetch | Research areas, CV, projects, PhD students, teaching | tamaleaver.net, wishcrys.com |
| Research center/lab page | **High** | WebFetch | Role, funded projects, collaborators, research themes | digitalchild.org.au/team-members/, ierlab.com/about/ |
| ResearchGate | **Med-High** | WebFetch | All publications, research areas, stats, co-authors | researchgate.net/profile/Michele-Willson |
| ORCID | **Medium** | WebFetch | Structured profile, affiliations, limited pubs | orcid.org/0000-0002-3703-3020 |
| Google Scholar (snippet) | **Medium** | WebSearch | Citation count, research field tags | "Cited by 2,517 - Internet Studies - Disability Studies" |

### Discovery Workflow

```
For each professor at an SPA school:
1. WebSearch "[Name] [University] professor research"
2. Scan results — ignore staffportal URLs, look for:
   → Personal domain (.net, .com)
   → Research center (.org.au, .edu.au but NOT staffportal)
   → ResearchGate (researchgate.net)
   → ORCID (orcid.org)
3. WebFetch 2-3 alternative sources
4. Cross-reference: 2+ sources confirming same research = verified
5. Combine: research areas (personal site) + publications (ResearchGate) + citations (Scholar)
```

### Known SPA Schools & Their Alternative Sources

| School | SPA Portal | Working Alternatives |
|--------|-----------|---------------------|
| **Curtin University** | staffportal.curtin.edu.au (React SPA, ~2KB shell) | tamaleaver.net, wishcrys.com, digitalchild.org.au, researchgate.net |
| **Victoria University of Wellington** | people.wgtn.ac.nz (Angular SPA, 4150B shell) | researchgate.net, ORCID, Google Scholar snippets |
| **University of Auckland** | profiles.auckland.ac.nz (SPA shell) | researchgate.net, ORCID, Google Scholar snippets |
| **BNBU-UIC** | staff.uic.edu.cn (SPA, but sometimes loads in browser) | Google Scholar, ORCID |

### When L0-SPA is the RIGHT choice

- Staff portal returns <5KB (confirmed SPA shell)
- No discoverable API endpoint in JS bundle
- Tavily extract also returns empty (server-side fetch still gets JS shell)
- BUT: scholar is well-known enough to have a personal website or ResearchGate presence

### When to escalate instead

- Scholar has NO alternative online presence (very junior, no personal site, no ResearchGate)
- Scholar's only verified presence is on the SPA portal → escalate to L3 (browser verification) or L4 (Tavily)
- Need hyper-specific data only on the staff portal (office hours, phone number, grant amounts)

## SPA / JavaScript-Rendered Sites

Many university faculty profile systems are single-page applications (SPA) that return empty HTML shells to curl. Do not give up at a 200 status with no content.

### Find the API Endpoint

1. Download the SPA's main JavaScript bundle (e.g., `app.{hash}.js` or `chunk-vendors.{hash}.js`).
2. Search the bundle for API path patterns:
   ```bash
   curl -sL "$SPA_URL/js/app.*.js" | tr ',' '\n' | grep -i 'api\|baseurl\|faculty\|profile\|page'
   ```
3. Look for patterns like `/api/.../page`, `/api/.../list`, `/api/.../primary/{id}`.
4. Once found, test with curl. Common parameters: `pageNum`, `pageSize`, `facultyType`, `excludeJobTypes`, `dataSourcesCodes`.

### Call the API for Complete Data

Always try to fetch the full dataset in one call:
```
/api/.../page?size=100000&pages=1&facultyType=GZ&languageType=en
```
This avoids pagination and gives you all faculty records to filter locally. Total counts (e.g., `"total": 439`) confirm you got everything.

### Extract Structured Fields

Key fields to extract from each record:
- `enName`, `name` (Chinese name), `email`
- `jobs[]`: `jobEnName` (title), `departmentEnName` (thrust/department), `parentEnName` (hub/school)
- `website` (personal/lab site), `permaLink` (institutional repository)
- `degreeEnName`, `schoolName`, `majorEnName` (educational background)
- `rsidentifier[]`: Google Scholar, ORCID, ResearcherID, ScopusID
- `lastName`, `firstName` (needed for URL construction)

### Filter by Target Department

After getting all records, filter locally:
```python
for item in lists:
    for job in item.get('jobs', []):
        if job.get('departmentEnName') == 'Thrust of Urban Governance and Design':
            # This person is in the target department
```

## URL Pattern Inference

### Hash Routes vs Direct Paths

SPA frameworks (Vue, React) often have two routing systems:
- **Hash routes**: `/#/faculty-personal-page/{name}/{email}` — often don't render standalone content
- **Direct paths**: `/faculty-personal-page/{name}/{email}` — often the "real" page that renders fully

When hash routes fail, check the JS bundle for route definitions:
```bash
grep -oE '(path:\s*"[^"]*personal[^"]*"|name:\s*"[^"]*personal[^"]*")' app.js
```

### Constructing Personal Profile URLs

Once the URL pattern is understood, construct it from API data:

```
https://{host}/faculty-personal-page/{LASTNAME}-{FIRSTNAME}/{email_username}
```

Where:
- `LASTNAME` = UPPERCASE from API's `lastName` field
- `FIRSTNAME` = as-is from API's `firstName` field (may contain spaces for multi-word names)
- `email_username` = part before `@` in email

Always verify constructed URLs by opening them in the browser. Do not assume the pattern works for all; test at least one, then batch-verify all.

## Parallel Sub-Agent Strategy

When checking multiple independent targets (different schools, domains, or systems), launch parallel sub-agents to run checks concurrently.

> **Tool note**: The exact sub-agent launch command varies by coding agent. In WorkBuddy, use the `Agent` tool with `subagent_type="Explore"`. In Codex, use `spawn_agent`. In other agents, use the equivalent parallel/sub-agent feature.

### When to Parallelize

- Checking different schools simultaneously (e.g., CUHKSZ + UIC + UNNC)
- Verifying multiple candidate profile pages when they are on different domains
- Searching for PhD program pages across different university subdomains

### Sub-Agent Task Design

Give each sub-agent a clear, self-contained task:
- Specific URLs to check with curl
- What to look for (program names, faculty lists, research keywords)
- What format to report back in

Example:
```
Check CUHKSZ for urban planning faculty:
1. curl https://hss.cuhk.edu.cn/en - check for faculty listing
2. curl https://sse.cuhk.edu.cn/en - check for related programs
3. Search for keywords: urban, planning, geography, transportation
4. Report: which URLs work, any faculty found, their profile URLs
```

### Coordination

- Spawn all sub-agents in one batch for maximum parallelism
- Continue your own work (browser verification, API queries) while they run
- Collect results and integrate into the spreadsheet

## Browser Automation for Verification

Use browser automation to verify page content that curl cannot access (JS-rendered content, hidden tabs, etc.).

> **Tool note**: The exact browser tool varies by coding agent. In WorkBuddy, use the `Agent` tool to fetch and verify URLs, or use an available browser skill. In other agents, use the equivalent browser automation feature. If no browser tool is available, use WebFetch as a fallback and note any limitations.

### Verifying Personal Pages

For each candidate URL, use a browser tool or WebFetch to:
1. Navigate to the profile URL
2. Wait for the page to fully render (if using browser automation)
3. Extract the page text content
4. Verify the page contains the person's name, title, and department

If using browser automation, the steps are:
- Go to the URL and wait for network idle
- Extract `document.body.innerText`
- Check for the person's name and research keywords

If browser automation is unavailable, use WebFetch and note any JS-rendered content that could not be verified.

### Accessing Hidden Content (Tabs/Accordions)

Many profile pages hide research interests behind clickable tabs. If using browser automation:
1. Locate the tab (e.g., "RESEARCH INTEREST", "Publications")
2. Click to reveal hidden content
3. Extract the now-visible text

If using WebFetch only, check whether the content appears in the static HTML. If not, note: "研究兴趣可能在JS标签页中，需浏览器验证."

### Batch Verification Pattern

Verify multiple candidate pages sequentially:
- For each candidate, fetch the page content
- Extract name, title, department, research interests
- If JS-rendered content is missing, note it
- Record findings in the table's 备注 field

## Deep Discovery: Full-to-Filter-to-Verify Pipeline

Don't stop at the first batch of results. Systematically expand:

1. **Full sweep**: Get ALL faculty from the target department via API
2. **Filter**: For each person not yet in the spreadsheet, check degree, major, and research keywords for relevance
3. **Prioritize**: Rank by match to student's directions. Look at PhD institution, research keywords, and department fit
4. **Verify**: Open personal pages for top candidates, click research interest tabs
5. **Expand**: Look at adjacent departments that may have relevant faculty (e.g., Intelligent Transportation, Innovation/Policy/Entrepreneurship)

### Cross-Department Expansion

When the primary department has been exhausted:
- Check if the university has related thrusts/departments in adjacent fields
- Same API call covers ALL departments — just change the filter
- Example: Urban Governance → also check Intelligent Transportation, Innovation Policy & Entrepreneurship, Data Science

## Handling Unreachable Subdomains

Some university subdomains may be unreachable from the sandbox (DNS issues, geo-blocking, firewalls):
- Document the URLs that were tried and failed
- If a sub-agent discovers content via curl but the browser can't reach it, record the findings in the `排除或待确认` sheet with a ⚠️ note
- Suggest the user verify the unreachable URLs from their own browser
- Do NOT add candidates to the main table if their profile pages cannot be verified

## PhD Program Page Discovery

When the department's own website is unreachable, look for the graduate school's program catalog:
1. Visit `fytgs.{university}.edu.cn` or `gs.{university}.edu.cn` (graduate school)
2. Look for "Postgraduate Programs" or "Program Catalog"
3. Search for the target program name
4. The graduate school page is often on the main university domain and more accessible

Construct program URLs following the pattern:
```
https://fytgs.{university}.edu.cn/programs/{program-slug}
```

Where `program-slug` uses hyphens and lowercase (e.g., `urban-governance-and-design`).

## Search Engine Fallback (Degraded Mode)

When APIs and direct URL access both fail:
- Use DuckDuckGo/Google with site-specific queries: `site:{university}.edu {name} {department}`
- Search for the person's Google Scholar, ORCID, or ResearchGate profile as secondary evidence
- Always verify found URLs by opening them; never use search result snippets as evidence


### DDG HTML Search (CRITICAL - when Bing/Google are blocked)

When Bing and Google return encrypted URLs or block curl/browser, use DuckDuckGo's HTML-only search:

**URL**: https://html.duckduckgo.com/html/?q=ENCODED+QUERY

This returns plain HTML with unencrypted result URLs that can be parsed with regex. Essential for discovering:
- Slug patterns unknown to the search agent (e.g. cssamk vs sam-kwong, wang-hao-victor vs wang-hao)
- Official staff profile pages on non-standard paths (e.g. cityu.edu.hk/stfprofile/cssamk.htm)
- SPA-blocked school profile URLs that only appear in search results

**DDG result link format**: //duckduckgo.com/l/?uddg=URL_ENCODED_TARGET - decode with urllib.parse.unquote()

**Last verified**: 2026-06-30

## Tavily Search-Pro Integration (L4 Fallback)

When ALL L1-L3 methods fail — WAF blocks curl, browser, and search engines; DDG returns empty; Google encrypts URLs — use tavily-search-pro as a server-side proxy to bypass client-side anti-crawl protections.

**Prerequisites**: `TAVILY_API_KEY` environment variable must be set. See tavily-search-pro skill for installation.

### Extract — Bypass WAF to Read Blocked Pages

When WebFetch/curl return 403 (Cloudflare, Incapsula, etc.) for a professor's profile page, use Tavily extract to pull content via server-side fetch:

```bash
TAVILY_API_KEY="$TAVILY_API_KEY" "$HOME/.workbuddy/binaries/python/envs/default/bin/python3" "$HOME/.workbuddy/skills/tavily-search-pro/lib/tavily_search.py" extract "https://scholars.cityu.edu.hk/en/persons/dani-madrid-morales" --format markdown
```

**When to use**:
- WebFetch returns 403/Cloudflare challenge page
- curl gets Incapsula WAF response
- Browser also blocked by anti-bot
- You already know the URL but can't read its content

**Extract with query reranking** — when extracting a long page, use `--query` to pull only the relevant sections:
```bash
... extract "https://blocked-site.edu/profile/john-smith" --query "research interests PhD supervision"
```

### Search — Alternative Search Engine When Google/DDG Fail

When DDG HTML search returns empty or Google encrypts URLs, use Tavily search for clean, unencrypted results:

```bash
TAVILY_API_KEY="$TAVILY_API_KEY" "$HOME/.workbuddy/binaries/python/envs/default/bin/python3" "$HOME/.workbuddy/skills/tavily-search-pro/lib/tavily_search.py" search "John Smith NUS professor psychology" --include-domains nus.edu.sg
```

**Advantages over DDG/Google**:
- Returns unencrypted, directly usable URLs
- Can filter by domain (`--include-domains`) for site-specific search
- Can include LLM-synthesized answers (`--answer`) for quick relevance assessment
- Works even when search engines block automated queries

**News/Finance modes** — for finding recent faculty announcements:
```bash
... news "NUS new psychology professor 2026" --time month
... finance "university faculty hiring trends" --time year
```

### Crawl — Discover Faculty Pages on a Blocked Site

When you can't access a department's faculty listing page directly, use Tavily crawl to discover all professor profile URLs:

```bash
TAVILY_API_KEY="$TAVILY_API_KEY" "$HOME/.workbuddy/binaries/python/envs/default/bin/python3" "$HOME/.workbuddy/skills/tavily-search-pro/lib/tavily_search.py" crawl "https://www.cityu.edu.hk/com/" --instructions "Find all faculty and professor profile pages" --limit 20
```

**When to use**:
- Department staff page is blocked by WAF
- Need to discover profile URL patterns (slugs, UUIDs) for a school
- Want to find all staff-related pages on a domain

### Map — Sitemap Discovery for URL Pattern Mining

When you need to understand a university site's structure to find faculty page patterns:

```bash
TAVILY_API_KEY="$TAVILY_API_KEY" "$HOME/.workbuddy/binaries/python/envs/default/bin/python3" "$HOME/.workbuddy/skills/tavily-search-pro/lib/tavily_search.py" map "https://www.otago.ac.nz/" --max-depth 2 --limit 100
```

**When to use**:
- Need to discover all staff-related URL paths on a domain
- Want to find `/staff/`, `/people/`, `/faculty/` patterns
- URL pattern mining before individual searches

### Research — Deep Department Analysis

For comprehensive research on a specific department's PhD supervision landscape:

```bash
TAVILY_API_KEY="$TAVILY_API_KEY" "$HOME/.workbuddy/binaries/python/envs/default/bin/python3" "$HOME/.workbuddy/skills/tavily-search-pro/lib/tavily_search.py" research "PhD supervisors in consumer psychology at NUS Business School" --model pro
```

**When to use**:
- Initial scan of a department's research landscape
- Finding supervisors whose profiles are scattered across multiple subdomains
- Comprehensive overview before targeted individual searches

### L4 Escalation Protocol

**Rule**: Only use L4 after L3 has been **confirmed** to fail. L4 consumes Tavily credits (1-2 per call, research costs more), so reserve it for genuine blockers.

**Escalation flow**:
1. Try L1 (curl) → fails with 403/WAF
2. Try L2 (API mining) → no API found or JS bundle inaccessible
3. Try L3 (DDG/Google search) → empty results or encrypted URLs
4. **Escalate to L4** → use appropriate Tavily mode

**Cost-aware usage**:
| Mode | Credits | When appropriate |
|------|---------|-----------------|
| extract | 1-2 per URL | Known URL but content blocked |
| search | 1-2 | Need to find URLs via search |
| crawl | 1-2 per page | Discovering site structure |
| map | 1 | URL pattern mining |
| research | varies | Deep department analysis (use sparingly) |

**After L4 success**: Record the strategy in `school-strategies.md` with `Layer: L4` so future sessions skip L1-L3 and go directly to Tavily for that school.

## Common HTTP Error Patterns and Tavily Solutions

Real-world examples from link verification batches. Each pattern has a specific L4 solution.

### Pattern 1: SPA Empty Shell (e.g., Curtin University staffportal)

**Problem**: The staff profile portal is a React/Vue SPA. `curl`, WebFetch, and even Tavily extract all return ~2KB of JS shell with zero extractable content. Status is 200, but there's no HTML content to parse.

**L1 result**: 200 OK, ~2KB empty shell
**Browser result**: Works fine (browser renders the SPA)
**Tavily extract**: Also returns empty shell (server-side fetch still gets JS, not rendered content)
**Solution**: L0-SPA — skip the staff portal entirely. Use alternative academic identity sources:
1. WebSearch `"[Name] Curtin University professor research"`
2. Find personal websites (tamaleaver.net, wishcrys.com), ResearchGate, research center pages
3. WebFetch alternative sources for full content
4. Cross-reference: 2+ independent sources confirmed = verified

**Rule of thumb**: 200 status + <5KB response on a known profile URL = SPA shell. Do NOT keep trying the same URL — switch to L0-SPA immediately. The content exists but it's client-side rendered.

### Pattern 2: 406 Not Acceptable on HEAD Requests (e.g., VUW, UoA)

**Problem**: Some servers reject HEAD requests but accept GET. `curl -I` returns 406, but `curl -sL` or browser GET works fine.

**L1 result**: 406 on HEAD, 200 on GET
**Tavily solution**: Not needed — just switch from HEAD to GET. But if GET also returns blocked content (SPA shell), use Tavily extract:

```bash
... extract "https://www.vuw.ac.nz/staff/jane-doe" --format markdown
```

**Rule of thumb**: 406 on HEAD ≠ broken URL. Always retry with GET before escalating. Only escalate to L4 if GET also fails or returns empty content.

### Pattern 3: SSL Certificate Errors on .edu.cn Sites (e.g., BNBU-UIC)

**Problem**: Some Chinese .edu.cn sites use SSL certificates that Python's certificate bundle doesn't recognize. `curl` and `python requests` throw SSL errors, but browsers (which have broader CA trust stores) work fine.

**L1 result**: SSL: CERTIFICATE_VERIFY_FAILED
**Browser result**: Works fine (broader CA trust)
**Tavily solution**: `extract` mode — Tavily's server infrastructure handles SSL negotiation independently from local Python, bypassing the certificate issue entirely:

```bash
... extract "https://faculty.uic.edu.cn/en/profile/zhang-san" --format markdown
```

**Rule of thumb**: SSL errors on .edu.cn sites are a Python/curl limitation, not a broken URL. Tavily extract completely sidesteps the problem by fetching from its own servers. This is the most reliable L4 use case for Chinese university sites.

### Pattern 4: 500 Internal Server Error on Old URLs (e.g., Jonathan Zhu at CityU)

**Problem**: A professor's old profile URL returns 500. The page may have moved to a new system (e.g., CityU Scholars portal) but the old URL wasn't properly redirected.

**L1 result**: 500 Internal Server Error
**L3 result**: Search `"Jonathan Zhu CityU professor"` → find new URL on scholars.cityu.edu.hk
**Tavily solution**: `search` mode — find the current working URL when the old one is dead:

```bash
... search "Jonathan Zhu CityU professor" --include-domains cityu.edu.hk,scholars.cityu.edu.hk
```

Then `extract` the new URL to verify content:

```bash
... extract "https://scholars.cityu.edu.hk/en/persons/jonathan-zhu" --format markdown
```

**Rule of thumb**: 500 on an old URL → don't mark as broken immediately. Search for the current URL. Tavily search+extract combo is the fastest way to find and verify the replacement.

### Quick Reference: Error → L4 Mode Mapping

| Error | Meaning | Solution | Notes |
|-------|---------|----------|-------|
| **SPA shell (200 + <5KB)** | JS-rendered portal, no content in response | **L0-SPA**: find alt sources (personal site, ResearchGate) | Do NOT retry same URL — client-side render, impossible to extract server-side |
| **403** | WAF blocked (Cloudflare/Incapsula) | extract | Most common L4 use case |
| **429** | Rate limited | extract | URL is valid, Tavily uses different rate pool |
| **406** | HEAD rejected | extract (only if GET also fails) | First retry with GET |
| **500** | Server error on old URL | search → extract | Find replacement URL first |
| **SSL error** | Python cert issue (.edu.cn) | extract | Tavily bypasses local cert validation |
| **Timeout/DNS** | Network unreachable | search | Can't extract if site is genuinely offline |

