// Build the presentation (docs/out/Slide.pptx) from docs/nhom.json and docs/assets/.
//   node tools/build_slides.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const ASSETS = path.join(ROOT, "docs", "assets");
const OUT_DIR = path.join(ROOT, "docs", "out");
const team = JSON.parse(fs.readFileSync(path.join(ROOT, "docs", "nhom.json"), "utf8"));
const N = JSON.parse(fs.readFileSync(path.join(ASSETS, "numbers.json"), "utf8"));
const OUT = path.join(OUT_DIR, process.argv[2] || "Slide.pptx");
const GROUP = /^\d+$/.test(team.nhom) ? `Nhóm ${team.nhom}` : team.nhom;

// ---------------------------------------------------------------- helpers
const vn = (x, d = 2) => Number(x).toFixed(d).replace(".", ",");
const M = N.main;
const img = (name) => path.join(ASSETS, name);
const LABEL = {
  nearest: "Nearest neighbor",
  "box-average": "Box average",
  palette: "Median-cut",
  kmeans: "K-means RGB",
  ordered: "Ordered dither",
  "floyd-steinberg": "Floyd–Steinberg",
  proposed: "Đề xuất",
};

const COLORS = {
  red: "B5121B", // dominant – PTIT red
  deep: "6E0B11",
  ink: "1F2328",
  muted: "5B6168",
  tint: "F7ECEC",
  green: "2E7D4F",
  gold: "E0A526",
  slate: "5B6770",
  grid: "D9D9D9",
  white: "FFFFFF",
};
const THEME = {
  name: "Pixel Art PTIT",
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  colors: {
    dk1: COLORS.ink, lt1: COLORS.white, dk2: COLORS.deep, lt2: COLORS.tint,
    accent1: COLORS.red, accent2: COLORS.green, accent3: COLORS.gold,
    accent4: COLORS.slate, accent5: "9AA5AD", accent6: "3B5BA9",
    hlink: "3B5BA9", folHlink: "6E4BA9",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = team.ten_de_tai;
pres.author = `${team.lop} ${GROUP}`;
const C = pres.SchemeColor;
const footer = `${team.lop} · ${GROUP} · Đồ án Xử lý ảnh`;

// Motif: a tiny 2x2 "pixel" glyph in the palette colours, placed before titles.
function pixelGlyph(slide, x, y, s = 0.13, dark = false) {
  const cols = dark ? [COLORS.gold, COLORS.white, COLORS.white, COLORS.gold] : [COLORS.red, COLORS.gold, COLORS.deep, COLORS.red];
  [[0, 0], [1, 0], [0, 1], [1, 1]].forEach(([i, j], n) =>
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x + i * (s + 0.02), y: y + j * (s + 0.02), w: s, h: s,
      fill: { color: cols[n] }, line: { color: cols[n], width: 0 }, objectName: `pixel-${n}`,
    })
  );
}

pres.defineSlideMaster({
  title: "DARK",
  background: { color: COLORS.deep },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: COLORS.white },
  margin: [0.5, 0.5, 0.45, 0.5],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.95, y: 0.28, w: 8.55, h: 0.7, fontSize: 28, bold: true, color: C.text2, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: footer, options: { x: 0.5, y: 5.24, w: 6, h: 0.26, fontSize: 10, color: COLORS.muted, margin: 0 } } },
  ],
  slideNumber: { x: 9.0, y: 5.24, w: 0.5, h: 0.26, fontSize: 10, color: COLORS.muted, align: "right" },
});

function content(title, section, notes) {
  const slide = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  slide.addText(title, { placeholder: "title" });
  pixelGlyph(slide, 0.5, 0.48);
  if (notes) slide.addNotes(notes);
  return slide;
}

function caption(slide, text, x, y, w, opts = {}) {
  slide.addText(text, { x, y, w, h: 0.3, fontSize: 11, color: COLORS.muted, align: "center", margin: 0, isTextBox: true, ...opts });
}

function bullets(slide, items, x, y, w, h, size = 15) {
  slide.addText(
    items.map((t, i) => {
      const runs = Array.isArray(t) ? t : [{ text: t }];
      return runs.map((r, k) => ({
        text: r.text,
        options: { ...(k === 0 ? { bullet: true } : {}), ...(r.options || {}), ...(k === runs.length - 1 && i < items.length - 1 ? { breakLine: true } : {}) },
      }));
    }).flat(),
    { x, y, w, h, fontSize: size, color: COLORS.ink, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true }
  );
}

function stat(slide, value, label, x, y, w, color = COLORS.red) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 1.15, fill: { color: COLORS.tint }, line: { color: COLORS.tint }, rectRadius: 0.08, objectName: "stat-card" });
  slide.addText(value, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.62, fontSize: 30, bold: true, color, margin: 0, isTextBox: true });
  slide.addText(label, { x: x + 0.15, y: y + 0.68, w: w - 0.3, h: 0.42, fontSize: 11, color: COLORS.ink, margin: 0, valign: "top", isTextBox: true });
}

