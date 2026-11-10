# Chuyển ảnh thành Pixel Art bằng pipeline lượng tử hóa màu

Đồ án Xử lý ảnh – **Lựa chọn 2: Dự án xử lý ảnh thực tế**.

Bài toán: cho một ảnh chụp màu bất kỳ, tạo ảnh phong cách *pixel art* gồm một lưới
ô vuông thô (kích thước pixel `P`) và một bảng màu nhỏ `K` màu. Ảnh kết quả phải
**giống ảnh gốc** (PSNR, SSIM, ΔE2000 tốt) và **sạch** như pixel art vẽ tay, tức là ít
"pixel lẻ" (ô có màu khác hẳn mọi ô xung quanh).

Pipeline đề xuất được so sánh với các phương pháp đối chứng (nearest neighbor,
median-cut của Pillow, K-means RGB, dithering) trên **100 ảnh của tập BSDS300**.

## 1. Pipeline

```
Ảnh màu ─► (1) Tiền xử lý ─► (2) Lấy mẫu xuống ─► (3) Lượng tử hóa màu ─► (4) Hậu xử lý ─► (5) Phóng to ─► Pixel art
           chuẩn hóa kích      trung bình khối      K-means trên CIELAB      lọc đa số trên       nearest
           thước + lọc         P×P (box)            (khởi tạo k-means++)     lưới nhãn (loại      neighbor
           trung vị 3×3                                                      pixel lẻ) + viền
                                                                             Sobel (tùy chọn)
```

| Bước | Phương pháp | Tham số mặc định | Lý do chọn |
|---|---|---|---|
| Tiền xử lý | Resize Lanczos (tùy chọn), cắt về bội số của `P`; lọc trung vị 3×3 | `max_side=None`, lọc 3×3 | Lọc trung vị loại nhiễu xung và chi tiết vụn nhưng giữ biên, nhờ vậy lưới thô bớt ô lẻ |
| Lấy mẫu xuống | Trung bình vùng (box filter) mỗi khối P×P | `P=4` | Chống răng cưa (aliasing) so với lấy mẫu điểm |
| Lượng tử hóa | K-means trong không gian CIELAB, khởi tạo k-means++ | `K=16`, seed 0 | Khoảng cách Lab gần với cảm nhận màu của mắt hơn RGB; giữ được màu nhỏ nhưng nổi bật mà median-cut hay làm mất |
| Hậu xử lý | Lọc đa số (mode) có điều kiện: chỉ thay ô không trùng nhãn với ô nào trong 8 lân cận | 1 lượt | Loại pixel lẻ nhưng không làm mòn nét mảnh rộng từ 2 ô trở lên |
| Phóng to | Nearest neighbor | – | Giữ cạnh ô vuông sắc nét |

Kiến thức của học phần được dùng: lấy mẫu và lượng tử hóa ảnh; lọc không gian
(lọc trung vị, lọc trung bình); phát hiện biên Sobel; lọc đa số / xử lý hình thái
trên ảnh nhãn; phân cụm K-means. *Chú thích số chương cụ thể theo đề cương của lớp
được ghi trong báo cáo.*

## 2. Cấu trúc thư mục

```text
code/
├── pixel_art_studio/
│   ├── pipeline.py        # Pipeline đề xuất (5 bước)
│   ├── processing.py      # Các phương pháp đối chứng + K-means dùng chung
│   ├── metrics.py         # PSNR, SSIM, ΔE2000, số màu, tỉ lệ pixel lẻ
│   ├── controller.py      # Ứng dụng desktop (Tkinter)
│   ├── studio_view.py
│   ├── preview_window.py
│   └── app.py
├── run_pipeline.py        # Chạy trên 1 ảnh hoặc 1 thư mục (dòng lệnh)
├── evaluate.py            # Đánh giá định lượng + ablation + vẽ hình
├── download_data.py       # Tải bộ dữ liệu BSDS300
└── pixel_art_experiments.ipynb
samples/                   # 9 ảnh mẫu (lấy từ tập test BSDS300)
tests/                     # Unit test
results/eval/              # Kết quả đánh giá: CSV, summary.md, hình fig_*.png
docs/
├── nhom.json              # Thông tin lớp, nhóm, thành viên (điền trước khi build)
├── assets/                # Hình và số liệu trích từ results/eval (sinh tự động)
└── out/                   # BaoCao.docx/.pdf, Slide.pptx/.pdf (sinh tự động)
tools/                     # Script sinh báo cáo, slide và file zip nộp bài
requirements.txt
```

