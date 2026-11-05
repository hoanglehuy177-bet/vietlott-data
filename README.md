# 🎰 Vietlott Data

Dữ liệu kết quả xổ số Vietlott **Mega 6/45** và **Power 6/55** — tự động cập nhật hàng ngày.

## 📊 Dữ liệu

- **File:** `data/vietlott_data.json`
- **Nguồn:** minhchinh.com
- **Cập nhật:** Tự động lúc 19:15 ICT mỗi ngày qua GitHub Actions

## 🔄 GitHub Actions

Workflow `.github/workflows/crawl.yml` chạy hàng ngày:
1. Crawl kết quả 7 ngày gần nhất từ minhchinh.com
2. Thêm kỳ mới vào `data/vietlott_data.json`
3. Commit & push nếu có dữ liệu mới

Có thể chạy thủ công từ tab **Actions → Run workflow** và chọn số ngày cần crawl.

## 📱 Web App

Web app tự động load data từ repo này — luôn có kết quả mới nhất.

## Format dữ liệu

```json
{
  "date": "2026-10-08",
  "vietlott_type": "power_655",
  "main_numbers": ["01", "07", "12", "27", "31", "52"],
  "bonus_number": "06",
  "jackpot_value": 129672825150,
  "jackpot2_value": 3800633150,
  "winners": 0,
  "winners_jp2": 1,
  "winners_g3": 34621,
  "source": "minhchinh.com"
}
```
