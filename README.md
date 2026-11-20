# Bandwidth Minimization Problem (BMP) - Exact Solvers & SAT Encodings

Dự án nghiên cứu, cài đặt và đánh giá thực nghiệm toàn diện các phương pháp giải chính xác (**Exact Algorithms**) cho bài toán **Bandwidth Minimization Problem on Graphs (BMP)**, phục vụ Bài tập lớn số 2 - Học phần **Các vấn đề hiện đại trong Khoa học Máy tính**, Khoa Công nghệ Thông tin - Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội (UET - VNU).

---

## 1. Giới thiệu Bài toán Bandwidth Minimization Problem (BMP)

Cho một đồ thị vô hướng đơn $G = (V, E)$ với $|V| = n$ đỉnh và $|E| = m$ cạnh. Một phép gán nhãn (hoán vị) $\pi$ là một song ánh từ tập đỉnh $V$ vào tập vị trí $\{1, 2, \dots, n\}$:
$$\pi: V \to \{1, 2, \dots, n\}$$

Băng thông (Bandwidth) của đồ thị $G$ dưới phép gán nhãn $\pi$, ký hiệu là $B_\pi(G)$, là khoảng cách lớn nhất trên thước đo thứ tự giữa hai đỉnh kề nhau:
$$B_\pi(G) = \max_{(u, v) \in E} |\pi(u) - \pi(v)|$$

Bài toán BMP tìm kiếm phép gán nhãn tối ưu $\pi^*$ sao cho băng thông là nhỏ nhất:
$$B^*(G) = \min_{\pi} B_\pi(G)$$

BMP là bài toán thuộc lớp **NP-khó** (NP-hard), có ứng dụng quan trọng trong:
* Tối ưu hóa cấu trúc ma trận thưa (Sparse Matrix Bandwidth Reduction) để tăng tốc độ phân rã Cholesky/LU.
* Thiết kế vi mạch tích hợp cỡ lớn (VLSI Design) và định tuyến layout vi xử lý.
* Định tuyến truyền thông phân tán và song song hóa tính toán khoa học.

---

## 2. Cấu trúc Thư mục Dự án

