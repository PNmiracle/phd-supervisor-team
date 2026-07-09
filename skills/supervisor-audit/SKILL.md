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
| 国内邮箱 | 100% | 国内学校 `导师联系方式` 含有效 email |
| AI 痕迹 | 0 条 | 备注无 emoji/⚠/机械短语 |
| 选导意向保护 | 0 条已填 | `选导意向` 为空 |

## 置信度通过条件

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