// ---------------------------------------------------------------- 1. title
pres.addSection({ title: "Mở đầu" });
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Mở đầu" });
  pixelGlyph(s, 0.5, 0.45, 0.13, true);
  s.addText("HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG · KHOA TRÍ TUỆ NHÂN TẠO", { x: 0.85, y: 0.42, w: 8.6, h: 0.32, fontSize: 11, color: "F3C9CB", bold: true, margin: 0, isTextBox: true });
  s.addText("Đồ án Xử lý ảnh · Lựa chọn 2 – Dự án thực tế", { x: 0.5, y: 1.05, w: 4.9, h: 0.35, fontSize: 14, color: COLORS.gold, margin: 0, isTextBox: true });
  s.addText("Chuyển ảnh chụp thành pixel art", { x: 0.5, y: 1.45, w: 4.9, h: 1.2, fontSize: 34, bold: true, color: COLORS.white, margin: 0, valign: "top", isTextBox: true });
  s.addText("Pipeline lượng tử hóa màu trên không gian Lab có khử pixel lẻ", { x: 0.5, y: 2.65, w: 4.9, h: 0.6, fontSize: 15, color: "F3C9CB", margin: 0, valign: "top", isTextBox: true });
  s.addText(
    [
      { text: `${team.lop} · ${GROUP}`, options: { bold: true, breakLine: true } },
      ...team.thanh_vien.map((m) => ({ text: `${m.ho_ten} – ${m.mssv}`, options: { breakLine: true } })),
      { text: `Giảng viên: ${team.giang_vien}` },
    ],
    { x: 0.5, y: 3.45, w: 4.9, h: 1.75, fontSize: 12, color: COLORS.white, margin: 0, valign: "top", paraSpaceAfter: 2, isTextBox: true }
  );
  s.addImage({ path: img("hero_proposed.png"), x: 5.7, y: 1.05, w: 3.8, h: 2.533, altText: "Ảnh chim đại bàng sau khi chuyển thành pixel art" });
  s.addText("Kết quả: pixel 4, 16 màu", { x: 5.7, y: 3.65, w: 3.8, h: 0.3, fontSize: 11, color: "F3C9CB", align: "center", margin: 0, isTextBox: true });
  s.addNotes("Giới thiệu nhóm và đề tài. Bài toán: biến một ảnh chụp bất kỳ thành ảnh phong cách pixel art có lưới ô thô và ít màu, sao cho vừa giống ảnh gốc vừa sạch như pixel art vẽ tay.");
}

// ---------------------------------------------------------------- 2. problem
pres.addSection({ title: "Bài toán và dữ liệu" });
{
  const s = content("Bài toán: ảnh chụp → pixel art", "Bài toán và dữ liệu",
    "Đầu vào là ảnh màu và hai tham số: kích thước pixel P và số màu K. Đầu ra là ảnh cùng kích thước gồm các khối PxP, tối đa K màu. Khó khăn chính là hai mục tiêu mâu thuẫn: càng bám chi tiết ảnh gốc thì càng nhiều pixel lẻ.");
  s.addImage({ path: img("hero_original.png"), x: 0.5, y: 1.25, w: 2.1, h: 1.4, altText: "Ảnh gốc" });
  s.addText("→", { x: 2.6, y: 1.6, w: 0.45, h: 0.6, fontSize: 28, color: COLORS.red, align: "center", bold: true, margin: 0, isTextBox: true });
  s.addImage({ path: img("hero_proposed.png"), x: 3.05, y: 1.25, w: 2.1, h: 1.4, altText: "Pixel art" });
  caption(s, "Đầu vào: ảnh màu bất kỳ", 0.5, 2.7, 2.1);
  caption(s, "Đầu ra: lưới P×P, ≤ K màu", 3.05, 2.7, 2.1);
  bullets(s, [
    [{ text: "Đầu vào: ", options: { bold: true } }, { text: "ảnh RGB, kích thước pixel P, số màu K" }],
    [{ text: "Đầu ra: ", options: { bold: true } }, { text: "ảnh PNG cùng kích thước, mỗi khối P×P một màu trong bảng K màu" }],
  ], 0.5, 3.2, 4.65, 1.7, 14);

  s.addText("Khó khăn cốt lõi", { x: 5.6, y: 1.2, w: 3.9, h: 0.4, fontSize: 18, bold: true, color: COLORS.red, margin: 0, isTextBox: true });
  const hard = [
    ["Hai mục tiêu mâu thuẫn", "Giống ảnh gốc (PSNR, SSIM) nhưng phải sạch, không có pixel lẻ"],
    ["Chọn bảng màu", "Với K nhỏ, median-cut dễ bỏ mất vùng màu nhỏ nhưng nổi bật"],
    ["Răng cưa và nhiễu", "Lấy mẫu xuống sinh ra các ô có màu ngẫu nhiên"],
  ];
  hard.forEach(([h, d], i) => {
    const y = 1.72 + i * 1.12;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.6, y: y + 0.05, w: 0.38, h: 0.38, fill: { color: [COLORS.red, COLORS.gold, COLORS.deep][i] }, line: { width: 0, color: COLORS.white } });
    s.addText(String(i + 1), { x: 5.6, y: y + 0.05, w: 0.38, h: 0.38, fontSize: 14, bold: true, color: COLORS.white, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([{ text: h, options: { bold: true, breakLine: true } }, { text: d, options: { fontSize: 13, color: COLORS.muted } }],
      { x: 6.15, y, w: 3.35, h: 1.0, fontSize: 15, color: COLORS.ink, valign: "top", margin: 0, isTextBox: true });
  });
}