```text
BMP/
├── data/                               # Bộ dữ liệu thực nghiệm chuẩn Harwell-Boeing
│   ├── hb_33/                          # 33 đồ thị cỡ nhỏ và vừa (N từ 24 đến 200 đỉnh)
│   └── hb_80/                          # 80 đồ thị cỡ lớn (N từ 200 đến 1000+ đỉnh)
├── report/                             # Báo cáo học thuật định dạng Elsevier CAS LaTeX
│   ├── bmp_report.tex                  # Mã nguồn LaTeX bài báo cáo
│   └── bmp_report.pdf                  # File PDF hoàn chỉnh đã biên dịch
├── results/
│   ├── benchmark/                      # Các kịch bản chạy benchmark tự động
│   │   ├── run_solver.py               # Chạy nhanh một solver trên file cụ thể để kiểm tra
│   │   ├── benchmark_group3.py         # Benchmark 5 phương pháp Solver (CP-SAT, CPLEX, Gurobi, SAT)
│   │   ├── benchmark_group3_worker.py  # Worker độc lập có cô lập tiến trình và giới hạn tài nguyên
│   │   ├── validate_group3_csv.py      # Kiểm nghiệm tính hợp lệ nghiệm của dữ liệu nhóm 3
│   │   ├── benchmark_amo.py            # Benchmark so sánh 5 kỹ thuật mã hóa At-Most-One (AMO)
│   │   ├── benchmark_amo_worker.py     # Worker thực thi benchmark AMO
│   │   ├── validate_amo_csv.py         # Kiểm tra tính hợp lệ dữ liệu AMO
│   │   ├── benchmark_group1.py         # Benchmark so sánh Pairwise vs Order, Iterative vs Incremental
│   │   ├── benchmark_group1_worker.py  # Worker thực thi benchmark Nhóm 1
│   │   ├── validate_group1_csv.py      # Kiểm tra tính hợp lệ dữ liệu Nhóm 1
│   │   └── benchmark_sat.py            # Giám sát cây tiến trình và bộ nhớ RAM
│   ├── data/                           # Dữ liệu kết quả thực nghiệm thô dạng CSV
│   │   ├── group3_official_strong_lb_120s.csv # Kết quả chạy 5 Solvers (timeout 120s)
│   │   ├── amo_120s.csv                       # Kết quả khảo sát các mã hóa AMO
│   │   └── group1_product_120s.csv            # Kết quả so sánh các chiến lược SAT
│   └── visualization/                  # Trực quan hóa và đồ thị phân tích
│       ├── notebooks/                  # Các Jupyter Notebook phân tích chuyên sâu
│       │   ├── group3_visualization.ipynb     # Phân tích so sánh hiệu năng các Solvers
│       │   ├── amo_visualization.ipynb        # Phân tích so sánh các kỹ thuật AMO
│       │   └── group1_visualization.ipynb     # Phân tích so sánh Repeated SAT vs Incremental SAT
│       └── png/                        # Các biểu đồ xuất bản dùng trong báo cáo
├── src/                                # Mã nguồn thuật toán và mô hình
│   ├── graph.py                        # Đọc file .mtx.rnd, cấu trúc Graph vô hướng
│   ├── graph_bounds.py                 # Tính cận dưới (Degree, Clique, Density) & RCM Upper Bound
│   ├── verify.py                       # Kiểm nghiệm độc lập tính đúng đắn của hoán vị và bandwidth
│   ├── solvers/                        # Module các Exact Solvers đối chiếu
│   │   ├── common.py                   # Kiểu kết quả SolverResult, callback và tiện ích chung
│   │   ├── cpsat.py                    # Solver Google OR-Tools CP-SAT (AllDifferent + Bounds)
│   │   ├── gurobi.py                   # Solver Gurobi Optimizer (Mixed Integer Programming - MIP)
│   │   ├── cplex_cp.py                 # Solver IBM ILOG CPLEX CP Optimizer (DOcplex.CP)
│   │   └── cplex_mip.py                # Solver IBM ILOG CPLEX MIP (DOcplex.MP)
│   ├── encodings/                      # Các kỹ thuật mã hóa sang bài toán SAT
│   │   ├── bmp/
│   │   │   ├── pairwise.py             # Mã hóa Pairwise (biến nhị phân x[v, p] = 1 nếu đỉnh v ở vị trí p)
│   │   │   └── order.py                # Mã hóa Order (biến ngưỡng t[v, p] = 1 nếu vị trí(v) <= p)
│   │   └── cardinality/                # Các kỹ thuật mã hóa ràng buộc At-Most-One (AMO)
│   │       ├── common.py               # Interface chung cho bộ mã hóa AMO
│   │       ├── binomial.py             # Binomial (Pairwise) AMO
│   │       ├── binary.py               # Binary (Bitwise) AMO
│   │       ├── commander.py            # Commander-Variable AMO
│   │       ├── product.py              # 2D Product AMO
│   │       └── sequential.py           # Sequential Counter AMO
│   └── search/                         # Các chiến lược tìm kiếm bandwidth tối ưu
│       ├── common.py                   # Quản lý ngưỡng tìm kiếm (cận dưới LB, cận trên UB)
│       ├── repeated.py                 # Repeated SAT (giải lặp nhiều lần độc lập)
│       └── incremental.py              # Incremental SAT (sử dụng CaDiCaL Solver với Assumptions)
├── requirements.txt                    # Danh sách các thư viện phụ thuộc
└── README.md
```

---

## 3. Các Phương pháp và Mô hình Cài đặt

### 3.1. Nhóm Exact Solvers (CP & MIP)
* **Google OR-Tools CP-SAT** (`src/solvers/cpsat.py`): Sử dụng biến nguyên vị trí $p_u \in [1, n]$, ràng buộc song ánh `AddAllDifferent(p)` và ràng buộc khoảng cách $|p_u - p_v| \le bw$ với mọi cạnh $(u, v) \in E$.
* **Gurobi Optimizer MIP** (`src/solvers/gurobi.py`): Mô hình hóa quy hoạch nguyên nhị phân với biến $x_{u, i} \in \{0, 1\}$, ràng buộc gán đơn vị cho mỗi đỉnh và mỗi vị trí, liên kết vị trí qua tổng trọng số.
* **IBM ILOG CPLEX CP Optimizer** (`src/solvers/cplex_cp.py`): Mô hình Constraint Programming trên nền tảng `docplex.cp`.
* **IBM ILOG CPLEX MIP** (`src/solvers/cplex_mip.py`): Mô hình Mixed-Integer Programming trên nền tảng `docplex.mp`.