## 3. Môi trường và cài đặt

- Python ≥ 3.10 (đã kiểm thử với Python 3.12, Windows 11). Ứng dụng giao diện cần Tkinter (có sẵn trong bản cài Python chuẩn).
- Thư viện: NumPy, Pillow, scikit-image, matplotlib.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 4. Dữ liệu

- **BSDS300** (Berkeley Segmentation Dataset), tập test gồm 100 ảnh màu 481×321:
  https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/bsds/BSDS300-images.tgz
- Tải và giải nén tự động vào `data/BSDS300/images/`:

```powershell
python code/download_data.py
```

Bài toán không cần nhãn tay: ảnh gốc đã chuẩn hóa chính là ảnh tham chiếu để tính độ đo.

## 5. Chạy chương trình

**Chạy trên ảnh mẫu** (pipeline đề xuất, `P=4`, `K=16`):

```powershell
python code/run_pipeline.py --input samples --output results/samples
```

Đầu ra mong đợi: các file `results/samples/<tên>_pipeline.png` và một bảng độ đo in ra màn hình, ví dụ:

```text
image                       PSNR    SSIM  dE2000  colors   isol%      ms
101085.jpg                 ...
Saved 9 result(s) to ...\results\samples
```

Một số tùy chọn khác:

```powershell
# Lưu ảnh từng bước của pipeline, pixel thô hơn, 8 màu, có viền
python code/run_pipeline.py --input samples/42049.jpg --pixel-size 8 --colors 8 --outline --save-stages

# Chạy một phương pháp đối chứng: nearest, palette, kmeans, floyd-steinberg, ...
python code/run_pipeline.py --input samples --method palette
```

**Đánh giá định lượng** trên 100 ảnh (mất khoảng vài phút, chạy song song nhiều tiến trình):

```powershell
python code/evaluate.py --data data/BSDS300/images/test --out results/eval
```

Đầu ra mong đợi trong `results/eval/`:

- `metrics_per_image.csv`: độ đo của từng ảnh × phương pháp × tham số.
- `summary.md`: bảng trung bình ± độ lệch chuẩn, tỉ lệ thắng/thua theo từng ảnh, ablation, ảnh hưởng của `K` và `P`.
- `fig_comparison.png`, `fig_zoom.png`, `fig_pipeline_stages.png`, `fig_metrics.png`, `fig_sweep_k.png`.

Thêm `--limit 10 --no-sweep` để chạy thử nhanh.

**Ứng dụng giao diện** (xem trước 9 kiểu trên một ảnh, chuyển đổi hàng loạt): xem
hướng dẫn từng bước ở mục 5.1 ngay dưới đây.

### 5.1. Khởi chạy ứng dụng giao diện từng bước (Windows)

