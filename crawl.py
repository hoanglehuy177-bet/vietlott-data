#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vietlott Crawler — dùng cho GitHub Actions
Crawl kết quả Mega 6/45 và Power 6/55 từ minhchinh.com
Lưu vào data/vietlott_data.json
"""

import re
import json
import time
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
DATA_FILE = Path("data/vietlott_data.json")
DATA_FILE.parent.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer": "https://www.minhchinh.com/",
}

VIETLOTT_CFG = {
    "mega_645": {
        "max_num": 45, "count_main": 6, "has_bonus": False,
        "draw_days": {2, 4, 6},   # T4, T6, CN (Python weekday: Mon=0)
        "url_tpl": "https://www.minhchinh.com/xs-mega-645-ket-qua-mega-645-ngay-{d}-{m}-{y}.html",
    },
    "power_655": {
        "max_num": 55, "count_main": 6, "has_bonus": True,
        "draw_days": {1, 3, 5},   # T3, T5, T7
        "url_tpl": "https://www.minhchinh.com/xs-power-655-ket-qua-power-655-ngay-{d}-{m}-{y}.html",
    },
}

# ─────────────────────────────────────────────
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(records):
    # Sort by date ascending
    records.sort(key=lambda r: r["date"])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu {len(records)} kỳ vào {DATA_FILE}")

def existing_keys(records):
    return {(r["date"], r["vietlott_type"]) for r in records}

# ─────────────────────────────────────────────
def parse_numbers(html, cfg):
    """Trích xuất bộ số từ HTML minhchinh.com"""
    max_n = cfg["max_num"]
    count = cfg["count_main"]
    has_bonus = cfg["has_bonus"]
    target = count + 1 if has_bonus else count

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "aside", "nav", "header", "footer", "form"]):
        tag.decompose()
    for tag in soup.find_all(class_=re.compile(
            r"(sidebar|widget|hot|latest|menu|tin-tuc|right|ads)", re.I)):
        tag.decompose()

    draws = {}

    # Priority 1: .mega-detail / .power-detail
    for cont in soup.find_all("div", class_=re.compile(r"(mega-detail|power-detail)", re.I)):
        cid = id(cont)
        if cid not in draws:
            draws[cid] = []
        for num in re.findall(r"\b(\d{2})\b", cont.get_text(separator=" ")):
            if num not in draws[cid] and 1 <= int(num) <= max_n:
                draws[cid].append(num)

    valid = [v for v in draws.values() if len(v) >= count]

    # Priority 2: ball class
    if not valid:
        draws = {}
        for tag in soup.find_all(class_=re.compile(r"(bong|ball|so_trung|ve_so)", re.I)):
            txt = tag.get_text(strip=True)
            if re.match(r"^\d{2}$", txt) and 1 <= int(txt) <= max_n:
                cont = (tag.find_parent(["table", "ul"])
                        or tag.find_parent("div", class_=re.compile(r"(box|panel|result|kq|wrap|row)", re.I))
                        or tag.find_parent("div"))
                if cont:
                    cid = id(cont)
                    if cid not in draws:
                        draws[cid] = []
                    if txt not in draws[cid]:
                        draws[cid].append(txt)
        valid = [v for v in draws.values() if len(v) >= count]

    if not valid:
        return None, None

    # Pick best set
    best = next((v for v in valid if len(v) == target), valid[0])
    main = sorted(best[:count], key=int)
    bonus = best[count] if has_bonus and len(best) > count else None
    return main, bonus

def parse_jackpot(html, cfg):
    """Trích xuất giá trị jackpot, số người trúng từ bảng HTML"""
    has_bonus = cfg["has_bonus"]
    soup = BeautifulSoup(html, "html.parser")
    jp1, jp2, w1, w2, g3 = 0, 0, 0, 0, 0

    for table in soup.find_all("table"):
        txt = table.get_text().lower()
        if not any(k in txt for k in ["jackpot", "đặc biệt", "giải ba", "giải 3"]):
            continue
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if len(tds) < 3:
                continue
            name = tds[0].get_text(strip=True).lower()
            qty_s = tds[-2].get_text(strip=True)
            val_s = tds[-1].get_text(strip=True)
            money = int(re.sub(r"[^\d]", "", val_s)) if re.sub(r"[^\d]", "", val_s) else 0
            win = 0
            if qty_s not in ["-", "X", "x", ""] and "x" not in qty_s.lower():
                win = int(re.sub(r"[^\d]", "", qty_s)) if re.sub(r"[^\d]", "", qty_s) else 0
            if "jackpot 1" in name or "đặc biệt 1" in name:
                jp1, w1 = money, win
            elif "jackpot 2" in name or "đặc biệt 2" in name:
                jp2, w2 = money, win
            elif ("jackpot" in name or "đặc biệt" in name) and "2" not in name:
                jp1, w1 = money, win
            elif "giải ba" in name or "giải 3" in name:
                g3 = win
        if jp1 > 0 or g3 > 0:
            break

    return jp1, jp2, w1, w2, g3

# ─────────────────────────────────────────────
def fetch_one(d: date, vtype: str, session) -> dict | None:
    cfg = VIETLOTT_CFG[vtype]
    url = cfg["url_tpl"].format(d=f"{d.day:02d}", m=f"{d.month:02d}", y=d.year)

    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        resp.encoding = "utf-8"
        html = resp.text
    except Exception as e:
        print(f"  ⚠️  GET {url} → {e}")
        return None

    # Bot-block check
    if any(k in html.lower() for k in ["cloudflare", "access denied", "captcha", "403 forbidden"]):
        print(f"  🚫 Bị chặn: {url}")
        return None

    main, bonus = parse_numbers(html, cfg)
    if not main:
        # Trang tồn tại nhưng chưa có kết quả (thường là trang "sắp diễn ra")
        if any(k in html.lower() for k in ["sắp diễn ra", "chưa có kết quả", "updating", "coming soon"]):
            print(f"  ⏳ Chưa có kết quả: {d}")
        else:
            print(f"  ❓ Không parse được số: {url}")
        return None

    jp1, jp2, w1, w2, g3 = parse_jackpot(html, cfg)

    record = {
        "date": str(d),
        "vietlott_type": vtype,
        "main_numbers": main,
        "jackpot_value": jp1,
        "winners": w1,
        "winners_g3": g3,
        "source": "minhchinh.com",
    }
    if cfg["has_bonus"] and bonus:
        record["bonus_number"] = bonus
        record["jackpot2_value"] = jp2
        record["winners_jp2"] = w2

    return record

# ─────────────────────────────────────────────
def get_draw_dates(vtype: str, start: date, end: date):
    """Lấy tất cả ngày xổ của loại vtype trong khoảng [start, end]"""
    cfg = VIETLOTT_CFG[vtype]
    draw_days = cfg["draw_days"]
    dates = []
    cur = start
    while cur <= end:
        # Python weekday: Mon=0 … Sun=6; minhchinh dùng T2=1,T3=2,...,CN=6 (isoweekday)
        # draw_days trong cfg theo Python weekday (Mon=0): 2=Wed,4=Fri,6=Sun cho mega
        if cur.weekday() in draw_days:
            dates.append(cur)
        cur += timedelta(days=1)
    return dates

# ─────────────────────────────────────────────
def main():
    # Đọc --days từ arg, mặc định 7
    days_back = 7
    for arg in sys.argv[1:]:
        if arg.startswith("--days="):
            days_back = int(arg.split("=")[1])
        elif arg.lstrip("-").isdigit():
            days_back = int(arg.lstrip("-"))

    today = date.today()
    start = today - timedelta(days=days_back)
    print(f"🔍 Crawl từ {start} đến {today} (days_back={days_back})")

    records = load_data()
    keys = existing_keys(records)
    new_count = 0

    with requests.Session() as session:
        for vtype in ["mega_645", "power_655"]:
            dates = get_draw_dates(vtype, start, today)
            print(f"\n📋 {vtype}: {len(dates)} ngày cần kiểm tra")
            for d in dates:
                key = (str(d), vtype)
                if key in keys:
                    print(f"  ✓ {d} đã có")
                    continue
                print(f"  ⬇️  Đang lấy {vtype} {d}...", end=" ", flush=True)
                result = fetch_one(d, vtype, session)
                if result:
                    records.append(result)
                    keys.add(key)
                    new_count += 1
                    print(f"→ {result['main_numbers']}")
                else:
                    print("→ bỏ qua")
                time.sleep(1.5)  # Lịch sự với server

    print(f"\n{'='*50}")
    print(f"✅ Thêm {new_count} kỳ mới | Tổng: {len(records)} kỳ")
    save_data(records)

if __name__ == "__main__":
    main()
