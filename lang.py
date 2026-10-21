# 小克桌宠 ClawdPet 的多语言：界面上的话写的是中文，_() 按现在的语言换成对应的翻译（翻译在 lang.json）。
# 原创：Miaomiao（GitHub: Miaomiaomeowmeow）· CC BY-NC-SA 4.0 · https://github.com/Miaomiaomeowmeow/clawd-pet
#
# 语言：settings.json 的 "lang"；没设就看 Windows 的显示语言。换语言后小克会重启一下。
# 想加一种语言：在 lang.json 每一条里加上它的翻译，再在下面 LANGS 里加一行（找不到翻译的话会显示中文原文）。

import ctypes
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LANGS = {"zh": "简体中文", "zh-TW": "繁體中文", "en": "English", "ja": "日本語", "ko": "한국어"}
# 给 AI 的话里说“用什么语言写”
LANG_NAME = {"zh": "简体中文", "zh-TW": "繁體中文", "en": "English", "ja": "日本語", "ko": "한국어"}
# 每种语言用的字体（Windows 自带）
FONTS = {"zh": "Microsoft YaHei UI", "zh-TW": "Microsoft JhengHei UI", "en": "Segoe UI", "ja": "Yu Gothic UI", "ko": "Malgun Gothic"}


def _read(path, fallback):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return fallback


def system_lang():
    """Windows 的显示语言 → 我们有的语言"""
    try:
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError):
        return "en"
    prim = lid & 0x3FF
    if prim == 0x04:  # 中文：台湾、香港、澳门用繁体
        return "zh-TW" if lid in (0x0404, 0x0C04, 0x1404) else "zh"
    return {0x11: "ja", 0x12: "ko"}.get(prim, "en")


def pick():
    want = (_read(os.path.join(HERE, "settings.json"), {}) or {}).get("lang") or "auto"
    return want if want in LANGS else system_lang()


CUR = pick()
_TABLE = _read(os.path.join(HERE, "lang.json"), {}) if CUR != "zh" else {}


def _(text):
    """中文原文 → 现在语言的翻译；没有翻译就用原文"""
    if CUR == "zh":
        return text
    return (_TABLE.get(text) or {}).get(CUR) or text


def font():
    return FONTS.get(CUR, "Segoe UI")