// ---------------------------------------------------------------- 3. data
{
  const s = content("Dữ liệu: BSDS300, 100 ảnh test", "Bài toán và dữ liệu",
    "Dùng tập test của Berkeley Segmentation Dataset 300: 100 ảnh màu 481x321 gồm cảnh vật, người, động vật, kiến trúc. Ảnh được cắt về 480x320 để khớp lưới. Không cần gán nhãn: ảnh gốc là tham chiếu để tính độ đo. 9 ảnh mẫu đi kèm trong thư mục samples.");
  s.addImage({ path: img("samples_grid.png"), x: 0.5, y: 1.2, w: 5.2, h: 3.504, altText: "9 ảnh mẫu từ BSDS300" });
  caption(s, "9 ảnh mẫu trong samples/ (lấy từ tập test)", 0.5, 4.78, 5.2);
  stat(s, String(N.n_images), "ảnh đánh giá (yêu cầu ≥ 50)", 6.1, 1.2, 3.4);
  stat(s, "480×320", "sau chuẩn hóa: cắt về bội số của P", 6.1, 2.5, 3.4, COLORS.deep);
  stat(s, "0", "nhãn tay: ảnh gốc chính là ảnh tham chiếu", 6.1, 3.8, 3.4, COLORS.green);
}

// ---------------------------------------------------------------- 4. pipeline
pres.addSection({ title: "Phương pháp" });
{
  const s = content("Pipeline đề xuất: 5 bước", "Phương pháp",
    "Năm bước. Tiền xử lý: chuẩn hóa kích thước và lọc trung vị 3x3. Lấy mẫu xuống bằng trung bình khối để chống răng cưa. Lượng tử hóa bằng K-means trên Lab. Hậu xử lý bằng lọc đa số trên ảnh nhãn để loại pixel lẻ. Cuối cùng phóng to nearest neighbor. Mỗi bước gắn với một chương của học phần.");
  const steps = [
    ["Tiền xử lý", "Lọc trung vị 3×3", "Ch. 3", "stage_2_denoised.png"],
    ["Lấy mẫu xuống", "Trung bình khối P=4", "Ch. 2, 3", "stage_3_downsampled.png"],
    ["Lượng tử hóa", "K-means Lab, K=16", "Ch. 2, 8", "stage_4_quantized.png"],
    ["Hậu xử lý", "Lọc đa số 1 lượt", "Ch. 7", "stage_5_cleaned.png"],
    ["Phóng to", "Nearest neighbor", "Ch. 2", "stage_6_output.png"],
  ];
  const gap = 0.1, w = (9 - 4 * gap) / 5;
  steps.forEach(([name, param, ch, file], i) => {
    const x = 0.5 + i * (w + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.2, w, h: 0.78, fill: { color: i % 2 ? COLORS.tint : COLORS.red }, line: { color: COLORS.red, width: 1 }, rectRadius: 0.08 });
    s.addText([{ text: `${i + 1}. ${name}`, options: { bold: true, breakLine: true } }, { text: param, options: { fontSize: 11 } }],
      { x: x + 0.05, y: 1.2, w: w - 0.1, h: 0.78, fontSize: 13, color: i % 2 ? COLORS.ink : COLORS.white, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addImage({ path: img(file), x, y: 2.15, w, h: w * 0.75, altText: `Kết quả bước ${name}` });
    s.addText(ch, { x, y: 2.15 + w * 0.75 + 0.08, w, h: 0.3, fontSize: 12, bold: true, color: COLORS.red, align: "center", margin: 0, isTextBox: true });
  });
  s.addText("Ảnh: cùng một vùng phóng to sau từng bước. Ch. = chương của học phần (lọc không gian 3; lấy mẫu, lượng tử hóa 2; hình thái học 7; phân cụm 8).",
    { x: 0.5, y: 4.2, w: 9, h: 0.6, fontSize: 12, color: COLORS.muted, margin: 0, valign: "top", isTextBox: true });
}

// ---------------------------------------------------------------- 5. K-means Lab
{
  const s = content("Bước 3: K-means trên không gian Lab", "Phương pháp",
    "K-means phân cụm màu các ô trong không gian CIELAB, nơi khoảng cách gần với cảm nhận của mắt; khởi tạo k-means++. Mỗi màu trong bảng lấy bằng trung bình RGB của các ô thuộc cụm nên luôn hợp lệ. Ví dụ: median-cut chia theo số điểm ảnh nên chiếc váy vàng, một vùng nhỏ, bị gộp vào màu nâu; Lab K-means giữ được màu vàng.");
  bullets(s, [
    [{ text: "Không gian CIELAB: ", options: { bold: true } }, { text: "khoảng cách Euclid gần với cảm nhận màu của mắt" }],
    [{ text: "Khởi tạo k-means++: ", options: { bold: true } }, { text: "tâm ban đầu trải đều, kết quả ổn định (seed cố định)" }],
    [{ text: "Bảng màu: ", options: { bold: true } }, { text: "trung bình RGB của từng cụm, không lệch gam khi đổi ngược Lab → RGB" }],
    [{ text: `Ablation: Lab giảm ΔE2000 từ ${vn(M["abl-rgb"].delta_e)} (RGB) xuống ${vn(M.proposed.delta_e)}`, options: { bold: true, color: COLORS.green } }],
  ], 0.5, 1.25, 4.1, 3.7, 14);
  const cols = [["dancer_original.png", "Ảnh gốc"], ["dancer_palette.png", "Median-cut: mất màu vàng"], ["dancer_proposed.png", "Đề xuất: giữ màu vàng"]];
  cols.forEach(([file, label], i) => {
    const x = 4.85 + i * 1.57;
    s.addImage({ path: img(file), x, y: 1.25, w: 1.47, h: 2.205, altText: label });
    caption(s, label, x - 0.05, 3.52, 1.57, { h: 0.5, valign: "top", color: i === 2 ? COLORS.green : i === 1 ? COLORS.red : COLORS.muted, bold: i > 0 });
  });
}

// ---------------------------------------------------------------- 6. majority filter
{
  const s = content("Bước 4: lọc đa số loại pixel lẻ", "Phương pháp",
    "Một ô là pixel lẻ nếu nhãn màu của nó không trùng với ô nào trong 8 lân cận. Chỉ những ô này mới bị gán lại bằng nhãn phổ biến nhất trong lân cận. Khác với lọc mode 3x3 thông thường, cách làm này không làm mòn góc hay nét mảnh rộng từ 2 ô trở lên. Bỏ bước này, tỉ lệ pixel lẻ tăng từ 0,06% lên gần 5,9%.");
  s.addImage({ path: img("isolated_demo.png"), x: 0.5, y: 1.25, w: 1.6, h: 1.6, altText: "Một ô vàng đứng riêng giữa các ô xanh" });
  s.addText([{ text: "Pixel lẻ", options: { bold: true, breakLine: true, color: COLORS.red } }, { text: "Ô không trùng màu với ô nào trong 8 lân cận → thay bằng nhãn phổ biến nhất xung quanh" }],
    { x: 2.3, y: 1.25, w: 2.6, h: 1.6, fontSize: 13, color: COLORS.ink, valign: "top", margin: 0, isTextBox: true });
  bullets(s, [
    "Chỉ sửa ô lẻ, giữ nguyên nét rộng ≥ 2 ô",
    "Khác lọc mode 3×3 thông thường: không làm mòn góc",
    "Cài đặt vector hóa bằng NumPy trên ảnh nhãn",
  ], 0.5, 3.1, 4.4, 1.8, 14);
  [["zoom_no_cleanup.png", `Trước: ${vn(M["abl-no-cleanup"].isolated_pct)}% pixel lẻ`, COLORS.red], ["zoom_proposed.png", `Sau: ${vn(M.proposed.isolated_pct)}% pixel lẻ`, COLORS.green]].forEach(([file, label, color], i) => {
    const x = 5.15 + i * 2.2;
    s.addImage({ path: img(file), x, y: 1.25, w: 2.1, h: 1.575, altText: label });
    caption(s, label, x, 2.9, 2.1, { color, bold: true });
  });
  s.addText("Vùng phóng to của cùng một ảnh, pixel 4, K = 16", { x: 5.15, y: 3.3, w: 4.3, h: 0.3, fontSize: 11, color: COLORS.muted, align: "center", margin: 0, isTextBox: true });
}

// ---------------------------------------------------------------- 7. baselines & metrics
{
  const s = content("Phương pháp đối chứng và độ đo", "Phương pháp",
    "Đối chứng chính là median-cut của Pillow, cùng ngân sách 16 màu. Ngoài ra so với nearest neighbor, K-means trên RGB và hai kiểu dithering. Bốn độ đo: PSNR và SSIM đo độ trung thực, Delta E 2000 đo sai khác màu theo cảm nhận, và tỉ lệ pixel lẻ đo độ sạch, vì PSNR/SSIM không phản ánh được tiêu chí này.");
  const head = (t) => ({ text: t, options: { bold: true, color: COLORS.white, fill: { color: COLORS.red } } });
  const rowsL = [
    [head("Đối chứng"), head("Mô tả")],
    ["Nearest neighbor", "Lấy mẫu điểm, không giới hạn màu"],
    [{ text: "Median-cut (chính)", options: { bold: true } }, "Trung bình khối + median-cut 16 màu"],
    ["K-means RGB", "Trung bình khối + K-means RGB"],
    ["Dithering", "Bayer 4×4 / Floyd–Steinberg, 4 mức/kênh"],
  ];
  s.addTable(rowsL, { x: 0.5, y: 1.25, w: 4.4, colW: [1.6, 2.8], fontSize: 12, color: COLORS.ink, border: { type: "solid", pt: 0.5, color: COLORS.grid }, rowH: 0.42, valign: "middle" });
  const rowsR = [
    [head("Độ đo"), head("Đo gì")],
    ["PSNR ↑ (dB)", "Sai số từng điểm ảnh"],
    ["SSIM ↑", "Tương đồng cấu trúc"],
    ["ΔE2000 ↓", "Sai khác màu theo cảm nhận"],
    [{ text: "Pixel lẻ ↓ (%)", options: { bold: true } }, "Ô không trùng màu 8 lân cận"],
  ];
  s.addTable(rowsR, { x: 5.1, y: 1.25, w: 4.4, colW: [1.6, 2.8], fontSize: 12, color: COLORS.ink, border: { type: "solid", pt: 0.5, color: COLORS.grid }, rowH: 0.42, valign: "middle" });
  s.addText("Mọi phương pháp chạy trên cùng ảnh đầu vào, cùng P = 4, K = 16; số liệu là trung bình trên 100 ảnh.",
    { x: 0.5, y: 3.65, w: 9, h: 0.4, fontSize: 13, color: COLORS.muted, margin: 0, isTextBox: true });
}

// ---------------------------------------------------------------- 8. headline results
pres.addSection({ title: "Kết quả" });
{
  const s = content("Kết quả: gần như không còn pixel lẻ", "Kết quả",
    `So với median-cut: pixel lẻ giảm từ ${vn(M.palette.isolated_pct)}% xuống ${vn(M.proposed.isolated_pct)}%, tốt hơn trên cả ${N.wins_vs_palette.isolated_pct}/100 ảnh. Delta E giảm từ ${vn(M.palette.delta_e)} xuống ${vn(M.proposed.delta_e)}, tốt hơn trên ${N.wins_vs_palette.delta_e}/100 ảnh.`);
  stat(s, `${vn(M.proposed.isolated_pct)}%`, `pixel lẻ (median-cut ${vn(M.palette.isolated_pct)}%)`, 0.5, 1.2, 2.1, COLORS.green);
  stat(s, `${N.wins_vs_palette.isolated_pct}/100`, "ảnh ít pixel lẻ hơn median-cut", 0.5, 2.5, 2.1, COLORS.green);
  stat(s, vn(M.proposed.delta_e), `ΔE2000 (median-cut ${vn(M.palette.delta_e)})`, 0.5, 3.8, 2.1, COLORS.red);
  const order = ["floyd-steinberg", "ordered", "palette", "kmeans", "proposed"];
  s.addChart(pres.charts.BAR, [{ name: "Pixel lẻ (%)", labels: order.map((m) => LABEL[m]), values: order.map((m) => +M[m].isolated_pct.toFixed(2)) }], {
    x: 2.9, y: 1.15, w: 6.6, h: 3.95, barDir: "bar",
    showTitle: true, title: "Tỉ lệ pixel lẻ (%) – thấp hơn là tốt hơn", titleFontSize: 13, titleColor: COLORS.ink, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: COLORS.ink, dataLabelFormatCode: "0.00", dataLabelFontFace: "+mn-lt",
    chartColors: [COLORS.slate, COLORS.slate, COLORS.slate, COLORS.slate, COLORS.green], invertedColors: [COLORS.slate],
    catAxisLabelColor: COLORS.ink, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt",
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
    barGapWidthPct: 60,
  });
}

// ---------------------------------------------------------------- 9. full table
{
  const s = content("Bảng so sánh đầy đủ (100 ảnh, P=4, K=16)", "Kết quả",
    "Bảng đầy đủ. Đề xuất có Delta E tốt nhất trong nhóm 16 màu và pixel lẻ gần 0. Đổi lại, PSNR thấp hơn median-cut khoảng 0,6 dB và SSIM thấp hơn khoảng 0,06, vì lọc đa số cố ý xóa chi tiết một ô mà PSNR/SSIM vẫn tính điểm. Nearest và box average không giới hạn số màu nên không cùng ngân sách.");
  const head = ["Phương pháp", "PSNR ↑", "SSIM ↑", "ΔE2000 ↓", "Số màu", "Pixel lẻ % ↓"].map((t) => ({ text: t, options: { bold: true, color: COLORS.white, fill: { color: COLORS.red }, align: "center" } }));
  const rows = [head];
  ["nearest", "box-average", "palette", "kmeans", "ordered", "floyd-steinberg", "proposed"].forEach((m) => {
    const r = M[m];
    const hl = m === "proposed";
    const o = hl ? { bold: true, fill: { color: COLORS.tint } } : {};
    rows.push([
      { text: LABEL[m] + (m === "palette" ? " (chính)" : ""), options: o },
      ...[vn(r.psnr), vn(r.ssim, 3), vn(r.delta_e), r.colors > 100 ? `~${Math.round(r.colors)}` : String(Math.round(r.colors)), vn(r.isolated_pct)].map((t) => ({ text: t, options: { ...o, align: "center" } })),
    ]);
  });
  s.addTable(rows, { x: 0.5, y: 1.2, w: 9, colW: [2.4, 1.2, 1.2, 1.4, 1.3, 1.5], fontSize: 13, color: COLORS.ink, border: { type: "solid", pt: 0.5, color: COLORS.grid }, rowH: 0.4, valign: "middle" });
  s.addText([
    { text: "Đánh đổi: ", options: { bold: true, color: COLORS.red } },
    { text: `PSNR thấp hơn median-cut ${vn(M.palette.psnr - M.proposed.psnr)} dB, SSIM thấp hơn ${vn(M.palette.ssim - M.proposed.ssim, 3)}, do lọc đa số cố ý xóa chi tiết một ô.` },
  ], { x: 0.5, y: 4.55, w: 9, h: 0.5, fontSize: 13, color: COLORS.ink, margin: 0, valign: "top", isTextBox: true });
}

// ---------------------------------------------------------------- 10. visual comparison
{
  const s = content("So sánh trực quan trên cùng ảnh đầu vào", "Kết quả",
    "Cùng một vùng phóng to. Median-cut và K-means RGB còn nhiều ô lẻ rải rác ở vùng cây và mặt tượng. Pipeline đề xuất cho các mảng màu liền mạch, gần với pixel art vẽ tay hơn.");
  const items = [["zoom_original.png", "Ảnh gốc"], ["zoom_palette.png", "Median-cut"], ["zoom_kmeans.png", "K-means RGB"], ["zoom_proposed.png", "Đề xuất"]];
  items.forEach(([file, label], i) => {
    const x = 0.5 + i * 2.3;
    s.addImage({ path: img(file), x, y: 1.35, w: 2.2, h: 1.65, altText: label });
    caption(s, label, x, 3.08, 2.2, { bold: i === 3, color: i === 3 ? COLORS.green : COLORS.muted });
  });
  s.addText(`Pixel lẻ trung bình: Median-cut ${vn(M.palette.isolated_pct)}% · K-means RGB ${vn(M.kmeans.isolated_pct)}% · Đề xuất ${vn(M.proposed.isolated_pct)}%`,
    { x: 0.5, y: 3.65, w: 9, h: 0.4, fontSize: 14, color: COLORS.ink, align: "center", margin: 0, isTextBox: true });
}

// ---------------------------------------------------------------- 11. ablation
{
  const s = content("Ablation: mỗi bước đóng góp gì?", "Kết quả",
    "Bỏ lọc đa số: pixel lẻ tăng mạnh nhất, nên đây là bước quyết định. Bỏ Lab, dùng RGB: Delta E tăng từ 5,67 lên 6,01. Bỏ lọc trung vị: thay đổi rất nhỏ trên BSDS300, vì ảnh ít nhiễu và bước trung bình khối đã làm mịn sẵn.");
  const head = ["Cấu hình", "PSNR ↑", "ΔE2000 ↓", "Pixel lẻ % ↓"].map((t) => ({ text: t, options: { bold: true, color: COLORS.white, fill: { color: COLORS.red }, align: "center" } }));
  const rows = [head];
  [["proposed", "Đề xuất (đầy đủ)"], ["abl-no-denoise", "− lọc trung vị"], ["abl-rgb", "− Lab (dùng RGB)"], ["abl-no-cleanup", "− lọc đa số"]].forEach(([m, label]) => {
    const o = m === "proposed" ? { bold: true, fill: { color: COLORS.tint } } : {};
    rows.push([{ text: label, options: o }, ...[vn(M[m].psnr), vn(M[m].delta_e), vn(M[m].isolated_pct)].map((t) => ({ text: t, options: { ...o, align: "center" } }))]);
  });
  s.addTable(rows, { x: 0.5, y: 1.25, w: 5.0, colW: [1.9, 0.95, 1.05, 1.1], fontSize: 13, color: COLORS.ink, border: { type: "solid", pt: 0.5, color: COLORS.grid }, rowH: 0.45, valign: "middle" });
  const notes = [
    [COLORS.red, "Lọc đa số là bước quyết định", `Bỏ đi: pixel lẻ ${vn(M.proposed.isolated_pct)}% → ${vn(M["abl-no-cleanup"].isolated_pct)}%`],
    [COLORS.green, "Lab tốt hơn RGB", `ΔE2000 ${vn(M["abl-rgb"].delta_e)} → ${vn(M.proposed.delta_e)}`],
    [COLORS.slate, "Lọc trung vị gần như không tác dụng", "Ảnh BSDS ít nhiễu; chưa kiểm chứng trên ảnh nhiễu"],
  ];
  notes.forEach(([color, h, d], i) => {
    const y = 1.25 + i * 1.18;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.8, y: y + 0.06, w: 0.22, h: 0.22, fill: { color }, line: { color, width: 0 } });
    s.addText([{ text: h, options: { bold: true, breakLine: true } }, { text: d, options: { fontSize: 12, color: COLORS.muted } }],
      { x: 6.15, y, w: 3.35, h: 1.0, fontSize: 14, color: COLORS.ink, valign: "top", margin: 0, isTextBox: true });
  });
}

