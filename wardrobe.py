# 小克桌宠 ClawdPet 的衣柜：贴在小克旁边的一个竖窗，两页——外表（整套 / 耳朵 / 尾巴 / 手上 / 头上 / 脸上 / 身上 / 颜色）、状态。
# 原创：Miaomiao（GitHub: Miaomiaomeowmeow）· CC BY-NC-SA 4.0 · https://github.com/Miaomiaomeowmeow/clawd-pet
#
# 跟「今日小克终未地」工作台的衣柜一个套路：
# - 每个选项是一张小预览；鼠标放上去 = 桌面上的小克先试穿，移开就换回来；点一下才真的穿上；现在穿着的高亮
# - 最后一格「＋ 新的」：〔小克〕小克自己挑 3 个 / ✨ AI 照你说的做 3 个 / ✍ 自己画（自己写）
#   AI 借电脑上已经登录的 Codex 或 Claude Code（不用 Key，慢几秒到几十秒）；都没有就复制一句话给你自己的 AI
# - 「整理」：内置的藏起来（能恢复），自己做的、AI 做的真删
# 数据都存在 status.json（parts 衣服、presets 整套、colors 颜色、states 状态、lines 说的话、hidden 藏起来的），pet.py 也能加。

import glob
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import colorchooser

import lang
from lang import _

TONES = ("#6d6164", "#652062", "#7920e5", "#96b5e5", "#96b500")  # 描边备用色，和桌宠里的一样
CATS = [("set", _("整套")), ("build", _("体型")), ("ears", _("耳朵")), ("tail", _("尾巴")), ("hold", _("手上")),
        ("hat", _("头上")), ("face", _("脸上")), ("body", _("身上")), ("color", _("颜色"))]
CAT_ZH = dict(CATS)
BUILTIN = {
    "ears": [("none", _("不要")), ("fox", _("狐狸耳")), ("cat", _("猫耳")), ("bunny", _("兔耳")), ("bear", _("熊耳"))],
    "tail": [("none", _("不要")), ("fox", _("狐狸尾")), ("cat", _("猫尾")), ("bunny", _("兔尾"))],
    "hold": [("none", _("空手")), ("cat", _("抱猫")), ("fish", _("小鱼")), ("tea", _("奶茶"))],
    "hat": [("none", _("不戴")), ("hard", _("安全帽")), ("beret", _("贝雷帽")), ("crown", _("小皇冠")), ("chef", _("厨师帽")), ("witch", _("魔法帽")),
            ("straw", _("草帽")), ("santa", _("圣诞帽")), ("bow", _("蝴蝶结")), ("phones", _("耳机")), ("flower", _("小花"))],
    "face": [("none", _("不要")), ("glasses", _("眼镜")), ("shades", _("墨镜")), ("blush", _("腮红")), ("band", _("创可贴"))],
    "body": [("none", _("不要")), ("overalls", _("背带裤")), ("apron", _("围裙")), ("cape", _("披风")), ("bowtie", _("领结")),
             ("scarf:#ffe14a", _("黄围巾")), ("scarf:#e2412b", _("红围巾"))],
    "color": [("#d97757", _("原色")), ("#9b7bff", _("紫")), ("#3fc7c7", _("水青")), ("#ff8fc2", _("粉")), ("#5a4a7a", _("夜紫")),
              ("#7bd389", _("薄荷")), ("#f5c400", _("柠檬")), ("#4f7fd9", _("蓝"))],
}
# 画衣服时每个部位大概在哪（坐标同 clawd()：x -8～31、y -12～21；站着时身子 x 4～17、y 2～13）
AREA = {
    "hat": "头顶：x 4～17，y -8～1（可以盖住头顶一点）",
    "ears": "耳朵：头顶两边各一只，x 3～8 和 13～18，y -7～1，左右对称",
    "tail": "尾巴：身子左边，x -7～3，y 3～13",
    "face": "脸上：x 5～16，y 4～10（别把眼睛 x 7～8、13～14、y 5～8 全盖住）",
    "body": "身上：x 4～17，y 8～13",
    "hold": "手上抱着的东西：身子前面，x 6～15，y 9～15",
    "prop": "状态的小道具：头顶上方或右上角，x 14～28，y -11～1",
}
# 画板上用虚线框标出“大概画在这里”：(x0, y0, x1, y1)
AREA_BOX = {"hat": (4, -8, 17, 1), "ears": (3, -7, 18, 1), "tail": (-7, 3, 3, 13), "face": (5, 4, 16, 10),
            "body": (4, 8, 17, 13), "hold": (6, 9, 15, 15)}
PALETTE = ["#151513", "#ffffff", "#e2412b", "#ff8fc2", "#f5c400", "#ffe14a", "#7bd389", "#3fc7c7",
           "#4f7fd9", "#9b7bff", "#5b3a29", "#9fb3c8"]
PAPER, INK, YELLOW, LINE, MUTED, BG = "#ffffff", "#151513", "#ffe14a", "#d8d4cb", "#8a857a", "#f6f1e7"


# ---------- 借电脑上的 AI（Codex / Claude Code） ----------

def find_cli(tool):
    exe = shutil.which(tool)
    if exe:
        return exe
    if tool == "codex" and os.name == "nt":  # Codex 桌面版自带的命令行
        hits = sorted(glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "OpenAI", "Codex", "bin", "*", "codex.exe")),
                      key=os.path.getmtime, reverse=True)
        if hits:
            return hits[0]
    return ""


def which_ai():
    for t in ("codex", "claude"):
        if find_cli(t):
            return t
    return ""


def ask_ai(prompt, timeout=180):
    """借 Codex 或 Claude Code 问一句，在空的临时文件夹里只读地跑；返回回答文字。出错抛 RuntimeError（话是给人看的）"""
    tool = which_ai()
    if not tool:
        raise RuntimeError(_("电脑上没找到 Codex 或 Claude Code"))
    exe = find_cli(tool)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with tempfile.TemporaryDirectory(prefix="clawdpet-ai-") as work:
        if tool == "codex":
            last = os.path.join(work, "answer.txt")
            cmd = [exe, "exec", "--skip-git-repo-check", "-s", "read-only", "-C", work, "-o", last,
                   "-c", "model_reasoning_effort=low", "-"]  # 少想一点：画小东西不用想太久
        else:
            cmd = [exe, "-p", "--output-format", "text"]
        try:
            r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               cwd=work, timeout=timeout, creationflags=flags)
            if tool == "codex" and r.returncode != 0 and "reasoning" in (r.stderr or ""):
                cmd.remove("-c"); cmd.remove("model_reasoning_effort=low")
                r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   cwd=work, timeout=timeout, creationflags=flags)
        except subprocess.TimeoutExpired:
            raise RuntimeError(_("{0} 想太久了（超过 {1} 秒），再试一次？").format(tool, timeout))
        out = r.stdout
        if tool == "codex" and os.path.exists(last):
            out = open(last, encoding="utf-8", errors="replace").read()
        if r.returncode != 0 and not (out or "").strip():
            err = (r.stderr or "").strip()[-160:]
            if re.search(r"log ?in|auth|登录", err, re.I):
                raise RuntimeError(_("{0} 好像没登录：先在它那边登录一次").format(tool))
            raise RuntimeError(_("{0} 出错了：{1}").format(tool, err or '没说原因'))
        return out


def parse_items(text):
    """从回答里抠出 {"items": [...]}"""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise RuntimeError(_("AI 没按格式回答，再试一次？"))
    try:
        items = json.loads(m.group(0)).get("items") or []
    except ValueError:
        raise RuntimeError(_("AI 回答的格式坏了，再试一次？"))
    return [q for q in items if isinstance(q, dict)][:3]


def clean_px(px):
    out = []
    for item in str(px or "").split(";"):
        try:
            x, y, c = [t.strip() for t in item.split(",")]
            x, y, c = int(float(x)), int(float(y)), c.lstrip("#").lower()
            if c != "-":
                int(c, 16)
            if (c == "-" or (len(c) == 6 and c != "ff00fe")) and -8 <= x <= 31 and -12 <= y <= 21:
                out.append(f"{x},{y},{c}")
        except ValueError:
            pass
    return ";".join(out[:200])


GRID_HELP = ("坐标格：x 从 -8 到 31，y 从 -12 到 21，一格一个像素。小克站着时：身子是 x 4～17、y 2～13 的方块"
             "（眼睛在 x 7～8 和 13～14、y 5～8），四条腿在 y 14～18。\n"
             "px 写成 'x,y,颜色;x,y,颜色'，颜色是 6 位十六进制、不带 #，别用 ff00fe；颜色写 - 表示把小克那一格擦掉（可以用来改眼睛、改表情）；"
             "20～80 个点，2～4 种颜色，轮廓清楚，像素风。")


# ---------- 衣柜窗口 ----------

