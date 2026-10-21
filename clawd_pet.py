# 小克桌宠 ClawdPet：桌面上透明、置顶、能拖动的像素小克（只支持 Windows）。
# 原创：Miaomiao（GitHub: Miaomiaomeowmeow）· 许可 CC BY-NC-SA 4.0（可以二改，不准商用；改了公开要照同样许可、写清改了什么）
# Original work by Miaomiao (GitHub: Miaomiaomeowmeow) · CC BY-NC-SA 4.0 · https://github.com/Miaomiaomeowmeow/clawd-pet
#
# 左键点一下 = 打开工作台「今日小克终未地」（装了的话；没装就只是个桌宠，点它会跳一下）；左键拖 = 挪位置；右键 = 菜单。
# 状态从同目录 status.json 读（每秒看一次有没有改）：任何 AI 助手跑一条命令就能让它变，见 pet.py。
# 窗口位置、大小、开关这些只跟这台电脑有关的，存在 settings.json。
# 跟克讲机、Claude 应用的联动都是开关，默认关（右键 → 联动）。

import base64
import ctypes
import json
import os
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import urllib.request
import webbrowser
from tkinter import filedialog

import lang
from lang import _

APP, VERSION = _("小克桌宠 ClawdPet"), "1.0"
GITHUB = "https://github.com/Miaomiaomeowmeow/clawd-pet"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans"
AUTHOR_GITHUB = "https://github.com/Miaomiaomeowmeow"   # 作者的其他作品（工作台、克讲机……）都会发在这里
LINKEDIN = "https://www.linkedin.com/in/miaomiao-yang-331901383"
XHS = "@羊猫猫不是猫"                                     # 小红书
WEBSITE = ""   # 作者的个人网站（简历 + 别的好玩的作品）：还在做，做好了填这里；空着时指向领英
HERE = os.path.dirname(os.path.abspath(__file__))
STATUS = os.path.join(HERE, "status.json")
SETTINGS = os.path.join(HERE, "settings.json")
RECENT = os.path.join(HERE, "recent.json")     # pet.py 记的最近几条（哪个项目、说了什么）
STARTUP_BAT = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup\ClawdPet.bat")
# 名片：各个小克程序在用户文件夹里留一张，写着自己装在哪，别的程序就能找到它，不用填路径
CARDS = os.environ.get("CLAWD_CARDS") or os.path.join(os.path.expanduser("~"), ".clawd")  # 测试时可以用 CLAWD_CARDS 换个文件夹（工作台那边也认）
PET_CARD = os.path.join(CARDS, "pet.json")             # 桌宠自己写
WB_CARD = os.path.join(CARDS, "workbench.json")        # 工作台（今日小克终未地）写：{"dir", "url"}
TALKIE_CARD = os.path.join(CARDS, "talkie.json")       # 克讲机写：{"path"}（克讲机还没公开）
WB_URL = "http://localhost:8765"                       # 工作台默认开在这里

KEY = "#ff00fe"  # 这个颜色会变成透明，画小克时别用它
INK, PAPER, YELLOW = "#151513", "#ffffff", "#ffe14a"
TONES = ("#6d6164", "#652062", "#7920e5", "#96b5e5", "#96b500")  # 描边备用色，和工作台里的一样
FONT = (lang.font(), 10)   # 按语言换字体（日文、韩文、繁体各用 Windows 自带的）

STATES = ["urgent", "busy", "relaxed", "cheer", "sleep"]
STATE_ZH = {"urgent": _("着急"), "busy": _("忙碌"), "relaxed": _("悠闲"), "cheer": _("欢呼"), "sleep": _("睡觉")}
LINES = {"urgent": _("急急急！"), "busy": _("在忙在忙～"), "relaxed": _("猫猫赛高"), "cheer": _("做完啦！"), "sleep": "zzZ…"}
POKE = [_("嘿！"), _("我在呢～"), _("摸摸我干嘛～"), _("今天也加油！"), _("嘿嘿"), _("要喝水哦")]  # 没装工作台时点小克
PRESETS = {
    "原版小克": {"ears": "none", "tail": "none", "color": "#d97757", "hold": "none"},
    "狐狸小克": {"ears": "fox", "tail": "fox", "color": "#d97757", "hold": "cat"},
    "紫色猫猫": {"ears": "cat", "tail": "cat", "color": "#9b7bff", "hold": "cat", "face": "blush"},
    "水青兔兔": {"ears": "bunny", "tail": "bunny", "color": "#3fc7c7", "hold": "tea"},
    "粉粉小熊": {"ears": "bear", "tail": "none", "color": "#ff8fc2", "hold": "fish", "body": "bowtie"},
    "终末地工程师": {"ears": "fox", "tail": "fox", "color": "#d97757", "hold": "none", "hat": "hard", "body": "overalls", "scarf": "#ffe14a"},
    "小魔女": {"ears": "cat", "tail": "cat", "color": "#5a4a7a", "hold": "cat", "hat": "witch", "body": "cape"},
}
SIZES = {"小": 3, "中": 4, "大": 6}
# 内置的性格（只用桌宠、没连工作台时用）：第一次打开随机给一个；也能自己写、让 AI 按要求写。
# 「小克挑」「让小克按性格写话」都照它来
PERSONAS = {
    "sunny": (_("小太阳"), _("热情、话多、爱夸人，什么事都往好处想")),
    "tsundere": (_("嘴硬心软"), _("嘴上嫌弃，其实很关心你；不肯承认自己开心")),
    "sloth": (_("慢吞吞"), _("佛系、爱睡觉，说话慢半拍，最怕被催")),
    "hero": (_("中二勇者"), _("把小事都当冒险，爱喊口号、给自己起称号")),
    "neat": (_("整理控"), _("爱干净、讲规矩，看到乱就想收拾")),
    "shy": (_("社恐"), _("害羞、说话小声，被夸会脸红")),
    "foodie": (_("小吃货"), _("什么都能联想到吃，饿了就没精神")),
    "thinker": (_("小哲学家"), _("爱想大道理，说话像在写诗")),
}
DEFAULT_STATUS = {"state": "relaxed", "say": "", "look": PRESETS["原版小克"], "url": "", "parts": [], "presets": []}
CLICK = {"claude": _("Claude 应用"), "workbench": _("工作台（今日小克终未地）"), "none": _("什么都不打开（小克跳一下）")}
DEFAULT_SETTINGS = {"size": "中", "x": None, "y": None, "topmost": True, "bubble": True, "click": "claude", "clickTarget": "",
                    "rotate": 0, "rotateWb": 0, "rotAt": 0, "linkWorkbench": False, "linkTalkie": False, "linkClaude": False, "workbenchDir": "", "talkiePath": ""}
