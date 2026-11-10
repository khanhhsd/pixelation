# Kết quả đánh giá định lượng

- Số ảnh đánh giá: **100**; kích thước pixel = **4**, số màu K = **16**.
- Ảnh tham chiếu: ảnh gốc đã chuẩn hóa (cắt về bội số của kích thước pixel).
- Giá trị: trung bình ± độ lệch chuẩn trên toàn bộ ảnh. ↑ càng cao càng tốt, ↓ càng thấp càng tốt.
- Nearest/Box average không giới hạn số màu và dithering dùng 4 mức/kênh (cố định), nên
  không cùng ngân sách màu với các phương pháp bảng màu K màu.

## 1. So sánh với các phương pháp đối chứng

| Phương pháp | PSNR (dB) ↑ | SSIM ↑ | ΔE2000 ↓ | Số màu | Pixel lẻ (%) ↓ | Thời gian (ms) |
|---|---|---|---|---|---|---|
| Nearest neighbor (đối chứng) | 21.57 ± 3.08 | 0.589 ± 0.132 | 4.811 ± 1.883 | 6229.25 ± 1526.75 | 90.02 ± 10.29 | 0.704 ± 0.536 |
| Box average | 23.80 ± 3.01 | 0.645 ± 0.119 | 4.046 ± 1.509 | 7267.40 ± 1507.23 | 91.06 ± 9.94 | 1.947 ± 0.899 |
| Median-cut palette (đối chứng) | 22.56 ± 2.55 | 0.592 ± 0.112 | 6.158 ± 1.696 | 16.00 ± 0.00 | 11.31 ± 6.54 | 26.33 ± 12.66 |
| K-means RGB | 23.07 ± 2.74 | 0.596 ± 0.112 | 5.726 ± 1.636 | 16.00 ± 0.00 | 8.885 ± 5.324 | 742.74 ± 159.99 |
| Ordered dithering | 16.32 ± 0.69 | 0.207 ± 0.057 | 15.75 ± 1.99 | 18.76 ± 4.62 | 19.15 ± 3.20 | 3.894 ± 1.689 |
| Floyd–Steinberg | 16.87 ± 0.69 | 0.238 ± 0.060 | 17.43 ± 1.86 | 27.50 ± 4.63 | 26.67 ± 3.54 | 779.14 ± 219.71 |
| **Proposed (đầy đủ)** | 21.99 ± 2.75 | 0.536 ± 0.128 | 5.667 ± 1.660 | 16.00 ± 0.00 | 0.063 ± 0.115 | 905.27 ± 212.33 |

## 2. Proposed so với Median-cut (đối chứng chính) trên từng ảnh

| Độ đo | Proposed tốt hơn | Hòa | Kém hơn |
|---|---|---|---|
| psnr | 14/100 | 0 | 86 |
| ssim | 0/100 | 0 | 100 |
| delta_e | 88/100 | 0 | 12 |
| isolated_pct | 100/100 | 0 | 0 |

## 3. Ablation – bỏ từng bước của pipeline

| Phương pháp | PSNR (dB) ↑ | SSIM ↑ | ΔE2000 ↓ | Số màu | Pixel lẻ (%) ↓ | Thời gian (ms) |
|---|---|---|---|---|---|---|
| Median-cut palette (đối chứng) | 22.56 ± 2.55 | 0.592 ± 0.112 | 6.158 ± 1.696 | 16.00 ± 0.00 | 11.31 ± 6.54 | 26.33 ± 12.66 |
| **Proposed (đầy đủ)** | 21.99 ± 2.75 | 0.536 ± 0.128 | 5.667 ± 1.660 | 16.00 ± 0.00 | 0.063 ± 0.115 | 905.27 ± 212.33 |
| Proposed − khử nhiễu | 22.01 ± 2.74 | 0.542 ± 0.126 | 5.683 ± 1.661 | 16.00 ± 0.00 | 0.082 ± 0.141 | 736.81 ± 111.08 |
| Proposed − Lab (dùng RGB) | 21.99 ± 2.84 | 0.546 ± 0.131 | 6.006 ± 1.762 | 16.00 ± 0.00 | 0.149 ± 0.218 | 837.51 ± 126.36 |
| Proposed − lọc đa số | 22.73 ± 2.67 | 0.565 ± 0.118 | 5.423 ± 1.541 | 16.00 ± 0.00 | 5.871 ± 3.666 | 886.77 ± 165.03 |

## 4. Ảnh hưởng của số màu K (kích thước pixel = 4)

| K | Median-cut palette (đối chứng) ΔE / pixel lẻ % | K-means RGB ΔE / pixel lẻ % | Proposed (đầy đủ) ΔE / pixel lẻ % |
|---|---|---|---|
| 8 | 7.09 / 5.06 | 6.60 / 3.84 | 6.38 / 0.01 |
| 16 | 6.16 / 11.31 | 5.73 / 8.89 | 5.67 / 0.06 |
| 32 | 5.51 / 19.92 | 5.17 / 16.03 | 5.40 / 0.32 |
| 64 | 5.08 / 30.07 | 4.82 / 24.87 | 5.34 / 1.01 |

## 5. Ảnh hưởng của kích thước pixel (K = 16)

| Pixel | Median-cut palette (đối chứng) SSIM / pixel lẻ % | K-means RGB SSIM / pixel lẻ % | Proposed (đầy đủ) SSIM / pixel lẻ % |
|---|---|---|---|
| 2 | 0.762 / 10.07 | 0.768 / 7.91 | 0.657 / 0.02 |
| 4 | 0.592 / 11.31 | 0.596 / 8.89 | 0.536 / 0.06 |
| 8 | 0.455 / 14.24 | 0.456 / 11.26 | 0.432 / 0.14 |
| 16 | 0.388 / 19.14 | 0.388 / 15.62 | 0.382 / 0.28 |