### 3.2. Phương pháp Tiếp cận bằng SAT (Boolean Satisfiability)
* **Mã hóa BMP**:
  * **Pairwise Encoding**: Biến $x_{v, p}$ mang ý nghĩa đỉnh $v$ được đặt ở vị trí $p$. Ràng buộc vị trí đơn nhất và đỉnh đơn nhất yêu cầu các ràng buộc Exactly-One (EO = ALO + AMO).
  * **Order Encoding**: Biến ngưỡng $t_{v, p}$ mang ý nghĩa đỉnh $v$ có vị trí $\le p$. Loại bỏ hoàn toàn ràng buộc AMO cho mỗi đỉnh nhờ tính chất chuỗi ngưỡng.
* **5 Kỹ thuật mã hóa At-Most-One (AMO)**:
  1. *Binomial*: $O(n^2)$ mệnh đề, 0 biến phụ.
  2. *Binary*: $O(n \log n)$ mệnh đề, $O(\log n)$ biến phụ.
  3. *Commander*: Chia nhóm đệ quy với biến chỉ huy.
  4. *2D Product*: Sắp xếp dạng lưới 2 chiều $p \times q$.
  5. *Sequential Counter*: Dãy biến phụ tích lũy tuần tự.
* **Chiến lược Tìm kiếm Bandwidth**:
  * **Repeated SAT**: Khởi tạo lại solver cho mỗi giá trị băng thông thử nghiệm.
  * **Incremental SAT**: Giữ nguyên tri thức mệnh đề học được (Learned Clauses) qua các lượt thử nghiệm bằng solver **CaDiCaL** (`python-sat`) kết hợp kỹ thuật giả định (**Assumptions**).

---

## 4. Hướng dẫn Cài đặt & Môi trường

### 4.1. Yêu cầu Hệ thống
* Hệ điều hành: Linux (Ubuntu 20.04/22.04+ khuyến nghị) hoặc macOS/Windows.
* Python: `>= 3.10`.
* Cài đặt bộ công cụ giải thương mại (Tùy chọn nếu cần chạy Gurobi hoặc CPLEX):
  * **Gurobi**: Cần kích hoạt license hợp lệ (`grbgetkey`).
  * **CPLEX**: Cần cài đặt IBM ILOG CPLEX Optimization Studio và liên kết `docplex`.

### 4.2. Cài đặt Thư viện Phụ thuộc
Khuyến nghị tạo môi trường ảo (virtual environment):

```bash
# Tạo và kích hoạt môi trường ảo
python3 -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate

# Cài đặt các gói phụ thuộc
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Hướng dẫn Sử dụng & Chạy Thực nghiệm

### 5.1. Chạy nhanh một Solver trên file đồ thị đơn lẻ
File `results/benchmark/run_solver.py` hỗ trợ giải và kiểm nghiệm nhanh một instance BMP bằng bất kỳ solver nào:

```bash
# Chạy solver mặc định (CP-SAT) trên đồ thị mẫu
python results/benchmark/run_solver.py

# Chỉ định solver cụ thể: [cpsat | gurobi | cplex_cp | cplex_mip]
python results/benchmark/run_solver.py cpsat
python results/benchmark/run_solver.py gurobi
python results/benchmark/run_solver.py cplex_cp
python results/benchmark/run_solver.py cplex_mip
```

### 5.2. Chạy Benchmark Đánh giá Tự động
Các script benchmark đều hỗ trợ cơ chế chạy worker độc lập, chống tràn RAM, tự động ghi nhận bộ nhớ đỉnh (Peak RSS) và hỗ trợ resume khi chạy tiếp:

```bash
# 1. Benchmark 5 phương pháp Solver (CP-SAT, CPLEX CP, CPLEX MIP, Gurobi, SAT)
python results/benchmark/benchmark_group3.py

# 2. Benchmark so sánh 5 kỹ thuật mã hóa At-Most-One (AMO)
python results/benchmark/benchmark_amo.py