// ---------------------------------------------------------------- 12. K sweep
{
  const s = content("Ảnh hưởng của số màu K", "Kết quả",
    "Với K từ 8 đến 16, đề xuất tốt nhất ở cả hai độ đo. Khi K tăng lên 32-64, Delta E của đề xuất kém hơn K-means RGB, vì bảng màu dày khiến bộ lọc đa số xóa nhiều ô hợp lệ hơn. Pipeline vì vậy phù hợp nhất với phong cách pixel art ít màu.");
  const ks = ["8", "16", "32", "64"];
  const series = (metric) => ["palette", "kmeans", "proposed"].map((m) => ({ name: LABEL[m], labels: ks, values: ks.map((k) => +N.sweep_k[m][k][metric].toFixed(2)) }));
  const common = {
    showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: "+mn-lt", legendColor: COLORS.ink,
    chartColors: [COLORS.slate, COLORS.gold, COLORS.red], lineSize: 2, lineDataSymbolSize: 7,
    catAxisLabelColor: COLORS.ink, valAxisLabelColor: COLORS.ink, catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: COLORS.grid, size: 0.5 }, catGridLine: { style: "none" },
    showTitle: true, titleFontSize: 13, titleColor: COLORS.ink, titleFontFace: "+mn-lt",
    showCatAxisTitle: true, catAxisTitle: "Số màu K", catAxisTitleFontSize: 11, catAxisTitleColor: COLORS.muted,
  };
  s.addChart(pres.charts.LINE, series("delta_e"), { ...common, x: 0.5, y: 1.15, w: 4.4, h: 3.5, title: "ΔE2000 ↓" });
  s.addChart(pres.charts.LINE, series("isolated_pct"), { ...common, chartColors: [COLORS.slate, COLORS.gold, COLORS.red], x: 5.1, y: 1.15, w: 4.4, h: 3.5, title: "Pixel lẻ (%) ↓" });
  s.addText("K ≤ 16: đề xuất tốt nhất ở cả hai độ đo · K ≥ 32: ΔE kém hơn K-means RGB",
    { x: 0.5, y: 4.72, w: 9, h: 0.35, fontSize: 13, color: COLORS.ink, align: "center", margin: 0, isTextBox: true });
}

