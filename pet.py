# 小克桌宠 ClawdPet 的小命令：让桌宠变状态、说话。任何 AI 助手（Codex、Claude Code、Cursor、WorkBuddy……）都能用。
# 原创：Miaomiao（GitHub: Miaomiaomeowmeow）· CC BY-NC-SA 4.0 · https://github.com/Miaomiaomeowmeow/clawd-pet
#
# 用法（在哪个文件夹跑都行；项目名默认 = 当前文件夹的名字）：
#   python pet.py busy "在写登录页"          状态：urgent 着急 / busy 忙碌 / relaxed 悠闲 / cheer 欢呼 / sleep 睡觉（也认中文）
#   python pet.py cheer "做好啦" --project 我的网站
#   python pet.py say "随便说一句"            只换说的话，状态不变
#   python pet.py status                      看现在是什么状态
#   python pet.py recent                      看最近 10 条
#   python pet.py where                       桌宠装在哪
#   python pet.py hook busy | done | wait     给自动接法用（Claude Code 的 hooks、Codex 的 notify），见 hooks/ 文件夹
#   python pet.py state add 摸鱼 --pose relaxed --say "摸一下/嘘"     自己加状态（还有 part / color / preset / build，见 AI-RULES.md）
#   python pet.py char add 灰猫 --px "…"  /  char use 灰猫  /  char use 小克          换形象（自己画的角色，不只是小克）
#   python pet.py click claude | workbench | none | <程序路径或网址>  点一下小克打开什么（默认 Claude 应用）
#   python pet.py link workbench on|off  /  link talkie on|off          联动开关（装了的话第一次发现会自己打开）
# 桌宠每秒看一次 status.json，改了马上就变；桌宠没开着也没关系，下次打开就是这个状态。

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATUS = os.path.join(HERE, "status.json")
RECENT = os.path.join(HERE, "recent.json")
TONES = ("#6d6164", "#652062", "#7920e5", "#96b5e5", "#96b500")  # 描边备用色，和桌宠里的一样
STATES = {"urgent": "着急", "busy": "忙碌", "relaxed": "悠闲", "cheer": "欢呼", "sleep": "睡觉"}
ZH = {v: k for k, v in STATES.items()}
HOOK = {"busy": ("busy", "在干活…"), "done": ("cheer", "做完一步啦！"), "wait": ("urgent", "等你回我一下～")}
MAX_SAY = 40

try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass


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


def update(state=None, say=None, project=None):
    data = read_json(STATUS, {})
    data = data if isinstance(data, dict) else {}
    if state:
        data["state"] = state
    if say is not None:
        data["say"] = say[:MAX_SAY]
    write_json(STATUS, data)
    rec = read_json(RECENT, [])
    rec = rec if isinstance(rec, list) else []
    rec.append({"at": int(time.time()), "state": data.get("state", ""), "say": (say or "")[:MAX_SAY], "project": project or ""})
    write_json(RECENT, rec[-30:])
    return data


def take(args, flag):
    """从参数里拿出 --project 这种：返回 (值, 剩下的参数)"""
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1], args[:i] + args[i + 2:]
        return "", args[:i]
    return None, args


def hook(kind, extra):
    """自动接法：Claude Code 把这次的信息从 stdin 传进来（JSON，里面有 cwd）；Codex 的 notify 把 JSON 放在最后一个参数里"""
    info = {}
    raw = extra[-1] if extra else ""
    if not raw and not sys.stdin.isatty():
        try:  # 按 UTF-8 读：Windows 默认按 GBK 读，路径里有中文就会读坏
            raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        except (OSError, ValueError, AttributeError):
            raw = ""
    try:
        info = json.loads(raw) if raw else {}
    except ValueError:
        info = {}
    if kind not in HOOK:
        return
    if kind == "done" and isinstance(info, dict) and info.get("type") not in (None, "agent-turn-complete"):
        return
    cwd = info.get("cwd") if isinstance(info, dict) else None
    state, say = HOOK[kind]
    update(state, say, os.path.basename(os.path.normpath(cwd)) if cwd else "")


SLOTS = {"ears": "耳朵", "tail": "尾巴", "hold": "手上", "hat": "头上", "face": "脸上", "body": "身上"}


def clean_px(px):
    """像素：'x,y,颜色;x,y,颜色'，坐标同桌宠的格子（身子在 x 4～17、y 2～13），颜色 6 位十六进制；不合格的点丢掉"""
    out = []
    for item in str(px or "").split(";"):
        try:
            x, y, c = [t.strip() for t in item.split(",")]
            x, y, c = int(float(x)), int(float(y)), c.lstrip("#").lower()
            if c != "-":  # - = 把小克那一格擦掉
                int(c, 16)
            if (c == "-" or (len(c) == 6 and c != "ff00fe")) and -8 <= x <= 31 and -12 <= y <= 21:
                out.append(f"{x},{y},{c}")
        except ValueError:
            pass
    return ";".join(out[:200])


