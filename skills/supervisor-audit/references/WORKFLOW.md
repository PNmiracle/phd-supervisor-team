# 1+1 工作流：执行 + 自查优化

每个学生 chat 的标准处理流程。一轮执行任务 + 一轮对抗审计修复，保证交付质量。

## 流程总览

```
┌─ Step 0: claim ──────────────────────────┐
│  领取任务，锁定 Bitable 行，获取上下文      │
│  python3 run_1plus1.py claim "学生名"       │
└───────────────┬───────────────────────────┘
                │ 输出: prompt, vika_url, attachments
┌───────────────▼───────────────────────────┐
│  Step 1: process (Agent 执行)              │
│  调用 phd-supervisor-selector skill        │
│  解析提示词 → 搜索导师 → 写入 Vika 表       │
│  新建导师 / 删除不匹配 / 补充方向信息        │
└───────────────┬───────────────────────────┘
                │
┌───────────────▼───────────────────────────┐
│  Step 2: audit (对抗自查)                  │
│  python3 run_1plus1.py audit "学生名"       │
│  → 自动执行 audit_state.py 全维度检查      │
│  → 4 维度: 链接有效性 / 国内邮箱 / AI痕迹  │
│    / 选导意向保护                           │
└───────────────┬───────────────────────────┘
                │ 输出: passes / weak_dim / dead_links / missing_emails / ai_artefacts
┌───────────────▼───────────────────────────┐
│  Step 3: fix (针对性修复)                  │
│  根据 audit 返回的问题逐项修复：            │
│  - dead_links → 搜索替代链接或删除          │
│  - missing_cn_emails → 补充邮箱             │
│  - ai_artefact → 清除 emoji/机械短语        │
│  - 未通过 → 修复后再次 audit 验证            │
└───────────────┬───────────────────────────┘
                │
┌───────────────▼───────────────────────────┐
│  Step 4: complete (交付)                   │
│  python3 run_1plus1.py done "学生名"       │
│    --passed true --feedback "..."          │
│  → audit 全部通过 → 阶段=已完成              │
│  → 仍有问题 → 阶段=人工待审批 + 失败原因      │
└───────────────────────────────────────────┘
```

## Step 0: claim

```bash
python3 run_1plus1.py claim "学生名"
```

返回 JSON：
```json
{
  "ok": true,
  "record_id": "recXXX",
  "student": "学生名",
  "prompt": "...",
  "vika_url": "https://vika.cn/share/...",
  "attachments": [{...}],
  "stage": "AI 处理中",
  "locked_by": "chat-学生名"
}
```

若 `ok=false`，根据 `message` 判断：
- 「任务正被 XXX 处理中」→ 等待或提醒用户
- 「任务已完成」→ 汇报交付结果
- 「任务处于人工待审批」→ 展示失败原因

## Step 1: process (Agent 执行)

Agent 使用 claim 返回的 `vika_url` 和 `prompt`，完整调用 `phd-supervisor-selector` skill：

1. 解析提示词中的学生方向、目标地区/学校、排除条件
2. 按 skill 的搜索编排搜索各校导师
3. 对每位导师：验证主页、检查 PhD 资格、匹配方向
4. 写入 Vika 表（新增/删除/修改备注）
5. 遵守全部 skill 规则：选导意向保护、SPA 检测、备注三段式、emoji 清理等

**关键指标**：此步骤完成后，Vika 表应有完整的导师列表和符合格式要求的备注。

## Step 2: audit (对抗自查)

```bash
python3 run_1plus1.py audit "学生名"
```

内部执行 `audit_state.py`，检查 6 个维度：

| 维度 | 检查内容 | 阈值 |
|------|---------|------|
| **必填字段完整性** | `导师`、`学校名字`、`Department`、`导师主页`、`备注` 必填；国内学校 `导师联系方式` 必填；若表含 `导师研究领域`/`博士申请信息`/`其他导师信息` 则不应为空 | 0 条缺失 |
| **匹配置信度** | 记录是否有方向匹配证据：`导师研究领域` 非空、或 `备注` 含方向描述（非仅有职称）、或 `博士申请信息` 非空 | ≥ 95% |
| 链接有效性 | `导师主页` HTTP 请求 200 + >5KB | ≥ 95% |
| 国内邮箱 | 国内学校 `导师联系方式` 含 email | 100% |
| AI 痕迹 | 备注无 emoji/⚠/机械短语 | 0 条 |
| 选导意向 | `选导意向` 字段为空 | 0 条已填 |