// ---------------------------------------------------------------- 13. discussion
pres.addSection({ title: "Kết luận" });
{
  const s = content("Thảo luận và hạn chế", "Kết luận",
    "Bốn điểm cần nói rõ: đánh đổi độ trung thực; lọc trung vị gần như không giúp gì trên tập dữ liệu này; hạn chế khi K lớn; và tốc độ, vì cài đặt bằng Python thuần nên chậm hơn median-cut viết bằng C.");
  const cards = [
    ["Đánh đổi độ trung thực", `PSNR −${vn(M.palette.psnr - M.proposed.psnr)} dB, SSIM −${vn(M.palette.ssim - M.proposed.ssim, 3)} so với median-cut. PSNR/SSIM không đo được độ sạch nên cần thêm độ đo pixel lẻ.`],
    ["Lọc trung vị", "Gần như không tác dụng trên BSDS300 (ảnh ít nhiễu). Có thể hữu ích với ảnh điện thoại thiếu sáng, nhưng chưa kiểm chứng."],
    ["K lớn (32–64)", "ΔE kém hơn K-means RGB vì lọc đa số xóa nhiều ô hợp lệ khi bảng màu dày. Phù hợp nhất với K ≤ 16."],
    ["Tốc độ", `≈ ${vn(M.proposed.time_ms / 1000, 1)} s/ảnh (Python thuần) so với ≈ ${Math.round(M.palette.time_ms)} ms của median-cut (C). Có thể tăng tốc K-means.`],
  ];
  cards.forEach(([h, d], i) => {
    const x = 0.5 + (i % 2) * 4.6, y = 1.2 + Math.floor(i / 2) * 1.9;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 4.4, h: 1.7, fill: { color: COLORS.tint }, line: { color: COLORS.tint }, rectRadius: 0.08 });
    pixelGlyph(s, x + 0.2, y + 0.22, 0.08);
    s.addText(h, { x: x + 0.5, y: y + 0.12, w: 3.75, h: 0.42, fontSize: 16, bold: true, color: COLORS.deep, margin: 0, valign: "middle", isTextBox: true });
    s.addText(d, { x: x + 0.2, y: y + 0.6, w: 4.0, h: 1.0, fontSize: 13, color: COLORS.ink, margin: 0, valign: "top", isTextBox: true });
  });
}