def wardrobe_cmd(kind, args):
    """加 / 删 / 列出 自己的状态、衣服、颜色（AI 照 AI-RULES.md 用）"""
    pose, args = take(args, "--pose")
    say, args = take(args, "--say")
    px, args = take(args, "--px")
    slot, args = take(args, "--slot")
    look, args = take(args, "--look")
    color, args = take(args, "--color")
    bw, args = take(args, "--w")
    bh, args = take(args, "--h")
    by, args = take(args, "--by")
    act, name = (args[0] if args else "list"), " ".join(args[1:]).strip()
    data = read_json(STATUS, {})
    data = data if isinstance(data, dict) else {}
    key = {"state": "states", "part": "parts", "color": "colors", "preset": "presets", "build": "builds", "char": "chars"}[kind]
    items = [q for q in data.get(key) or []]
    if act == "list":
        for q in items:
            print(q if isinstance(q, str) else q.get("color") if kind == "color" else q.get("name") if kind == "preset" else
                  f"{q.get('name')}  (宽 {round(float(q.get('sx') or 1) * 100)}% 高 {round(float(q.get('sy') or 1) * 100)}%)" if kind == "build" else f"{q.get('name')}  ({q.get('pose') or SLOTS.get(q.get('slot'), q.get('slot'))})")
        return 0
    if kind == "char" and act == "use":  # 换成这个形象（小克 = 换回小克）
        lk = dict(data.get("look") or {})
        if name in ("小克", "clawd", "Clawd"):
            lk.update({"char": "clawd", "color": "#d97757"})
        else:
            q = next((q for q in items if q.get("name") == name), None)
            if not q:
                print(f"没有叫「{name}」的形象（pet.py char list 看看有哪些）")
                return 2
            lk.update({"char": "u:" + str(q["id"]), "color": q.get("color") or lk.get("color") or "#d97757"})
        data["look"] = lk
        write_json(STATUS, data)
        print(f"换好了：{name}")
        return 0
    if act == "del":
        left = [q for q in items if (q if isinstance(q, str) else q.get("color") if kind == "color" else q.get("name")) != name]
        data[key] = left
        write_json(STATUS, data)
        print(f"删掉了 {len(items) - len(left)} 个")
        return 0
    if act != "add" or not name:
        print(f"用法：pet.py {kind} add 名字 …  /  pet.py {kind} del 名字  /  pet.py {kind} list")
        return 2
    new_id = "%x" % int(time.time() * 1000)
    if kind == "color":
        c = "#" + name.lstrip("#").lower()[:6]
        if c not in [q if isinstance(q, str) else q.get("color") for q in items]:
            items.append({"color": c, "name": c, "by": by or "ai"})
    elif kind == "char":
        p = clean_px(px)
        cols = [t.split(",")[2] for t in p.split(";") if t and not t.endswith(",-")]
        if len(cols) < 20:
            print("--px 太少了：一整只形象要 80～250 个点，脚踩在 y=18，左右居中在 x=11 附近（见 AI-RULES.md）")
            return 2
        main = (color or "").lstrip("#").lower()
        if main not in cols:
            main = max(set(cols), key=cols.count)
        items.append({"id": new_id, "name": name[:8], "px": p, "color": "#" + main, "by": by or "ai"})
    elif kind == "build":
        try:
            sx, sy = [max(.6, min(1.3, float(v or 100) / 100)) for v in (bw, bh)]
        except ValueError:
            print("--w / --h 是百分比，60～130，例 --w 120 --h 95")
            return 2
        items.append({"id": new_id, "name": name[:6], "sx": sx, "sy": sy, "by": by or "ai"})
    elif kind == "preset":
        try:
            lk = json.loads(look or "")
            assert isinstance(lk, dict)
        except (ValueError, AssertionError):
            print("--look 要写成 JSON，例 '{\"ears\":\"cat\",\"hat\":\"crown\",\"color\":\"#9b7bff\"}'")
            return 2
        items.append({"name": name[:12], "look": lk, "by": by or "ai"})
    elif kind == "state":
        pose = ZH.get(pose, pose) if pose else "busy"
        if pose not in STATES:
            print("--pose 只能是 " + " / ".join(STATES))
            return 2
        lines = [x.strip()[:MAX_SAY] for x in str(say or "").replace("|", "/").split("/") if x.strip()]
        items.append({"id": new_id, "name": name[:12], "pose": pose, "lines": lines[:6], "px": clean_px(px), "by": by or "ai"})
    else:
        if slot not in SLOTS:
            print("--slot 只能是 " + " / ".join(f"{k} {v}" for k, v in SLOTS.items()))
            return 2
        p = clean_px(px)
        if not p:
            print("--px 是空的或格式不对：'x,y,颜色;x,y,颜色'，例 '8,-2,ff8fc2;9,-2,ff8fc2'")
            return 2
        items.append({"id": new_id, "name": name[:12], "slot": slot, "px": p, "by": by or "ai"})
    data[key] = items
    write_json(STATUS, data)
    print(f"加好了：{name}（右键小克 → {'状态' if kind == 'state' else '造型 → 换形象' if kind == 'char' else '造型 → 打开衣柜'} 就能看到）"
          + (f"；换上它：pet.py char use {name}" if kind == "char" else ""))
    return 0