**置信度通过条件**：链接准确率 ≥ 95% **且** 匹配置信度 ≥ 95% — 两个条件同时满足，`置信度` 才能设为 `通过`，才能进入 `已完成` 阶段接人工待审核。

返回 JSON：
```json
{
  "passes": false,
  "weak_dim": "match_confidence",
  "metrics": {
    "total_records": 56,
    "missing_field_records": 0,
    "total_missing_fields": 0,
    "match_matched": 52,
    "match_unmatched": 4,
    "links_alive": 54,
    "links_dead": 2,
    "cn_email_filled": 20,
    "cn_records_total": 20,
    "ai_artefact_count": 0,
    "selection_intent_filled": 0
  },
  "details": {
    "missing_fields": [],
    "unmatched_records": ["recXXX: 张三", "..."],
    "dead_links": ["https://..."],
    "missing_cn_emails": [],
    "ai_artefact_records": [],
    "filled_intent_records": []
  }
}
```

**置信度判定规则**：必须同时满足 `链接准确率 >= 95%` 和 `匹配置信度 >= 95%`，才能 `--passed true`，否则即使其他维度通过也必须 `--passed false` 返工。

若 `passes=true`，直接跳到 Step 4 complete。

## Step 3: fix (针对性修复)

根据 audit 返回的 `details` 逐项处理：

**missing_fields**（必填字段缺失）——**返工给 Step 1 选导助手**：
- 这是 process 阶段漏填或没填完整的字段，不能由 audit 环节直接修补
- 把缺失字段清单（记录 ID + 字段名）回传给选导助手
- 选导助手重新搜索/验证对应导师，补充 `Department`、`导师研究领域`、`导师联系方式`（国内）、`博士申请信息`、`其他导师信息`、`备注` 等字段
- 补充完成后，再次运行 `python3 run_1plus1.py audit "学生名"` 验证

**unmatched_records**（匹配置信度不足）——**返工给 Step 1 选导助手**：
- 这些记录的 `导师研究领域`、`备注` 方向描述、或 `博士申请信息` 全部缺失
- 选导助手需重新搜索这些导师的研究方向，填充 `导师研究领域` 或补充 `备注` 中的方向描述
- 若确实无法匹配（导师方向完全不相关），可在备注中标注原因并考虑删除
- 补充/处理后再次运行 audit 验证匹配置信度是否恢复到 95% 以上

**dead_links**：对每个死链：
- 用 WebSearch 重新搜索导师姓名 + 学校
- 找到新的有效链接 → 更新 Vika 表
- 找不到 → 考虑删除该导师记录（或标记原因）

**missing_cn_emails**：对每个缺邮箱的国内导师：
- 搜索导师主页或学校教职员页面，找邮箱
- 找不到 → 在备注中标注「未找到邮箱」

**ai_artefact_records**：对每条 AI 痕迹：
- 移除 emoji 和 ⚠ 符号
- 改写机械短语为拟人化表达
- 用 `unicodedata` 验证

修复完成后，再次运行 `python3 run_1plus1.py audit "学生名"` 验证。最多修复 2 次。如果 2 次后仍因 `missing_fields`/`match_confidence`/`links` 未通过，再进入 Step 4 `--passed false` 人工待审批。

## Step 4: complete (交付)

```bash
# 仅当链接准确率 >= 95% 且 匹配置信度 >= 95% 时才能 --passed true
python3 run_1plus1.py done "学生名" --passed true --feedback "链接准确率 97% + 匹配置信度 96%，达标"
```

- `--passed true`：阶段=已完成，置信度=通过。**必须同时满足链接准确率 >= 95% 且 匹配置信度 >= 95%**
- `--passed false`：阶段=人工待审批，需附带 `--reason "链接准确率 93% 未达标"` 或 `--reason "匹配置信度 89% 未达标"`
- `--feedback`：追加到 AI 反馈列的日志

## 异常处理

若任何一步出现不可恢复的错误（API 限流、网络超时等）：
```bash
python3 run_1plus1.py fail "学生名" --reason "Vika API 429 too many requests"
```
任务会进入 `错误次数` 递增，达到 3 次后进入人工待审批。
