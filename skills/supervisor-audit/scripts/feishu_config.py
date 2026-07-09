#!/usr/bin/env python3
"""Shared Feishu Bitable configuration from environment variables.

Never hardcode credentials. Set these in your shell profile or WorkBuddy env:

    export FEISHU_APP_ID="cli_xxx"
    export FEISHU_APP_SECRET="rT4f..."
    export FEISHU_APP_TOKEN="PUR6..."
    export FEISHU_TABLE_ID="tblf..."
    export VIKA_TOKEN="usk..."
"""
import os


def _require(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Please set it in ~/.zshrc or the WorkBuddy environment."
        )
    return value


APP_ID = _require("FEISHU_APP_ID")
APP_SECRET = _require("FEISHU_APP_SECRET")
APP_TOKEN = _require("FEISHU_APP_TOKEN")
TABLE_ID = _require("FEISHU_TABLE_ID")

# Vika token is optional here; audit_state.py still accepts it as an argument.
VIKA_TOKEN = os.environ.get("VIKA_TOKEN")

# API endpoints
AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BASE_URL = "https://open.feishu.cn/open-apis/bitable/v1"

# Task management constants
STAGE_PENDING = "任务发布未进行"
STAGE_PROCESSING = "AI 处理中"
STAGE_PAUSED = "暂停"
STAGE_DONE = "已完成"
STAGE_REVIEW = "人工待审批"

PRIORITY_ORDER = {"P0-高优": 0, "P1-一般": 1, "P2-低优": 2}

# Fields used by the scheduler
FIELD_STUDENT = "学生"
FIELD_ROUND = "第几轮选导"
FIELD_PRIORITY = "优先级"
FIELD_PROMPT = "提示词"
FIELD_ATTACHMENTS = "附件"
FIELD_STAGE = "阶段"
FIELD_FEEDBACK = "AI 反馈"
FIELD_START_TIME = "开始时间"
FIELD_END_TIME = "结束时间"
FIELD_LOCK_TIME = "锁定时间"
FIELD_NODE = "处理节点"
FIELD_ERROR_COUNT = "错误次数"
FIELD_FAILURE_REASON = "失败原因"
FIELD_CONFIDENCE = "置信度"
