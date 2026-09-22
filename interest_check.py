# -*- coding: utf-8 -*-
"""interest_check.py — 敘事有趣度檢測工具

用法:
  python interest_check.py <章節檔...>
  python interest_check.py manuscript_v2/ch*.md
  python interest_check.py ch001.md ch002.md --json
"""
import sys, re, json, glob
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── 微觀指標（單章） ──────────────────────────────────

CONCRETE_NOUNS = [
    # 實體物件
    "電話", "手機", "筆電", "電腦", "答錄機", "交換機", "機櫃", "交接箱",
    "掃描器", "轉接器", "硬盤", "磁碟", "晶片", "算盒", "天線", "電表",
    "水箱", "水泵", "電梯", "扶梯", "衣車", "裁縫", "玻璃櫃", "收銀機",
    "日曆", "照片", "信", "筆記", "筆", "紙", "地圖", "紅燈", "黃燈",
    "霓虹燈", "路燈", "窗簾", "旗袍", "衣架", "拐杖", "頭盔", "電單車",
    "貨車", "工服", "告示", "傳單", "銅牌", "橫幅", "門", "窗", "牆",
    "台階", "巷", "天橋", "水族箱", "涼茶", "茶餐廳", "商場", "當舖",
    "寫字樓", "機房", "水管", "電纜", "光纖", "銅線", "同軸", "電話線",
    "頻道", "頻譜", "掃描", "錄音", "播放", "喇叭", "耳機", "麥克風",
    "燈", "開關", "插座", "電線", "電池", "備用", "工具", "螺絲", "扳手",
    "手套", "靴", "背包", "手錶", "項鏈", "戒指", "眼鏡", "鏡", "瓶",
    "杯", "碗", "筷", "匙", "鍋", "爐", "冰箱", "洗衣機", "電視", "收音機",
]

HOOK_PATTERNS = [
    r"[？?]\s*$",                          # 結尾是問句
    r"然後[她他它][^\n]{0,30}[？?]",      # 然後她...？
    r"[^\n]{0,20}按下[^\n]{0,10}[錄音通話撥號]",  # 按下某個動作
    r"[^\n]{0,20}打開[^\n]{0,10}[^\n]{0,5}[？?]", # 打開...？
    r"[^\n]{0,15}響[^\n]{0,10}了",         # 某個東西響了
    r"[^\n]{0,15}亮[^\n]{0,10}了",         # 某個東西亮了
    r"[^\n]{0,15}開[^\n]{0,10}了[^\n]{0,5}[？?]", # 開了...？
    r"第[^\n]{0,10}[？?]",                  # 第...？
    r"[^\n]{0,20}不是[^\n]{0,15}[。\n]",   # 不是...（轉折）
    r"[^\n]{0,20}原來[^\n]{0,15}",          # 原來...
]

SURPRISE_PATTERNS = [
    r"竟然", r"居然", r"沒想到", r"意想不到",
    r"不是[^。]{0,15}而是", r"突然",
    r"原來", r"才發現", r"才想起",
    r"第一次", r"從來沒", r"從未",
]

STAKES_PATTERNS = [
    r"風險", r"代價", r"危險", r"威脅", r"失去", r"沒收",
    r"判死", r"歸零", r"清除", r"拆", r"註銷", r"停用",
    r"違反", r"違規", r"處罰", r"賠償", r"拒保",
    r"不可逆", r"沒法", r"來不及", r"時間不多",
]

REVELATION_PATTERNS = [
    r"原來", r"才發現", r"才明白", r"才想起",
    r"不是[^。]{0,15}而是", r"其實",
    r"真相", r"秘密", r"隱藏",
]

DIMENSION_JUMP = [
    (r"一[粒顆個]星|宇宙|銀河|光年|星系", "宇宙尺度"),
    (r"全城|全市|全球|整個城市|全世界", "城市/全球尺度"),
    (r"一[棟座幢]樓|一條街|一個區|一片", "街區尺度"),
    (r"一[間間]房|一個角落|一張台|一部機", "房間尺度"),
    (r"一[粒顆個]灰|一[條根]線|一[個個]字|一[粒粒]塵", "微觀尺度"),
    (r"十八年|三年|三十年|一輩子", "生命尺度"),
    (r"一[晚個]夜|一分鐘|一秒|凌晨", "瞬間尺度"),
]

