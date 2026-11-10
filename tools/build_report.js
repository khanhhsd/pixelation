// Build the written report (docs/out/BaoCao.docx) from docs/nhom.json, docs/assets/ and results/eval/.
//   node tools/build_report.js
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun, LevelFormat, Packer,
  PageBreak, PageNumber, Paragraph, ShadingType, Table, TableCell, TableRow, TextRun, VerticalAlign, WidthType,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const ASSETS = path.join(ROOT, "docs", "assets");
const EVAL = path.join(ROOT, "results", "eval");
const OUT_DIR = path.join(ROOT, "docs", "out");
const team = JSON.parse(fs.readFileSync(path.join(ROOT, "docs", "nhom.json"), "utf8"));
const N = JSON.parse(fs.readFileSync(path.join(ASSETS, "numbers.json"), "utf8"));
const M = N.main;
const vn = (x, d = 2) => Number(x).toFixed(d).replace(".", ",");

const FONT = "Times New Roman";
const RED = "B5121B";
const CONTENT_W = 9071; // A4 width 11906 - 2 * 1417 (2.5 cm margins), DXA

// ---------------------------------------------------------------- helpers
function runs(text, base = {}) {
  // **bold** spans inside a string
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((part) =>
    part.startsWith("**") ? new TextRun({ ...base, text: part.slice(2, -2), bold: true }) : new TextRun({ ...base, text: part })
  );
}
const p = (text, opts = {}) => new Paragraph({ children: runs(text), alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 300 }, ...opts });
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const bullet = (text) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 300 } });
const numbered = (text, instance) => new Paragraph({ numbering: { reference: "numbers", level: 0, instance }, children: runs(text), alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 300 } });

let figureNo = 0, tableNo = 0;
function figure(file, widthIn, caption) {
  const full = fs.existsSync(path.join(ASSETS, file)) ? path.join(ASSETS, file) : path.join(EVAL, file);
  const data = fs.readFileSync(full);
  const w = data.readUInt32BE(16), h = data.readUInt32BE(20); // PNG IHDR
  const width = Math.round(widthIn * 96);
  figureNo += 1;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data, transformation: { width, height: Math.round((width * h) / w) }, altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: `Hình ${figureNo}. `, bold: true, italics: true, size: 22 }), new TextRun({ text: caption, italics: true, size: 22 })] }),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(caption, header, rows, widths, highlightRow = -1) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, i, { head = false, hl = false } = {}) =>
    new TableCell({
      borders, width: { size: widths[i], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
      margins: { top: 50, bottom: 50, left: 90, right: 90 },
      shading: head ? { fill: RED, type: ShadingType.CLEAR, color: "auto" } : hl ? { fill: "F7ECEC", type: ShadingType.CLEAR, color: "auto" } : undefined,
      children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        children: [new TextRun({ text: String(text), bold: head || hl, color: head ? "FFFFFF" : undefined, size: 22 })] })],
    });
  if (caption) tableNo += 1;
  return [
    ...(caption ? [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 160, after: 80 },
      children: [new TextRun({ text: `Bảng ${tableNo}. `, bold: true, italics: true, size: 22 }), new TextRun({ text: caption, italics: true, size: 22 })] })] : []),
    new Table({
      width: { size: total, type: WidthType.DXA }, columnWidths: widths, alignment: AlignmentType.CENTER,
      rows: [
        new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, { head: true })) }),
        ...rows.map((r, ri) => new TableRow({ children: r.map((t, i) => cell(t, i, { hl: ri === highlightRow })) })),
      ],
    }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}

const LABEL = {
  nearest: "Nearest neighbor", "box-average": "Box average", palette: "Median-cut (đối chứng chính)",
  kmeans: "K-means RGB", ordered: "Ordered dithering", "floyd-steinberg": "Floyd–Steinberg", proposed: "Đề xuất",
};
const colorsTxt = (c) => (c > 100 ? `~${Math.round(c)}` : String(Math.round(c)));

