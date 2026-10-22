# BMP — hiểu bài toán và lộ trình thực hiện Assignment 2

Tài liệu này giải thích **vì sao** mỗi phần của dự án cần tồn tại và **luồng thực thi** từ dữ liệu đầu vào đến báo cáo. Nguồn yêu cầu là file `Assignment 2 - requirements.pdf` trong thư mục gốc. Bài báo `2 - Bandwidth Minimization Problem -  BMP.pdf` giúp hiểu bài toán và bộ benchmark; Assignment 2 nói rõ bài báo **chỉ để tham khảo về BMP**, không yêu cầu cài thuật toán simulated annealing trong bài báo.

## 1. Đầu tiên: BMP đang tối ưu điều gì?

Đầu vào của một instance là đồ thị vô hướng `G = (V, E)` có `n` đỉnh. Ta gán cho mỗi đỉnh một vị trí khác nhau từ `1` đến `n`; gọi phép gán này là `π`. Với một thứ tự cụ thể, bandwidth là:

```text
B(π) = max {|π(u) - π(v)| : (u, v) thuộc E}
```

Mục tiêu là tìm `π` sao cho `B(π)` nhỏ nhất. Nếu đồ thị không có cạnh, chương trình nên quy ước bandwidth là `0` và ghi rõ quy ước đó.

Ví dụ, với đường đi `A—B—C—D`, thứ tự `A,B,C,D` có bandwidth `1`; thứ tự `A,C,B,D` có bandwidth `2` vì cạnh `A—B` trải qua hai vị trí. Bài toán không chỉ hỏi “có một thứ tự hợp lệ không?” vì **mọi hoán vị đều là một thứ tự hợp lệ**; nó hỏi thứ tự nào cho giá trị lớn nhất trên các cạnh là nhỏ nhất.

Ở góc nhìn ma trận, đổi vị trí các đỉnh tương đương với đổi cùng một thứ tự hàng và cột của ma trận. Ta muốn các ô khác 0 ở gần đường chéo chính. Với BMP không trọng số đang xét, vị trí phần tử khác 0 quyết định cạnh; giá trị số của phần tử không đi vào công thức bandwidth.

## 2. Dataset ở đâu và phải đọc như thế nào?

`data/hb_33/` có 33 file và `data/hb_80/` có 80 file, tổng cộng 113 instance. Đây là các ca thử gắn với những tên trong các bảng kết quả Harwell–Boeing của bài báo: bảng 6 là nhóm 33, bảng 7 và 8 trình bày nhóm 80. **Các bảng trong bài báo là kết quả tham chiếu; các file trong `data/` mới là đầu vào của chương trình.**

Một file hiện có, ví dụ `data/hb_33/bcspwr01.mtx.rnd`, bắt đầu như sau:

```text
Nombre del problema: bcspwr01.mtx.rnd
39 39 46
1 30
1 6
...
```

Dòng thứ hai ghi `số hàng số cột số cạnh`; các dòng sau là cặp đỉnh, đánh số từ 1. File này mô tả đồ thị 39 đỉnh, 46 cạnh. Phần mở rộng `.mtx.rnd` dễ gây nhầm: **đây là danh sách cạnh riêng của benchmark, không phải tệp Matrix Market `.mtx` chuẩn**. Hãy viết parser cho đúng định dạng này, không gọi thẳng `scipy.io.mmread`.

Việc cần làm trong `src/graph.py`:

1. Đọc header; kiểm tra ma trận vuông và số dòng cạnh khớp với `m`.
2. Kiểm tra chỉ số đỉnh nằm trong `1..n`; chuẩn hóa mỗi cạnh thành `(min(u,v), max(u,v))`.
3. Xác định và ghi rõ chính sách với cạnh trùng, self-loop, đồ thị nhiều thành phần. Nếu lọc cạnh, lưu cả số cạnh trước và sau khi lọc.
4. Trả về **cùng một đồ thị đã chuẩn hóa** cho SAT, CP và MIP. Nếu từng solver đọc file theo cách khác nhau thì số liệu so sánh không còn có ý nghĩa.
5. Lưu tên instance và đường dẫn nguồn để sau này có thể chạy lại đúng ca thử.

Việc cần làm trong `src/verify.py`: nhận đồ thị và hoán vị do solver trả về; kiểm tra đủ `n` đỉnh, không trùng vị trí, rồi **tự tính lại** `B(π)` theo mọi cạnh. Đây là lớp kiểm chứng chung cho tất cả solver; không chỉ tin giá trị mục tiêu mà solver báo.

## 3. Vì sao cần SAT nhiều lần để giải bài toán tối ưu?

SAT solver cơ bản trả lời câu hỏi đúng/sai. Với một ngưỡng `k`, ta hỏi:

> Có hoán vị `π` nào mà mọi cạnh `(u,v)` đều thỏa `|π(u)-π(v)| ≤ k` không?

