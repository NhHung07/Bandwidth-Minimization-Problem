# Bandwidth Minimization Problem (BMP) — Assignment 2

Đây là **khung dự án** cho bài tập lớn số 2. Các module Python và notebook hiện mới được đặt đúng vị trí; thuật toán, benchmark và báo cáo chưa được cài đặt. Xem [WORKFLOW.md](WORKFLOW.md) để hiểu bài toán, yêu cầu bắt buộc, lý do của từng bước và thứ tự triển khai.

## Cây thư mục

```text
data/
  hb_33/                       33 đồ thị từ nhóm nhỏ của bài báo
  hb_80/                       80 đồ thị từ nhóm lớn của bài báo
  README.md                    định dạng .mtx.rnd và quy tắc đọc
src/
  graph.py                     đọc đồ thị và chuẩn hóa dữ liệu
  verify.py                    kiểm tra nghiệm và tính bandwidth độc lập
  encodings/
    bmp/
      pairwise.py              mô hình SAT pairwise cho BMP
      order.py                 mô hình SAT order cho BMP
    cardinality/
      binomial.py              AMO đôi một; không phải mô hình BMP hoàn chỉnh
      binary.py
      commander.py
      product.py
      sequential.py
  search/
    repeated.py               giải SAT nhiều lần theo ngưỡng k
    incremental.py            tái sử dụng solver SAT theo ngưỡng k
  solvers/
    cpsat.py
    cplex_cp.py
    cplex_mip.py
    gurobi.py
scripts/
  benchmark_encodings.py      chạy và ghi kết quả so sánh SAT
  benchmark_solvers.py        chạy và ghi kết quả so sánh các solver
notebooks/                    phân tích và trực quan hóa kết quả
results/data/                 CSV sinh ra từ thực nghiệm
report/                       báo cáo LaTeX cần viết theo mẫu cas-sc
```

**Lưu ý:** `data/` là đầu vào; `results/data/` là đầu ra. Mọi phương pháp cần dùng cùng dữ liệu và cùng quy tắc chuyển ma trận thành đồ thị. Các file `.mtx.rnd` hiện có là danh sách cạnh riêng của bộ benchmark, không phải định dạng Matrix Market `.mtx` chuẩn.

Tài liệu gốc: [Assignment 2](Assignment%202%20-%20requirements.pdf), [bài báo BMP tham khảo](2%20-%20Bandwidth%20Minimization%20Problem%20-%20%20BMP.pdf), [giải thích đề tài](GIAI_THICH_DE_TAI_BMP.md).