// ---------------------------------------------------------------- cover page
const center = (text, size, opts = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text, size, ...opts })] });
const cover = [
  center("HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG", 28, { bold: true }),
  center("KHOA TRÍ TUỆ NHÂN TẠO", 28, { bold: true }),
  center("———————", 26),
  new Paragraph({ spacing: { before: 1400 }, children: [] }),
  center("BÁO CÁO ĐỒ ÁN", 36, { bold: true }),
  center("HỌC PHẦN XỬ LÝ ẢNH", 30, { bold: true }),
  new Paragraph({ spacing: { before: 500 }, children: [] }),
  center("Đề tài:", 26, { italics: true }),
  center(team.ten_de_tai.toUpperCase(), 32, { bold: true, color: RED }),
  center("(Lựa chọn 2 – Dự án xử lý ảnh thực tế)", 26, { italics: true }),
  new Paragraph({ spacing: { before: 700 }, children: [] }),
  center(`Giảng viên hướng dẫn: ${team.giang_vien}`, 26),
  center(`Lớp: ${team.lop}      Nhóm: ${team.nhom}`, 26),
  new Paragraph({ spacing: { before: 200 }, children: [] }),
  ...table(null, ["Họ và tên", "MSSV"],
    team.thanh_vien.map((m) => [m.ho_ten, m.mssv]), [5000, 3000]),
  new Paragraph({ spacing: { before: 900 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Hà Nội, tháng 11/2026", size: 26, italics: true })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---------------------------------------------------------------- body
const W = N.wins_vs_palette;
const body = [
  h1("1. Bài toán"),
  p("**Định nghĩa.** Cho một ảnh màu RGB kích thước W×H, kích thước pixel P và số màu K. Cần sinh ảnh phong cách pixel art gồm lưới (W/P)×(H/P) ô vuông, mỗi ô được tô bằng một trong K màu của bảng màu. Ảnh kết quả có cùng kích thước với ảnh gốc."),
  bullet("**Đầu vào:** ảnh màu bất kỳ (JPEG, PNG, BMP, …) và hai tham số P, K."),
  bullet("**Đầu ra:** ảnh PNG gồm các khối P×P với tối đa K màu."),
  p("**Khó khăn cốt lõi.**"),
  numbered("**Hai mục tiêu mâu thuẫn:** ảnh phải giống ảnh gốc (độ trung thực) nhưng đồng thời phải “sạch” như pixel art vẽ tay, tức là các vùng màu liền mạch và không có pixel lẻ. Phương pháp nào bám sát từng chi tiết của ảnh gốc thì lại sinh nhiều pixel lẻ.", 1),
  numbered("**Lượng tử hóa màu:** với K nhỏ (8–16 màu), cách chọn bảng màu quyết định màu nào bị mất. Median-cut chia theo số lượng điểm ảnh nên dễ bỏ qua các vùng màu nhỏ nhưng nổi bật.", 1),
  numbered("**Răng cưa và nhiễu:** lấy mẫu xuống làm xuất hiện các ô có màu ngẫu nhiên.", 1),

  h1("2. Dữ liệu"),
  p(`Nhóm sử dụng tập test của **BSDS300** (Berkeley Segmentation Dataset) gồm **${N.n_images} ảnh** màu kích thước 481×321, bao gồm cảnh tự nhiên, người, động vật và kiến trúc (đề bài yêu cầu tối thiểu 50 ảnh đánh giá). Dữ liệu được tải tự động bằng script code/download_data.py từ trang của Đại học Berkeley.`),
  p("Mỗi ảnh được cắt về 480×320 (bội số của P) để lưới ô khớp chính xác. Bài toán **không cần gán nhãn tay**: ảnh gốc sau chuẩn hóa chính là ảnh tham chiếu để tính độ đo. Thư mục samples/ chứa 9 ảnh mẫu lấy từ tập này để chạy thử."),

  h1("3. Phương pháp"),
  h2("3.1. Pipeline đề xuất"),
  p("Pipeline gồm 5 bước, tương ứng khung Dữ liệu – Tiền xử lý – Xử lý chính – Hậu xử lý – Đánh giá của đề bài. Bảng 1 ghi rõ tham số, lý do lựa chọn và kiến thức của học phần được dùng ở từng bước."),
  ...table("Các bước của pipeline đề xuất", ["Bước", "Thao tác và tham số", "Lý do chọn", "Chương"], [
    ["1. Tiền xử lý", "Chuẩn hóa kích thước; lọc trung vị 3×3", "Loại nhiễu và kết cấu vụn, giữ được biên", "3"],
    ["2. Lấy mẫu xuống", "Trung bình khối P×P (P = 4)", "Chống răng cưa so với lấy mẫu điểm", "2, 3"],
    ["3. Lượng tử hóa", "K-means trên CIELAB, khởi tạo k-means++, K = 16, tối đa 30 vòng lặp", "Khoảng cách Lab gần cảm nhận màu của mắt", "2, 8"],
    ["4. Hậu xử lý", "Lọc đa số có điều kiện (1 lượt); viền Sobel tùy chọn", "Loại pixel lẻ, giữ nét rộng ≥ 2 ô", "5, 7"],
    ["5. Phóng to", "Nearest neighbor", "Giữ cạnh khối sắc nét", "2"],
  ], [1700, 3100, 3271, 1000]),
  p("**Lọc trung vị (chương 3).** Bộ lọc phi tuyến loại bỏ nhiễu xung và các chi tiết rất nhỏ nhưng giữ được biên, giúp lưới thô sau khi lấy mẫu bớt ô có màu ngẫu nhiên."),
  p("**Lấy mẫu xuống (chương 2–3).** Mỗi khối P×P được thay bằng trung bình các điểm ảnh trong khối, tương đương lọc trung bình rồi lấy mẫu, nhờ đó giảm hiện tượng răng cưa so với lấy mẫu điểm (nearest neighbor)."),
  p("**K-means trên không gian Lab (chương 2, 8).** Lượng tử hóa màu được xem như bài toán phân cụm các màu của lưới. Nhóm phân cụm trong không gian CIELAB vì ở đó khoảng cách Euclid xấp xỉ sai khác màu mà mắt người cảm nhận. Tâm ban đầu được chọn bằng k-means++ (xác suất tỉ lệ với bình phương khoảng cách tới tâm gần nhất), sau đó lặp thuật toán Lloyd tới khi hội tụ. Mỗi màu của bảng màu là trung bình RGB của các ô thuộc cụm, nên luôn hợp lệ và không bị lệch gam khi đổi ngược Lab → RGB."),
  p("**Lọc đa số có điều kiện (chương 7).** Ô (i, j) được coi là pixel lẻ nếu nhãn của nó không trùng với nhãn của ô nào trong 8 lân cận. Chỉ những ô lẻ mới bị gán lại bằng nhãn xuất hiện nhiều nhất trong 8 lân cận. Khác với lọc mode 3×3 thông thường (vốn làm mòn góc và nét mảnh), bộ lọc có điều kiện giữ nguyên mọi cấu trúc rộng từ 2 ô trở lên; tính chất này được kiểm chứng bằng unit test. Tùy chọn viền dùng toán tử Sobel (chương 5) trên độ sáng của lưới."),
  ...figure("fig_pipeline_stages.png", 6.2, "Một vùng ảnh sau từng bước của pipeline (P = 4, K = 16)"),
  h2("3.2. Phương pháp đối chứng"),
  bullet("**Nearest neighbor / Box average:** lấy mẫu điểm hoặc trung bình khối, không giới hạn số màu."),
  bullet("**Median-cut (đối chứng chính):** trung bình khối, sau đó lượng tử hóa median-cut của thư viện Pillow về K màu, không dithering. Cùng ngân sách màu với phương pháp đề xuất."),
  bullet("**K-means RGB:** giống bước 2–3 của đề xuất nhưng phân cụm trên RGB, không có tiền xử lý và hậu xử lý."),
  bullet("**Ordered / Floyd–Steinberg dithering:** ma trận Bayer 4×4 hoặc khuếch tán sai số, 4 mức mỗi kênh."),
  h2("3.3. Độ đo"),
  p("Ngoài các độ đo chuẩn PSNR, SSIM (scikit-image) và sai khác màu cảm nhận ΔE2000 trung bình (CIEDE2000), nhóm đề xuất thêm độ đo **tỉ lệ pixel lẻ**: phần trăm ô lưới không trùng màu với ô nào trong 8 lân cận. Lý do là PSNR/SSIM chỉ đo độ giống ảnh gốc, không phản ánh được tính “sạch”, vốn là tiêu chí quan trọng của pixel art. Mọi phương pháp chạy trên cùng ảnh đầu vào với cùng P = 4, K = 16."),

  h1("4. Kết quả"),
  h2("4.1. So sánh với phương pháp đối chứng"),
  ...table(`Kết quả trung bình trên ${N.n_images} ảnh BSDS300 (P = 4, K = 16). ↑ cao hơn tốt hơn, ↓ thấp hơn tốt hơn`,
    ["Phương pháp", "PSNR (dB) ↑", "SSIM ↑", "ΔE2000 ↓", "Số màu", "Pixel lẻ (%) ↓"],
    ["nearest", "box-average", "palette", "kmeans", "ordered", "floyd-steinberg", "proposed"].map((m) =>
      [LABEL[m], vn(M[m].psnr), vn(M[m].ssim, 3), vn(M[m].delta_e), colorsTxt(M[m].colors), vn(M[m].isolated_pct)]),
    [2871, 1200, 1100, 1250, 1150, 1500], 6),
  p(`So với median-cut trên từng ảnh, phương pháp đề xuất có tỉ lệ pixel lẻ thấp hơn ở **${W.isolated_pct}/${N.n_images}** ảnh và ΔE2000 thấp hơn ở **${W.delta_e}/${N.n_images}** ảnh; ngược lại PSNR cao hơn ở ${W.psnr}/${N.n_images} ảnh và SSIM cao hơn ở ${W.ssim}/${N.n_images} ảnh. Nearest neighbor và box average đạt PSNR/SSIM cao nhưng dùng hàng nghìn màu và có tới khoảng 90% ô lẻ, nên không phải pixel art đúng nghĩa.`),
  ...figure("fig_comparison.png", 6.3, "So sánh trên cùng ảnh đầu vào. Hàng 2: median-cut làm mất màu vàng của chiếc váy, phương pháp đề xuất giữ được"),
  ...figure("fig_zoom.png", 6.3, "Phóng to một vùng: các ô lẻ rải rác ở median-cut và K-means RGB bị loại bỏ trong phương pháp đề xuất"),
  h2("4.2. Ablation – bỏ từng bước"),
  ...table("Ảnh hưởng của từng bước (P = 4, K = 16)", ["Cấu hình", "PSNR ↑", "SSIM ↑", "ΔE2000 ↓", "Pixel lẻ (%) ↓"],
    [["proposed", "Đề xuất (đầy đủ)"], ["abl-no-denoise", "− lọc trung vị"], ["abl-rgb", "− Lab (K-means trên RGB)"], ["abl-no-cleanup", "− lọc đa số"]].map(([m, l]) =>
      [l, vn(M[m].psnr), vn(M[m].ssim, 3), vn(M[m].delta_e), vn(M[m].isolated_pct)]),
    [3271, 1400, 1400, 1500, 1500], 0),
  h2("4.3. Ảnh hưởng của số màu K"),
  ...table("ΔE2000 / tỉ lệ pixel lẻ (%) theo số màu K (P = 4)", ["K", "Median-cut", "K-means RGB", "Đề xuất"],
    ["8", "16", "32", "64"].map((k) => [k, ...["palette", "kmeans", "proposed"].map((m) => `${vn(N.sweep_k[m][k].delta_e)} / ${vn(N.sweep_k[m][k].isolated_pct)}`)]),
    [1200, 2600, 2600, 2671]),
  ...figure("fig_sweep_k.png", 6.0, "ΔE2000 và tỉ lệ pixel lẻ theo số màu K"),

  h1("5. Thảo luận"),
  numbered(`**Pixel lẻ gần như được loại bỏ hoàn toàn:** từ ${vn(M.palette.isolated_pct)}% (median-cut) và ${vn(M.kmeans.isolated_pct)}% (K-means RGB) xuống ${vn(M.proposed.isolated_pct)}%. Ablation cho thấy bước lọc đa số đóng góp chính: bỏ bước này thì tỉ lệ tăng lại lên ${vn(M["abl-no-cleanup"].isolated_pct)}%.`, 2),
  numbered(`**Màu sắc theo cảm nhận tốt hơn đối chứng chính:** ΔE2000 bằng ${vn(M.proposed.delta_e)} so với ${vn(M.palette.delta_e)} của median-cut. Phân cụm trên Lab giảm ΔE từ ${vn(M["abl-rgb"].delta_e)} (RGB) xuống ${vn(M.proposed.delta_e)}. Ví dụ trực quan ở Hình 2 (hàng 2): median-cut gộp chiếc váy vàng, một vùng nhỏ, vào màu be, còn K-means Lab giữ được màu vàng.`, 2),
  numbered(`**Đánh đổi:** PSNR thấp hơn median-cut ${vn(M.palette.psnr - M.proposed.psnr)} dB và SSIM thấp hơn ${vn(M.palette.ssim - M.proposed.ssim, 3)}. Nguyên nhân chủ yếu là lọc đa số, vì bước này cố ý xóa chi tiết một ô, vốn là thông tin mà PSNR/SSIM tính điểm (bỏ lọc đa số, PSNR tăng lên ${vn(M["abl-no-cleanup"].psnr)} dB). Đây là đánh đổi có chủ đích giữa độ trung thực và độ sạch.`, 2),
  numbered("**Lọc trung vị gần như không có tác dụng** trên BSDS300: các độ đo thay đổi rất nhỏ. Ảnh của tập này ít nhiễu, đồng thời bước trung bình khối đã làm mịn sẵn. Bước này có thể hữu ích hơn với ảnh nhiễu (ảnh điện thoại chụp thiếu sáng), nhưng nhóm chưa kiểm chứng trường hợp đó.", 2),
  numbered(`**Hạn chế khi K lớn:** với K = 32–64, ΔE của phương pháp đề xuất kém hơn K-means RGB (ví dụ ${vn(N.sweep_k.proposed["64"].delta_e)} so với ${vn(N.sweep_k.kmeans["64"].delta_e)} khi K = 64), vì khi bảng màu dày, lọc đa số xóa cả những ô hợp lệ. Pipeline phù hợp nhất với phong cách pixel art ít màu (K ≤ 16).`, 2),
  numbered(`**Thời gian chạy:** khoảng ${vn(M.proposed.time_ms / 1000, 1)} s/ảnh (Python thuần, đo khi chạy song song nhiều tiến trình nên chỉ mang tính tương đối), chậm hơn median-cut (khoảng ${Math.round(M.palette.time_ms)} ms, cài đặt bằng C). Phần chậm nhất là K-means.`, 2),
  p("**Hướng phát triển:** chọn K tự động (phương pháp elbow), lọc đa số có trọng số theo biên để bảo toàn chi tiết nhỏ quan trọng (mắt, chữ), đánh giá trên ảnh nhiễu thật và khảo sát người dùng để đánh giá chủ quan."),
  p("**Sản phẩm phần mềm.** Ngoài script dòng lệnh (code/run_pipeline.py) và script đánh giá (code/evaluate.py), nhóm cung cấp ứng dụng giao diện Tkinter cho phép xem trước 9 kiểu chuyển đổi trên một ảnh và chuyển đổi hàng loạt. Mã nguồn có 17 unit test, bao gồm test hồi quy cho lỗi K-means của phiên bản trước (phân cụm trên ảnh thu nhỏ 128 px làm mất độ phân giải lưới)."),

  h1("6. Khai báo sử dụng AI"),
  p("Nhóm có sử dụng trợ lý AI **Claude (Anthropic), thông qua công cụ Claude Code**, để hỗ trợ các việc sau:"),
  bullet("Tái cấu trúc mã nguồn theo yêu cầu nộp bài; viết pipeline đề xuất (K-means Lab, lọc đa số), các độ đo và script đánh giá, ablation;"),
  bullet("Phát hiện và sửa lỗi K-means của phiên bản trước; viết unit test;"),
  bullet("Soạn README, bản nháp báo cáo này và slide thuyết trình (sinh tự động từ kết quả đánh giá)."),
  p("Toàn bộ số liệu trong báo cáo được sinh trực tiếp từ kết quả chạy chương trình (results/eval). Nhóm đã kiểm tra lại mã nguồn, chạy lại thí nghiệm và chịu trách nhiệm về nội dung cuối cùng."),

  h1("Tài liệu tham khảo"),
  numbered("D. Martin, C. Fowlkes, D. Tal, J. Malik. A Database of Human Segmented Natural Images and its Application to Evaluating Segmentation Algorithms. ICCV, 2001.", 3),
  numbered("P. Heckbert. Color Image Quantization for Frame Buffer Display. SIGGRAPH, 1982.", 3),
  numbered("D. Arthur, S. Vassilvitskii. k-means++: The Advantages of Careful Seeding. SODA, 2007.", 3),
  numbered("G. Sharma, W. Wu, E. Dalal. The CIEDE2000 Color-Difference Formula. Color Research & Application, 2005.", 3),
  numbered("Z. Wang, A. Bovik, H. Sheikh, E. Simoncelli. Image Quality Assessment: From Error Visibility to Structural Similarity. IEEE TIP, 2004.", 3),
  numbered("R. Floyd, L. Steinberg. An Adaptive Algorithm for Spatial Greyscale. Proc. SID, 1976.", 3),
];

// ---------------------------------------------------------------- document
const doc = new Document({
  creator: `${team.lop} ${team.nhom}`,
  title: team.ten_de_tai,
  styles: {
    default: { document: { run: { font: FONT, size: 26 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: RED }, paragraph: { spacing: { before: 280, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 27, bold: true }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 640, hanging: 320 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 640, hanging: 360 } } } }] },
    ],
  },
  sections: [
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1417, right: 1417 } } }, children: cover },
    {
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1417, right: 1417 }, pageNumbers: { start: 1 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 22 })] })] }) },
      children: body,
    },
  ],
});

fs.mkdirSync(OUT_DIR, { recursive: true });
const out = path.join(OUT_DIR, process.argv[2] || "BaoCao.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("Wrote", out); });