Nếu câu trả lời là SAT, `k` là một **cận trên khả thi**. Nếu UNSAT, mọi giá trị `≤ k` đều bất khả thi. Từ đó ta tìm `k` nhỏ nhất. Nếu `k` khả thi và `k-1` được chứng minh UNSAT, ta mới có chứng minh tối ưu. **Timeout không phải UNSAT.** Một lời giải tốt nhất tìm được khi timeout chỉ là cận trên, chưa chắc là tối ưu.

Hai kiểu chạy Assignment 2 yêu cầu:

- **SAT nhiều lần (`src/search/repeated.py`):** dựng hoặc nạp công thức cho từng `k` và gọi solver mới mỗi lần. Cách này đơn giản, là mốc kiểm tra tính đúng.
- **Incremental SAT (`src/search/incremental.py`):** giữ một solver và tái sử dụng các clause đã học khi thay đổi `k`; dùng assumptions/activation literals hoặc chỉ thêm những ràng buộc làm ngưỡng chặt hơn. Cách thêm ràng buộc phải giữ đúng logic của ngưỡng hiện tại. Mục tiêu thực nghiệm là xem việc tái sử dụng có tiết kiệm thời gian hay không.

Hai cách phải trả cùng kết luận trên những đồ thị nhỏ nếu đều hoàn thành. Trong kết quả, ghi cả thời gian tạo CNF và thời gian giải, số lần gọi SAT, trạng thái SAT/UNSAT/timeout.

## 4. Hai encoding BMP bắt buộc là gì?

### Pairwise BMP (`src/encodings/bmp/pairwise.py`)

Một lựa chọn là biến Boolean `x[v,p]`: đỉnh `v` đặt ở vị trí `p`. Cần bảo đảm mỗi đỉnh chiếm đúng một vị trí, mỗi vị trí có đúng một đỉnh. Với mỗi cạnh `(u,v)` và mọi cặp vị trí `(p,q)` mà `|p-q| > k`, cấm đồng thời `x[u,p]` và `x[v,q]`. Khi đó một nghiệm SAT tương ứng với một hoán vị có bandwidth không vượt `k`.

### Order BMP (`src/encodings/bmp/order.py`)

Một lựa chọn là biến ngưỡng `t[v,p]` mang nghĩa `π(v) ≤ p`. Các biến của cùng đỉnh phải đơn điệu theo `p`; điểm chuyển trạng thái xác định vị trí của đỉnh. Cần thêm ràng buộc để mỗi vị trí thuộc đúng một đỉnh và để hai đầu mỗi cạnh cách nhau không quá `k`. Ví dụ, nếu `π(u) ≤ p` thì từ điều kiện cạnh phải suy ra `π(v) ≤ p+k` khi `p+k` còn trong miền. Khi cài đặt, phải ghi rõ ý nghĩa biến, các trường hợp biên, cách giải mã nghiệm và lập luận tại sao công thức tương đương với bài toán gốc.

**Phân biệt rất quan trọng:** `src/encodings/cardinality/binomial.py` chỉ là một cách mã hóa ràng buộc **At-Most-One (AMO)** bằng các cặp clause. Nó có thể được gọi từ pairwise BMP, nhưng **không tự nó là pairwise BMP**. Tương tự, binary, commander, product và sequential counter là các lựa chọn cho AMO/ALO được Assignment 2 **khuyến khích thử thêm**. Chúng không thay thế yêu cầu cài cả pairwise BMP và order BMP.

Vì có 2 encoding BMP × 2 kiểu chạy SAT, phần thực nghiệm SAT bắt buộc cần tối thiểu **4 cấu hình**:

| Encoding BMP | SAT nhiều lần | Incremental SAT |
| --- | --- | --- |
| Pairwise | Bắt buộc | Bắt buộc |
| Order | Bắt buộc | Bắt buộc |

## 5. Vì sao còn cần CPLEX, Gurobi và CP-SAT?

Assignment 2 yêu cầu so sánh SAT với các phương pháp giải chính xác khác: CPLEX CP, CPLEX MIP, Gurobi và CP-SAT. Các module tương ứng nằm ở `src/solvers/`. Mỗi module phải dùng **đúng đồ thị đã chuẩn hóa** và trả về tối thiểu: hoán vị/nhãn vị trí, bandwidth, thời gian, trạng thái, cùng cận dưới nếu solver cung cấp.

Các solver khác nhau có thể tìm được cùng một nghiệm nhưng tốn thời gian rất khác nhau. Vì vậy, cần dùng cùng máy, cùng giới hạn thời gian, cùng số luồng nếu có thể và cùng tập instance. Trên những ca chưa giải xong, ghi nghiệm khả thi và cận chứng minh riêng; chỉ đánh dấu `OPTIMAL` khi có chứng cứ.

## 6. Thứ tự công việc nên làm