// ---------------------------------------------------------------- 14. conclusion (dark)
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Kết luận" });
  pixelGlyph(s, 0.5, 0.48, 0.13, true);
  s.addText("Kết luận", { x: 0.95, y: 0.28, w: 8.7, h: 0.7, fontSize: 28, bold: true, color: COLORS.white, margin: 0, valign: "middle", isTextBox: true });
  s.addText([
    { text: "Pipeline 5 bước gồm lọc trung vị, trung bình khối, K-means Lab và lọc đa số", options: { bullet: true, breakLine: true } },
    { text: `Pixel lẻ ${vn(M.proposed.isolated_pct)}% so với ${vn(M.palette.isolated_pct)}% (median-cut); ΔE2000 ${vn(M.proposed.delta_e)} so với ${vn(M.palette.delta_e)}`, options: { bullet: true, breakLine: true } },
    { text: "Đánh đổi có kiểm soát: PSNR và SSIM giảm nhẹ", options: { bullet: true, breakLine: true } },
    { text: "Hướng phát triển: chọn K tự động, lọc đa số theo biên, thử trên ảnh nhiễu, khảo sát người dùng", options: { bullet: true } },
  ], { x: 0.5, y: 1.2, w: 4.75, h: 3.0, fontSize: 15, color: COLORS.white, valign: "top", paraSpaceAfter: 10, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.45, y: 1.2, w: 4.05, h: 2.3, fill: { color: "4A070B" }, line: { color: "4A070B" }, rectRadius: 0.08 });
  s.addText([
    { text: "Chạy thử", options: { bold: true, color: COLORS.gold, breakLine: true, fontSize: 14 } },
    { text: "pip install -r requirements.txt", options: { breakLine: true } },
    { text: "python code/run_pipeline.py --input samples", options: { breakLine: true } },
    { text: "python code/download_data.py", options: { breakLine: true } },
    { text: "python code/evaluate.py --data data/BSDS300/images/test", options: { breakLine: true } },
    { text: "cd code && python -m pixel_art_studio" },
  ], { x: 5.6, y: 1.3, w: 3.8, h: 2.1, fontSize: 10, fontFace: "Courier New", color: COLORS.white, valign: "top", paraSpaceAfter: 6, margin: 0, isTextBox: true });
  s.addText("Cảm ơn thầy và các bạn đã lắng nghe – Hỏi đáp", { x: 0.5, y: 4.55, w: 9, h: 0.5, fontSize: 18, bold: true, color: COLORS.gold, align: "center", margin: 0, isTextBox: true });
  s.addNotes("Tóm tắt kết quả, nêu hướng phát triển, có thể chạy demo bằng ứng dụng giao diện. Sau đó mời câu hỏi.");
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  await pres.writeFile({ fileName: OUT });
  const { applyTheme } = require(process.env.PPTX_SKILL_THEME || path.join(__dirname, "apply_theme.js"));
  await applyTheme(OUT, THEME);
  console.log("Wrote", OUT);
})();
