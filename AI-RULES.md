# 贴进 AI 说明文件的那一段 · Snippet for your AI's instruction file

> For any AI assistant: written in Chinese; the commands are the same in every language. Write the pet's messages in the user's language.

安装向导（AI-SETUP.md）第 ③ 题会让 AI 把下面这段贴进它自己会读的说明文件（`AGENTS.md`、`CLAUDE.md`、`GEMINI.md`……）。也可以自己手动贴：把 `<安装路径>` 换成桌宠装在哪的绝对路径（右键小克 → 关于 → 打开桌宠所在的文件夹，看地址栏）。

小克桌宠 ClawdPet · 原创 Miaomiao（GitHub: Miaomiaomeowmeow）· CC BY-NC-SA 4.0

---

复制下面这段 ↓

```markdown
## 小克桌宠（让桌面上的小克知道你在干嘛）

桌宠装在 `<安装路径>`。在**当前项目文件夹**里跑：`python "<安装路径>/pet.py" <状态> "一句话"`（项目名会自动用当前文件夹的名字）

- 开始做一块活：`pet.py busy "在做什么"`
- 做完一块：`pet.py cheer "做成了什么"`
- 卡住了、要用户来回话 / 决定 / 点同意：`pet.py urgent "要用户做什么"`
- 没事了：`pet.py relaxed`
- 话写短一点（20 个字以内最好），用用户的语言；用户会在桌面上看到
- 桌宠没开也没关系，命令照样跑；跑不了（找不到文件）就跳过，别影响正事
```

---

## 让 AI 加衣服、加状态（用户让你做的时候再看）

小克的衣柜里点「＋ 新的」时，如果电脑上没有能借的 AI，会复制一句话让用户贴给你。照下面做：

**格子坐标**：x 从 -8 到 31，y 从 -12 到 21，一格一个像素。小克站着时身子是 x 4～17、y 2～13 的方块（眼睛在 x 7～8 和 13～14、y 5～8），四条腿在 y 14～18。
**像素写法**：`x,y,颜色;x,y,颜色`，颜色是 6 位十六进制、不带 #，别用 `ff00fe`（那是透明色）；颜色写 `-` = 把小克那一格擦成透明。20～80 个点、2～4 种颜色，像素风、轮廓清楚。

| 部位 `--slot` | 大概画在哪 |
|---|---|
| `hat` 头上 | x 4～17，y -8～1 |
| `ears` 耳朵 | 头顶两边各一只：x 3～8 和 13～18，y -7～1，左右对称 |
| `tail` 尾巴 | 身子左边：x -7～3，y 3～13 |
| `face` 脸上 | x 5～16，y 4～10（别把眼睛全盖住） |
| `body` 身上 | x 4～17，y 8～13 |
| `hold` 手上 | 身子前面：x 6～15，y 9～15 |

```
python "<安装路径>/pet.py" part add 草莓帽 --slot hat --px "8,-3,e2412b;9,-3,e2412b;10,-4,7bd389"
python "<安装路径>/pet.py" state add 摸鱼 --pose relaxed --say "摸一下下/鱼在哪/嘘" --px "20,-6,9fb3c8;21,-6,9fb3c8"
python "<安装路径>/pet.py" color add #e2412b
python "<安装路径>/pet.py" build add 布丁 --w 125 --h 85
python "<安装路径>/pet.py" preset add 海盗 --look "{\"hat\":\"witch\",\"body\":\"cape\",\"face\":\"shades\",\"color\":\"#5a4a7a\"}"
python "<安装路径>/pet.py" part list      （state list / part del 名字 / state del 名字 也行）
```

- 状态的 `--pose` 是用哪种姿势画：`urgent` 着急举牌 / `busy` 站着 / `relaxed` 趴着 / `cheer` 举手 / `sleep` 睡觉；`--px` 可以不写。写的话可以画小道具（头顶上方或右上角，x 14～28，y -11～1），也可以改小克这时的样子：先用小克的颜色把眼睛涂掉再画新表情，或者用 `-` 擦掉几格。坐标是这个姿势里的真实位置：`relaxed` 趴着时小克整体往下 3 格，`sleep` 往下 4 格
- 形象 `char`（整只换掉的角色，不是衣服）：`pet.py char add 灰猫 --px "…" --color #8fb3c8`，再 `pet.py char use 灰猫`（换回来：`char use 小克`）。一整只站着的样子：大约 12～18 格宽、12～18 格高，脚踩在 y=18，左右居中在 x=11 附近，要有眼睛，80～250 个点填满身子；主色是用得最多的那个颜色。5 个姿势会自动配，衣服会按它的大小套上去
- 体型 `build`：`--w` 宽、`--h` 高，都是百分比 60～130（100 = 标准）
- 整套（`preset`）只能用已有的部件：`ears` none/fox/cat/bunny/bear · `tail` none/fox/cat/bunny · `hold` none/cat/fish/tea · `hat` none/hard/beret/crown/chef/witch/straw/santa/bow/phones/flower · `face` none/glasses/shades/blush/band · `body` none/overalls/apron/cape/bowtie · `scarf` none 或 #颜色 · `color` #颜色；用户自己画的部件写 `u:<id>`（`part list` 看不到 id 的话就别用）
- 加好的状态以后能按名字叫：`pet.py 摸鱼 "偷偷休息一下"`
- 名字和样子别跟已有的重复（先 `list` 看一眼）；加完告诉用户去衣柜里看


## 设置：点一下打开什么、联动

```
python "<安装路径>/pet.py" click claude          （默认：Claude 桌面应用）
python "<安装路径>/pet.py" click workbench       （「今日小克终未地」工作台）
python "<安装路径>/pet.py" click none            （什么都不打开，小克跳一下）
python "<安装路径>/pet.py" click "C:/…/Codex.exe"   （任何程序或网址）
python "<安装路径>/pet.py" link workbench on|off
python "<安装路径>/pet.py" link talkie on|off
```

桌宠开着也会马上生效。