| Giai đoạn | Công việc | Điều kiện để coi là xong |
| --- | --- | --- |
| 0. Chuẩn bị | Nhóm 2–3 người, đăng ký đề tài; thống nhất với giảng viên nếu diễn giải “pairwise/order” còn khác nhau | Có phạm vi và quy ước mô hình được ghi lại |
| 1. Dữ liệu | Viết `graph.py`, đọc `.mtx.rnd`, chuẩn hóa; viết `verify.py` | Đọc được toàn bộ 113 file, đếm đúng `n,m`; kiểm tra được một hoán vị bất kỳ |
| 2. Đồ thị nhỏ | Tự tạo đường đi, chu trình, đồ thị đầy đủ và đồ thị không cạnh | Biết trước hoặc vét cạn được đáp án để đối chiếu |
| 3. Pairwise | Cài công thức quyết định với `k`, giải mã nghiệm | Với đồ thị nhỏ, SAT/UNSAT và bandwidth tính lại đều đúng |
| 4. Order | Cài công thức quyết định độc lập, giải mã nghiệm | Trả cùng kết luận với pairwise trên đồ thị nhỏ |
| 5. Tối ưu SAT | Cài repeated và incremental cho **cả hai** encoding | Bốn cấu hình cho cùng tối ưu trên ca nhỏ đã kiểm chứng |
| 6. Solver đối chiếu | Cài CPLEX CP, CPLEX MIP, Gurobi, CP-SAT | Kết quả được `verify.py` chấp nhận; tối ưu trùng nhau trên ca giải hết |
| 7. Thực nghiệm | Chạy cùng bộ instance, có các ma trận lớn; lưu CSV thô | Có trạng thái, bandwidth/cận, thời gian và cấu hình máy cho từng lần chạy |
| 8. Mở rộng | Thử AMO/ALO binary, commander, product, sequential nếu còn thời gian | Báo cáo rõ ảnh hưởng đến số biến/clause và thời gian |
| 9. Báo cáo | Vẽ hình bằng `cnsplots`, viết LaTeX `cas-sc`, công bố nguồn và kết quả | Báo cáo có Data Availability trỏ đến repository tái lập được |

Đây là thứ tự phụ thuộc: chưa có parser và verifier thì chưa thể tin số liệu solver; chưa kiểm chứng trên đồ thị nhỏ thì chạy tập lớn chỉ tạo ra nhiều kết quả khó biết đúng sai.

## 7. Luồng thực thi mục tiêu

```text
data/hb_33 hoặc data/hb_80 (*.mtx.rnd)
              │
              ▼
       src/graph.py  ──► đồ thị G = (V,E) đã chuẩn hóa
              │
              ├──► pairwise.py ──┐
              ├──► order.py ─────┼──► repeated.py / incremental.py ──┐
              └──► solvers/* ────┴─────────────────────────────────────┤
                                                                        ▼
                                                               src/verify.py
                                                                        │
                                                                        ▼
                                                       results/data/*.csv
                                                                        │
                                                                        ▼
                                               notebooks + cnsplots + report/
```

`scripts/benchmark_encodings.py` và `scripts/benchmark_solvers.py` là các chương trình điều phối luồng trên: chọn instance, cấu hình phương pháp, đặt timeout, gọi verifier và ghi CSV. Chúng **không nên chứa lại một bản cài thuật toán riêng**, vì như vậy rất dễ so sánh các chương trình đang giải những bài toán khác nhau.

## 8. Kết quả cần lưu để viết báo cáo có thể kiểm tra lại

Một dòng kết quả nên chứa: tên instance, nguồn file, `n`, số cạnh sau chuẩn hóa, phương pháp, encoding AMO/ALO (nếu có), ngưỡng/chiến lược tìm kiếm, bandwidth của nghiệm, cận dưới, trạng thái (`OPTIMAL`, `FEASIBLE`, `TIMEOUT`, `ERROR`...), thời gian tạo mô hình, thời gian giải, tổng thời gian, giới hạn thời gian và số luồng. Với SAT, thêm số biến, số clause và số lần gọi solver.

Bảng `LB`/`Best` trong bài báo là **mốc tham khảo của nghiên cứu trước**, không phải nhãn để đưa vào solver. Khi so sánh, phải chắc chắn đã dùng cùng định nghĩa đồ thị và cùng cách xử lý đỉnh cô lập/thành phần liên thông. Không ghi một giá trị “tối ưu” chỉ vì nó bằng `Best` nếu chương trình chưa chứng minh được tối ưu, trừ trường hợp có thể chứng minh bằng cận dưới độc lập.

## 9. Sản phẩm cuối theo Assignment 2

1. Mã nguồn cho 2 encoding BMP × 2 cách chạy SAT và 4 solver đối chiếu.
2. Tập kết quả thực nghiệm trên các ma trận lớn, bảng và đồ thị minh họa.
3. Báo cáo dạng bài báo khoa học bằng LaTeX, theo hướng dẫn trong file mẫu và `\documentclass[a4paper,fleqn]{cas-sc}`.
4. Repository chứa mã nguồn và kết quả; đường dẫn đặt tại mục **Data Availability**.
5. Hình minh họa thực nghiệm bằng thư viện Python `cnsplots` theo yêu cầu của Assignment 2.

Hiện các file Python/notebook/CSV mới là **vị trí dành sẵn**, chưa có cài đặt hay số liệu. Khi bắt đầu làm, ưu tiên hoàn thành và kiểm chứng từng giai đoạn trước khi chạy benchmark toàn bộ.
