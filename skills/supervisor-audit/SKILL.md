---
name: supervisor-audit
description: Automated audit scripts for the PhD supervisor selection workflow. Runs multi-dimensional quality checks (field completeness, match confidence, link validity, email compliance, AI artefacts) against Vika supervisor tables and integrates with Feishu Bitable task management for 1+1 workflow processing.
---

# Supervisor Audit（选导审计工具）

## 概述

选导审计工具为博士选导工作流提供自动化质量检查。对接 Vika 导师数据表和飞书多维表格任务管理，实现完整的 1+1 工作流（执行 + 对抗审计修复）。

## 核心脚本

| 脚本 | 用途 |
|------|------|
| `audit_state.py` | 核心审计引擎，6 维度检查（必填字段、匹配置信度、链接有效性、国内邮箱、AI 痕迹、选导意向保护） |
| `run_1plus1.py` | 1+1 工作流调度器（claim → audit → fix → done） |
| `state_machine.py` | 飞书 Bitable 任务状态管理（领取、完成、失败、过期锁释放） |
| `feishu_client.py` | 飞书 API 客户端 |
| `feishu_config.py` | 飞书配置和环境变量管理 |

## 审计维度

| 维度 | 阈值 | 说明 |
|------|------|------|
| 必填字段完整性 | 0 条缺失 | `导师`、`学校名字`、`Department`、`导师主页`、`备注`；国内学校额外检查 `导师联系方式` |
| 匹配置信度 | ≥ 95% | 记录是否有方向匹配证据（`导师研究领域` 非空 / `备注` 含方向描述 / `博士申请信息` 非空） |
| 链接有效性 | ≥ 95% | HTTP 200 + 内容 >5KB（非 SPA 壳） |
| **链接类型合规** | **100%** | **导师主页必须是大学官方页面，排除第三方平台/医生预约页/CRM聚合页** |
| **方向核心度** | **100%** | **关键词必须是核心方向，不能只是"研究方向之一"；硬排除项（线虫/dry lab/癌症主线）必须拦截** |
| **URL 健康** | **100%** | **无 `__trashed`、非 302 跳转、非 SPA 空壳** |
| 国内邮箱 | 100% | 国内学校 `导师联系方式` 含有效 email |
| AI 痕迹 | 0 条 | 备注无 emoji/⚠/机械短语 |
| 选导意向保护 | 0 条已填 | `选导意向` 为空 |

## 强制验证清单（对抗审核时不可跳过）

审计每条记录时，必须按以下顺序逐项检查。任一检查项不通过即标记为 P0（严重问题）：

### 1. 链接类型检查

| 检查项 | 通过标准 | 失败示例 |
|--------|---------|---------|
| 域名合规 | `.edu` 或学校官方子域 | DovePress、Loop、ResearchGate、ORCID |
| 页面类型 | 个人研究页（含 Publications/Research/CV） | 医生预约页、CRM 中心页、院系列表页 |
| 第三方平台 | 直接判定失败，无例外 | 任何出版商简介、学术社交网络 |

### 2. 方向核心度检查

| 检查项 | 通过标准 | 失败示例 |
|--------|---------|---------|
| 核心方向 | 关键词在实验室主页/论文中出现频率 >50% | "研究方向之一"、仅在综述中提及 |
| 硬排除 | 线虫/果蝇/酵母模式生物 → 排除 | C. elegans 心衰模型 |
| 硬排除 | 纯计算生物学（>70% dry lab）→ 排除 | 突变谱/生信分析为主 |
| 硬排除 | 癌症生物学为主线 → 排除 | 白血病干细胞为主，iPSC 只是副业 |

### 3. URL 健康检查

| 检查项 | 通过标准 | 失败示例 |
|--------|---------|---------|
| 无废弃标记 | URL 不含 `__trashed`、`_legacy`、`_old` | `profile/jessica-fetterman__trashed/` |
| 非 302 跳转 | 最终页面是个人页，不是搜索页/列表页 | 旧 URL 跳转到医院搜索页 |
| 非 SPA 空壳 | 页面内容 >5KB 且含导师专属信息 | 200 响应但仅含导航栏的 JS 壳 |
| 内容可验证 | WebFetch 能读取到姓名+职称+研究方向 | Cloudflare 挑战页、WAF 拦截页 |

### P0 判定标准

以下任一情况直接标记 P0（必须修正后才能进入下一轮）：
- 导师主页为第三方平台
- 导师主页为医生预约/CRM 页
- 研究方向属于硬排除项（线虫/dry lab/癌症主线）
- URL 含废弃标记或跳转失效
- 方向关键词只是"研究方向之一"而非核心方向

### 审核输出格式

```
=== P0 清单（必须修正）===
1. [记录编号] [导师名] — [P0原因]
   → [修正建议]

=== P1 清单（建议修正）===
...

=== 结论 ===
[PASS / FAIL] — X 条 P0，Y 条 P1
```

无 P0 时输出：
```
PASS — 本批 X 条记录全部通过强制验证清单
```

**双门槛机制**：必须同时满足链接准确率 ≥ 95% **且** 匹配置信度 ≥ 95%，置信度才能设为"通过"，才能进入已完成/人工待审核阶段。

## 1+1 工作流

```bash
# Step 0: 领取任务
python3 run_1plus1.py claim "学生名"

# Step 1: 选导助手执行搜索和填表
# （由 phd-supervisor-agent 完成）

# Step 2: 自动化审计
python3 run_1plus1.py audit "学生名"

# Step 3: 根据审计结果修复（返工给选导助手）

# Step 4: 交付
python3 run_1plus1.py done "学生名" --passed true --feedback "..."
```

详细流程见 `references/WORKFLOW.md`。

## 环境变量

```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=rT4f...
FEISHU_APP_TOKEN=PUR6...
FEISHU_TABLE_ID=tblf...
VIKA_TOKEN=usk...
```
