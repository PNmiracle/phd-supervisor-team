# 选导自动化升级迁移说明

## 核心变化

本次升级按「替代 A」落地：保留 WorkBuddy + 飞书 Bitable，但彻底简化状态机。

| 旧设计 | 新设计 |
|--------|--------|
| 状态存在本地 `pass_log.json` 和飞书看板两处 | 状态唯一来源：飞书 Bitable |
| 单任务轮询 + 8 轮深度优化 | 批量单次处理 + audit 一次判定 |
| 文件锁 TTL 30 分钟 | 无文件锁；用 Bitable `锁定时间` + `处理节点` 做防重 |
| 所有结果都进「人工待审批」 | audit 通过自动进「已完成」，不通过才进「人工待审批」 |
| 6 个看板列（含独立的「AI自检」） | 5 个核心列；「AI自检」合并到「AI 处理中」 |

## 环境变量

所有飞书凭证已改为从环境变量读取，请添加到 `~/.zshrc` 或 WorkBuddy 环境配置中：

```bash
export FEISHU_APP_ID="cli_你的app_id"
export FEISHU_APP_SECRET="你的app_secret"
export FEISHU_APP_TOKEN="PUR6..."
export FEISHU_TABLE_ID="tblf..."
export VIKA_TOKEN="usk..."
```

修改后执行 `source ~/.zshrc` 使其生效。

## Bitable 新增字段

已自动添加以下字段（若不存在）：

- `锁定时间` (DateTime)：任务被领取时写入，用于死锁检测。
- `处理节点` (Text)：标记当前处理者/会话。
- `错误次数` (Number)：连续失败计数，达到 3 次后进入「人工待审批」。
- `失败原因` (Text)：audit 不通过或异常时写入，方便人工审批。
- `置信度` (SingleSelect：通过/未通过)：自动判定结果。

## 推荐状态流

```
任务发布未进行
      ↓
AI 处理中（写入锁定时间、处理节点）
      ↓
audit_state 审计 Vika 表
      ├─ 通过 → 已完成（自动）
      └─ 不通过 → 人工待审批（带失败原因）
```

## 关键脚本

| 脚本 | 作用 |
|------|------|
| `run_scheduler.py` | WorkBuddy 自动化入口：释放死锁、批量领取任务、输出 JSON |
| `state_machine.py` | 新调度器：get_pending_tasks / claim_tasks / complete_task / fail_task / release_stale_locks |
| `feishu_client.py` | 飞书 Bitable API 客户端（标准库，零依赖） |
| `feishu_config.py` | 凭证与字段名常量 |
| `setup_bitable_fields.py` | 一次性脚本：确保 Bitable 新增字段存在 |
| `audit_state.py` | 保留，继续用于 Vika 表质量审计 |
| `query_feishu.py` | 查询待处理任务（已改用新配置） |
| `query_schema.py` / `debug_fields.py` | 调试用（已改用新配置） |
| `run_1plus1.py` | 1+1 工作流调度器（claim / audit / done / fail） |
| `WORKFLOW.md` | 1+1 标准流程文档（每个 chat 的必读规范） |

## WorkBuddy 自动化 Prompt 调整建议

旧的 8 轮循环逻辑可以替换为：

```text
1. 运行 `python3 run_scheduler.py` 获取本批次要处理的学生任务。
2. 对每个 claim 到的任务：
   a. 解析提示词中的 Vika 分享链接。
   b. 调用 phd-supervisor-selector skill 完成该学生的导师筛选。
   c. 运行 `python3 audit_state.py <DATASHEET_ID> $VIKA_TOKEN`。
   d. 若 audit 通过：调用 state_machine.complete_task(record_id, passed=True, feedback_lines=[...])。
   e. 若 audit 不通过：调用 state_machine.complete_task(record_id, passed=False, failure_reason=weak_dim, feedback_lines=[...])。
3. 若处理过程中抛异常：调用 state_machine.fail_task(record_id, failure_reason=str(e))。
```