# 体型（跟工作台一样）：宽、高各放大几倍，以脚底中间 (11, 19) 为准；自己调的存在 status.json 的 builds 里，look.build 写 u:<id>
BUILDS = {"normal": _("标准"), "slim": _("瘦瘦"), "chubby": _("胖嘟嘟"), "tall": _("高个子"), "short": _("矮墩墩"), "round": _("圆滚滚"), "tiny": _("迷你"), "big": _("大只")}
BUILD_SC = {"slim": (.82, 1.05), "chubby": (1.2, .97), "tall": (.92, 1.22), "short": (1.08, .8), "round": (1.25, .9), "tiny": (.75, .75), "big": (1.15, 1.15)}
HEAD = 10  # 小克头顶留的空（格），体型变高也放得下
# 克讲机联动（默认关）：克讲机和小克之间传话的文件夹
BRIDGE = os.path.join(os.path.expanduser("~"), ".claude", "clawkie-bridge")
NOTICE = os.path.join(BRIDGE, "notice.json")      # 克讲机给小克的提醒（新回答、生图请求……）
POSE = os.path.join(BRIDGE, "pet-pose.json")      # 克讲机现在在干嘛 → 小克手里的对讲机摆什么动作
FOCUS = os.path.join(BRIDGE, "focus.json")        # 你刚在哪个对话发了消息 → 小克看它还欠着哪些备忘
TALKIE_STATE = os.path.join(BRIDGE, "talkie.json")
# Claude 应用联动（默认关）：应用给每个对话存一个记录，里面 lastFocusedAt = 你最后点进它的时间（商店版和普通版两个位置都找）
APP_SESSIONS = [os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude-code-sessions")]
_pk = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages")
if os.path.isdir(_pk):
    APP_SESSIONS += [os.path.join(_pk, d, "LocalCache", "Roaming", "Claude", "claude-code-sessions") for d in os.listdir(_pk) if d.startswith("Claude_")]

# 小克手里的迷你对讲机（克讲机联动打开时才画）：四个动作的位置（格子坐标同 clawd()：身子 x 4～18、y 2～14，右手在 x 18～21）
POSES = {
    "idle":   {"at": (18.5, 8.5)},                 # 别在右边腰上
    "listen": {"at": (18.5, -2.5), "waves": (23.5, -1)},  # 举到耳边听，天线红灯闪
    "talk":   {"at": (15.5, 6.5), "waves": (21, 7.5)},  # 凑到嘴边说，往外冒声波
    "paint":  {"at": (8.5, 9), "paint": True},     # 捧在胸前看屏幕，屏上冒小色块
}
ROTATE = {0: _("不换"), 30: _("每 30 分钟"), 60: _("每 1 小时"), 180: _("每 3 小时"), 1440: _("每天")}  # 随机换小克：工作台 ⚙ 里选「桌宠随机换」再粘贴


# ---------- 读写文件 ----------

def read_json(path, fallback):
    try:
        with open(path, encoding="utf-8-sig") as f:  # utf-8-sig：开头带 BOM（PowerShell 写的）也能读
            return json.load(f)
    except (OSError, ValueError):
        return fallback


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ---------- 画小克（照 clawdSVG） ----------

def norm_look(l):
    l = l or {}
    n = {"char": "clawd", "ears": "fox", "tail": "fox", "color": "#d97757", "hold": "cat", "hat": "none", "face": "none", "body": "none", "scarf": "none", "build": "normal"}
    n.update(l)
    if l.get("fox") is False and "ears" not in l: n["ears"] = "none"
    if l.get("fox") is False and "tail" not in l: n["tail"] = "none"
    if l.get("cat") is False and "hold" not in l: n["hold"] = "none"
    return n


def build_scale(look, builds):
    """这身的体型：(宽倍数, 高倍数)"""
    b = str(norm_look(look).get("build") or "normal")
    if b.startswith("u:"):
        q = next((q for q in builds or [] if isinstance(q, dict) and "u:" + str(q.get("id")) == b), None)
        if not q:
            return (1, 1)
        clamp = lambda v: max(.6, min(1.3, float(v or 1)))
        return (clamp(q.get("sx")), clamp(q.get("sy")))
    return BUILD_SC.get(b, (1, 1))


def fit(cells, sc):
    """按体型拉伸：以脚底中间 (11, 19) 为准"""
    sx, sy = sc
    if (sx, sy) == (1, 1):
        return cells
    return [(k, 11 + (x - 11) * sx, 19 + (y - 19) * sy, w * sx, h * sy, c) for k, x, y, w, h, c in cells]


def overlay(px, cells):
    """把一串像素 'x,y,颜色;…' 加到格子后面；颜色写 - 的格子 = 擦掉（画成透明）"""
    for item in str(px or "").split(";"):
        try:
            x, y, col = item.split(",")
            col = col.strip()
            cells.append(("r", float(x), float(y), 1, 1, "-" if col == "-" else "#" + col.strip("#")))
        except ValueError:
            pass
    return cells


def shade(hex_, k):
    n = int(hex_[1:7], 16)
    c = [n >> 16, n >> 8 & 255, n & 255]
    c = [round(v + (255 - v) * k if k > 0 else v * (1 + k)) for v in c]
    return "#" + "".join(f"{max(0, min(255, v)):02x}" for v in c)


# ---------- 形象：默认是小克；也可以是自己画 / AI 画的别的角色 ----------
# 一个形象 = 站着的样子（像素 px，脚踩在 y=18 附近）+ 主色 color（换颜色时换掉的就是它）+ 可选的 poses（自己改过的姿势，整张换掉）。
# 没改过的姿势自动配：着急举牌、欢呼冒星星、悠闲喝茶、睡觉冒 Z；衣服照小克身上的位置，按它的大小套上去。
CHARS = []                     # 现在有哪些自己的形象（桌宠读 status.json 的 chars 时更新）
CLAWD_BOX = (4, 2, 18, 19)     # 小克站着时：身子 + 腿占的地方（x0, y0, x1, y1）
POSE_DY = {"relaxed": 2, "sleep": 3, "cheer": -1}


def parse_px(px):
    out = []
    for item in str(px or "").split(";"):
        try:
            x, y, c = item.split(",")
            out.append((int(float(x)), int(float(y)), c.strip()))
        except ValueError:
            pass
    return out


def find_char(look, chars=None):
    ch = str(norm_look(look).get("char") or "clawd")
    if ch == "clawd":
        return None
    return next((q for q in (CHARS if chars is None else chars) or [] if isinstance(q, dict) and "u:" + str(q.get("id")) == ch), None)


def char_box(c):
    pts = [q for q in parse_px(c.get("px")) if q[2] != "-"]
    if not pts:
        return CLAWD_BOX
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def to_box(cells, box, dy=0):
    """小克身上的东西（衣服、对讲机）挪到别的形象身上：按两个人的大小拉伸"""
    x0, y0, x1, y1 = CLAWD_BOX
    bx0, by0, bx1, by1 = box
    sx, sy = (bx1 - bx0) / (x1 - x0), (by1 - by0) / (y1 - y0)
    return [(k, bx0 + (x - x0) * sx, by0 + (y - y0) * sy + dy, w * sx, h * sy, c) for k, x, y, w, h, c in cells]


def pose_props(st, box):
    """没自己改过的姿势：配上小道具（都是一格一格的，画板里能接着改）"""
    bx0, by0, bx1, by1 = box
    g = []
    P = lambda x, y, c: g.append(("r", x, y, 1, 1, c))
    if st == "urgent":       # 举红牌子、冒汗
        for x in range(bx1, bx1 + 7):
            for y in range(by0 - 10, by0 - 4):
                P(x, y, "#e2412b")
        for y in (by0 - 9, by0 - 8, by0 - 7):
            P(bx1 + 3, y, "#ffffff")
        P(bx1 + 3, by0 - 5, "#ffffff")
        for y in range(by0 - 4, by0 + 2):
            P(bx1 + 3, y, INK)
        P(bx0 - 2, by0, "#7fd8e8"); P(bx0 - 3, by0 + 1, "#7fd8e8")
    elif st == "cheer":      # 两边冒星星
        for cx, cy in ((bx0 - 4, by0 - 3), (bx1 + 3, by0 - 1)):
            for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
                P(cx + dx, cy + dy, "#f5c400")
    elif st == "relaxed":    # 旁边一杯茶
        for x in range(bx1 + 1, bx1 + 4):
            for y in range(by1 - 3, by1 - 1):
                P(x, y, "#ffffff")
        P(bx1 + 4, by1 - 3, "#ffffff")
        P(bx1 + 1, by1 - 5, "#bdbeb8"); P(bx1 + 3, by1 - 6, "#bdbeb8")
    elif st == "sleep":      # 冒 Z
        V, x, y = "#7b5cff", bx1 + 1, by0 - 4
        for i in range(4):
            P(x + i, y, V); P(x + i, y + 3, V)
        P(x + 2, y + 1, V); P(x + 1, y + 2, V)
    return g


def char_cells(c, L, st, parts):
    """画一个自己的形象（跟 clawd() 返回一样的格子）"""
    g = [("r", 0, 0, 0, 0, t) for t in TONES]  # 占位：前 5 格在小克身上是签名，这里画成看不见的
    own = (c.get("poses") or {}).get(st)
    box = char_box(c)
    dy = 0 if own else POSE_DY.get(st, 0)
    main, want = str(c.get("color") or "").lower(), str(L.get("color") or "").lower()
    for x, y, col in parse_px(own or c.get("px")):
        col = "-" if col == "-" else "#" + col.lstrip("#")
        if main and want and want != main and col.lower() == main:
            col = want  # 换颜色：把主色换成选的颜色
        g.append(("r", x, y + dy, 1, 1, col))
    # 衣服：小克穿着会多出来的那些格子，按大小挪到这个形象身上
    from collections import Counter
    dressed = {**L, "char": "clawd", "build": "normal"}
    naked = {**dressed, "ears": "none", "tail": "none", "hold": "none", "hat": "none", "face": "none", "body": "none", "scarf": "none"}
    left = Counter(clawd(naked, "busy", parts, [])[5:])
    acc = []
    for cell in clawd(dressed, "busy", parts, [])[5:]:
        if left[cell] > 0:
            left[cell] -= 1
        else:
            acc.append(cell)
    g += to_box(acc, box, dy)
    if not own:
        g += [(k, x, y + dy, w, h, cc) for k, x, y, w, h, cc in pose_props(st, box)]
    return g


def clawd(look, st, parts, chars=None):
    """返回要画的格子：("r", x, y, w, h, 颜色) 实心；("o", x, y, w, h, 颜色) 只描边。坐标同 SVG viewBox -8 -12 40 34。"""
    L = norm_look(look)
    c = find_char(L, chars)
    if c:
        return char_cells(c, L, st, parts)
    B = L["color"]
    HI, DK, CR, TIP, CAT, PK = shade(B, .28), INK, "#fff3e0", shade(B, -.45), "#2a2438", "#ffb6d5"
    g = []
    P = lambda x, y, w, h, c: g.append(("r", x, y, w, h, c))
    dy = 3 if st == "relaxed" else 4 if st == "sleep" else 0
    for i, c in enumerate(TONES):  # 衬底的 5 格（马上被身子盖住）
        P(6 + i * 2, 8 + dy, 1, 1, c)

    def custom(pid, oy):
        p = next((q for q in parts if "u:" + str(q.get("id")) == pid), None)
        if not p: return
        for item in str(p.get("px", "")).split(";"):
            try:
                x, y, c = item.split(",")
                P(float(x), float(y) + oy, 1, 1, "-" if c.strip() == "-" else "#" + c.strip())
            except ValueError:
                pass

    if L["tail"] == "fox":
        P(-4, 7+dy, 4, 6, B); P(-6, 5+dy, 4, 4, B); P(-7, 3+dy, 3, 3, CR); P(-6, 2+dy, 2, 1, CR); P(-1, 11+dy, 2, 3, B)
    if L["tail"] == "cat":
        P(-1, 11+dy, 2, 2, B); P(-3, 9+dy, 2, 2, B); P(-4, 6+dy, 2, 3, B); P(-3, 5+dy, 2, 1, B)
    if L["tail"] == "bunny":
        P(-2, 11+dy, 3, 3, "#fff"); P(-1, 10+dy, 1, 1, "#fff")
    if L["tail"].startswith("u:"): custom(L["tail"], dy)
    if L["body"] == "cape":
        P(2, 3+dy, 18, 12, "#e2412b"); P(1, 13+dy, 20, 2, "#c23421")
    if st == "relaxed": P(3, 16, 5, 2, B); P(14, 16, 5, 2, B)
    elif st == "sleep": P(5, 16, 12, 2, B)
    else:
        for x in (5, 8, 12, 15): P(x, 14, 2, 5, B)
    P(4, 2+dy, 14, 10 if st == "sleep" else 12, B); P(4, 2+dy, 14, 2, HI)
    ear = {"fox": [(5, -3, 1, 1, TIP), (4, -2, 3, 1, B), (4, -1, 4, 1, B), (4, 0, 5, 2, B), (5, -1, 1, 1, CR), (5, 0, 2, 1, CR)],
           "cat": [(5, -2, 1, 1, B), (4, -1, 3, 1, B), (4, 0, 4, 2, B), (5, 0, 2, 1, PK)],
           "bunny": [(5, -7, 3, 9, B), (6, -6, 1, 6, PK)], "bear": [(3, -1, 4, 3, B), (4, 0, 2, 1, TIP)]}.get(L["ears"], [])
    for x, y, w, h, c in ear:
        P(x, y+dy, w, h, c); P(22-x-w, y+dy, w, h, c)
    if L["ears"].startswith("u:"): custom(L["ears"], dy)
    ey = 5 + dy
    if st == "sleep": P(6, ey+3, 3, 1, DK); P(13, ey+3, 3, 1, DK)
    elif st in ("relaxed", "cheer"):
        for bx in (6, 13): P(bx, ey+2, 1, 1, DK); P(bx+1, ey+1, 1, 1, DK); P(bx+2, ey+2, 1, 1, DK)
    elif st == "urgent": P(7, ey-1, 2, 5, DK); P(13, ey-1, 2, 5, DK)
    else: P(7, ey, 2, 4, DK); P(13, ey, 2, 4, DK)

    f = L["face"]
    if f == "glasses":
        g.append(("o", 6, ey-.5, 4, 5, DK)); g.append(("o", 12, ey-.5, 4, 5, DK)); P(10, ey+1, 2, .7, DK)
    if f == "shades":
        P(6, ey, 4, 3, DK); P(12, ey, 4, 3, DK); P(10, ey+1, 2, 1, DK); P(7, ey, 1, 1, "#6d6d68"); P(13, ey, 1, 1, "#6d6d68")
    if f == "blush": P(4, ey+4, 2, 1, "#ff8fc2"); P(16, ey+4, 2, 1, "#ff8fc2")
    if f == "band": P(14, ey-3, 4, 1, "#f2c49b"); P(15, ey-3, 1, 1, "#d9a37a")
    if f.startswith("u:"): custom(f, dy)
    bd = L["body"]
    if bd == "overalls":
        P(4, 10+dy, 14, 4, "#4f7fd9"); P(6, 6+dy, 2, 4, "#4f7fd9"); P(14, 6+dy, 2, 4, "#4f7fd9"); P(6, 10+dy, 1, 1, "#ffe14a"); P(15, 10+dy, 1, 1, "#ffe14a")
    if bd == "apron": P(6, 8+dy, 10, 6, "#fff"); P(6, 8+dy, 10, 1, PK); P(10, 11+dy, 2, 2, PK)
    if bd == "cape": P(5, 8+dy, 12, 1, "#ffe14a")
    if bd == "bowtie": P(7, 9+dy, 3, 2, "#e2412b"); P(12, 9+dy, 3, 2, "#e2412b"); P(10, 9+dy, 2, 2, "#a82a1b")
    if bd.startswith("u:"): custom(bd, dy)
    if L["scarf"] and L["scarf"] != "none": P(4, 9+dy, 14, 2, L["scarf"]); P(15, 11+dy, 3, 3, L["scarf"])

    hold = L["hold"]

    def item_at(x, y, mood):
        if hold == "cat":
            P(x, y, 6, 4, CAT); P(x, y-1, 1, 1, CAT); P(x+5, y-1, 1, 1, CAT); P(x, y+4, 6, 2, CAT); P(x+6, y+4, 2, 1, CAT)
            if mood == "sleep": P(x+1, y+2, 1, 1, "#ff8fc2"); P(x+4, y+2, 1, 1, "#ff8fc2")
            else: P(x+1, y+1, 1, 1, "#ff8fc2"); P(x+4, y+1, 1, 1, "#ff8fc2"); P(x+2, y+2, 2, 1, "#4a3f5c")
            if mood == "urgent": P(x-1, y-1, 1, 2, CAT); P(x+6, y-1, 1, 2, CAT); P(x+2, y-2, 2, 1, CAT)
        elif hold == "fish":
            P(x-1, y+1, 7, 3, "#9fb3c8"); P(x+6, y, 2, 5, "#9fb3c8"); P(x, y+2, 1, 1, DK); P(x+2, y+1, 3, 1, "#c3d2e0")
        elif hold == "tea":
            P(x+1, y, 4, 6, "#f4e3c3"); P(x+1, y, 4, 1, "#fff"); P(x+3, y-3, 1, 4, "#ff8fc2"); P(x+1, y+4, 4, 1, "#5b3a29"); P(x+2, y+5, 1, 1, "#5b3a29")
        elif hold.startswith("u:"):
            custom(hold, y - 10)

    holding = hold != "none"
    if st == "cheer":
        P(1, -2, 3, 5, B); P(18, -2, 3, 5, B); item_at(8, -8, "cheer"); P(3, -6, 4, 3, B); P(15, -6, 4, 3, B)
        P(-3, -9, 1, 3, "#f5c400"); P(-4, -8, 3, 1, "#f5c400"); P(25, -6, 1, 3, "#f5c400"); P(24, -5, 3, 1, "#f5c400")
    elif st == "urgent":
        item_at(8, 10, "urgent")
        if holding: P(4, 11, 3, 3, B)
        else: P(1, 7, 3, 4, B)
        P(18, 3, 3, 5, B); P(21, -2, 1, 8, DK); P(17, -11, 9, 8, "#e2412b"); P(21, -10, 1, 4, "#fff"); P(21, -5, 1, 1, "#fff"); P(19, 1, 3, 3, B)
        P(1, 0, 1, 2, "#7fd8e8"); P(0, 2, 1, 1, "#7fd8e8")
    else:
        item_at(8, 10 + dy - (1 if st == "sleep" else 0), st)
        if holding: P(4, 11+dy, 3, 3, B); P(15, 11+dy, 3, 3, B)
        else: P(1, 7+dy, 3, 4, B); P(18, 7+dy, 3, 4, B)

    h = L["hat"]
    Y = lambda n: n + dy
    if h == "hard": P(6, Y(-1), 10, 3, "#ffe14a"); P(5, Y(1), 12, 1, DK); P(10, Y(-2), 2, 1, "#ffe14a")
    if h == "beret": P(7, Y(-1), 8, 2, "#ff8fc2"); P(6, Y(0), 10, 2, "#ff8fc2"); P(10, Y(-2), 2, 1, "#7b5cff")
    if h == "crown": P(7, Y(-1), 8, 2, "#f5c400"); P(7, Y(-3), 2, 2, "#f5c400"); P(10, Y(-4), 2, 3, "#f5c400"); P(13, Y(-3), 2, 2, "#f5c400"); P(10, Y(0), 2, 1, "#e2412b")
    if h == "chef": P(7, Y(-5), 8, 4, "#fff"); P(6, Y(-6), 4, 2, "#fff"); P(12, Y(-6), 4, 2, "#fff"); P(6, Y(-1), 10, 2, "#fff"); P(6, Y(0), 10, 1, "#d8d8d0")
    if h == "witch": P(10, Y(-8), 2, 2, "#6b4bd6"); P(9, Y(-6), 4, 2, "#6b4bd6"); P(8, Y(-4), 6, 2, "#6b4bd6"); P(7, Y(-2), 8, 2, "#6b4bd6"); P(4, Y(0), 14, 1, "#4a32a8"); P(10, Y(-4), 2, 1, "#ffe14a")
    if h == "straw": P(6, Y(-2), 10, 3, "#f2d58a"); P(6, Y(0), 10, 1, "#e2412b"); P(2, Y(1), 18, 1, "#e3c06b")
    if h == "santa": P(7, Y(-2), 8, 3, "#e2412b"); P(12, Y(-4), 3, 2, "#e2412b"); P(15, Y(-5), 2, 2, "#fff"); P(6, Y(0), 10, 2, "#fff")
    if h == "bow": P(7, Y(-1), 3, 3, "#ff6fae"); P(12, Y(-1), 3, 3, "#ff6fae"); P(10, Y(0), 2, 1, "#d94a8c")
    if h == "phones": P(4, Y(-1), 14, 1, DK); P(4, Y(-1), 1, 4, DK); P(17, Y(-1), 1, 4, DK); P(2, Y(3), 3, 4, "#3fc7c7"); P(17, Y(3), 3, 4, "#3fc7c7")
    if h == "flower": P(14, Y(-1), 3, 3, "#ff8fc2"); P(13, Y(0), 1, 1, "#ff8fc2"); P(17, Y(0), 1, 1, "#ff8fc2"); P(15, Y(0), 1, 1, "#ffe14a")
    if h.startswith("u:"): custom(h, dy)
    if st == "relaxed" and hold != "tea":
        P(20, 15, 4, 3, "#fff"); P(24, 16, 1, 1, "#fff"); P(21, 12, 1, 2, "#bdbeb8"); P(23, 11, 1, 2, "#bdbeb8")
    if st == "sleep":  # 网页里是文字 Z，这里用像素画，透明窗口里文字边缘会发花
        V = "#7b5cff"
        P(20, -3, 5, 1, V); P(23, -2, 1, 1, V); P(22, -1, 1, 1, V); P(21, 0, 1, 1, V); P(20, 1, 5, 1, V)
        P(26, -8, 3, 1, V); P(27, -7, 1, 1, V); P(26, -6, 3, 1, V)
    return g


# ---------- 窗口 ----------

class Pet:
    def __init__(self):
        self.status = {**DEFAULT_STATUS, **read_json(STATUS, {})}
        if not os.path.exists(STATUS):
            write_json(STATUS, self.status)
        self.mtime = self._mtime()
        self.settings = {**DEFAULT_SETTINGS, **read_json(SETTINGS, {})}
        self.bob = 0
        self.hop_until = 0      # 点一下跳起来
        self.egg = []           # 连点气泡的时间（彩蛋）
        self.drag = None
        self.click_job = None   # 单击要等一下，看是不是双击
        self.double = False
        self.long_job = None    # 长按 = 按住说话（克讲机联动）
        self.long = False
        self.notice_id = (read_json(NOTICE, {}) or {}).get("id")
        self.pose_info = {}
        self.todo = None        # 脚下那条：现在点着的对话还欠着的备忘 {"key", "items"}（克讲机联动）
        self.strip_note = ("", 0)  # 脚下那条临时放克讲机的通知：(话, 到几点)
        self.say_tmp = ("", 0)     # 上面气泡临时说一句（换好啦、嘿！），几秒后变回来
        self.memo_cache = (0, [])  # talkie.json 的改动时间, 备忘
        self.app_seen = {}      # 应用的对话记录文件 → (改动时间, 对话编号, 最后点进的时间)
        self.app_top = None     # 现在点着的是哪个对话
        self.remind_until = 0
        self.wb_busy = False    # 正在开工作台
        self.bubble_box = None
        self.preview = None     # 衣柜里鼠标放上去试穿 / 试看：{"look": …, "state": …}
        self.line_key, self.line_pick = None, ""
        self.wardrobe = None
        self.talkie_check = 0
        self.set_mt = 0
        try:
            self.set_mt = os.path.getmtime(SETTINGS)
        except OSError:
            pass
        if not self.status.get("persona"):
            self.status["persona"] = {"key": random.choice(list(PERSONAS)), "by": "builtin"}
            write_json(STATUS, self.status)
        self.write_card()

        self.root = tk.Tk()
        self.root.title(APP)
        self.root.overrideredirect(True)
        self.root.config(bg=KEY)
        self.root.wm_attributes("-transparentcolor", KEY)
        self.root.wm_attributes("-topmost", self.settings["topmost"])
        try:
            self.root.iconbitmap(os.path.join(HERE, "clawd.ico"))
        except tk.TclError:
            pass
        self.canvas = tk.Canvas(self.root, bg=KEY, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double)
        self.canvas.bind("<Button-3>", self.on_menu)

        self.layout()
        x, y = self.settings["x"], self.settings["y"]
        if x is None or y is None:
            x = self.root.winfo_screenwidth() - self.w - 40
            y = self.root.winfo_screenheight() - self.h - 80
        elif not self.settings.get("head"):  # 新版头顶多留了空：窗口变高了，往上挪一次，脚还在原来的地方
            y -= HEAD * self.s
            self.settings["head"] = 1
        self.root.geometry(f"+{int(x)}+{int(y)}")
        self.draw()
        self.root.after(1000, self.poll)
        self.root.after(600, self.tick)
        self.root.after(60000, self.rotate_tick)

    # 名片：告诉别的程序（工作台、你的 AI）桌宠装在哪、怎么让它变状态
    def write_card(self):
        try:
            os.makedirs(CARDS, exist_ok=True)
            write_json(PET_CARD, {"app": "clawd-pet", "version": VERSION, "dir": HERE, "status": STATUS,
                                  "cmd": f'python "{os.path.join(HERE, "pet.py")}"', "at": int(time.time())})
        except OSError:
            pass

    def talkie_path(self):
        for p in (self.settings.get("talkiePath"), (read_json(TALKIE_CARD, {}) or {}).get("path")):
            if p and os.path.exists(p):
                return p
        return ""

    def talkie_on(self):
        return bool(self.settings.get("linkTalkie")) and bool(self.talkie_path())

    def claude_on(self):
        """按你点着的 Claude 对话提醒备忘（配克讲机用）"""
        return bool(self.settings.get("linkClaude"))

    def wb_on(self):
        return bool(self.settings.get("linkWorkbench"))

    # 尺寸
    def layout(self):
        self.s = SIZES.get(self.settings["size"], 4)
        self.font = tkfont.Font(family=FONT[0], size=FONT[1])
        self.bh = self.font.metrics("linespace") * 2 + 26  # 气泡区固定放两行，说的话变长也不会把小克挤动
        self.w = max(54 * self.s, 240)
        self.feet = self.bh + (34 + HEAD) * self.s + 6
        self.th = self.font.metrics("linespace") + 16      # 脚下那条：克讲机的待办 / 通知（没有就是空的、透明）
        self.h = self.feet + self.th
        self.canvas.config(width=self.w, height=self.h)
        self.root.geometry(f"{self.w}x{self.h}")

    # 状态会过期（2026-10-12：之前停在「去登录小红书」一整天没变）：
    # 欢呼只开心 15 分钟；着急 / 忙碌超过 STALE_H 小时没人更新，就当没事了变悠闲；半夜不着急就睡觉
    STALE_H = 3

    def custom_state(self, key=None):
        """自己加的状态：status.json 里 states = [{id, name, pose, lines, px, by}]，state 写成 c:<id>"""
        key = key if key is not None else self.raw_state()
        if key == "c:__preview" and self.preview and self.preview.get("cs"):
            return self.preview["cs"]
        if not str(key).startswith("c:"):
            return None
        return next((q for q in self.status.get("states") or [] if isinstance(q, dict) and "c:" + str(q.get("id")) == key), None)

    def raw_state(self):
        if self.preview and self.preview.get("cs"):
            return "c:__preview"
        if self.preview and self.preview.get("state"):
            return self.preview["state"]
        return self.status.get("state", "busy")

    def stale(self):
        age = time.time() - (self.mtime or 0)
        st = self.pose_of(self.status.get("state", "busy"))
        return (st == "cheer" and age > 15 * 60) or (st in ("urgent", "busy") and age > self.STALE_H * 3600)

    def pose_of(self, key):
        """一个状态用 5 种姿势里的哪一种画"""
        if key in STATES:
            return key
        cs = self.custom_state(key)
        return cs.get("pose") if cs and cs.get("pose") in STATES else "busy"

    def state(self):
        if self.preview and (self.preview.get("state") or self.preview.get("cs")):  # 衣柜里试看，不管过期和半夜
            return self.pose_of(self.raw_state())
        st = self.pose_of(self.status.get("state", "busy"))
        if self.stale():
            st = "relaxed"
        if st != "urgent" and 1 <= time.localtime().tm_hour < 7:
            st = "sleep"
        return st

    def all_states(self, with_hidden=False):
        """能挑的状态：(key, 名字, 姿势, 自己加的那条或 None)；藏起来的内置状态不算"""
        hid = set((self.status.get("hidden") or {}).get("state") or [])
        out = [(k, STATE_ZH[k], k, None) for k in STATES if with_hidden or k not in hid]
        for q in self.status.get("states") or []:
            if isinstance(q, dict) and q.get("id"):
                out.append(("c:" + str(q["id"]), str(q.get("name") or "?"), self.pose_of("c:" + str(q["id"])), q))
        return out

    def lines_for(self, key):
        """这个状态说的话：自己写的 > 自己加的状态带的 > 默认"""
        mine = (self.status.get("lines") or {}).get(key) or []
        cs = self.custom_state(key)
        pool = [x for x in mine if str(x).strip()] or [x for x in (cs or {}).get("lines") or [] if str(x).strip()]
        if not pool:
            return LINES.get(self.pose_of(key), "")
        if self.line_key != (key, self.mtime):  # 状态变了才换一句，别每次重画都换
            self.line_key, self.line_pick = (key, self.mtime), random.choice(pool)
        return self.line_pick

    def set_random_state(self):
        key, name, __, __ = random.choice(self.all_states())
        self.set_status(state=key, say="")
        self.say_once(_("⚄ {0}！").format(name))

    def draw(self):
        c, s = self.canvas, self.s
        c.delete("all")
        st = self.state()
        ox = (self.w - 40 * s) / 2 + 8 * s  # viewBox 从 -8 开始
        oy0 = self.bh + (12 + HEAD) * s + 6
        oy = oy0 - self.bob * s - (3 * s if time.time() < self.hop_until else 0)
        look = (self.preview or {}).get("look") or self.status.get("look")
        global CHARS
        CHARS = self.status.get("chars") or []
        chars = (self.preview or {}).get("chars") or CHARS
        cells = clawd(look, st, (self.preview or {}).get("parts") or self.status.get("parts") or [], chars)
        cs = self.custom_state()
        if cs and st == self.pose_of(self.raw_state()) and (cs.get("char") or "clawd") == norm_look(look)["char"]:  # 自己加的状态：小道具、擦掉 / 重画的地方（按这个姿势里的真实位置）
            overlay(cs.get("px"), cells)
        sc = self.sc = build_scale(look, (self.preview or {}).get("builds") or self.status.get("builds"))
        cells = fit(cells, sc)
        self.tip_y = oy0 + (19 + (-12 - 19) * sc[1]) * s - 3  # 气泡尖尖停在这里（跟体型走，不跟着晃）
        for kind, x, y, w, h, col in cells:
            x0, y0 = ox + x * s, oy + y * s
            col = KEY if col == "-" else col
            if kind == "r":
                c.create_rectangle(x0, y0, x0 + w * s, y0 + h * s, fill=col, width=0)
            else:
                c.create_rectangle(x0, y0, x0 + w * s, y0 + h * s, outline=col, width=max(1, round(.7 * s)))
        if self.talkie_on() and self.settings.get("walkie", True):  # 手里的迷你克讲机（克讲机联动打开时才画）
            box = [1e9, 1e9, -1e9, -1e9]
            wc = [("r", *q) for q in self.walkie_cells()]
            ch = find_char(look, chars)
            if ch:  # 别的形象：对讲机按它的大小挪到手边
                wc = to_box(wc, char_box(ch), 0 if (ch.get("poses") or {}).get(st) else POSE_DY.get(st, 0))
            for __, x, y, w, h, col in fit(wc, sc):
                x0, y0 = ox + x * s, oy + y * s
                c.create_rectangle(x0, y0, x0 + w * s, y0 + h * s, fill=col, width=0)
                box = [min(box[0], x0), min(box[1], y0), max(box[2], x0 + w * s), max(box[3], y0 + h * s)]
            self.walkie_box = (box[0] - 3, box[1] - 3, box[2] + 3, box[3] + 3)  # 宽一点好点中
        else:
            self.walkie_box = None
        if self.settings["bubble"]:
            # 上面气泡 = 小克自己说的，跟工作台（今日小克终未地）定的一样；临时一句（换好啦）几秒后变回来
            raw = self.raw_state()
            say = self.status.get("say") if not self.preview and self.pose_of(raw) == st and not self.stale() else ""
            if time.time() < self.say_tmp[1]:
                say = self.say_tmp[0]
            self.draw_bubble(say or (self.lines_for(raw) if self.pose_of(raw) == st else LINES[st]), st)
        else:
            self.bubble_box = None
        self.draw_strip()

    def draw_strip(self):
        """脚下那条（用户 2026-10-15：小克说的话分两个——上面是它自己说的，下面写待办）：
        现在点着的对话还欠着的备忘；克讲机有通知时临时先放通知。点一下 = 打开克讲机"""
        c = self.canvas
        self.strip_top = 1e9
        if not self.talkie_on():
            return
        note = self.strip_note[0] if time.time() < self.strip_note[1] else ""
        if note:
            text, tail, led, bg = note, " ▸", YELLOW, PAPER
        elif self.todo:
            items = self.todo["items"]
            text, tail, led, bg = items[0], (_("  共{0}件 ▸").format(len(items)) if len(items) > 1 else " ▸"), "#e2412b", YELLOW
        else:
            return
        top = self.feet + 2
        text = " ".join(str(text).split())
        t = c.create_text(0, 0, text=text + tail, font=self.font, fill=INK, anchor="nw")
        cut = text
        while cut and c.bbox(t)[2] - c.bbox(t)[0] > self.w - 44:  # 一行放不下就截前面的话，件数留着
            cut = cut[:-1]
            c.itemconfig(t, text=cut + "…" + tail)
        x0, y0, x1, y1 = c.bbox(t)
        bw, bh = x1 - x0 + 30, self.th - 4
        left = (self.w - bw) / 2
        k = 5  # 切角，跟上面气泡一样
        c.create_polygon([left + k, top, left + bw, top, left + bw, top + bh - k, left + bw - k, top + bh, left, top + bh, left, top + k],
                         fill=bg, outline=INK, width=2)
        c.create_rectangle(left + 8, top + bh / 2 - 3, left + 14, top + bh / 2 + 3, fill=led, outline=INK, width=1)  # 小灯：红 = 待办
        c.coords(t, left + 20, top + (bh - (y1 - y0)) / 2)
        c.tag_raise(t)
        self.strip_top = top

    def pose(self):
        """克讲机在干嘛：听回答 / 你在说话 / 在画图；提醒备忘时举到耳边"""
        if time.time() < self.remind_until:
            return "listen"
        p = self.pose_info.get("pose") or "idle"
        if p != "idle" and time.time() > (self.pose_info.get("until") or 0):
            return "idle"
        return p if p in POSES else "idle"

    def walkie_cells(self):
        """迷你对讲机的格子：描边、机身、屏、喇叭、侧键、天线。
        颜色默认跟着小克自己的颜色配（用户 2026-10-15：“颜色跟这个小人不太符合……根据不同的小克变成适配的颜色”）：
        机身 = 小克的颜色压深，屏 = 奶油色，按键 = 小克的颜色提亮；菜单里也能换回「跟克讲机机身」"""
        if self.settings.get("walkieColor", "pet") == "pet":
            B = norm_look(self.status.get("look"))["color"]
            body, screen, accent = shade(B, -0.42), "#fff3e0", shade(B, 0.35)
        else:
            cols = self.pose_info.get("colors") or {}
            body, screen, accent = cols.get("body") or "#2f4fd8", cols.get("screen") or "#f2d04a", cols.get("accent") or "#e2412b"
        pose = self.pose()
        P = POSES[pose]
        x, y = P["at"]
        blink = self.bob == 1
        hand = shade(norm_look(self.status.get("look"))["color"], -0.18)
        g = [(x + 2.6, y - 3, 0.9, 3.2, INK),                                   # 天线
             (x + 2.4, y - 3.6, 1.3, 1.1, accent if (pose == "listen" and blink) else INK),
             (x - 0.5, y - 0.5, 5, 8, INK), (x, y, 4, 7, body),                # 描边 + 机身
             (x + 0.6, y + 0.7, 2.8, 2, screen),                               # 屏
             (x + 0.8, y + 3.4, 2.4, 0.45, INK), (x + 0.8, y + 4.3, 2.4, 0.45, INK),  # 喇叭孔
             (x + 1.5, y + 5.4, 1, 0.8, accent),                               # 按键
             (x - 1, y + 2.2, 0.6, 1.8, accent)]                               # 侧面通话键
        # 手：抬起来的胳膊 / 捏着对讲机的小爪子（比身子深一点，看得出来）
        if pose == "listen":
            g += [(18, 2, 2, 5, norm_look(self.status.get("look"))["color"]), (x - 0.6, y + 3, 1.6, 2, hand)]
        elif pose == "talk":
            g += [(x - 0.6, y + 3.5, 1.4, 2, hand)]
        elif pose == "paint":
            g += [(x - 0.8, y + 4, 1.4, 1.8, hand), (x + 3.4, y + 4, 1.4, 1.8, hand)]
        if P.get("paint"):  # 屏上冒小色块，一闪一闪
            for i, col in enumerate(("#e2412b", "#f5c400", "#2f4fd8")):
                if blink or i != 1:
                    g.append((x + 0.9 + i * 0.8, y + 1.1 + (i % 2) * 0.6, 0.7, 0.7, col))
        wv = P.get("waves")
        if wv:  # 声波：一闪一闪的两道
            wx, wy = wv
            k = 1 if blink else 0
            if pose == "listen":
                g += [(wx, wy + 1, 0.6, 2, accent), (wx + 1.2 + k * 0.3, wy, 0.6, 4, accent)]
            else:  # 说话：三道横的，一伸一缩
                g += [(wx, wy, 1.5 + k, 0.6, accent), (wx, wy + 1.5, 2.5 + k, 0.6, accent), (wx, wy + 3, 1.5 + k, 0.6, accent)]
        return g

    def check_talkie(self):
        """读克讲机的动作；你刚在哪个对话发了消息，就看那个对话还欠着哪些备忘"""
        info = read_json(POSE, None)
        if isinstance(info, dict):
            self.pose_info = info
        # 你点着哪个对话（读应用的记录，每秒一次，只重读改过的文件，一次几毫秒）
        top = self.app_focus() if self.claude_on() else None
        if top:
            ids = top[0]
        else:  # 读不到应用记录：退回看插件写的“你刚在哪个对话发了消息”
            f = read_json(FOCUS, None)
            ids = (f["sid"],) if isinstance(f, dict) and f.get("sid") else ()
        switched = bool(ids) and self.app_top is not None and ids[0] != self.app_top  # 桌宠刚开时不算“点进”
        if ids:
            self.app_top = ids[0]
        self.remind_for(ids, switched)

    def app_focus(self):
        """最后点进的那个对话：(它的所有对话编号, 点进的时间 ms)"""
        import glob
        best = None
        for root in APP_SESSIONS:
            files = glob.glob(os.path.join(root, "*", "*", "local_*.json"))
            if not files:
                continue
            for f in files:
                try:
                    mt = os.path.getmtime(f)
                except OSError:
                    continue
                old = self.app_seen.get(f)
                if not old or old[0] != mt:
                    d = read_json(f, None)
                    if not isinstance(d, dict):
                        continue
                    ids = tuple(i for i in [d.get("cliSessionId")] + list(d.get("priorCliSessionIds") or []) if i)  # 重开过的对话编号会换，旧的也认
                    old = self.app_seen[f] = (mt, ids, d.get("lastFocusedAt") or 0)
                if old[1] and (not best or old[2] > best[1]):
                    best = (old[1], old[2])
            break
        return best

    def all_memos(self):
        try:
            mt = os.path.getmtime(TALKIE_STATE)
        except OSError:
            return []
        if mt != self.memo_cache[0]:
            st = read_json(TALKIE_STATE, None)
            if isinstance(st, dict):
                self.memo_cache = (mt, st.get("memos") or [])
        return self.memo_cache[1]

    def remind_for(self, ids, switched=False):
        """脚下那条一直跟着现在点着的对话（备忘改了、做完了，一秒内跟着变）；
        刚点进一个欠着备忘的对话，小克还把对讲机举到耳边几秒"""
        memos = [m for m in self.all_memos() if not m.get("done") and (m.get("link") or {}).get("sid") in ids]
        memos.sort(key=lambda m: -(m.get("at") or 0))
        todo = {"key": ids[0], "items": [m.get("text", "") for m in memos]} if memos else None
        if todo != self.todo:
            self.todo = todo
            self.draw()
        if todo and switched:
            self.remind_until = time.time() + 8

    def draw_bubble(self, text, st):
        c = self.canvas
        full = text = " ".join(str(text).split())
        t = c.create_text(0, 0, text=text, font=self.font, fill=INK, width=self.w - 28, anchor="nw")
        while text and c.bbox(t)[3] - c.bbox(t)[1] > self.font.metrics("linespace") * 2 + 2:  # 超过两行就截掉
            text = text[:-1]
            c.itemconfig(t, text=text + "…")
        if text != full and not text:
            c.itemconfig(t, text="…")
        x0, y0, x1, y1 = c.bbox(t)
        bw, bh = x1 - x0 + 20, y1 - y0 + 10
        left = (self.w - bw) / 2
        top = max(2, getattr(self, "tip_y", self.bh) - 7 - bh)
        k = 6  # 切角，跟工作台的工业风一样
        pts = [left + k, top, left + bw, top, left + bw, top + bh - k, left + bw - k, top + bh,
               self.w / 2 + 5, top + bh, self.w / 2, top + bh + 7, self.w / 2 - 5, top + bh,
               left, top + bh, left, top + k]
        c.create_polygon(pts, fill=PAPER, outline=INK, width=2)
        self.bubble_box = (left, top, left + bw, top + bh)
        c.create_rectangle(left + 3, top + 3, left + 9, top + 5, fill="#e2412b" if st == "urgent" else YELLOW, width=0)
        c.coords(t, left + 10, top + 5)
        c.tag_raise(t)

    # 轻轻上下晃：忙 / 急快一点，睡觉慢一点
    def tick(self):
        st = self.state()
        self.bob = 0 if self.bob or st == "sleep" else 1
        self.draw()
        self.root.after({"urgent": 250, "cheer": 300, "busy": 600, "relaxed": 900, "sleep": 1500}[st], self.tick)

    # 每秒看一下 status.json 改了没
    def _mtime(self):
        try:
            return os.path.getmtime(STATUS)
        except OSError:
            return 0

    def poll(self):
        m = self._mtime()
        if m != self.mtime:
            self.mtime = m
            data = read_json(STATUS, None)
            if isinstance(data, dict):  # 写到一半读不出来就先不管，下次再读
                self.status = {**DEFAULT_STATUS, **data}
                self.draw()
        try:
            smt = os.path.getmtime(SETTINGS)
        except OSError:
            smt = self.set_mt
        if smt != self.set_mt:  # pet.py 或你的 AI 改了设置
            self.set_mt = smt
            new = read_json(SETTINGS, None)
            if isinstance(new, dict):
                size = self.settings.get("size")
                self.settings.update({k: v for k, v in new.items() if k not in ("x", "y")})
                if self.settings.get("size") != size:
                    self.set_size(self.settings["size"])
                self.draw()
        if time.time() - self.talkie_check > 10:
            self.talkie_check = time.time()
            if not self.settings.get("workbenchSeen") and self.workbench()[0]:
                self.settings["workbenchSeen"] = True
                self.settings["linkWorkbench"] = True
                self.save_settings()
                self.say_once(_("发现工作台啦～右键就能打开它"))
            if not self.settings.get("talkieSeen") and self.talkie_path():
                self.settings["talkieSeen"] = True
                self.settings["linkTalkie"] = True
                self.save_settings()
                self.say_once(_("发现克讲机啦，我拿上了～（右键 → 联动能关）"))
        if self.talkie_on():
            self.check_talkie()
            # 克讲机收起时有新回答 / 新生图请求：脚下冒一条
            n = read_json(NOTICE, None)
            if isinstance(n, dict) and n.get("id") and n.get("id") != self.notice_id:
                self.notice_id = n["id"]
                if time.time() - (n.get("at") or 0) < 60:
                    self.strip_note = (str(n.get("text") or ""), time.time() + 30)
                    self.draw()
        elif self.todo:
            self.todo = None
        self.root.after(1000, self.poll)

    def set_status(self, **kv):
        data = read_json(STATUS, None)
        data = data if isinstance(data, dict) else dict(self.status)
        data.update(kv)
        write_json(STATUS, data)
        self.status = {**DEFAULT_STATUS, **data}
        self.mtime = self._mtime()
        self.draw()

    def save_settings(self):
        self.settings["x"], self.settings["y"] = self.root.winfo_x(), self.root.winfo_y()
        self.settings.setdefault("_o", base64.b64encode("made by 喵喵".encode("utf-8")).decode())
        write_json(SETTINGS, self.settings)
        try:
            self.set_mt = os.path.getmtime(SETTINGS)
        except OSError:
            pass

    # 点一下 / 拖动
    def on_press(self, e):
        self.drag = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y(), False)
        self.long = False
        self.long_job = self.root.after(450, self.on_long) if self.talkie_on() else None

    def on_drag(self, e):
        if not self.drag:
            return
        sx, sy, wx, wy, moved = self.drag
        dx, dy = e.x_root - sx, e.y_root - sy
        if moved or abs(dx) + abs(dy) > 4:
            self.drag = (sx, sy, wx, wy, True)
            self.root.geometry(f"+{wx + dx}+{wy + dy}")
            if self.long_job:  # 拖起来了就不算长按
                self.root.after_cancel(self.long_job)
                self.long_job = None

    def on_long(self):
        """长按小克 = 按住说话：叫出对讲机并开始语音，松手停"""
        self.long_job = None
        if self.drag and not self.drag[4]:
            self.long = True
            self.say_once(_("在听～说吧"))
            self.open_talkie("start")

    def on_release(self, e):
        if self.long_job:
            self.root.after_cancel(self.long_job)
            self.long_job = None
        if self.long:
            self.long = False
            self.drag = None
            self.open_talkie("stop")
            return
        on_strip = (self.drag and not self.drag[4] and e.y >= getattr(self, "strip_top", 1e9)
                    and (self.todo or time.time() < self.strip_note[1]))
        if on_strip:  # 点脚下那条：打开克讲机（待办 → 记档）
            note = time.time() < self.strip_note[1]
            self.strip_note = ("", 0)
            self.open_talkie(mode=None if note else "memo")
            self.drag = None
            self.draw()
            return
        bb = self.bubble_box
        if self.drag and not self.drag[4] and bb and bb[0] <= e.x <= bb[2] and bb[1] <= e.y <= bb[3]:
            self.drag = None
            self.poke_bubble()
            return
        wb = getattr(self, "walkie_box", None)
        if self.drag and not self.drag[4] and wb and wb[0] <= e.x <= wb[2] and wb[1] <= e.y <= wb[3] and not self.double:
            # 单击手里的迷你对讲机 = 打开克讲机（单击小克身上别处还是原来的：打开 Claude / 工作台）
            self.drag = None
            self.open_talkie()
            return
        if self.double:  # 双击的第二下松手，不算单击
            self.double = False
        elif self.drag and self.drag[4]:
            self.save_settings()
        elif self.drag:
            self.click_job = self.root.after(280, self.on_click)
        self.drag = None

    def on_click(self):
        self.click_job = None
        how = self.settings.get("click", "claude")
        if how == "workbench" and self.wb_on():
            self.open_workbench()
        elif how == "claude":
            self.open_claude()
        elif how == "app" and self.settings.get("clickTarget"):
            self.open_target(self.settings["clickTarget"])
        else:
            self.poke()

    def on_double(self, e):
        if self.click_job:
            self.root.after_cancel(self.click_job)
            self.click_job = None
        self.double = True
        if self.talkie_on():
            self.open_talkie()
        else:  # 没接克讲机：双击就当点一下
            self.on_click()

    def persona(self):
        """现在的性格：{"name", "desc"}（内置的按现在的语言显示）"""
        p = self.status.get("persona") or {}
        if p.get("key") in PERSONAS:
            name, desc = PERSONAS[p["key"]]
            return {"name": name, "desc": desc, "key": p["key"], "by": "builtin"}
        return {"name": str(p.get("name") or ""), "desc": str(p.get("desc") or ""), "by": p.get("by") or "me"}

    def poke(self, text=None):
        """点小克：跳一下，说句话（按性格写过的话优先）"""
        self.hop_until = time.time() + 0.35
        mine = [x for x in (self.status.get("lines") or {}).get("poke") or [] if str(x).strip()]
        self.say_once(text or random.choice(mine or POKE))
        self.root.after(380, self.draw)

    def poke_bubble(self):
        """连点头顶气泡 7 下（3 秒内）：作者签名"""
        now = time.time()
        self.egg = [t for t in self.egg if now - t < 3] + [now]
        if len(self.egg) >= 7:
            self.egg = []
            self.poke("made by 喵喵 · Miaomiao 原创")

    # 克讲机：已经开着它自己会挪到小克旁边，没开就开一个
    def open_talkie(self, talk=None, mode=None):
        path = self.talkie_path()
        if not path:
            self.say_once(_("找不到克讲机～"))
            return
        exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        r = self.root
        near = [str(v) for v in (r.winfo_x(), r.winfo_y(), r.winfo_width(), r.winfo_height())]
        subprocess.Popen([exe if os.path.exists(exe) else "pythonw", path, "--near", *near] + (["--talk", talk] if talk else []) + (["--mode", mode] if mode else []))

    # 工作台在哪：先看自己设的位置，再看工作台留的名片
    def workbench(self):
        card = read_json(WB_CARD, {}) or {}
        mine = self.settings.get("workbenchDir") or ""
        d = mine or card.get("dir") or ""
        if d and not os.path.exists(os.path.join(d, "server.py")):
            d = ""
        url = card.get("url") if card.get("url") and (not mine or os.path.normcase(card.get("dir") or "") == os.path.normcase(mine)) else ""
        return d, url or self.status.get("url") or WB_URL

    @staticmethod
    def alive(url):
        try:
            with urllib.request.urlopen(url, timeout=0.6) as r:
                return r.status < 500
        except Exception:
            return False

    def open_workbench(self):
        """工作台开着 → 打开它；装了但没开 → 先把它开起来；没装 → 小克只是跳一下"""
        if self.wb_busy:
            return
        self.wb_busy = True
        self.wb_step = None     # 后台只往这里放进度，界面由主线程每 0.1 秒来看（tkinter 不能从别的线程改）
        d, url = self.workbench()

        def job():
            ok = self.alive(url)
            if not ok and d:
                self.wb_step = "starting"
                try:
                    py = os.path.join(os.path.dirname(sys.executable), "python.exe")
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 7  # 最小化：那个黑窗口就是工作台，关掉 = 工作台关了
                    subprocess.Popen([py if os.path.exists(py) else "python", "server.py"], cwd=d,
                                     creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=si)
                    for __ in range(30):
                        time.sleep(0.4)
                        if self.alive(url):
                            ok = True
                            break
                except OSError:
                    pass
            self.wb_step = ("done", ok, bool(d), url)

        threading.Thread(target=job, daemon=True).start()
        self.root.after(100, self.wait_workbench)

    def wait_workbench(self, told=False):
        step = self.wb_step
        if isinstance(step, tuple):
            self.after_workbench(*step[1:])
            return
        if step == "starting" and not told:
            self.say_once(_("帮你把工作台开起来～"))
            told = True
        self.root.after(100, lambda: self.wait_workbench(told))

    def after_workbench(self, ok, installed, url):
        self.wb_busy = False
        if ok:
            self.open_app_window(url)
        elif installed:
            self.poke(_("工作台没开起来～去它的文件夹双击 start.bat 试试"))
        elif not self.settings.get("hinted"):
            self.set_setting("hinted", True)
            self.poke(_("还没找到工作台～右键「联动」可以设置"))
        else:
            self.poke()

    # 工作台用单独的窗口打开（浏览器的「应用」模式：没有标签页和地址栏）；先用 Edge，没有再用 Chrome，都没有才普通打开
    def open_app_window(self, url):
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        for exe in (os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"), os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"), os.path.join(local, "Google", "Chrome", "Application", "chrome.exe")):
            if os.path.exists(exe):
                try:
                    subprocess.Popen([exe, "--app=" + url, "--window-size=1280,880"])
                    return
                except OSError:
                    pass
        webbrowser.open(url)

    def open_claude(self):
        try:
            os.startfile("claude://")  # Claude 桌面版自己登记的链接，会把它叫到前面
        except OSError:
            self.say_once(_("没找到 Claude 应用～"))

    def open_target(self, t):
        """点一下打开你自己选的程序 / 网址"""
        try:
            if t.startswith(("http://", "https://")):
                webbrowser.open(t)
            else:
                os.startfile(t)
        except OSError:
            self.say_once(_("打不开它～右键「点一下打开」重新选一个"))

    def pick_target(self, kind):
        if kind == "url":
            from tkinter import simpledialog
            t = simpledialog.askstring(_("点一下打开哪个网址"), _("网址（http 开头）："), parent=self.root,
                                       initialvalue=self.settings.get("clickTarget") if str(self.settings.get("clickTarget")).startswith("http") else "https://")
            if not t or not t.startswith(("http://", "https://")):
                return
        else:
            t = filedialog.askopenfilename(title=_("点一下打开哪个程序？（Codex、别的 AI 应用、任何程序或快捷方式）"),
                                           filetypes=[(_("程序 / 快捷方式"), "*.exe *.lnk *.bat *.cmd *.url"), (_("全部"), "*.*")])
            if not t:
                return
            t = os.path.normpath(t)
        self.settings["clickTarget"] = t
        self.set_setting("click", "app")
        self.say_once(_("记住啦！点我就打开它"))

    def target_name(self):
        t = str(self.settings.get("clickTarget") or "")
        return (t if t.startswith("http") else os.path.splitext(os.path.basename(t))[0])[:24]

    def toggle_workbench(self):
        if self.wb_on():
            self.set_setting("linkWorkbench", False)
            if self.settings.get("click") == "workbench":
                self.set_setting("click", "claude")
            self.say_once(_("工作台断开啦"))
            return
        if not self.workbench()[0]:
            self.pick_workbench()
            return
        self.set_setting("linkWorkbench", True)
        self.say_once(_("工作台连上啦"))

    def toggle_talkie(self):
        if not self.talkie_on() and not self.talkie_path():
            self.say_once(_("还没找到克讲机～它是作者的另一个作品，GitHub 上还没有的话，过段时间就会发"))
            return
        self.toggle("linkTalkie")
        self.say_once(_("克讲机连上啦") if self.settings["linkTalkie"] else _("克讲机断开啦"))

    def pick_workbench(self):
        d = filedialog.askdirectory(title=_("工作台（今日小克终未地）装在哪个文件夹？"))
        if not d:
            return
        d = os.path.normpath(d)
        if os.path.exists(os.path.join(d, "server.py")):
            self.settings["workbenchDir"] = d
            self.set_setting("linkWorkbench", True)
            self.say_once(_("工作台连上啦"))
        else:
            self.say_once(_("这个文件夹里没有工作台～（要有 server.py）"))

    # 工作台衣柜里点「复制给桌宠」，再到这里粘贴：造型 + 自己画的部件 + 存的整体造型
    def paste_look(self):
        try:
            data = json.loads(self.root.clipboard_get())
        except (tk.TclError, ValueError):
            data = None
        if not isinstance(data, dict) or not data.get("clawdPet"):
            self.say_once(_("剪贴板里没有造型～先去工作台衣柜点「复制给桌宠」"))
            return
        pool = [q for q in data.get("pool") or [] if isinstance(q, dict) and q.get("look")][:12]
        if pool:  # 一群小克轮流来
            self.set_status(pool=pool, parts=data.get("parts") or [], say="")
            self.rotate_now()
            if not self.settings.get("rotate"):
                self.set_setting("rotate", 60)
            return
        self.set_status(look=data.get("look") or self.status["look"], parts=data.get("parts") or [], presets=data.get("presets") or [], pool=[], say="")
        self.say_once(_("换好啦！"))

    # 随机换一身：从衣柜里的整套（内置的 + 你自己存的）里挑一身，跟现在的不一样
    def random_look(self):
        hid = set((self.status.get("hidden") or {}).get("preset") or [])
        pool = [(_(n), l) for n, l in PRESETS.items() if n not in hid]
        pool += [(str(q.get("name") or "?"), q["look"]) for q in self.status.get("presets") or [] if isinstance(q, dict) and q.get("look")]
        cur = norm_look(self.status.get("look"))
        pool = [(n, l) for n, l in pool if norm_look(l) != cur] or pool
        if not pool:
            return
        name, look = random.choice(pool)
        self.set_status(look=dict(look))
        self.settings["rotAt"] = time.time()
        self.save_settings()
        self.say_once(_("换了一身：{0}").format(name))

    # 随机换成工作台里的小克：从工作台粘贴来的那一群里换一只（不耗 token，只是本地换造型）
    def rotate_now(self):
        pool = [q for q in self.status.get("pool") or [] if isinstance(q, dict) and q.get("look")]
        if not pool:
            self.say_once(_("还没有一群小克～先去工作台 ⚙ 选「桌宠随机换」再粘贴"))
            return
        cur = self.status.get("petName")
        pick = random.choice([q for q in pool if q.get("name") != cur] or pool)
        self.set_status(look=pick["look"], petName=pick.get("name") or "", say="")
        self.settings["rotAt"] = time.time()
        self.save_settings()
        self.say_once(_("换我来啦～我是{0}").format(pick.get('name') or '小克'))

    def rotate_tick(self):
        since = time.time() - (self.settings.get("rotAt") or 0)
        wb = self.settings.get("rotateWb") or 0
        mine = self.settings.get("rotate") or 0
        if wb and self.wb_on() and self.status.get("pool"):   # 连着工作台、选了换工作台里的小克：优先
            if since >= wb * 60:
                self.rotate_now()
        elif mine and not self.wb_on() and since >= mine * 60:
            self.random_look()
        self.root.after(60000, self.rotate_tick)

    def say_once(self, text):
        """上面气泡临时说一句，6 秒后变回工作台定的话（以前会一直盖着工作台的话）"""
        self.say_tmp = (text, time.time() + 6)
        self.draw()

    # 右键菜单
    def on_menu(self, e):
        m = tk.Menu(self.root, tearoff=0, font=FONT)
        d, __ = self.workbench()
        if self.wb_on():
            m.add_command(label=_("打开工作台"), command=self.open_workbench)
        if self.talkie_on():
            m.add_command(label=_("克讲机（双击小克也行，长按 = 按住说话）"), command=self.open_talkie)
        if self.wb_on() or self.talkie_on():
            m.add_separator()

        sm = tk.Menu(m, tearoff=0, font=FONT)
        cur = tk.StringVar(value=self.status.get("state", "busy"))
        for k, name, __, cs in self.all_states():
            sm.add_radiobutton(label=("✎ " if cs and cs.get("by") == "me" else "✨ " if cs and cs.get("by") == "ai" else _("克 ") if cs else "") + name,
                               variable=cur, value=k, command=lambda k=k: self.set_status(state=k, say=""))
        sm.add_separator()
        sm.add_command(label=_("⚄ 随机一个"), command=self.set_random_state)
        sm.add_command(label=_("＋ 加一个新状态 / 改说的话…"), command=lambda: self.open_wardrobe("state"))
        m.add_cascade(label=_("状态"), menu=sm)

        rc = tk.Menu(m, tearoff=0, font=FONT)
        rec = read_json(RECENT, [])
        items = [r for r in (rec if isinstance(rec, list) else []) if isinstance(r, dict)][-10:][::-1]
        for r in items:
            when = time.strftime("%m-%d %H:%M", time.localtime(r.get("at") or 0))
            who = f"{r.get('project')} · " if r.get("project") else ""
            rc.add_command(label=f"{when}  {STATE_ZH.get(r.get('state'), '')}  {who}{r.get('say') or ''}"[:60], state="disabled")
        if not items:
            rc.add_command(label=_("还没有：让你的 AI 用 pet.py 告诉我在做什么"), state="disabled")
        m.add_cascade(label=_("最近在做"), menu=rc)

        lm = tk.Menu(m, tearoff=0, font=FONT)
        if self.wb_on():
            lm.add_command(label=_("连着工作台：形象、衣服、性格都在工作台里改"), state="disabled")
            lm.add_command(label=_("打开工作台去换"), command=self.open_workbench)
        else:
            lm.add_command(label=_("换形象…（小克、自己画的、AI 画的）"), command=lambda: self.open_wardrobe("char"))
            lm.add_command(label=_("打开衣柜…（试穿、自己画、让 AI 做）"), command=lambda: self.open_wardrobe("look"))
            lm.add_command(label=_("性格…（{0}）").format(self.persona()["name"]), command=lambda: self.open_wardrobe("persona"))
            lm.add_separator()
        hid = set((self.status.get("hidden") or {}).get("preset") or []) if not self.wb_on() else set(PRESETS)
        for name, look in PRESETS.items():
            if name in hid:
                continue
            lm.add_command(label=_(name), command=lambda look=look: self.set_status(look=dict(look)))
        mine = [q for q in self.status.get("presets") or [] if isinstance(q, dict) and q.get("look")] if not self.wb_on() else []
        if mine:
            lm.add_separator()
            for q in mine:
                lm.add_command(label="✎ " + str(q.get("name") or "?"), command=lambda look=q["look"]: self.set_status(look=dict(look)))
        if not self.wb_on():
            lm.add_separator()
            lm.add_command(label=_("⚄ 随机换一身（从上面这些整套里挑）"), command=self.random_look)
            rl = tk.Menu(lm, tearoff=0, font=FONT)
            rot = tk.IntVar(value=self.settings.get("rotate") or 0)
            for k, v in ROTATE.items():
                rl.add_radiobutton(label=v, variable=rot, value=k, command=lambda k=k: self.set_setting("rotate", k))
            lm.add_cascade(label=_("定时随机换一身"), menu=rl)
        if self.wb_on():
            lm.add_separator()
            lm.add_command(label=_("粘贴工作台的造型"), command=self.paste_look)
            rm = tk.Menu(lm, tearoff=0, font=FONT)  # 换成工作台里别的小克（工作台 ⚙ 里选「桌宠随机换」再粘贴）
            rw = tk.IntVar(value=self.settings.get("rotateWb") or 0)
            for k, v in ROTATE.items():
                rm.add_radiobutton(label=v, variable=rw, value=k, command=lambda k=k: self.set_setting("rotateWb", k))
            rm.add_separator()
            rm.add_command(label=_("现在换一只"), command=self.rotate_now)
            lm.add_cascade(label=_("随机换成工作台里的小克"), menu=rm)
        m.add_cascade(label=_("造型"), menu=lm)

        zm = tk.Menu(m, tearoff=0, font=FONT)
        size = tk.StringVar(value=self.settings["size"])
        for k in SIZES:
            zm.add_radiobutton(label=_(k), variable=size, value=k, command=lambda k=k: self.set_size(k))
        m.add_cascade(label=_("大小"), menu=zm)

        cm = tk.Menu(m, tearoff=0, font=FONT)
        click = tk.StringVar(value=self.settings["click"])
        for k, v in CLICK.items():
            if k == "workbench" and not self.wb_on():
                continue
            cm.add_radiobutton(label=v, variable=click, value=k, command=lambda k=k: self.set_setting("click", k))
        if self.settings.get("clickTarget"):
            cm.add_radiobutton(label=_("别的：") + self.target_name(), variable=click, value="app", command=lambda: self.set_setting("click", "app"))
        cm.add_separator()
        cm.add_command(label=_("选一个别的程序…（Codex、别的 AI 应用……）"), command=lambda: self.pick_target("app"))
        cm.add_command(label=_("填一个网址…"), command=lambda: self.pick_target("url"))
        m.add_cascade(label=_("点一下打开"), menu=cm)

        km = tk.Menu(m, tearoff=0, font=FONT)  # 联动：开了才出现相关的东西；电脑上装了，第一次发现会自己开
        wv = tk.BooleanVar(value=self.wb_on())
        km.add_command(label=_("这两个都是作者的其他作品，装了会自己连上"), state="disabled")
        km.add_checkbutton(label=_("工作台（今日小克终未地）"), variable=wv, command=self.toggle_workbench)
        if self.wb_on():
            km.add_command(label=_("　 在：") + (d if d else _("还没找到")) + _("（点这里换）"), command=self.pick_workbench)
        km.add_separator()
        tv = tk.BooleanVar(value=self.talkie_on())
        km.add_checkbutton(label=_("克讲机（手里拿迷你对讲机，双击 / 长按叫它）"), variable=tv, command=self.toggle_talkie)
        if not self.wb_on() or not self.talkie_on():
            km.add_separator()
            km.add_command(label=_("去作者的 GitHub 找它们（还没有的话，过段时间就会发）"), command=lambda: webbrowser.open(AUTHOR_GITHUB))
        if self.talkie_on():
            km.add_command(label=(_("　 ✓ ") if self.settings.get("walkie", True) else _("　 　 ")) + _("手里拿着迷你对讲机"),
                           command=lambda: (self.set_setting("walkie", not self.settings.get("walkie", True)), self.draw()))
            pet_col = self.settings.get("walkieColor", "pet") == "pet"
            km.add_command(label=_("　 　 迷你对讲机颜色：") + (_("跟小克（点一下换成跟克讲机机身）") if pet_col else _("跟克讲机机身（点一下换成跟小克）")),
                           command=lambda: (self.set_setting("walkieColor", "talkie" if pet_col else "pet"), self.draw()))
            cv = tk.BooleanVar(value=self.claude_on())
            km.add_checkbutton(label=_("　 按你点着的 Claude 对话提醒备忘"), variable=cv, command=lambda: self.toggle("linkClaude"))
        m.add_cascade(label=_("联动"), menu=km)

        bub = tk.BooleanVar(value=self.settings["bubble"])
        m.add_checkbutton(label=_("显示说话气泡"), variable=bub, command=lambda: self.toggle("bubble"))
        top = tk.BooleanVar(value=self.settings["topmost"])
        m.add_checkbutton(label=_("一直在最上面"), variable=top, command=lambda: self.toggle("topmost"))
        auto = tk.BooleanVar(value=os.path.exists(STARTUP_BAT))
        m.add_checkbutton(label=_("开机自动出现"), variable=auto, command=self.toggle_startup)
        lg = tk.Menu(m, tearoff=0, font=FONT)
        lv = tk.StringVar(value=self.settings.get("lang") or "auto")
        lg.add_radiobutton(label=_("跟着 Windows") + "（" + lang.LANGS[lang.system_lang()] + "）", variable=lv, value="auto",
                           command=lambda: self.set_lang("auto"))
        for code, name in lang.LANGS.items():
            lg.add_radiobutton(label=name, variable=lv, value=code, command=lambda code=code: self.set_lang(code))
        m.add_cascade(label=_("语言") + (" · Language" if lang.CUR != "en" else ""), menu=lg)
        m.add_separator()

        am = tk.Menu(m, tearoff=0, font=FONT)
        am.add_command(label=_("{0} v{1} · 原创 Miaomiao").format(APP, VERSION), state="disabled")
        am.add_command(label=_("许可 CC BY-NC-SA 4.0：可以改，不准商用（点开看）"), command=lambda: webbrowser.open(LICENSE_URL))
        am.add_command(label=_("GitHub：Miaomiaomeowmeow/clawd-pet"), command=lambda: webbrowser.open(GITHUB))
        am.add_separator()
        am.add_command(label=_("打开状态文件"), command=lambda: subprocess.Popen(["notepad.exe", STATUS]))
        am.add_command(label=_("打开桌宠所在的文件夹"), command=lambda: os.startfile(HERE))
        m.add_cascade(label=_("关于"), menu=am)
        cm2 = tk.Menu(m, tearoff=0, font=FONT)  # 联系作者：作者在找工作，放显眼一点
        cm2.add_command(label=_("★ 作者在找工作！有工作机会请联系我"), state="disabled")
        cm2.add_command(label=_("LinkedIn 领英：Miaomiao Yang（点开）"), command=lambda: webbrowser.open(LINKEDIN))
        cm2.add_command(label=_("小红书：{0}（点一下复制）").format(XHS), command=self.copy_xhs)
        cm2.add_separator()
        cm2.add_command(label=_("作者的网站（简历 + 更多作品）") if WEBSITE else _("作者的网站：还在做，先关注领英，新作品会发在那"),
                        command=lambda: webbrowser.open(WEBSITE or LINKEDIN))
        cm2.add_command(label=_("作者的其他作品（GitHub）"), command=lambda: webbrowser.open(AUTHOR_GITHUB))
        m.add_cascade(label=_("联系作者 · 在找工作！"), menu=cm2)
        m.add_command(label=_("退出"), command=self.quit)
        m.tk_popup(e.x_root, e.y_root)

    def set_lang(self, code):
        """换语言：存好，重开一只新的（等这只关掉再开）"""
        if (self.settings.get("lang") or "auto") == code:
            return
        self.set_setting("lang", code)
        exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        subprocess.Popen([exe if os.path.exists(exe) else sys.executable, os.path.abspath(__file__), "--after", str(os.getpid())], cwd=HERE)
        self.quit()

    def copy_xhs(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(XHS)
        self.say_once(_("复制好啦，去小红书搜一下～"))

    def open_wardrobe(self, page="look"):
        import wardrobe  # 衣柜在单独的文件里（wardrobe.py）
        if self.wardrobe and self.wardrobe.alive():
            self.wardrobe.show(page)
        else:
            self.wardrobe = wardrobe.Wardrobe(self, page)

    def set_size(self, k):
        bottom = self.root.winfo_y() + self.h
        center = self.root.winfo_x() + self.w / 2
        self.settings["size"] = k
        self.layout()
        self.root.geometry(f"+{int(center - self.w / 2)}+{int(bottom - self.h)}")  # 脚的位置不变
        self.draw()
        self.root.after(50, self.save_settings)

    def set_setting(self, key, v):
        self.settings[key] = v
        self.save_settings()

    def toggle(self, key):
        self.settings[key] = not self.settings[key]
        if key == "topmost":
            self.root.wm_attributes("-topmost", self.settings["topmost"])
        self.draw()
        self.save_settings()

    def toggle_startup(self):
        if os.path.exists(STARTUP_BAT):
            os.remove(STARTUP_BAT)
        else:
            pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pyw):
                pyw = sys.executable
            with open(STARTUP_BAT, "w", encoding="mbcs", errors="replace") as f:
                f.write(f'@start "" "{pyw}" "{os.path.abspath(__file__)}"\r\n')

    def quit(self):
        self.save_settings()
        self.root.destroy()


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 高分屏上像素不糊
    except (AttributeError, OSError):
        pass
    if "--after" in sys.argv:  # 换语言重启：等旧的那只关掉
        try:
            old = int(sys.argv[sys.argv.index("--after") + 1])
            h = ctypes.windll.kernel32.OpenProcess(0x00100000, False, old)  # SYNCHRONIZE
            if h:
                ctypes.windll.kernel32.WaitForSingleObject(h, 8000)
                ctypes.windll.kernel32.CloseHandle(h)
        except (ValueError, IndexError, OSError):
            pass
    # 同一个文件夹的桌宠只开一只（重复双击不会冒出第二只）
    import zlib
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex = k32.CreateMutexW(None, False, "ClawdPet-%08x" % zlib.crc32(HERE.lower().encode("utf-8")))
    if ctypes.get_last_error() == 183:  # 已经有一只了
        sys.exit(0)
    Pet().root.mainloop()
