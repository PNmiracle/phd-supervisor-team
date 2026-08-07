# 协作流程：开始学生 & 结束学生

本文档定义两个核心协作命令的完整执行流程。当用户说"开始学生"或"结束学生"时，AI 按此文档执行。

---

## "开始学生" — 一键提交流程

当用户说**"开始学生"**或**"提交更新"**或类似表达时，自动执行完整提交流程，无需用户手动操作 git。

### 触发语

以下任何一句都会触发：
- `"开始学生"`
- `"提交更新"`
- `"帮我把改动推上去并开 PR"`
- `"同步并提交"`

### 执行流程（AI 按顺序自动完成）

**核心原则**：先保证本地干净，再拉最新代码，最后提交推送。全程不需要用户懂 git。

---

**第 1 步：检查 git 身份（避免提交者邮箱错误）**

```bash
cd ~/.workbuddy/skills/phd-supervisor-selector
git config user.name
git config user.email
```

- 如果输出为空，或邮箱以 `.local` 结尾（如 `<[email protected]>`）：
  - **暂停流程**，告诉用户：
    > git 身份未正确配置，commit 不会被 GitHub 认领。
    > 请对 AI 说："帮我配置 git，用户名填 `你的GitHub用户名`，邮箱填 `你的GitHub注册邮箱`"
  - 等用户配置好后，再重新执行第 1 步
- 如果已正确配置，继续第 2 步

---

**第 2 步：展示改动文件，让用户确认**

```bash
git status --short
```

- 把改动文件列表展示给用户看
- **问用户**："这些文件都要提交吗？"
- 如果用户说"只提交 XX 文件"：
  - 记录文件名，第 8 步只用 `git add XX`（不用 `git add -A`）
- 如果用户确认全部提交：
  - 第 8 步用 `git add -A`

---

**第 3 步：把当前改动 stash 起来（防止 pull 时报错）**

```bash
git stash push -m "临时保存：开始学生前"
```

- 这样即使有未暂存改动，`git pull --rebase` 也不会报错
- 如果 `git stash` 失败（不太可能），暂停并告诉用户

---

**第 4 步：确保在 main 分支，拉取最新代码**

```bash
git checkout main
git pull --rebase origin main
```

- 如果 `git pull --rebase` 遇到冲突：
  - **暂停流程**，告诉用户哪个文件冲突了
  - 展示冲突内容（`<<<<<<<` 标记的部分）
  - 让用户决定保留哪个版本，或两边都在
  - 解决后执行 `git add <文件>` -> `git rebase --continue`
  - 然后继续第 5 步

---

**第 5 步：检查是否有未合并的 PR（可选提醒）**

```bash
gh pr list --state open --json number,title,headRefName
```

- 如果有其他未合并的 PR：
  - 提示用户：
    > 还有未合并的 PR#XX（xxx），你可以等它合并后再开新的，也可以继续
  - 用户说"继续"才继续，说"先等一下"则暂停
- 如果没有未合并的 PR，直接继续第 6 步

---

**第 6 步：开新分支（自动命名）**

```bash
DATE=$(date +%Y-%m-%d)
BRANCH="feat/${DATE}-技能更新"

# 如果当天已有同名分支，加序号
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  N=2
  while git show-ref --verify --quiet "refs/remotes/origin/${BRANCH}-${N}"; do N=$((N+1)); done
  BRANCH="${BRANCH}-${N}"
fi

git checkout -b "$BRANCH"
```

- 分支名格式：`feat/YYYY-MM-DD-技能更新`（或加 `-2`、`-3` 后缀）

---

**第 7 步：应用 stash（把第 3 步保存的改动拿回来）**

```bash
git stash pop
```

- 如果 `git stash pop` 冲突：
  - **暂停流程**，展示冲突内容，让用户决定
  - 解决后执行 `git add <文件>`，然后继续第 8 步

---

**第 8 步：提交（根据第 2 步的用户选择）**

```bash
# 如果用户确认全部提交：
git add -A

# 如果用户说"只提交 XX 文件"：
# git add XX

# 自动生成 commit 消息
CHANGED=$(git diff --cached --name-only | tr '\n' ' ' | sed 's/ $//')
COMMIT_MSG="feat: $(date +%Y-%m-%d) 更新 ${CHANGED}"

git commit -m "$COMMIT_MSG"
```

- commit 消息会自动包含改了哪些文件
- 示例：`feat: 2026-07-04 更新 references/school-strategies.md`

---

**第 9 步：推送到 GitHub**

```bash
git push -u origin "$BRANCH"
```

- 如果 `git push` 失败（如网络问题），提示用户重试

---

**第 10 步：自动开 PR（gh CLI）**

```bash
gh pr create \
  --title "$COMMIT_MSG" \
  --body "本次更新：${CHANGED}" \
  --base main \
  --head "$BRANCH"
```

---

**第 11 步：PR 创建成功后，输出链接并提示**

告诉用户：
> PR 已创建：`https://github.com/.../pull/XX`
> 等待仓库管理员合并
> 合并后我会自动同步最新代码，下次直接说"开始学生"就行

### PR 合并后自动清理

合并后，用户下次说"开始学生"时，AI 在 pull 之后自动清理已合并的本地分支：

```bash
git branch --merged main | grep -v '^\*' | grep -v main | xargs -r git branch -d
```

### 只提交部分文件

如果用户说"只提交 XX 文件，其他先不提交"：
```bash
git add references/school-strategies.md
# 其余流程不变
```

### 冲突处理

如果 `git pull --rebase` 时冲突：
1. 暂停流程，告诉用户哪个文件冲突了，展示冲突内容
2. 让用户决定保留哪个版本，或两边都在
3. 解决后执行 `git add <文件>` -> `git rebase --continue`
4. 继续 push -> 开 PR

---

## "结束学生" — 知识沉淀流程

当用户说"**结束学生**"或类似表达时，执行知识提取 + 同步工作流：

1. **回顾本轮对话**，提取可入库的经验：
   - 哪些学校的搜索策略需要更新（写入 school-strategies.md）
   - 哪些搜索技巧值得记录（写入 search-techniques.md）
   - 哪些筛选规则需要调整（写入 selection-rules.md）
2. **向用户确认**："要不要把这些经验更新到 Skill 里？"
3. 用户确认后，更新对应文件
4. **自动执行"开始学生"流程**（见上方），提交推送开 PR
5. **协作模式**：多位老师通过同一 GitHub 仓库共同维护
