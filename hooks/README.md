# 让小克自动跟着对话变 · Auto-update the pet from your AI chats

接上以后不用 AI 自己记得跑命令：**你发消息 → 小克忙碌**，**AI 做完一轮 → 小克欢呼**，**AI 等你回话 / 点同意 → 小克着急**。
（不接也行：AI 照 `AI-RULES.md` 自己跑 `pet.py` 一样能让小克变，还能说具体在做什么。两样可以一起用。）

下面的 `<安装路径>` 换成桌宠装在哪的绝对路径，`\` 写成 `/`（例：`C:/Users/me/clawd-pet`）。

## Claude Code

打开 `~/.claude/settings.json`（全局，所有项目都生效），在 `"hooks"` 里加上下面三项（已经有 `"hooks"` 的话，把三项合进去，别覆盖原来的）。也可以照抄 `claude-code.json`：

```json
{
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python \"<安装路径>/pet.py\" hook busy", "timeout": 10 }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "python \"<安装路径>/pet.py\" hook done", "timeout": 10 }] }],
    "Notification":     [{ "hooks": [{ "type": "command", "command": "python \"<安装路径>/pet.py\" hook wait", "timeout": 10 }] }]
  }
}
```

改完重开 Claude Code 才生效。

## Codex

Codex 能在「做完一轮」时跑一个程序（`notify`）。打开 `~/.codex/config.toml`，在最上面加一行（已经有 `notify` 的话就别加，一个 Codex 只能接一个）：

```toml
notify = ["python", "<安装路径>/pet.py", "hook", "done"]
```

Codex 只有“做完一轮”这一个时机，所以只会自动变欢呼；“忙碌 / 着急”靠 AI 照 `AI-RULES.md` 自己跑命令。

## 别的 AI 助手

看它有没有“钩子 / hooks / 做完时跑命令”的设置：有的话，开始时跑 `pet.py hook busy`、做完时跑 `pet.py hook done`、等你时跑 `pet.py hook wait`。没有就只用 `AI-RULES.md`。

## 注意

- `hook` 这几条只给自动接法用（它会读掉 AI 工具传进来的信息）。你自己或 AI 手动让小克变，用 `pet.py busy "在做什么"`
- 小克的状态会自己过期：欢呼 15 分钟后、忙碌 / 着急 3 小时没人更新，就变回悠闲；半夜 1 点到 7 点不着急就睡觉