def analyze_chapter(text):
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("#"))
    plain = re.sub(r"\s+", "", body)
    n = len(plain)
    paras = [p.strip() for p in body.split("\n") if p.strip()]
    last_para = paras[-1] if paras else ""
    last_200 = plain[-200:] if len(plain) >= 200 else plain

    # 具體物件
    concrete_hits = {}
    for noun in CONCRETE_NOUNS:
        c = body.count(noun)
        if c > 0:
            concrete_hits[noun] = c
    concrete_count = sum(concrete_hits.values())
    concrete_types = len(concrete_hits)

    # 章末鉤子
    hook_score = 0
    hook_evidence = []
    for pat in HOOK_PATTERNS:
        if re.search(pat, last_para, re.MULTILINE):
            hook_score += 1
            hook_evidence.append(pat[:20])
    # 問號在最後 100 字
    if re.search(r"[？?]", last_200):
        hook_score += 1
        hook_evidence.append("末尾問句")

    # 驚喜
    surprise_hits = {}
    for pat in SURPRISE_PATTERNS:
        c = len(re.findall(pat, body))
        if c:
            surprise_hits[pat] = c
    surprise_count = sum(surprise_hits.values())

    # 賭注
    stakes_hits = {}
    for pat in STAKES_PATTERNS:
        c = len(re.findall(pat, body))
        if c:
            stakes_hits[pat] = c
    stakes_count = sum(stakes_hits.values())

    # 揭露
    revelation_count = 0
    for pat in REVELATION_PATTERNS:
        revelation_count += len(re.findall(pat, body))

    # 尺度跳躍
    dims = []
    for pat, name in DIMENSION_JUMP:
        if re.search(pat, body):
            dims.append(name)
    dim_count = len(set(dims))

    # 疑問數（章內開放問題）
    questions = len(re.findall(r"[？?]", body))

    # 抽象 vs 具體比率
    abstract_words = ["感覺", "意識", "概念", "意義", "本質", "精神", "靈魂",
                      "自由", "命運", "永恆", "無限", "未知", "可能", "希望",
                      "恐懼", "愛", "恨", "孤獨", "存在", "時間", "空間"]
    abstract_count = sum(body.count(w) for w in abstract_words)

    return {
        "chars": n,
        "paras": len(paras),
        "concrete_types": concrete_types,
        "concrete_total": concrete_count,
        "hook_score": hook_score,
        "hook_evidence": hook_evidence,
        "surprise_count": surprise_count,
        "stakes_count": stakes_count,
        "revelation_count": revelation_count,
        "dimensions": dims,
        "dim_count": dim_count,
        "questions": questions,
        "abstract_count": abstract_count,
        "abstract_ratio": round(abstract_count / max(n, 1) * 1000, 2),
    }


