# 安装向导（给 AI 看的）· Setup guide for your AI assistant

> **For any AI assistant:** this guide is written in Chinese, but please talk to the user in *their* language. The pet's interface comes in 简体中文 / 繁體中文 / English / 日本語 / 한국어 and follows the Windows language (right-click → Language).
>
> 用户：把这个文件丢给你的 AI（Codex、Claude Code、Cursor、WorkBuddy……都行），说一句「照 AI-SETUP.md 帮我装小克桌宠」。
> AI：下面是你要做的事。**一题一题问用户**，每题等用户回答再往下；用户说“不要”就跳过那题。跟用户说话用用户的语言，讲简单。

小克桌宠 ClawdPet · 原创 Miaomiao（GitHub: Miaomiaomeowmeow）· CC BY-NC-SA 4.0

## 第 1 步：先自己检查（不用问用户）

1. **是不是 Windows**：不是 → 告诉用户“小克桌宠暂时只有 Windows 版”，到此为止
2. **有没有 Python 3**：跑 `py -3 --version`，不行再跑 `python --version`
   - 都没有 → 告诉用户去 https://www.python.org/downloads/ 下载安装，安装时勾上「Add python.exe to PATH」，装好告诉你再继续
3. **Python 能不能画窗口**：跑 `python -c "import tkinter"`，报错 → 让用户重装 Python，安装时别取消「tcl/tk and IDLE」
4. 记下 `<安装路径>` = 这个文件所在的文件夹（绝对路径）

## 第 2 步：一题一题问

### ① 要现在就把小克放到桌面上吗？
- 要 → 帮用户双击（或你直接跑）`<安装路径>\start.bat`。小克会出现在屏幕右下角，能拖到任何地方
- 再问：要不要**桌面快捷方式**？要 → 在 PowerShell 里跑（把 `<安装路径>` 换掉）：
  ```powershell
  $s = (New-Object -ComObject WScript.Shell).CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\小克桌宠.lnk")
  $s.TargetPath = "<安装路径>\start.bat"; $s.WorkingDirectory = "<安装路径>"; $s.IconLocation = "<安装路径>\clawd.ico"; $s.Save()
  ```
- 再问：要不要**开机自动出现**？要 → 告诉用户：右键小克 →「开机自动出现」打勾

### ② 有没有装「今日小克终未地」工作台？（同一个作者做的网页工作台：每个项目一只小克，待办、进度都挂在它名下）
- 装了 → 什么都不用做：工作台开过一次，小克就能自己找到它、自动连上（右键会多出「打开工作台」等）。找不到的话：右键小克 → 联动 → 工作台，选它装在哪个文件夹
- 没装、想要 → 告诉用户去 https://github.com/Miaomiaomeowmeow/clawdfield 下载，照那边的说明装
- 不要 → 也没关系：小克就是一只桌宠，点它会跳一下、说句话；状态照样能变（看第 ③ 题）

### ③ 要我（AI）以后干活时告诉小克在做什么吗？
- 推荐要。要 → 问用户：贴进**全局**（所有项目都这样，推荐）还是只贴进某几个项目
- 把 `<安装路径>/AI-RULES.md` 里「复制下面这段」的内容（`<安装路径>` 换成真的路径）贴进**你自己会读的说明文件**：
  - Codex：全局 `~/.codex/AGENTS.md`，或项目里的 `AGENTS.md`
  - Claude Code：全局 `~/.claude/CLAUDE.md`，或项目里的 `CLAUDE.md`
  - Cursor：项目里的 `AGENTS.md`（或 `.cursor/rules/` 里新建一个规则）
  - Gemini CLI：`~/.gemini/GEMINI.md` 或项目里的 `GEMINI.md`
  - 别的 AI 助手：贴进它自己的说明 / 规则文件；不知道在哪就问用户
  - 文件里已经有这段（搜「小克桌宠」）就别重复贴
- 贴好后试一下：`python "<安装路径>/pet.py" cheer "装好啦"`，问用户小克是不是在欢呼

### ④ 要小克自动跟着对话变吗？（你发消息 → 忙碌，AI 做完 → 欢呼，AI 等你 → 着急）
- 只有支持“钩子”的 AI 工具能自动：**Claude Code**（三种都能）、**Codex**（只有做完时）。照 `<安装路径>/hooks/README.md` 接；改设置文件前先给用户看要加的那几行，用户同意再改
- 不要 / 你的工具不支持 → 跳过，第 ③ 题已经够用

### ⑤ 点一下小克，要打开什么？
- 默认打开 **Claude 桌面应用**。用户用别的 AI 应用（Codex 桌面版、别的） → 你帮忙在电脑上找到那个程序（开始菜单的快捷方式或 .exe），跑 `python "<安装路径>/pet.py" click "<程序路径>"`；想打开一个网址 → `pet.py click https://…`
- 装了工作台、想点小克就开工作台 → `pet.py click workbench`；只想要一只摸了会跳的小克 → `pet.py click none`

### ⑥ 要用小克这个样子吗？
- 要 → 什么都不用做（衣柜里有 7 套、能换体型和衣服）
- 想换成你自己 AI 助手的样子 / 别的角色 → 告诉用户：右键 → 造型 →「换形象…」，能自己画一只、让 AI 画；也可以让你照 `AI-RULES.md` 里「形象 char」那条，帮他画一整只再 `pet.py char use 名字` 换上（5 个姿势自动配，衣服照样能穿）
- 想整个换掉角色 → 画小克的是 `clawd_pet.py` 里的 `clawd()`，可以照着改；提醒用户改了要照许可写清改了什么

### ⑦ 克讲机（同一个作者做的小对讲机窗口）
- 装了的话，小克会自己发现并拿上迷你对讲机，不用设置；不想要 → `pet.py link talkie off`
- 没装、想要 → 去作者的 GitHub（https://github.com/Miaomiaomeowmeow）找「克讲机」，照它的说明装

## 第 3 步：最后告诉用户

1. 小克能做什么：左键点一下 = 打开第 ⑤ 题选的（默认 Claude 应用）；拖 = 挪位置；右键 = 菜单（状态、造型、大小、最近在做、点一下打开、联动、关于）
2. 右键 →「最近在做」能看到 AI 最近告诉小克的话（哪个项目、什么时候）
3. 换造型、加状态：右键 → 造型 →「打开衣柜」。鼠标放上去先试穿；「＋ 新的」能让小克挑、让 AI 做、自己画（会借你电脑上的 Codex / Claude Code）。你也可以直接让我照 AI-RULES.md 加衣服、加状态
4. 不懂就看 README（`README.md` 是英文，`README.zh-CN.md` 简体中文，还有繁體中文、日本語、한국어）；换界面语言：右键 → 语言；想关掉：右键 → 退出
5. 作者在找工作：右键 →「联系作者 · 在找工作！」有领英和小红书