class Wardrobe:
    TONES_SET = set(TONES)

    def __init__(self, pet, page="look"):
        self.pet = pet
        self.cp = sys.modules[pet.__class__.__module__]   # 桌宠本体（画小克的 clawd() 等）
        self.k = pet.root.winfo_fpixels("1i") / 96        # 高分屏放大
        self.page, self.cat = page, "set"
        self.tidy = False
        self.new_open = False
        self.cands = []          # 小克 / AI 做出来、还没留下的 3 个
        self.job = None          # 正在借 AI：{"result": None / ("ok", items) / ("err", 话)}
        self.sel_state = None    # 状态页：正在改哪个状态说的话
        self.font = (lang.font(), 10)
        self.small = (lang.font(), 9)
        self.bold = (lang.font(), 10, "bold")

        w = self.win = tk.Toplevel(pet.root)
        w.title(_("小克的衣柜"))
        w.configure(bg=BG)
        w.attributes("-toolwindow", True)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", self.close)
        self.W, self.H = int(276 * self.k), int(520 * self.k)
        self.TW, self.TH = int(72 * self.k), int(78 * self.k)   # 每格一样大
        self.place()
        self.build()
        self.show(page)

    # 位置：贴在小克旁边（左边放得下放左边，不然放右边），底边跟小克的脚齐
    def place(self):
        r = self.pet.root
        px, py = r.winfo_x(), r.winfo_y()
        x = px - self.W - 6 if px - self.W - 6 > 0 else px + r.winfo_width() + 6
        y = max(0, min(py + self.pet.feet - self.H, r.winfo_screenheight() - self.H - 60))
        self.win.geometry(f"{self.W}x{self.H}+{int(x)}+{int(y)}")

    def alive(self):
        try:
            return bool(self.win.winfo_exists())
        except tk.TclError:
            return False

    def close(self):
        self.pet.preview = None
        self.pet.draw()
        self.win.destroy()

    # ---- 数据 ----
    def st(self):
        return self.pet.status

    def lst(self, key):
        return [q for q in self.st().get(key) or []]

    def hidden(self, key):
        return list((self.st().get("hidden") or {}).get(key) or [])

    def set_hidden(self, key, vals):
        h = dict(self.st().get("hidden") or {})
        h[key] = vals
        self.pet.set_status(hidden=h)

    def look(self):
        return self.cp.norm_look(self.st().get("look"))

    # ---- 框架：上面两页切换，中间格子（能滚），下面「新的」和整理 ----
    def build(self):
        w, f = self.win, self.font
        top = tk.Frame(w, bg=BG)
        top.pack(fill="x", padx=int(8 * self.k), pady=(int(8 * self.k), 0))
        self.page_btn = {}
        for key, name in (("char", _("形象")), ("look", _("外表")), ("state", _("状态")), ("persona", _("性格"))):
            b = tk.Label(top, text=name, font=self.bold, bg=BG, fg=INK, padx=int(6 * self.k), pady=int(3 * self.k), cursor="hand2")
            b.pack(side="left")
            b.bind("<Button-1>", lambda e, key=key: self.show(key))
            self.page_btn[key] = b
        self.cat_bar = tk.Frame(w, bg=BG)
        self.cat_bar.pack(fill="x", padx=int(8 * self.k), pady=(int(6 * self.k), 0))
        self.cat_btn = {}
        for i, (key, name) in enumerate(CATS):
            b = tk.Label(self.cat_bar, text=name, font=self.small, bg=PAPER, fg=INK, relief="solid", bd=1,
                         padx=int(4 * self.k), pady=int(1 * self.k), cursor="hand2")
            b.grid(row=i // 5, column=i % 5, sticky="ew", padx=1, pady=1)
            b.bind("<Button-1>", lambda e, key=key: self.show_cat(key))
            self.cat_btn[key] = b
        for c in range(5):
            self.cat_bar.columnconfigure(c, weight=1, uniform="cat")

        # 格子区：能滚
        self.foot = tk.Frame(w, bg=BG)
        self.foot.pack(fill="x", side="bottom", padx=int(8 * self.k), pady=(0, int(8 * self.k)))
        mid = self.mid = tk.Frame(w, bg=BG)
        mid.pack(fill="both", expand=True, padx=int(8 * self.k), pady=int(6 * self.k))
        self.cv = tk.Canvas(mid, bg=BG, highlightthickness=0, height=int(60 * self.k))
        sb = tk.Scrollbar(mid, orient="vertical", command=self.cv.yview, width=int(10 * self.k))
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.grid = tk.Frame(self.cv, bg=BG)
        self.cv.create_window((0, 0), window=self.grid, anchor="nw")
        self.grid.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        w.bind("<MouseWheel>", lambda e: self.cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))

        # 「新的」：点最后一格才展开（放在下面一行的上面）
        self.new_box = tk.Frame(w, bg=PAPER, relief="solid", bd=1)
        for c in range(3):
            self.grid.columnconfigure(c, uniform="tile")

    def show(self, page):
        self.page = page
        self.new_open, self.cands, self.tidy = False, [], False
        for key, b in self.page_btn.items():
            b.configure(bg=YELLOW if key == page else BG, relief="solid" if key == page else "flat", bd=1)
        if page == "look" and not self.pet.wb_on():
            self.cat_bar.pack(fill="x", padx=int(8 * self.k), pady=(int(6 * self.k), 0), before=self.foot)
        else:
            self.cat_bar.pack_forget()
        self.refresh()
        self.win.deiconify()
        self.win.lift()

    def kind(self):
        """现在这一页 / 这一类是什么：char 形象、state 状态，或者外表里的某一类"""
        return self.page if self.page in ("char", "state", "persona") else self.cat

    def plain(self, char, color):
        """只看形象本身（不穿衣服）的样子"""
        return {"char": char, "color": color, "ears": "none", "tail": "none", "hold": "none", "hat": "none",
                "face": "none", "body": "none", "scarf": "none", "build": "normal"}

    def show_cat(self, key):
        self.cat, self.new_open, self.cands, self.tidy = key, False, [], False
        self.refresh()

    # ---- 一类里有哪些选项：{key, name, look, state, by, builtin, why} ----
    def items(self):
        L = self.look()
        out = []
        if self.page == "char":
            out.append({"key": "clawd", "name": _("小克"), "show": self.plain("clawd", "#d97757"),
                        "look": {**L, "char": "clawd", "color": "#d97757"}, "builtin": True, "on": L["char"] == "clawd"})
            for q in self.lst("chars"):
                if isinstance(q, dict) and q.get("id"):
                    v, col = "u:" + str(q["id"]), q.get("color") or L["color"]
                    out.append({"key": v, "name": str(q.get("name") or "?"), "show": self.plain(v, col),
                                "look": {**L, "char": v, "color": col}, "by": q.get("by") or "me", "on": L["char"] == v})
            return out
        if self.page == "state":
            hid = set(self.hidden("state"))
            for key, name, pose, cs in self.pet.all_states(with_hidden=True):
                if key in hid:
                    continue
                out.append({"key": key, "name": name, "state": key, "by": (cs or {}).get("by"), "builtin": cs is None,
                            "on": self.st().get("state") == key})
            return out
        cat = self.cat
        if cat == "set":
            hid = set(self.hidden("preset"))
            for name, look in self.cp.PRESETS.items():
                if name not in hid:
                    out.append({"key": name, "name": _(name), "look": dict(look), "builtin": True})
            for q in self.lst("presets"):
                if isinstance(q, dict) and q.get("look"):
                    out.append({"key": "p:" + str(q.get("name")), "name": str(q.get("name")), "look": dict(q["look"]), "by": q.get("by") or "me"})
            for it in out:
                it["on"] = self.cp.norm_look(it["look"]) == L
            return out
        if cat == "build":
            hid = set(self.hidden("build"))
            for v, name in self.cp.BUILDS.items():
                if v not in hid:
                    out.append({"key": v, "name": name, "look": {**L, "build": v}, "builtin": True, "on": L["build"] == v})
            for q in self.lst("builds"):
                if isinstance(q, dict) and q.get("id"):
                    v = "u:" + str(q["id"])
                    out.append({"key": v, "name": str(q.get("name") or "?"), "look": {**L, "build": v}, "by": q.get("by") or "me", "on": L["build"] == v})
            return out
        if cat == "color":
            hid = set(self.hidden("color"))
            for c, name in BUILTIN["color"]:
                if c not in hid:
                    out.append({"key": c, "name": name, "look": {**L, "color": c}, "builtin": True})
            for q in self.lst("colors"):
                c = q if isinstance(q, str) else (q or {}).get("color")
                if c:
                    out.append({"key": c, "name": (q.get("name") if isinstance(q, dict) else "") or c, "look": {**L, "color": c},
                                "by": (q.get("by") if isinstance(q, dict) else "") or "me"})
            for it in out:
                it["on"] = L["color"].lower() == it["key"].lower()
            return out
        hid = set(self.hidden(cat))
        for v, name in BUILTIN[cat]:
            if v in hid:
                continue
            if v.startswith("scarf:"):
                look = {**L, "scarf": v[6:]}
                on = L["scarf"] == v[6:]
            else:
                look = {**L, cat: v}
                if cat == "body" and v == "none":
                    look["scarf"] = "none"
                on = L[cat] == v and not (cat == "body" and v == "none" and L["scarf"] not in ("none", ""))
            out.append({"key": v, "name": name, "look": look, "builtin": True, "on": on})
        for q in self.lst("parts"):
            if isinstance(q, dict) and q.get("slot") == cat:
                v = "u:" + str(q.get("id"))
                out.append({"key": v, "name": str(q.get("name") or "?"), "look": {**L, cat: v}, "by": q.get("by") or "me", "on": L[cat] == v})
        return out

    # ---- 画一张小预览 ----
    def mini(self, parent, look=None, state=None, size=58, bg=PAPER, cs=None):
        k = self.k
        W, H = int(size * k), int(size * 0.86 * k)
        c = tk.Canvas(parent, width=W, height=H, bg=bg, highlightthickness=0)
        s = W / 40
        key = state or "busy"
        cs = cs or (self.pet.custom_state(key) if state else None)
        pose = cs.get("pose") if cs and cs.get("pose") in self.cp.STATES else self.pet.pose_of(key)
        look = look or self.st().get("look")
        cells = self.cp.clawd(look, pose, self.mini_parts(), self.mini_chars())
        if cs and (cs.get("char") or "clawd") == self.cp.norm_look(look)["char"]:
            self.cp.overlay(cs.get("px"), cells)
        sc = self.cp.build_scale(look, self.mini_builds())
        cells = self.cp.fit(cells, sc)
        # 体型页按真实比例画（大只真的大一点）；别的页缩到装得下
        s = s / 1.3 if (self.page == "look" and self.cat == "build") else s / max(1, sc[0], sc[1])
        for kind, x, y, w, h, col in cells:
            col = bg if col == "-" else col
            x0, y0 = (x + 8) * s + (W - 40 * s) / 2, (y + 12) * s + (H - 34 * s)
            if kind == "r":
                c.create_rectangle(x0, y0, x0 + w * s, y0 + h * s, fill=col, width=0)
            else:
                c.create_rectangle(x0, y0, x0 + w * s, y0 + h * s, outline=col, width=1)
        return c

    def badge(self, c, by):
        """角上的小标：✎ 你做的 · ✨ AI 做的 · 小克的脸 = 小克挑的；内置的不标"""
        if by == "me":
            c.create_text(4, 2, text="✎", anchor="nw", font=self.small, fill=INK)
        elif by == "ai":
            c.create_text(4, 2, text="✨", anchor="nw", font=self.small, fill="#c58a00")
        elif by == "clawd":
            self.clawd_icon(c, 4, 4)

    def clawd_icon(self, c, x, y):
        k = max(1, round(1.4 * self.k))
        c.create_rectangle(x, y, x + 9 * k, y + 7 * k, fill="#d97757", width=0)
        c.create_rectangle(x + 2 * k, y + 2 * k, x + 3 * k, y + 5 * k, fill=INK, width=0)
        c.create_rectangle(x + 6 * k, y + 2 * k, x + 7 * k, y + 5 * k, fill=INK, width=0)

    # ---- 重画格子 ----
    def refresh(self):
        if self.pet.wb_on() or self.page == "persona":
            for ch in self.grid.winfo_children():
                ch.destroy()
            self.new_open = False
            self.build_new()
            for ch in self.foot.winfo_children():
                ch.destroy()
            self.cv.yview_moveto(0)
            (self.build_linked if self.pet.wb_on() else self.build_persona)()
            return
        for c in range(3):  # 性格页改过列的设置，换回一格一样宽
            self.grid.columnconfigure(c, weight=0, uniform="tile")
        for b in self.cat_btn.values():
            b.configure(bg=PAPER)
        if self.page == "look":
            self.cat_btn[self.cat].configure(bg=YELLOW)
        for ch in self.grid.winfo_children():
            ch.destroy()
        items = self.items()
        cols = 3
        for i, it in enumerate(items):
            self.tile(self.grid, it, i // cols, i % cols)
        n = len(items)
        W, H = self.TW + 2, self.TH + 2
        plus = tk.Canvas(self.grid, width=W, height=H, bg=YELLOW if self.new_open else BG, highlightthickness=0, cursor="hand2")
        plus.create_rectangle(2, 2, W - 2, H - 2, dash=(4, 3), outline=INK)
        plus.create_text(W / 2, H / 2, text=_("＋ 新的"), font=self.font, fill=INK)
        plus.grid(row=n // cols, column=n % cols, padx=int(3 * self.k), pady=int(3 * self.k), sticky="n")
        plus.bind("<Button-1>", lambda e: (self.toggle_new(), self.refresh_plus(plus)))
        self.cv.yview_moveto(0)
        self.build_new()
        self.build_foot()

    def build_linked(self):
        """连着工作台：形象、衣服、性格都跟工作台走，这里不改（不然改了还要再搬回工作台）"""
        g, k = self.grid, self.k
        self.cat_bar.pack_forget()
        tk.Label(g, text=_("连着工作台"), font=self.bold, bg=BG, fg=INK).grid(row=0, column=0, columnspan=3, sticky="w", pady=(int(4 * k), 2))
        tk.Label(g, text=_("小克的形象、衣服、性格都在工作台里改，桌宠跟着工作台走，这里就不改了，免得两边不一样。\n\n"
                           "换法：在工作台里右键小克 → 造型 →「复制给桌宠」，再回来右键这只小克 → 造型 →「粘贴工作台的造型」。\n\n"
                           "想要一只只在桌宠上用的小克？在工作台里新建一只「桌宠小克」，打扮好再复制过来。"),
                 font=self.small, bg=BG, fg=INK, wraplength=int(240 * k), justify="left").grid(row=1, column=0, columnspan=3, sticky="w")
        row = tk.Frame(g, bg=BG)
        row.grid(row=2, column=0, columnspan=3, sticky="w", pady=int(10 * k))
        tk.Button(row, text=_("打开工作台"), font=self.small, relief="solid", bd=1, bg=YELLOW, command=self.pet.open_workbench).pack(side="left")
        tk.Button(row, text=_("粘贴工作台的造型"), font=self.small, relief="solid", bd=1, bg=PAPER,
                  command=self.pet.paste_look).pack(side="left", padx=(6, 0))
        tk.Label(g, text=_("不想连工作台了：右键 → 联动 → 把工作台关掉，衣柜就回来了"), font=self.small, bg=BG, fg=MUTED,
                 wraplength=int(240 * k), justify="left").grid(row=3, column=0, columnspan=3, sticky="w")

    def build_persona(self):
        """性格：随机一个 / 自己写 / AI 按要求写；小克挑东西、写话都照它"""
        g, k, pad = self.grid, self.k, int(4 * self.k)
        P = self.pet.persona()
        r = 0

        def lab(text, bold=False, fg=INK, wrap=True):
            nonlocal r
            tk.Label(g, text=text, font=self.bold if bold else self.small, bg=BG, fg=fg, wraplength=int(240 * k) if wrap else 0,
                     justify="left").grid(row=r, column=0, columnspan=2, sticky="w", pady=(pad, 0))
            r += 1

        lab(_("小克现在的性格"), bold=True)
        self.p_name = tk.Entry(g, font=self.font, relief="solid", bd=1)
        self.p_name.insert(0, P["name"])
        self.p_name.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(2, 0), ipady=2); r += 1
        self.p_desc = tk.Text(g, font=self.small, relief="solid", bd=1, height=3, width=28, wrap="word")
        self.p_desc.insert("1.0", P["desc"])
        self.p_desc.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(4, 0)); r += 1
        row = tk.Frame(g, bg=BG)
        row.grid(row=r, column=0, columnspan=2, sticky="w", pady=(4, 0)); r += 1
        tk.Button(row, text=_("存"), font=self.small, relief="solid", bd=1, bg=YELLOW, command=self.save_persona).pack(side="left")
        tk.Button(row, text=_("⚄ 随机一个"), font=self.small, relief="solid", bd=1, bg=PAPER, command=self.random_persona).pack(side="left", padx=(6, 0))

        lab(_("✨ 让 AI 按你的要求写一个"), fg=INK)
        row = tk.Frame(g, bg=BG)
        row.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(2, 0)); r += 1
        e = tk.Entry(row, font=self.small, relief="solid", bd=1, fg=MUTED)
        hint = _("想要什么样的性格（空着 = 随便）")
        e.insert(0, hint)
        e.bind("<FocusIn>", lambda ev: (e.delete(0, "end"), e.configure(fg=INK)) if e.get() == hint else None)
        e.pack(side="left", fill="x", expand=True, ipady=2)
        tk.Button(row, text=_("AI 写"), font=self.small, relief="solid", bd=1, bg=PAPER,
                  command=lambda: self.ai_persona("" if e.get() == hint else e.get().strip())).pack(side="left", padx=(4, 0))
        self.msg = tk.Label(g, text="", font=self.small, bg=BG, fg=MUTED, wraplength=int(240 * k), justify="left")
        self.msg_row = r; r += 1
        self.msg_pad = 0
        self.cand_row = tk.Frame(g, bg=BG)
        self.cand_row.grid(row=r, column=0, columnspan=2); r += 1

        lab(_("内置的性格（点一下换上；鼠标放上去听它说）"), fg=MUTED)
        for i, (key, (name, desc)) in enumerate(self.cp.PERSONAS.items()):
            b = tk.Label(g, text=name, font=self.small, bg=YELLOW if P.get("key") == key else PAPER, fg=INK, relief="solid", bd=1,
                         padx=int(4 * k), pady=int(2 * k), cursor="hand2")
            b.grid(row=r + i // 2, column=i % 2, sticky="ew", padx=1, pady=1)
            b.bind("<Button-1>", lambda ev, key=key: self.set_persona({"key": key, "by": "builtin"}))
            b.bind("<Enter>", lambda ev, desc=desc: self.pet.say_once(desc))
        r += (len(self.cp.PERSONAS) + 1) // 2
        g.columnconfigure(0, weight=1, uniform="p"); g.columnconfigure(1, weight=1, uniform="p")

        lab(_("按性格写话"), bold=True)
        lab(_("让小克照这个性格，把着急、忙碌、悠闲、欢呼、睡觉（还有你加的状态）和被点时说的话都重写一遍；写好先给你看，勾上的才换"), fg=MUTED)
        tk.Button(g, text=_("让小克按性格写话"), font=self.small, relief="solid", bd=1, bg=PAPER,
                  command=self.ai_lines).grid(row=r, column=0, columnspan=2, sticky="w", pady=(4, 0)); r += 1

    def set_persona(self, p):
        self.pet.set_status(persona=p)
        P = self.pet.persona()
        self.pet.say_once(_("我现在是「{0}」啦").format(P["name"]))
        self.refresh()

    def save_persona(self):
        name, desc = self.p_name.get().strip()[:12], self.p_desc.get("1.0", "end").strip()[:120]
        if not name:
            self.set_msg(_("先起个名字"))
            return
        P = self.pet.persona()
        if P.get("key") and name == P["name"] and desc == P["desc"]:
            return  # 内置的没改过
        self.set_persona({"name": name, "desc": desc, "by": getattr(self, "p_by", None) or "me"})
        self.p_by = None

    def random_persona(self):
        cur = (self.st().get("persona") or {}).get("key")
        self.set_persona({"key": random.choice([k for k in self.cp.PERSONAS if k != cur]), "by": "builtin"})

    def ai_persona(self, want):
        prompt = ("给一只桌面像素宠物「小克」想一个性格。只回一段 JSON，不要别的字。\n"
                  "name：性格的名字，≤6 字，像个外号；desc：≤40 字，写清性格、说话的样子、爱好。"
                  "name 和 desc 都用「" + lang.LANG_NAME.get(lang.CUR, "English") + "」写。\n"
                  '格式：{"items":[{"name":"","desc":""}]}\n'
                  "别跟这个一样：" + self.pet.persona()["name"] + "\n"
                  "这是用户本人的要求，压过上面所有规则，照做：" + (want or "随便想一个，可爱、有点意思"))
        if not which_ai():
            self.win.clipboard_clear()
            self.win.clipboard_append(_("请帮我的小克桌宠想一个性格：{0}。把名字和一句话描述告诉我，我自己填进去。").format(want or _("随便")))
            self.set_msg(_("没找到能借的 AI：复制好了一句话，贴给你的 AI，再把它写的填进上面"))
            return

        def done(text):
            try:
                q = parse_items(text)[0]
            except (RuntimeError, IndexError):
                self.set_msg(_("这次没做出能用的，再试一次？"))
                return
            self.p_name.delete(0, "end"); self.p_name.insert(0, str(q.get("name") or "")[:12])
            self.p_desc.delete("1.0", "end"); self.p_desc.insert("1.0", str(q.get("desc") or "")[:120])
            self.p_by = "ai"
            self.set_msg(_("AI 写好了，看看，点「存」才换上"))

        self.run_ai(prompt, done, _("AI 在写…"))

    def ai_lines(self):
        P = self.pet.persona()
        states = [(k, n) for k, n, __, __ in self.pet.all_states(True)] + [("poke", _("被点了一下"))]
        prompt = ("你是桌面像素宠物「小克」本人。你的性格是「" + P["name"] + "」：" + P["desc"] + "\n"
                  "照你的性格和口气，给下面每个情况各写 3 句你会说的话（每句 ≤12 字，口语，像在跟主人说话）："
                  + "；".join(f"{k}={n}" for k, n in states) + "。\n"
                  "都用「" + lang.LANG_NAME.get(lang.CUR, "English") + "」写。只回一段 JSON，不要别的字。\n"
                  '格式：{"items":[{"state":"busy","lines":["","",""]}]}（state 用等号前面的英文 / 编号）')
        if not which_ai():
            self.set_msg(_("没找到能借的 AI（Codex / Claude Code）：可以在「状态」页一个个自己写"))
            return

        def done(text):
            m = re.search(r"\{.*\}", text or "", re.S)
            try:
                items = json.loads(m.group(0)).get("items") if m else []
            except ValueError:
                items = []
            names = dict(states)
            got = [(str(q.get("state")), [str(x)[:20] for x in q.get("lines") or [] if str(x).strip()][:4]) for q in items or []
                   if isinstance(q, dict) and str(q.get("state")) in names]
            got = [(k, v) for k, v in got if v]
            if not got:
                self.set_msg(_("这次没做出能用的，再试一次？"))
                return
            self.set_msg("")
            LinesPicker(self, got, names)

        self.run_ai(prompt, done, _("小克在写…"))

    def tile(self, parent, it, row, col, cand=False):
        on = it.get("on")
        fr = tk.Frame(parent, bg=YELLOW if on else PAPER, highlightthickness=2 if on else 1,
                      highlightbackground=INK if on else LINE, cursor="hand2", width=self.TW, height=self.TH)
        fr.pack_propagate(False)
        fr.grid(row=row, column=col, padx=int(3 * self.k), pady=int(3 * self.k), sticky="n")
        c = self.mini(fr, it.get("show") or it.get("look"), it.get("state"), bg=fr["bg"], cs=it.get("cs"))
        c.pack(padx=int(3 * self.k), pady=(int(3 * self.k), 0))
        self.badge(c, it.get("by"))
        if self.tidy and not cand and it.get("key") not in ("none", "normal", "clawd") and not on:
            c.create_text(c.winfo_reqwidth() - 4, 2, text="×", anchor="ne", font=self.bold, fill="#e2412b")
        name = self.fit_text(it["name"], self.TW - int(8 * self.k))
        lab = tk.Label(fr, text=name, font=self.small, bg=fr["bg"], fg=INK)
        lab.pack(pady=(0, int(2 * self.k)))
        for wdg in (fr, c, lab):
            wdg.bind("<Enter>", lambda e, it=it: self.try_on(it))
            wdg.bind("<Leave>", lambda e: self.try_off())
            wdg.bind("<Button-1>", lambda e, it=it, cand=cand: self.pick(it, cand))

    def fit_text(self, text, width):
        """名字太长就截掉后面、加「…」：按真的字宽算（英文能放得比中文多）"""
        import tkinter.font as tkfont
        f = tkfont.Font(font=self.small)
        if f.measure(text) <= width:
            return text
        while text and f.measure(text + "…") > width:
            text = text[:-1]
        return text + "…"

    # 鼠标放上去：桌面上的小克先试穿 / 试看（只改小克，不重画衣柜，免得按钮被换掉点不到）
    def try_on(self, it):
        self.pet.preview = {"look": it.get("look"), "state": it.get("state"), "cs": it.get("cs"), "parts": self.mini_parts(),
                            "builds": self.mini_builds(), "chars": self.mini_chars()}
        self.pet.draw()
        if it.get("why"):
            self.pet.say_once(it["why"])

    def try_off(self):
        self.pet.preview = None
        self.pet.draw()

    def pick(self, it, cand=False):
        if cand:
            self.keep(it)
            return
        if self.tidy:
            self.remove(it)
            return
        if self.page == "state":
            self.pet.set_status(state=it["key"], say="")
            self.sel_state = it["key"]
        else:
            self.pet.set_status(look=self.cp.norm_look(it["look"]))
        self.pet.preview = None
        self.refresh()

    # ---- 整理：内置的藏起来，自己做的 / AI 做的真删 ----
    def remove(self, it):
        if it.get("on") or it.get("key") in ("none", "normal", "clawd"):
            self.pet.say_once(_("正穿着 / 正用着的不能删～"))
            return
        key = it["key"]
        if self.page == "char":
            self.pet.set_status(chars=[q for q in self.lst("chars") if "u:" + str(q.get("id")) != key])
        elif self.page == "state":
            if it.get("builtin"):
                self.set_hidden("state", self.hidden("state") + [key])
            else:
                self.pet.set_status(states=[q for q in self.lst("states") if "c:" + str(q.get("id")) != key])
        elif self.cat == "set":
            if it.get("builtin"):
                self.set_hidden("preset", self.hidden("preset") + [key])
            else:
                self.pet.set_status(presets=[q for q in self.lst("presets") if "p:" + str(q.get("name")) != key])
        elif self.cat == "build":
            if it.get("builtin"):
                self.set_hidden("build", self.hidden("build") + [key])
            else:
                self.pet.set_status(builds=[q for q in self.lst("builds") if "u:" + str(q.get("id")) != key])
        elif self.cat == "color":
            if it.get("builtin"):
                self.set_hidden("color", self.hidden("color") + [key])
            else:
                self.pet.set_status(colors=[q for q in self.lst("colors") if (q if isinstance(q, str) else (q or {}).get("color")) != key])
        else:
            if it.get("builtin"):
                self.set_hidden(self.cat, self.hidden(self.cat) + [key])
            else:
                self.pet.set_status(parts=[q for q in self.lst("parts") if "u:" + str(q.get("id")) != key])
        self.refresh()

    def hid_key(self):
        return self.page if self.page in ("char", "state") else {"set": "preset"}.get(self.cat, self.cat)

    def restore(self):
        self.set_hidden(self.hid_key(), [])
        self.refresh()

    # ---- 下面一行 ----
    def build_foot(self):
        for ch in self.foot.winfo_children():
            ch.destroy()
        f = self.foot
        if self.page == "char":
            c = self.cp.find_char(self.look(), self.mini_chars())
            if not c:
                tk.Label(f, text=_("小克的 5 个姿势是内置的；想改某个状态的样子，去「状态」页自己写一个"), font=self.small, bg=BG, fg=MUTED,
                         wraplength=int(250 * self.k), justify="left").pack(anchor="w", pady=(0, int(4 * self.k)))
            else:
                tk.Label(f, text=_("「{0}」的 5 个姿势：自动配好的，点一下能自己改").format(c.get("name") or ""), font=self.small, bg=BG,
                         fg=MUTED, wraplength=int(250 * self.k), justify="left").pack(anchor="w")
                row = tk.Frame(f, bg=BG)
                row.pack(fill="x", pady=(1, int(4 * self.k)))
                for st in self.cp.STATES:
                    col = tk.Frame(row, bg=BG)
                    col.pack(side="left", padx=1)
                    m = self.mini(col, self.look(), st, size=44, bg=PAPER)
                    m.pack()
                    own = bool((c.get("poses") or {}).get(st))
                    tk.Label(col, text=("✎ " if own else "") + self.cp.STATE_ZH[st], font=self.small, bg=BG, fg=INK).pack()
                    m.bind("<Button-1>", lambda e, st=st, c=c: PixelPad(self, "pose", pose=st, char=c))
                    m.bind("<Enter>", lambda e, st=st: (setattr(self.pet, "preview", {"state": st}), self.pet.draw()))
                    m.bind("<Leave>", lambda e: self.try_off())
        if self.page == "state":
            key = self.sel_state or self.st().get("state", "busy")
            name = next((n for k_, n, __, __ in self.pet.all_states(True) if k_ == key), key)
            tk.Label(f, text=_("「{0}」时说的话（几句用 / 隔开）").format(name), font=self.small, bg=BG, fg=MUTED).pack(anchor="w")
            row = tk.Frame(f, bg=BG)
            row.pack(fill="x", pady=(1, int(4 * self.k)))
            cur = (self.st().get("lines") or {}).get(key) or ((self.pet.custom_state(key) or {}).get("lines") or [])
            e = tk.Entry(row, font=self.small, relief="solid", bd=1)
            e.insert(0, " / ".join(cur))
            e.pack(side="left", fill="x", expand=True, ipady=2)
            tk.Button(row, text=_("存"), font=self.small, relief="solid", bd=1, bg=PAPER,
                      command=lambda: self.save_lines(key, e.get())).pack(side="left", padx=(4, 0))
        row = tk.Frame(f, bg=BG)
        row.pack(fill="x")
        tk.Button(row, text=_("完成整理") if self.tidy else _("整理"), font=self.small, relief="solid", bd=1,
                  bg=YELLOW if self.tidy else PAPER, command=self.toggle_tidy).pack(side="left")
        n = len(self.hidden(self.hid_key()))
        if n:
            tk.Button(row, text=_("恢复藏起来的 {0} 个").format(n), font=self.small, relief="flat", bg=BG, fg=MUTED,
                      cursor="hand2", command=self.restore).pack(side="left", padx=(6, 0))
        if self.page == "state":
            tk.Button(row, text=_("⚄ 随机一个"), font=self.small, relief="solid", bd=1, bg=PAPER,
                      command=lambda: (self.pet.set_random_state(), self.refresh())).pack(side="right")
        if self.tidy:
            tk.Label(f, text=_("点一下：内置的藏起来，自己做的删掉"), font=self.small, bg=BG, fg=MUTED).pack(anchor="w")

    def toggle_tidy(self):
        self.tidy = not self.tidy
        self.refresh()

    def save_lines(self, key, text):
        lines = [x.strip()[:40] for x in text.replace("|", "/").split("/") if x.strip()]
        d = dict(self.st().get("lines") or {})
        d[key] = lines
        self.pet.set_status(lines=d)
        self.pet.say_once(_("记住啦～") if lines else _("换回默认的话啦"))

    # ---- 「＋ 新的」：〔小克〕小克挑 / ✨ AI 做 / ✍ 自己做 ----
    def refresh_plus(self, plus):
        plus.configure(bg=YELLOW if self.new_open else BG)

    def toggle_new(self):
        self.new_open = not self.new_open
        self.build_new()

    def kind_name(self):
        return {"state": _("状态"), "char": _("形象")}.get(self.page) or CAT_ZH[self.cat]

    def build_new(self):
        box = self.new_box
        for ch in box.winfo_children():
            ch.destroy()
        if not self.new_open:
            box.pack_forget()
            return
        box.pack(fill="x", side="bottom", padx=int(8 * self.k), pady=(0, int(6 * self.k)), before=self.mid)
        p = int(6 * self.k)
        tk.Label(box, text=_("新的{0}").format(self.kind_name()), font=self.bold, bg=PAPER, fg=INK).pack(anchor="w", padx=p, pady=(p, 2))
        ai = which_ai()
        r1 = tk.Frame(box, bg=PAPER)
        r1.pack(fill="x", padx=p, pady=2)
        ic = tk.Canvas(r1, width=int(16 * self.k), height=int(12 * self.k), bg=PAPER, highlightthickness=0)
        self.clawd_icon(ic, 1, 1)
        ic.pack(side="left")
        tk.Button(r1, text=_("小克挑 3 个"), font=self.small, relief="solid", bd=1, bg=PAPER,
                  command=lambda: self.make("clawd", "")).pack(side="left", padx=(4, 0))
        tk.Label(r1, text=_("按它的性格：{0}").format(self.pet.persona()["name"]), font=self.small, bg=PAPER, fg=MUTED).pack(side="left", padx=(4, 0))
        r2 = tk.Frame(box, bg=PAPER)
        r2.pack(fill="x", padx=p, pady=2)
        tk.Label(r2, text="✨", font=self.small, bg=PAPER, fg="#c58a00").pack(side="left")
        e = tk.Entry(r2, font=self.small, relief="solid", bd=1, fg=MUTED)
        hint = _("想要什么样（空着 = 随便）")
        e.insert(0, hint)
        e.bind("<FocusIn>", lambda ev: (e.delete(0, "end"), e.configure(fg=INK)) if e.get() == hint else None)
        e.pack(side="left", fill="x", expand=True, padx=(4, 4), ipady=2)
        tk.Button(r2, text=_("AI 做 3 个"), font=self.small, relief="solid", bd=1, bg=PAPER,
                  command=lambda: self.make("ai", "" if e.get() == hint else e.get().strip())).pack(side="left")
        r3 = tk.Frame(box, bg=PAPER)
        r3.pack(fill="x", padx=p, pady=2)
        tk.Label(r3, text="✍", font=self.small, bg=PAPER).pack(side="left")
        mine = {"state": _("自己写一个（能改小克的样子）"), "set": _("把现在这身存成整套"), "color": _("自己调一个颜色"), "build": _("自己调一个体型"),
                "char": _("自己画一个形象")}.get(self.kind(), _("自己画一个{0}").format(CAT_ZH.get(self.cat, '')))
        tk.Button(r3, text=mine, font=self.small, relief="solid", bd=1, bg=PAPER, command=self.make_mine).pack(side="left", padx=(4, 0))
        self.msg = tk.Label(box, text="" if ai else _("没找到能借的 AI（Codex / Claude Code）：点上面两个会复制一句话，贴给你自己的 AI"),
                            font=self.small, bg=PAPER, fg=MUTED, wraplength=int(240 * self.k), justify="left")
        if self.msg.cget("text"):
            self.msg.pack(anchor="w", padx=p, pady=(2, 0))
        self.msg_pad = p
        self.cand_row = tk.Frame(box, bg=PAPER)
        self.cand_row.pack(fill="x", padx=p, pady=(2, p))
        self.show_cands()

    def set_msg(self, text, waiting=False):
        try:
            self.msg.configure(text=text)
            stop = getattr(self, "stop_btn", None)
            if stop is not None:
                stop.destroy()
                self.stop_btn = None
            if self.page == "persona":  # 性格页用 grid 排
                if text:
                    self.msg.grid(row=self.msg_row, column=0, columnspan=2, sticky="w", pady=(2, 0))
                else:
                    self.msg.grid_forget()
                parent = self.msg.master
            else:
                if text:
                    self.msg.pack(anchor="w", padx=self.msg_pad, pady=(2, 0), before=self.cand_row)
                else:
                    self.msg.pack_forget()
                parent = self.msg.master
            if waiting:
                self.stop_btn = tk.Button(parent, text=_("不等了"), font=self.small, relief="solid", bd=1, bg=PAPER, command=self.stop_job)
                if self.page == "persona":
                    self.stop_btn.grid(row=self.msg_row + 1, column=0, sticky="w", pady=(2, 0))
                else:
                    self.stop_btn.pack(anchor="e", padx=self.msg_pad, before=self.cand_row)
        except (tk.TclError, AttributeError):
            pass

    def show_cands(self):
        for ch in self.cand_row.winfo_children():
            ch.destroy()
        if self.cands:
            tk.Label(self.cand_row, text=_("放上去试试，点一下留下："), font=self.small, bg=PAPER, fg=MUTED).grid(row=0, column=0, columnspan=3, sticky="w")
        for i, it in enumerate(self.cands):
            self.tile(self.cand_row, it, 1, i, cand=True)

    # 借 AI：后台问，这边每秒更新「等了几秒」，可以不等了
    def run_ai(self, prompt, on_ok, label):
        if self.job:
            return
        self.pet.say_once(_("让我想想～"))
        job = self.job = {"result": None, "t": time.time(), "label": label, "on_ok": on_ok}

        def run():
            try:
                job["result"] = ("ok", ask_ai(prompt))
            except Exception as ex:  # 话是给人看的
                job["result"] = ("err", str(ex))

        threading.Thread(target=run, daemon=True).start()
        self.wait_job()

    def wait_job(self):
        job = self.job
        if not job or not self.alive() or job.get("cancel"):
            return
        if job["result"] is None:
            self.set_msg(job["label"] + _("已经等了 {0} 秒（借电脑上的 AI，一般十几秒到一两分钟）").format(int(time.time() - job["t"])), waiting=True)
            self.win.after(1000, self.wait_job)
            return
        self.job = None
        ok, val = job["result"]
        if ok != "ok":
            self.set_msg(val)
            return
        job["on_ok"](val)

    def stop_job(self):
        if self.job:
            self.job["cancel"] = True
            self.job = None
        self.set_msg(_("不等了（AI 那边做完也不会用）"))

    # 让小克 / AI 做 3 个
    def make(self, who, want):
        if self.job:
            return
        kind = self.kind()
        prompt = self.prompt(kind, who, want)
        if not which_ai():
            self.copy_for_ai(kind, who, want)
            return

        def done(text):
            try:
                items = parse_items(text)
            except RuntimeError as ex:
                self.set_msg(str(ex))
                return
            self.cands = [c for c in (self.to_item(kind, q, who) for q in items) if c]
            self.set_msg("" if self.cands else _("这次没做出能用的，再试一次？"))
            if self.new_open:
                self.show_cands()

        self.run_ai(prompt, done, _("小克在挑…") if who == "clawd" else _("AI 在做…"))

    def to_item(self, kind, q, who):
        by = "clawd" if who == "clawd" else "ai"
        name = str(q.get("name") or _("新的"))[:8]
        why = str(q.get("why") or "")[:30]
        L = self.look()
        if kind == "state":
            pose = q.get("pose") if q.get("pose") in self.cp.STATES else "busy"
            lines = [str(x)[:20] for x in q.get("lines") or [] if str(x).strip()][:4]
            return {"key": "new", "name": name, "by": by, "why": why,
                    "cs": {"pose": pose, "lines": lines, "px": clean_px(q.get("px"))}}
        if kind == "set":
            look = q.get("look") if isinstance(q.get("look"), dict) else {}
            allowed = {c: {v for v, __ in BUILTIN[c]} | {"u:" + str(p.get("id")) for p in self.lst("parts") if p.get("slot") == c}
                       for c in ("ears", "tail", "hold", "hat", "face", "body")}
            clean = {c: look.get(c) for c in allowed if look.get(c) in allowed[c]}
            if re.fullmatch(r"#[0-9a-fA-F]{6}", str(look.get("color") or "")):
                clean["color"] = look["color"]
            if re.fullmatch(r"#[0-9a-fA-F]{6}", str(look.get("scarf") or "")) or look.get("scarf") == "none":
                clean["scarf"] = look["scarf"]
            return {"key": "new", "name": name, "look": self.cp.norm_look({**L, **clean}), "by": by, "why": why}
        if kind == "char":
            px = clean_px(q.get("px"))
            cols = [t.split(",")[2] for t in px.split(";") if t and not t.endswith(",-")]
            if len(cols) < 20:
                return None
            main = str(q.get("color") or "").lstrip("#").lower()
            if main not in cols:
                main = max(set(cols), key=cols.count)
            cid = "cand%06x" % random.randrange(1 << 24)
            ch = {"id": cid, "name": name, "px": px, "color": "#" + main, "by": by}
            return {"key": "new", "name": name, "by": by, "why": why, "cand_char": ch,
                    "show": self.plain("u:" + cid, "#" + main), "look": {**L, "char": "u:" + cid, "color": "#" + main}}
        if kind == "build":
            try:
                sx, sy = [max(.6, min(1.3, float(q.get(k) or 1))) for k in ("sx", "sy")]
            except (TypeError, ValueError):
                return None
            cid = "cand%06x" % random.randrange(1 << 24)
            return {"key": "new", "name": name, "by": by, "why": why, "cand_build": {"id": cid, "sx": sx, "sy": sy},
                    "look": {**L, "build": "u:" + cid}}
        if kind == "color":
            c = str(q.get("color") or "")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
                return None
            return {"key": c, "name": name, "look": {**L, "color": c}, "by": by, "why": why}
        px = clean_px(q.get("px"))
        if not px:
            return None
        cid = "cand%06x" % random.randrange(1 << 24)
        return {"key": "new", "name": name, "by": by, "why": why, "cand_part": {"id": cid, "slot": kind, "px": px},
                "look": {**L, kind: "u:" + cid}}

    def keep(self, it):
        """候选点一下：留进库里，并且穿上 / 换成它"""
        kind = self.kind()
        new_id = "%x" % int(time.time() * 1000)
        if kind == "char":
            ch = {**it["cand_char"], "id": new_id}
            self.pet.set_status(chars=self.lst("chars") + [ch], look={**self.look(), "char": "u:" + new_id, "color": ch["color"]})
        elif kind == "state":
            states = self.lst("states") + [{"id": new_id, "name": it["name"], **it["cs"], "by": it["by"], "char": self.look()["char"]}]
            self.pet.set_status(states=states, state="c:" + new_id, say="")
        elif kind == "set":
            self.pet.set_status(presets=self.lst("presets") + [{"name": it["name"], "look": it["look"], "by": it["by"]}], look=it["look"])
        elif kind == "build":
            b = it["cand_build"]
            self.pet.set_status(builds=self.lst("builds") + [{"id": new_id, "name": it["name"], "sx": b["sx"], "sy": b["sy"], "by": it["by"]}],
                                look={**self.look(), "build": "u:" + new_id})
        elif kind == "color":
            self.pet.set_status(colors=self.lst("colors") + [{"color": it["key"], "name": it["name"], "by": it["by"]}],
                                look={**self.look(), "color": it["key"]})
        else:
            parts = self.lst("parts") + [{"id": new_id, "name": it["name"], "slot": kind, "px": it["cand_part"]["px"], "by": it["by"]}]
            self.pet.set_status(parts=parts, look={**self.look(), kind: "u:" + new_id})
        self.cands = [c for c in self.cands if c is not it]
        self.pet.preview = None
        self.pet.say_once(_("留下啦！"))
        self.refresh()

    # 候选里的衣服还没进库，试穿时临时放进去画
    def mini_chars(self):
        return (self.st().get("chars") or []) + [it["cand_char"] for it in self.cands if it.get("cand_char")]

    def mini_builds(self):
        return (self.st().get("builds") or []) + [it["cand_build"] for it in self.cands if it.get("cand_build")]

    def mini_parts(self):
        return (self.st().get("parts") or []) + [it["cand_part"] for it in self.cands if it.get("cand_part")]

    # ---- 给 AI 的话 ----
    def prompt(self, kind, who, want):
        existing = []
        if kind == "state":
            existing = [n for __, n, __, __ in self.pet.all_states(True)]
        elif kind == "set":
            existing = list(self.cp.PRESETS) + [str(q.get("name")) for q in self.lst("presets")]
        elif kind == "char":
            existing = ["小克"] + [str(q.get("name")) for q in self.lst("chars")]
        elif kind == "build":
            existing = list(self.cp.BUILDS.values()) + [str(q.get("name")) for q in self.lst("builds")]
        elif kind == "color":
            existing = [c for c, __ in BUILTIN["color"]] + [str(q if isinstance(q, str) else q.get("color")) for q in self.lst("colors")]
        else:
            existing = [n for __, n in BUILTIN.get(kind, [])] + [str(q.get("name")) for q in self.lst("parts") if q.get("slot") == kind]
        head = "你在帮桌面上的一只像素宠物「小克」（橙色小方块身子、两只竖眼睛、四条小短腿）做东西。只回一段 JSON，不要别的字。\n"
        if kind == "state":
            body = ("做 3 个新的「状态」（小克此刻在干嘛 / 什么心情）。每个：name（≤4 字）、pose（用哪种姿势画：urgent 着急举牌 / busy 站着 / "
                    "relaxed 趴着 / cheer 举手欢呼 / sleep 睡觉，选最合适的）、lines（这个状态时小克说的 3 句话，每句 ≤12 字，口语）、"
                    "px（可以空着；要画就画一个小道具，在 " + AREA["prop"] + "；也可以用 - 擦掉小克的几格、再画上新的，改它这时的表情和样子。"
                    "注意坐标是这个姿势里的真实位置：relaxed 趴着时小克整体往下 3 格，sleep 往下 4 格）、why（≤15 字）。\n" + GRID_HELP + "\n"
                    '格式：{"items":[{"name":"","pose":"","lines":["","",""],"px":"","why":""}]}')
        elif kind == "set":
            opts = "；".join(f"{c}：" + " / ".join(v for v, __ in BUILTIN[c] if not v.startswith("scarf:")) for c in ("ears", "tail", "hold", "hat", "face", "body"))
            mine = "；".join(f"{q.get('slot')}：u:{q.get('id')}（{q.get('name')}）" for q in self.lst("parts"))
            body = ("搭 3 套新的「整套造型」，只能从下面的选项里挑：" + opts + ("；用户自己的：" + mine if mine else "") +
                    "；scarf 围巾填 none 或一个颜色 #rrggbb；color 身子颜色 #rrggbb。每套：name（≤6 字）、look、why（≤15 字）。\n"
                    '格式：{"items":[{"name":"","look":{"ears":"","tail":"","hold":"","hat":"","face":"","body":"","scarf":"","color":""},"why":""}]}')
        elif kind == "char":
            body = ("画 3 个新的「形象」：桌宠这个角色本身（不是衣服），一只完整的像素小角色，站着、面朝前、要有眼睛。"
                    "大小：大约 12～18 格宽、12～18 格高，脚踩在 y=18（最下面一行就是 y=18），左右在 x 2～20 之间、居中在 x=11 附近。"
                    "颜色 3～5 种，其中一种是主色（身子的颜色，用得最多）。每个：name（≤5 字）、color（主色 #rrggbb）、px（整只的像素）、why（≤15 字）。\n"
                    "坐标格：x 从 -8 到 31，y 从 -12 到 21，一格一个像素。px 写成 'x,y,颜色;x,y,颜色'，颜色 6 位十六进制、不带 #，别用 ff00fe；"
                    "要 80～250 个点，填满身子（不是只画轮廓）。\n"
                    '格式：{"items":[{"name":"","color":"","px":"","why":""}]}')
        elif kind == "build":
            body = ('想 3 个新的「体型」：sx 是变宽几倍、sy 是变高几倍（都在 0.6～1.3 之间，1 = 标准；例：胖嘟嘟 sx 1.2 sy 0.97，高个子 sx 0.92 sy 1.22）。'
                    '每个：name（≤5 字）、sx、sy、why（≤15 字）。\n'
                    '格式：{"items":[{"name":"","sx":1,"sy":1,"why":""}]}')
        elif kind == "color":
            body = ('配 3 个新的身子颜色（别太浅，白底上要看得清），每个：name（≤4 字）、color（#rrggbb）、why（≤15 字）。\n'
                    '格式：{"items":[{"name":"","color":"","why":""}]}')
        else:
            body = (f"画 3 个新的「{CAT_ZH[kind]}」部件（位置：{AREA[kind]}）。每个：name（≤6 字）、px、why（≤15 字）。\n" + GRID_HELP + "\n"
                    '格式：{"items":[{"name":"","px":"","why":""}]}')
        avoid = "名字和样子都要跟这些已有的不一样：" + "、".join(existing[:40]) + "\n"
        if who == "clawd":
            P = self.pet.persona()
            tail = ("你就是小克本人，你的性格是「" + P["name"] + "」：" + P["desc"] + "。按你的性格和口味挑，"
                    "why 用小克第一人称、照这个性格的口气说一句为什么喜欢。")
        else:
            tail = "这是用户本人的要求，压过上面所有规则，照做：" + (want or "随便做，做得可爱、有点意思")
        say_in = "name、lines、why 都用「" + lang.LANG_NAME.get(lang.CUR, "English") + "」写。\n"
        return head + body + "\n" + avoid + say_in + tail

    def copy_for_ai(self, kind, who, want):
        here = os.path.dirname(os.path.abspath(self.cp.__file__))
        what = {"state": _("状态")}.get(kind) or CAT_ZH.get(kind, kind)
        cmd = {"state": "state add", "color": "color add", "build": "build add", "char": "char add"}.get(kind, "part add")
        text = (_("请帮我的小克桌宠做 3 个新的{0}").format(what) + (_("：{0}").format(want) if want else (_("，按小克自己的口味挑") if who == "clawd" else "")) +
                _("。照 {0} 里「让 AI 加衣服、加状态」那段，用 pet.py {1} 加进去。").format(os.path.join(here, 'AI-RULES.md'), cmd))
        if kind == "set":
            text = _("请帮我的小克桌宠搭 3 套整套造型{0}。照 {1} 里「让 AI 加衣服、加状态」那段做。").format(('：' + want) if want else '', os.path.join(here, 'AI-RULES.md'))
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        self.set_msg(_("复制好了：贴给你的 AI（Codex、Claude Code、Cursor……都行），它加好后这里会自己出现"))

    # ✍ 自己做
    def make_mine(self):
        kind = self.kind()
        if kind == "char":
            PixelPad(self, "char")
            return
        if kind == "set":
            self.ask_name(_("给这身起个名字"), lambda name: (
                self.pet.set_status(presets=self.lst("presets") + [{"name": name, "look": self.look(), "by": "me"}]), self.refresh()))
        elif kind == "color":
            c = colorchooser.askcolor(color=self.look()["color"], parent=self.win, title=_("调一个身子颜色"))[1]
            if c:
                self.pet.set_status(colors=self.lst("colors") + [{"color": c, "name": c, "by": "me"}], look={**self.look(), "color": c})
                self.refresh()
        elif kind == "state":
            StateForm(self)
        elif kind == "build":
            BuildForm(self)
        else:
            PixelPad(self, kind)

    def ask_name(self, title, done, default=""):
        d = tk.Toplevel(self.win)
        d.title(title)
        d.attributes("-toolwindow", True)
        d.attributes("-topmost", True)
        d.configure(bg=BG)
        e = tk.Entry(d, font=self.font, relief="solid", bd=1, width=16)
        e.insert(0, default)
        e.pack(padx=10, pady=(10, 6))
        e.focus_set()

        def ok(__=None):
            name = e.get().strip()[:12]
            if name:
                d.destroy()
                done(name)

        e.bind("<Return>", ok)
        tk.Button(d, text=_("好"), font=self.small, relief="solid", bd=1, bg=YELLOW, command=ok).pack(pady=(0, 10))
        d.geometry(f"+{self.win.winfo_x() + 20}+{self.win.winfo_y() + 80}")


# ---------- 按性格写的话：先看，勾上的才换 ----------

class LinesPicker:
    def __init__(self, wd, got, names):
        self.wd = wd
        k = wd.k
        d = self.d = tk.Toplevel(wd.win)
        d.title(_("小克按性格写的话"))
        d.attributes("-toolwindow", True)
        d.attributes("-topmost", True)
        d.configure(bg=BG)
        pad = int(8 * k)
        tk.Label(d, text=_("勾上的换成新写的；没勾的不动"), font=wd.small, bg=BG, fg=MUTED).pack(anchor="w", padx=pad, pady=(pad, 4))
        self.rows = []
        for key, lines in got:
            v = tk.BooleanVar(value=True)
            row = tk.Frame(d, bg=BG)
            row.pack(fill="x", padx=pad, pady=1)
            tk.Checkbutton(row, variable=v, bg=BG).pack(side="left")
            tk.Label(row, text=names.get(key, key), font=wd.bold, bg=BG, fg=INK, width=8, anchor="w").pack(side="left")
            tk.Label(row, text=" / ".join(lines), font=wd.small, bg=BG, fg=INK, wraplength=int(300 * k), justify="left").pack(side="left")
            self.rows.append((key, lines, v))
        bot = tk.Frame(d, bg=BG)
        bot.pack(fill="x", padx=pad, pady=pad)
        tk.Button(bot, text=_("全部不要"), font=wd.small, relief="solid", bd=1, bg=PAPER, command=d.destroy).pack(side="left")
        tk.Button(bot, text=_("换上勾上的"), font=wd.small, relief="solid", bd=1, bg=YELLOW, command=self.apply).pack(side="right")
        d.geometry(f"+{max(0, wd.win.winfo_x() - int(360 * k))}+{wd.win.winfo_y() + 40}")

    def apply(self):
        d = dict(self.wd.st().get("lines") or {})
        n = 0
        for key, lines, v in self.rows:
            if v.get():
                d[key] = lines
                n += 1
        self.wd.pet.set_status(lines=d)
        self.wd.pet.say_once(_("换好啦，{0} 个").format(n))
        self.d.destroy()


# ---------- ✍ 自己写一个状态 ----------

class StateForm:
    def __init__(self, wd):
        self.wd, self.px = wd, ""
        k = wd.k
        d = self.d = tk.Toplevel(wd.win)
        d.title(_("自己写一个状态"))
        d.attributes("-toolwindow", True)
        d.attributes("-topmost", True)
        d.configure(bg=BG)
        f, s = wd.font, wd.small
        pad = int(8 * k)
        tk.Label(d, text=_("叫什么"), font=s, bg=BG, fg=MUTED).pack(anchor="w", padx=pad, pady=(pad, 0))
        self.name = tk.Entry(d, font=f, relief="solid", bd=1)
        self.name.pack(fill="x", padx=pad, ipady=2)
        tk.Label(d, text=_("用哪种姿势"), font=s, bg=BG, fg=MUTED).pack(anchor="w", padx=pad, pady=(pad, 0))
        row = tk.Frame(d, bg=BG)
        row.pack(fill="x", padx=pad)
        self.pose = tk.StringVar(value="busy")
        for key in wd.cp.STATES:
            col = tk.Frame(row, bg=BG)
            col.pack(side="left", padx=1)
            c = wd.mini(col, state=key, size=42, bg=BG)
            c.pack()
            tk.Radiobutton(col, text=wd.cp.STATE_ZH[key], variable=self.pose, value=key, font=s, bg=BG,
                           command=self.preview).pack()
            c.bind("<Button-1>", lambda e, key=key: (self.pose.set(key), self.preview()))
        tk.Label(d, text=_("这时说的话（几句用 / 隔开）"), font=s, bg=BG, fg=MUTED).pack(anchor="w", padx=pad, pady=(pad, 0))
        self.lines = tk.Entry(d, font=f, relief="solid", bd=1)
        self.lines.pack(fill="x", padx=pad, ipady=2)
        row2 = tk.Frame(d, bg=BG)
        row2.pack(fill="x", padx=pad, pady=pad)
        tk.Button(row2, text=_("画小道具 / 改小克的样子（可不画）"), font=s, relief="solid", bd=1, bg=PAPER,
                  command=lambda: PixelPad(wd, "state", self.set_px, pose=self.pose.get(), px=self.px)).pack(side="left")
        tk.Button(row2, text=_("存"), font=s, relief="solid", bd=1, bg=YELLOW, command=self.save).pack(side="right")
        self.tip = tk.Label(d, text="", font=s, bg=BG, fg="#e2412b")
        self.tip.pack(anchor="w", padx=pad, pady=(0, pad))
        d.protocol("WM_DELETE_WINDOW", self.close)
        d.geometry(f"+{wd.win.winfo_x() + 10}+{wd.win.winfo_y() + 60}")

    def set_px(self, px):
        self.px = px
        self.preview()

    def preview(self):
        lines = [x.strip() for x in self.lines.get().replace("|", "/").split("/") if x.strip()]
        self.wd.pet.preview = {"cs": {"pose": self.pose.get(), "px": self.px, "lines": lines}}
        self.wd.pet.draw()

    def close(self):
        self.wd.pet.preview = None
        self.wd.pet.draw()
        self.d.destroy()

    def save(self):
        name = self.name.get().strip()[:8]
        if not name:
            self.tip.configure(text=_("先起个名字"))
            return
        lines = [x.strip()[:20] for x in self.lines.get().replace("|", "/").split("/") if x.strip()]
        new_id = "%x" % int(time.time() * 1000)
        wd = self.wd
        wd.pet.set_status(states=wd.lst("states") + [{"id": new_id, "name": name, "pose": self.pose.get(), "lines": lines, "px": self.px, "by": "me",
                                                       "char": wd.look()["char"]}],
                          state="c:" + new_id, say="")
        self.close()
        wd.refresh()


# ---------- ✍ 自己调一个体型 ----------

class BuildForm:
    def __init__(self, wd):
        self.wd = wd
        k = wd.k
        d = self.d = tk.Toplevel(wd.win)
        d.title(_("自己调一个体型"))
        d.attributes("-toolwindow", True)
        d.attributes("-topmost", True)
        d.configure(bg=BG)
        pad = int(8 * k)
        sx, sy = wd.cp.build_scale(wd.look(), wd.st().get("builds"))
        self.sx, self.sy = tk.IntVar(value=round(sx * 100)), tk.IntVar(value=round(sy * 100))
        for label, var in ((_("宽 %"), self.sx), (_("高 %"), self.sy)):
            row = tk.Frame(d, bg=BG)
            row.pack(fill="x", padx=pad, pady=(pad, 0))
            tk.Label(row, text=label, font=wd.small, bg=BG, width=4).pack(side="left")
            tk.Scale(row, from_=60, to=130, orient="horizontal", variable=var, length=int(180 * k), bg=BG, highlightthickness=0,
                     command=lambda __=None: self.preview()).pack(side="left")
        row = tk.Frame(d, bg=BG)
        row.pack(fill="x", padx=pad, pady=pad)
        tk.Label(row, text=_("名字"), font=wd.small, bg=BG).pack(side="left")
        self.name = tk.Entry(row, font=wd.small, relief="solid", bd=1, width=10)
        self.name.pack(side="left", padx=(4, 8), ipady=2)
        tk.Button(row, text=_("存"), font=wd.small, relief="solid", bd=1, bg=YELLOW, command=self.save).pack(side="right")
        self.tip = tk.Label(d, text=_("拖一拖，桌面上的小克马上跟着变"), font=wd.small, bg=BG, fg=MUTED)
        self.tip.pack(anchor="w", padx=pad, pady=(0, pad))
        d.protocol("WM_DELETE_WINDOW", self.close)
        d.geometry(f"+{wd.win.winfo_x() + 10}+{wd.win.winfo_y() + 80}")
        self.preview()

    def preview(self):
        self.wd.pet.preview = {"look": {**self.wd.look(), "build": "u:__try"},
                               "builds": [{"id": "__try", "sx": self.sx.get() / 100, "sy": self.sy.get() / 100}]}
        self.wd.pet.draw()

    def close(self):
        self.wd.pet.preview = None
        self.wd.pet.draw()
        self.d.destroy()

    def save(self):
        name = self.name.get().strip()[:6]
        if not name:
            self.tip.configure(text=_("先起个名字"), fg="#e2412b")
            return
        wd = self.wd
        new_id = "%x" % int(time.time() * 1000)
        wd.pet.set_status(builds=wd.lst("builds") + [{"id": new_id, "name": name, "sx": self.sx.get() / 100, "sy": self.sy.get() / 100, "by": "me"}],
                          look={**wd.look(), "build": "u:" + new_id})
        self.close()
        wd.refresh()


# ---------- ✍ 像素画板：画衣服 / 状态的小道具和改小克的样子 ----------

class PixelPad:
    X0, Y0, NX, NY = -8, -12, 40, 34

    def __init__(self, wd, slot, done=None, pose="busy", px="", char=None):
        self.wd, self.slot, self.done, self.pose, self.char = wd, slot, done, pose, char
        if slot == "pose" and char:  # 改形象的一个姿势：从现在的样子（自动配的或改过的）开始改
            L = wd.plain("u:" + str(char.get("id")), char.get("color") or "#d97757")
            px = ";".join(f"{int(x)},{int(y)},{c.lstrip('#')}" for k, x, y, w, h, c in wd.cp.char_cells(char, L, pose, [])[5:]
                          if w == 1 and h == 1 and c != "-")
        self.cells = {}      # (x, y) → 颜色；"-" = 擦掉小克的这一格
        for item in str(px or "").split(";"):
            try:
                x, y, c = item.split(",")
                self.cells[(int(x), int(y))] = "-" if c == "-" else "#" + c
            except ValueError:
                pass
        self.color = "#e2412b"
        k = wd.k
        self.C = max(6, int(8 * k))
        d = self.d = tk.Toplevel(wd.win)
        d.title({"state": _("画小道具 / 改小克的样子"), "char": _("画一个形象"), "pose": _("改这个姿势")}.get(slot)
                or _("画一个{0}").format(CAT_ZH.get(slot, '')))
        d.attributes("-toolwindow", True)
        d.attributes("-topmost", True)
        d.configure(bg=BG)
        pad = int(8 * k)
        tk.Label(d, text=(_("左键画、右键擦。整只画出来：虚线框差不多是小克的大小，脚踩在框的最下面；用得最多的颜色就是它的主色（换颜色时换的就是它）")
                          if slot == "char" else _("左键画、右键擦。这是这个形象现在的样子，改完点「好了」；想换回自动配的，点「换回自动的」")
                          if slot == "pose" else _("左键画、右键擦。改表情：用「小克色」把眼睛涂掉，再画新的；右键点小克身上 = 把那一格擦成透明（改轮廓、改姿势），「整只擦掉」= 从头画一只")
                          if slot == "state" else _("左键画、右键擦（右键点小克身上也能擦掉那一格）。淡淡的是小克，虚线框里是建议画的地方")),
                 font=wd.small, bg=BG, fg=MUTED, wraplength=self.C * self.NX, justify="left").pack(anchor="w", padx=pad, pady=(pad, 2))
        self.cv = tk.Canvas(d, width=self.C * self.NX, height=self.C * self.NY, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
        self.cv.pack(padx=pad)
        self.cv.bind("<Button-1>", self.paint)
        self.cv.bind("<B1-Motion>", self.paint)
        self.cv.bind("<Button-3>", self.erase)
        self.cv.bind("<B3-Motion>", self.erase)
        pal = tk.Frame(d, bg=BG)
        pal.pack(fill="x", padx=pad, pady=(6, 0))
        B = wd.look()["color"]
        mine = [B, wd.cp.shade(B, .28), wd.cp.shade(B, -.45)]  # 小克的身子色、头顶亮色、深色
        tk.Label(pal, text=_("小克色"), font=wd.small, bg=BG, fg=MUTED).pack(side="left", padx=(0, 2))
        for c in mine:
            b = tk.Label(pal, bg=c, width=2, relief="solid", bd=1, cursor="hand2")
            b.pack(side="left", padx=1)
            b.bind("<Button-1>", lambda e, c=c: self.use(c))
        tk.Frame(pal, bg=BG, width=6).pack(side="left")
        self.color = B if slot == "state" else (char.get("color") or self.color) if (slot == "pose" and char) else self.color
        for c in PALETTE:
            b = tk.Label(pal, bg=c, width=2, relief="solid", bd=1, cursor="hand2")
            b.pack(side="left", padx=1)
            b.bind("<Button-1>", lambda e, c=c: self.use(c))
        pal2 = tk.Frame(d, bg=BG)
        pal2.pack(fill="x", padx=pad, pady=(4, 0))
        tk.Label(pal2, text=_("正在用"), font=wd.small, bg=BG, fg=MUTED).pack(side="left")
        self.cur = tk.Label(pal2, text="  ", bg=self.color, relief="solid", bd=1, width=3)
        self.cur.pack(side="left", padx=(4, 8))
        tk.Button(pal2, text=_("其他颜色…"), font=wd.small, relief="solid", bd=1, bg=PAPER, command=self.more).pack(side="left")
        bot = tk.Frame(d, bg=BG)
        bot.pack(fill="x", padx=pad, pady=pad)
        if slot == "pose" and (char.get("poses") or {}).get(pose):
            tk.Button(bot, text=_("换回自动的"), font=wd.small, relief="solid", bd=1, bg=PAPER, command=self.auto_pose).pack(side="left", padx=(0, 6))
        if slot not in ("state", "pose"):
            tk.Label(bot, text=_("名字"), font=wd.small, bg=BG).pack(side="left")
            self.name = tk.Entry(bot, font=wd.small, relief="solid", bd=1, width=10)
            self.name.pack(side="left", padx=(4, 8), ipady=2)
        tk.Button(bot, text=_("清空"), font=wd.small, relief="solid", bd=1, bg=PAPER, command=self.clear).pack(side="left")
        if slot == "state":
            tk.Button(bot, text=_("整只擦掉"), font=wd.small, relief="solid", bd=1, bg=PAPER, command=self.erase_all).pack(side="left", padx=(4, 0))
        tk.Button(bot, text=_("好了"), font=wd.small, relief="solid", bd=1, bg=YELLOW, command=self.save).pack(side="right")
        self.tip = tk.Label(d, text="", font=wd.small, bg=BG, fg="#e2412b")
        self.tip.pack(anchor="w", padx=pad)
        self.base()
        for xy in list(self.cells):
            self.draw_cell(xy)
        d.geometry(f"+{max(0, wd.win.winfo_x() - self.C * self.NX - 40)}+{wd.win.winfo_y()}")

    def base(self):
        """淡淡的小克（这个部位先空着），方便对位置"""
        self.covered = set()
        C = self.C
        if self.slot in ("char", "pose"):  # 画形象：只画格子线；画新形象时再加一个小克大小的虚线框
            for x in range(self.NX + 1):
                self.cv.create_line(x * C, 0, x * C, self.NY * C, fill="#f0ece4")
            for y in range(self.NY + 1):
                self.cv.create_line(0, y * C, self.NX * C, y * C, fill="#f0ece4")
            if self.slot == "char":
                x0, y0, x1, y1 = self.wd.cp.CLAWD_BOX
                self.cv.create_rectangle((x0 - self.X0) * C, (y0 - self.Y0) * C, (x1 - self.X0) * C, (y1 - self.Y0) * C,
                                         outline="#c58a00", dash=(4, 3), width=2, tags="base")
            return
        look = self.wd.look()
        if self.slot in ("ears", "tail", "hold", "hat", "face", "body"):
            look[self.slot] = "none"
            look["char"] = "clawd"   # 衣服按小克身上的位置画，穿到别的形象上会自动挪
        C = self.C
        for x in range(self.NX + 1):
            self.cv.create_line(x * C, 0, x * C, self.NY * C, fill="#f0ece4")
        for y in range(self.NY + 1):
            self.cv.create_line(0, y * C, self.NX * C, y * C, fill="#f0ece4")
        self.covered = set()   # 小克身上有颜色的格子（「整只擦掉」用）
        for kind, x, y, w, h, col in self.wd.cp.clawd(look, self.pose, self.wd.st().get("parts") or []):
            if kind != "r" or col == "-":
                continue
            x0, y0 = (x - self.X0) * C, (y - self.Y0) * C
            # 改小克的样子：原色；画衣服：调淡，看得出是小克又不抢眼
            fillc = col if self.slot == "state" else self.wd.cp.shade(col if len(col) == 7 else "#999999", 0.72)
            self.cv.create_rectangle(x0, y0, x0 + w * C, y0 + h * C, fill=fillc, width=0, tags="base")
            if col not in self.wd.TONES_SET:
                for gx in range(int(x // 1), int(-(-(x + w) // 1))):
                    for gy in range(int(y // 1), int(-(-(y + h) // 1))):
                        self.covered.add((gx, gy))
        box = AREA_BOX.get(self.slot)
        if box:
            self.cv.create_rectangle((box[0] - self.X0) * C, (box[1] - self.Y0) * C, (box[2] + 1 - self.X0) * C, (box[3] + 1 - self.Y0) * C,
                                     outline="#c58a00", dash=(4, 3), width=2, tags="base")

    def save_pose(self, px):
        wd, cid = self.wd, str(self.char.get("id"))
        chars = []
        for q in wd.lst("chars"):
            if str(q.get("id")) == cid:
                q = {**q, "poses": {**(q.get("poses") or {}), self.pose: px}}
            chars.append(q)
        wd.pet.set_status(chars=chars)
        self.d.destroy()
        wd.refresh()

    def auto_pose(self):
        wd, cid = self.wd, str(self.char.get("id"))
        chars = []
        for q in wd.lst("chars"):
            if str(q.get("id")) == cid:
                q = {**q, "poses": {k: v for k, v in (q.get("poses") or {}).items() if k != self.pose}}
            chars.append(q)
        wd.pet.set_status(chars=chars)
        self.d.destroy()
        wd.refresh()

    def at(self, e):
        x, y = e.x // self.C + self.X0, e.y // self.C + self.Y0
        if self.X0 <= x < self.X0 + self.NX and self.Y0 <= y < self.Y0 + self.NY:
            return x, y
        return None

    def draw_cell(self, xy):
        tag = f"p{xy[0]}_{xy[1]}"
        self.cv.delete(tag)
        if xy in self.cells:
            C = self.C
            x0, y0 = (xy[0] - self.X0) * C, (xy[1] - self.Y0) * C
            if self.cells[xy] == "-":  # 擦掉的格子：白底 + 淡淡一个叉
                self.cv.create_rectangle(x0, y0, x0 + C, y0 + C, fill=PAPER, width=0, tags=tag)
                self.cv.create_line(x0 + 2, y0 + 2, x0 + C - 2, y0 + C - 2, fill="#d8d4cb", tags=tag)
            else:
                self.cv.create_rectangle(x0, y0, x0 + C, y0 + C, fill=self.cells[xy], width=0, tags=tag)

    def paint(self, e):
        xy = self.at(e)
        if xy:
            self.cells[xy] = self.color
            self.draw_cell(xy)

    def erase(self, e):
        xy = self.at(e)
        if not xy:
            return
        if xy in self.cells and self.cells[xy] != "-":
            del self.cells[xy]                 # 擦掉自己画的
            if xy in self.covered:
                self.cells[xy] = "-"           # 底下是小克：顺便把小克这一格也擦掉
        elif xy in self.covered:
            self.cells[xy] = "-"
        self.draw_cell(xy)

    def erase_all(self):
        for xy in self.covered:
            if xy not in self.cells:
                self.cells[xy] = "-"
                self.draw_cell(xy)

    def use(self, c):
        self.color = c
        self.cur.configure(bg=c)

    def more(self):
        c = colorchooser.askcolor(color=self.color, parent=self.d)[1]
        if c and c.lower() != "#ff00fe":
            self.use(c)

    def clear(self):
        for xy in list(self.cells):
            del self.cells[xy]
            self.draw_cell(xy)

    def save(self):
        if not self.cells and self.slot != "state":
            self.tip.configure(text=_("还什么都没画"))
            return
        px = ";".join(f"{x},{y},{c.lstrip('#').lower()}" for (x, y), c in self.cells.items())
        wd = self.wd
        if self.slot == "pose":
            self.save_pose(px)
            return
        if self.slot == "char":
            name = self.name.get().strip()[:8]
            if not name:
                self.tip.configure(text=_("先起个名字"))
                return
            cols = [c.lower() for c in self.cells.values() if c != "-"]
            main = max(set(cols), key=cols.count)
            new_id = "%x" % int(time.time() * 1000)
            wd.pet.set_status(chars=wd.lst("chars") + [{"id": new_id, "name": name, "px": px, "color": main, "by": "me"}],
                              look={**wd.look(), "char": "u:" + new_id, "color": main})
            self.d.destroy()
            wd.pet.say_once(_("换好啦！"))
            wd.refresh()
            return
        if self.slot == "state":
            self.d.destroy()
            self.done(px)
            return
        name = self.name.get().strip()[:8]
        if not name:
            self.tip.configure(text=_("先起个名字"))
            return
        wd = self.wd
        new_id = "%x" % int(time.time() * 1000)
        wd.pet.set_status(parts=wd.lst("parts") + [{"id": new_id, "name": name, "slot": self.slot, "px": px, "by": "me"}],
                          look={**wd.look(), self.slot: "u:" + new_id})
        self.d.destroy()
        wd.pet.say_once(_("穿上啦！"))
        wd.refresh()