注意：
- 不再需要 `acquire_lock` / `release_lock` 的 8 轮模式。
- 不需要读写本地 `pass_log.json`。
- 处理完一个批次即可结束本次自动化；下次触发会自动领取下一批。

## 关于旧 `pass_log.json`

旧状态文件 `.workbuddy/pass_log.json` 已不再被读取。首次运行 `check_stale_locks()` 时，所有处于「AI 处理中」但没有 `锁定时间` 的记录会被视为死锁并释放回「任务发布未进行」。如果你希望保留旧日志作为参考，可手动备份；否则可直接删除。

## 已验证

- 新增字段已成功写入 Bitable。
- `run_scheduler.py` 可正确领取任务并更新 `锁定时间` / `处理节点`。
- `complete_task` 可正确将任务移入「已完成」并清空锁定信息。
- 凭证已从代码中移除，改为环境变量读取。
- `chat_runner.py` 可正确按学生名领取任务并防止跨 chat 冲突。

## 扩展：一个 chat 管理一个学生（并行处理）

除了批量自动化 `run_scheduler.py`，现在也支持在 WorkBuddy 空间中为每个学生开一个独立 chat，各 chat 并行处理自己的任务。

### 核心机制

- 飞书 Bitable 仍然是唯一任务队列。
- 每个 chat 通过学生名领取自己的任务：
  ```bash
  python3 chat_runner.py "张竣菘"
  ```
- `chat_runner.py` 会返回任务详情（提示词、Vika 链接、附件、当前阶段），并尝试将任务标记为 `AI 处理中` + `处理节点=chat-张竣菘`。
- 如果该任务已被其他 chat 或批量自动化领取，`ok=false`，并返回当前 `locked_by`，避免冲突。

### chat 内工作流

在「张竣菘-初选」这类 chat 中，可配置如下 prompt：

```text
1. 运行 `python3 chat_runner.py "张竣菘"` 领取并确认本 chat 负责的学生任务。
2. 若返回 ok=true：
   a. 从返回的 vika_url 打开该学生的选导表。
   b. 调用 phd-supervisor-selector skill 完成导师筛选。
   c. 运行 `python3 audit_state.py <DATASHEET_ID> $VIKA_TOKEN`。
   d. 若 audit 通过：调用 state_machine.complete_task(record_id, passed=True, feedback_lines=[...])。
   e. 若 audit 不通过：调用 state_machine.complete_task(record_id, passed=False, failure_reason=weak_dim, feedback_lines=[...])。
3. 若返回 ok=false：
   - 如果 locked_by 是其他 chat/自动化，请等待或提醒用户不要重复处理。
   - 如果阶段是「已完成」或「人工待审批」，直接汇报当前状态。
4. 处理过程中抛异常：调用 state_machine.fail_task(record_id, failure_reason=str(e))。
```

### 两种模式对比

| 模式 | 适用场景 | 入口 | 并行度 |
|------|---------|------|--------|
| 批量自动化 | 无人值守、按批次自动跑 | `run_scheduler.py` | 单批次串行，多批次可并行 |
| 单学生 chat | 人工跟进、高峰期多学生并行 | `chat_runner.py` | 每个 chat 一个独立任务 |

两种模式共享同一张 Bitable，通过 `处理节点` 字段区分当前处理者，互不冲突。

### 防冲突规则

1. 同学生只能有一个 chat 在处理（`处理节点` 字段标识）。
2. 批量自动化 `run_scheduler.py` 使用 `workbuddy-auto` 作为节点名；chat 使用 `chat-学生名`。
3. 若 chat 发现自己的任务已被 `workbuddy-auto` 领取，应提示用户「该任务已被批量自动化接管」，避免争抢。
4. 死锁超过 30 分钟的任务会被 `release_stale_locks()` 自动释放。