SETTINGS = os.path.join(HERE, "settings.json")


def settings_cmd(cmd, args):
    """pet.py click claude|workbench|none|<程序路径或网址>   ·   pet.py link workbench|talkie on|off"""
    d = read_json(SETTINGS, {})
    d = d if isinstance(d, dict) else {}
    if cmd == "click":
        t = " ".join(args).strip()
        if not t:
            print("用法：pet.py click claude | workbench | none | <程序路径或网址>")
            return 2
        if t in ("claude", "workbench", "none"):
            d["click"] = t
        else:
            if not t.startswith(("http://", "https://")) and not os.path.exists(t):
                print(f"找不到「{t}」：写程序的完整路径，或者 http 开头的网址")
                return 2
            d["click"], d["clickTarget"] = "app", t
        write_json(SETTINGS, d)
        print(f"好了：点一下小克 = 打开 {t}")
        return 0
    if len(args) < 2 or args[0] not in ("workbench", "talkie") or args[1] not in ("on", "off"):
        print("用法：pet.py link workbench on|off   /   pet.py link talkie on|off")
        return 2
    key = {"workbench": "linkWorkbench", "talkie": "linkTalkie"}[args[0]]
    d[key] = args[1] == "on"
    d[{"workbench": "workbenchSeen", "talkie": "talkieSeen"}[args[0]]] = True
    write_json(SETTINGS, d)
    print(f"好了：{'工作台' if args[0] == 'workbench' else '克讲机'}联动{'打开' if d[key] else '关掉'}了")
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(open(__file__, encoding="utf-8").read().split("\n\n")[0].replace("# ", "").replace("#", ""))
        return 0
    project, argv = take(argv, "--project")
    if project is None:
        project = os.path.basename(os.getcwd())
    cmd, rest = argv[0], argv[1:]
    if cmd == "hook":
        try:
            hook(rest[0] if rest else "", rest[1:])
        except Exception:
            pass  # 桌宠的事出错了也别影响对话
        return 0
    if cmd == "status":
        d = read_json(STATUS, {})
        print(f"{STATES.get(d.get('state'), d.get('state') or '还没有')}  {d.get('say') or ''}")
        return 0
    if cmd == "recent":
        rec = read_json(RECENT, [])
        for r in (rec if isinstance(rec, list) else [])[-10:]:
            when = time.strftime("%m-%d %H:%M", time.localtime(r.get("at") or 0))
            print(f"{when}  {STATES.get(r.get('state'), '')}  {r.get('project') or ''}  {r.get('say') or ''}")
        return 0
    if cmd == "where":
        print(HERE)
        return 0
    if cmd == "say":
        update(None, " ".join(rest), project)
        print("桌宠说：" + " ".join(rest)[:MAX_SAY])
        return 0
    if cmd in ("state", "part", "color", "preset", "build", "char"):
        return wardrobe_cmd(cmd, rest)
    if cmd in ("click", "link"):
        return settings_cmd(cmd, rest)
    state = ZH.get(cmd, cmd)
    custom = {str(q.get("name")): "c:" + str(q.get("id")) for q in read_json(STATUS, {}).get("states") or [] if isinstance(q, dict)}
    if state in custom:  # 自己加的状态，按名字叫
        update(custom[state], " ".join(rest), project)
        print(f"桌宠：{state}  {' '.join(rest)[:MAX_SAY]}")
        return 0
    if state not in STATES:
        print(f"不认识「{cmd}」。状态只能是：" + " / ".join(f"{k} {v}" for k, v in STATES.items())
              + ("，或自己加的：" + " / ".join(custom) if custom else ""))
        return 2
    say = " ".join(rest)
    update(state, say, project)
    print(f"桌宠：{STATES[state]}  {say[:MAX_SAY]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