def analyze_arc(chapters_data):
    """跨章分析：懸念帳簿、趨勢、賭注曲線。"""
    open_q = 0
    closed_q = 0
    stakes_trend = []
    hook_trend = []
    dim_trend = []
    revelations = []

    for i, (name, data) in enumerate(chapters_data):
        # 懸念：問題數 vs 揭露數
        open_q += data["questions"]
        closed_q += data["revelation_count"]
        # 粗略：每章問題累加，揭露抵消
        net_open = open_q - closed_q

        stakes_trend.append(data["stakes_count"])
        hook_trend.append(data["hook_score"])
        dim_trend.append(data["dim_count"])

        if data["revelation_count"] > 0:
            revelations.append(i + 1)

    # 賭注趨勢：後半 vs 前半
    half = len(stakes_trend) // 2
    if half > 0:
        first_half = sum(stakes_trend[:half]) / half
        second_half = sum(stakes_trend[half:]) / max(len(stakes_trend) - half, 1)
        stakes_direction = "↑" if second_half >= first_half else "↓"
    else:
        stakes_direction = "="

    # 鉤子平均
    avg_hook = sum(hook_trend) / max(len(hook_trend), 1)

    # 尺度跳躍密度
    avg_dims = sum(dim_trend) / max(len(dim_trend), 1)

    return {
        "net_open_questions": open_q - closed_q,
        "open_ratio": round(open_q / max(closed_q, 1), 1),
        "stakes_direction": stakes_direction,
        "avg_hook_score": round(avg_hook, 1),
        "avg_dimensions": round(avg_dims, 1),
        "revelation_chapters": revelations,
        "chapters_without_revelation": [
            i + 1 for i in range(len(chapters_data))
            if chapters_data[i][1]["revelation_count"] == 0
        ],
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv

    files = []
    for a in args:
        if "*" in a or "?" in a:
            files.extend(sorted(glob.glob(a)))
        else:
            files.append(a)

    if not files:
        print("用法: python interest_check.py <章節檔...>")
        sys.exit(1)

    chapters_data = []
    for f in files:
        p = Path(f)
        if not p.exists():
            print(f"找不到: {f}")
            continue
        text = p.read_text(encoding="utf-8")
        data = analyze_chapter(text)
        chapters_data.append((p.name, data))

    if not chapters_data:
        print("沒有可分析的章節。")
        sys.exit(1)

    arc = analyze_arc(chapters_data)

    if as_json:
        print(json.dumps({"chapters": [
            {"file": n, **d} for n, d in chapters_data
        ], "arc": arc}, ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print("敘事有趣度檢測報告")
    print("=" * 60)

    for name, d in chapters_data:
        print(f"\n【{name}】 {d['chars']}字 {d['paras']}段")
        flags = []

        if d["concrete_types"] < 3:
            flags.append(f"⚠ 具體物件不足 ({d['concrete_types']}種，需≥3)")
        if d["hook_score"] == 0:
            flags.append("⚠ 章末無鉤子")
        if d["stakes_count"] == 0:
            flags.append("⚠ 無賭注/風險詞")
        if d["dim_count"] == 0:
            flags.append("⚠ 無尺度跳躍")
        if d["abstract_ratio"] > 5:
            flags.append(f"⚠ 抽象詞偏高 ({d['abstract_ratio']}‰)")
        if d["questions"] == 0 and d["revelation_count"] == 0:
            flags.append("⚠ 無問題亦無揭露（平章）")

        if flags:
            for f in flags:
                print(f"  {f}")
        else:
            print(f"  ✓ 具體物件 {d['concrete_types']}種 | 鉤子分 {d['hook_score']} | "
                  f"賭注 {d['stakes_count']} | 揭露 {d['revelation_count']} | "
                  f"尺度 {d['dim_count']} | 問題 {d['questions']}")

    print("\n" + "=" * 60)
    print("跨章趨勢")
    print("=" * 60)
    print(f"  懸念帳簿淨開放問題: {arc['net_open_questions']}")
    print(f"  開放/已解決比: {arc['open_ratio']}:1 (目標 3:1 ~ 5:1)")
    print(f"  賭注方向: {arc['stakes_direction']} (後半 vs 前半)")
    print(f"  平均鉤子分: {arc['avg_hook_score']} (每章滿分約3)")
    print(f"  平均尺度跳躍: {arc['avg_dimensions']} 種/章")
    print(f"  有揭露的章: {arc['revelation_chapters']}")

    # 警告
    print("\n⚠ 警告:")
    if arc["open_ratio"] > 8:
        print("  懸念堆積過多，考慮殺死一條最弱的")
    elif arc["open_ratio"] < 1.5:
        print("  懸念太少，快要悶，加新問題")
    if arc["stakes_direction"] == "↓":
        print("  賭注在下降，加不可逆的代價")
    if arc["avg_hook_score"] < 1:
        print("  多章無鉤子，章末需要懸而未決")
    if len(arc["revelation_chapters"]) == 0:
        print("  全程無揭露，讀者會失去信任")
    elif len(arc["revelation_chapters"]) < len(chapters_data) // 10:
        print("  揭露太疏，每10章至少1次")


if __name__ == "__main__":
    main()