# 3. Benchmark so sánh Repeated SAT vs Incremental SAT và Pairwise vs Order
python results/benchmark/benchmark_group1.py
```

### 5.3. Trực quan hóa và Phân tích Dữ liệu
Các Jupyter Notebook trong `results/visualization/notebooks/` cung cấp phân tích chi tiết:
* `group3_visualization.ipynb`: Đọc [group3_official_strong_lb_120s.csv](file:///home/hung/code/BMP/results/data/group3_official_strong_lb_120s.csv), vẽ biểu đồ so sánh chất lượng nghiệm, khoảng cách tương đối (Relative Gap), thời gian giải và mức tiêu thụ RAM giữa các Solver.
* `amo_visualization.ipynb`: Đọc [amo_120s.csv](file:///home/hung/code/BMP/results/data/amo_120s.csv), đánh giá số lượng biến/mệnh đề phụ sinh ra và ảnh hưởng đến thời gian giải.
* `group1_visualization.ipynb`: Đọc [group1_product_120s.csv](file:///home/hung/code/BMP/results/data/group1_product_120s.csv), so sánh tỷ lệ giải thành công và tốc độ hội tụ của Incremental SAT.

### 5.4. Biên dịch Báo cáo LaTeX
Báo cáo khoa học hoàn chỉnh được viết bằng LaTeX chuẩn định dạng Elsevier CAS (`cas-sc`):

```bash
cd report
xelatex bmp_report.tex
xelatex bmp_report.tex  # Chạy 2 lần để cập nhật cross-references
```

---

## 6. Kết quả Thực nghiệm Chính

Đánh giá thực nghiệm trên **113 đồ thị chuẩn Harwell-Boeing** với giới hạn tài nguyên khắt khe (120 giây và 8 GiB RAM mỗi lượt chạy):
1. **Khảo sát AMO**:
   * Kỹ thuật **2D Product** cho thấy sự cân bằng tối ưu giữa số lượng biến phụ và mệnh đề, đạt bandwidth tốt nhất quan sát được (kể cả hòa) trên **83/113** đồ thị.
   * Kỹ thuật **Sequential Counter** đạt số lượng chứng minh tối ưu cao nhất trong nhóm AMO (7 instance).
2. **Chiến lược SAT**:
   * Mô hình **Pairwise + Product + Incremental SAT** vượt trội hoàn toàn so với Repeated SAT: tìm được bandwidth nhỏ hơn trên **77/113** đồ thị và tiết kiệm đáng kể thời gian tìm kiếm nhờ tái sử dụng tri thức học được.
3. **So sánh Solvers**:
   * **IBM CPLEX CP Optimizer** và **Google OR-Tools CP-SAT** thể hiện hiệu năng tìm nghiệm khả thi rất mạnh trên các đồ thị cỡ lớn.
   * **Incremental SAT** cho khả năng chứng minh cận dưới và thu hẹp gap nhanh chóng ở các đồ thị có cấu trúc đặc thù.

---

## 7. Thành viên Thực hiện & Phân công Công việc

Dự án được thực hiện bởi nhóm sinh viên Khoa Công nghệ Thông tin, Trường Đại học Công nghệ (UET - VNU):

| Thành viên | Tài khoản GitHub | Phân công nhiệm vụ chính |
| :--- | :--- | :--- |
| **Phạm Đức Hùng** | `@Pham-Duc-Hung` | Nghiên cứu và cài đặt các SAT Encodings (Pairwise, Order), 5 kỹ thuật AMO, tiền xử lý đồ thị và hoàn thiện báo cáo LaTeX. |
| **Trần Nhật Hưng** | [`@NhHung07`](https://github.com/NhHung07) | Nghiên cứu, mô hình hóa và cài đặt các **Exact Solvers** (Google CP-SAT, Gurobi MIP, CPLEX CP, CPLEX MIP), kịch bản benchmark và trực quan hóa kết quả Nhóm 3. |
| **Phạm Hồng Nam** | `@phamnam` | Nghiên cứu cấu trúc dữ liệu, thu thập và tiền xử lý bộ dữ liệu Harwell-Boeing, kiểm nghiệm nghiệm (Verification) và đánh giá thực nghiệm. |

---

## 8. Giấy phép (License)
Dự án được phát triển phục vụ mục đích nghiên cứu và học tập trong khuôn khổ học phần Các vấn đề hiện đại trong Khoa học Máy tính.
Mã nguồn được lưu trữ tại: [GitHub Repository](https://github.com/NhHung07/Bandwidth-Minimization-Problem).