**Bước 1. Mở terminal.** Chọn một trong hai cách:
- Nhấn `Win + R`, gõ `powershell` rồi nhấn Enter; hoặc
- Trong VS Code: menu **Terminal → New Terminal** (`` Ctrl + ` ``).

**Bước 2. Kiểm tra Python** (cần phiên bản 3.10 trở lên):

```powershell
python --version
```

Nếu báo `'python' is not recognized` hoặc mở Microsoft Store, hãy cài Python từ
https://www.python.org/downloads/ và tích chọn **Add python.exe to PATH** khi cài.

**Bước 3. Di chuyển vào thư mục project** (thay đường dẫn cho đúng với máy của bạn):

```powershell
cd C:\Users\ADMIN\Downloads\pixelation-main\pixelation-main
```

**Bước 4. Cài thư viện (chỉ cần làm một lần):**

```powershell
python -m pip install -r requirements.txt
```

Kiểm tra lại: lệnh sau phải in ra `ok`.

```powershell
python -c "import PIL, numpy, skimage, matplotlib, tkinter; print('ok')"
```

**Bước 5. Khởi chạy ứng dụng:**

```powershell
cd code
python -m pixel_art_studio
```

Cửa sổ **Pixel Art Studio** sẽ hiện ra sau 1–2 giây. Nếu không thấy, hãy tìm biểu tượng
Python trên thanh taskbar. Terminal sẽ đứng yên trong lúc ứng dụng chạy; đóng cửa sổ
ứng dụng để quay lại terminal.

**Bước 6. Dùng thử với một ảnh:**
1. Ở khung **1 Choose workflow**, giữ lựa chọn **One image · preview and select styles**.
2. Bấm **Choose image…** và chọn `samples\101087.jpg`.
3. Đặt **Pixel size = 4**, **Palette colors = 16**, rồi bấm **Generate previews**.
4. So sánh thẻ **Adaptive palette** (median-cut, mất màu vàng của chiếc váy) với thẻ
   **Proposed pipeline** (giữ được màu vàng, không có pixel lẻ). Nháy đúp vào một thẻ
   để xem cỡ lớn, lăn chuột để phóng to hoặc thu nhỏ.
5. Bấm vào thẻ muốn lưu (có thể chọn nhiều thẻ), rồi bấm **Save selected styles**.
   Ảnh được lưu vào thư mục `results\` của project.

**Bước 7 (tùy chọn). Chuyển đổi hàng loạt:** chọn **All images · choose a folder**, bấm
**Choose folder…**, chọn thư mục `samples`, chọn **Proposed pipeline** ở ô
**Method for batch**, rồi bấm **Convert selected images**.

**Lưu ý với ảnh chụp từ điện thoại (khoảng 12 MP):** đặt **Pixel size từ 12 đến 16**.
Với Pixel size = 4, việc sinh xem trước cả 9 kiểu mất khoảng 40 giây (hai kiểu dithering
viết bằng Python thuần rất chậm), và ô quá nhỏ nên ảnh trông gần như ảnh gốc.

**Xử lý lỗi thường gặp:**

| Thông báo lỗi | Cách xử lý |
|---|---|
| `No module named 'PIL'` (hoặc `numpy`, `skimage`) | Chạy lại Bước 4 bằng đúng lệnh `python` dùng ở Bước 5 |
| `No module named pixel_art_studio` | Chưa vào thư mục `code`: chạy `cd code` trước Bước 5 |
| `No module named 'tkinter'` | Cài lại Python từ python.org và giữ tùy chọn **tcl/tk and IDLE** |
| Bấm **Generate previews** nhưng chờ rất lâu mới có kết quả | Ảnh quá lớn: tăng **Pixel size** hoặc chờ thêm (xem lưu ý ở trên) |

**Unit test:**

```powershell
python -m unittest discover -s tests -v
```

## 6. Độ đo

| Độ đo | Ý nghĩa |
|---|---|
| PSNR (dB) ↑ | Sai số theo điểm ảnh so với ảnh gốc |
| SSIM ↑ | Độ tương đồng cấu trúc |
| ΔE2000 ↓ | Sai khác màu theo cảm nhận (CIEDE2000, trung bình mọi điểm ảnh) |
| Số màu | Số màu thực sự dùng trong ảnh kết quả |
| Pixel lẻ (%) ↓ | Tỉ lệ ô lưới không trùng màu với ô nào trong 8 lân cận, đo mức "nhiễu" của pixel art |

## 7. Kết quả

Xem `results/eval/summary.md` và các hình trong `results/eval/`. Báo cáo đầy đủ:
`docs/out/BaoCao.pdf`; slide: `docs/out/Slide.pptx`.

## 8. Sinh lại báo cáo, slide và file nộp bài

Báo cáo và slide được sinh tự động từ kết quả đánh giá (không chép số tay):

```powershell
# 1. Điền lớp, nhóm, thành viên trong docs/nhom.json
# 2. Cần Node.js và Microsoft Word + PowerPoint (để xuất PDF)
cd tools; npm install; cd ..          # chỉ lần đầu
python tools/build_all.py
```

Kết quả: `docs/out/` và file `LopXX_NhomYY_PixelArt.zip` ở thư mục gốc (gồm code,
samples, tests, results/eval, README, requirements, báo cáo PDF, slide .pptx và .pdf).
