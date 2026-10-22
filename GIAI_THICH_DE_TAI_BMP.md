# Giải thích đề tài Bandwidth Minimization Problem (BMP)

> Tài liệu này dành cho người mới bắt đầu. Nguồn yêu cầu chính là [Assignment 2 - requirements.pdf](Assignment%202%20-%20requirements.pdf), đặc biệt là dòng **topic 2** ở trang 1 và phần yêu cầu chung ở trang 1–2. [Bandwidth Minimization Problem - BMP.pdf](Bandwidth%20Minimization%20Problem%20-%20BMP.pdf) là bài báo tham khảo để hiểu bài toán và cách trình bày một bài báo khoa học. Khi hai tài liệu có trọng tâm khác nhau, nhóm phải theo **file yêu cầu bài tập**.

## 1. Tóm tắt trong một phút

BMP yêu cầu **xếp các đỉnh của một đồ thị vào các vị trí 1, 2, ..., n**, mỗi vị trí đúng một đỉnh, sao cho **hai đỉnh nối với nhau không bị đặt quá xa**, xét theo *cạnh có khoảng cách lớn nhất*. Giá trị lớn nhất ấy gọi là **bandwidth**; mục tiêu là tìm cách xếp có bandwidth nhỏ nhất.

Trong bài tập này, nhóm không chỉ tìm một cách xếp tốt. Nhóm cần xây dựng và đánh giá **các phương pháp giải chính xác**: hai cách chuyển BMP thành SAT (**pairwise encoding** và **order encoding**), thử cả **SAT nhiều lần** và **Incremental SAT**, rồi so sánh với **CPLEX CP, CPLEX MIP, Gurobi và CP-SAT**. Cuối cùng, nhóm nộp mã nguồn, kết quả thực nghiệm và báo cáo dạng bài báo khoa học.

## 2. BMP là bài toán gì?

### 2.1. Từ đồ thị đến thứ tự các đỉnh

Một đồ thị vô hướng `G = (V, E)` gồm:

- `V`: tập đỉnh, có `n` đỉnh;
- `E`: tập cạnh; `(u, v) ∈ E` nghĩa là `u` và `v` có liên kết.

Ta gán cho mỗi đỉnh `v` một **nhãn/vị trí** `π(v)` thuộc `{1, ..., n}`. Mỗi nhãn chỉ dùng một lần, nên `π` là một **hoán vị**. Với một cách gán cụ thể:

```text
B(π) = max {|π(u) - π(v)| : (u, v) ∈ E}
```

Giá trị tối ưu cần tìm là `B* = minπ B(π)`. Với đồ thị không có cạnh, có thể quy ước `B(π) = 0` và ghi rõ quy ước này trong chương trình/báo cáo.

**Điểm dễ nhầm:** ta tối thiểu hóa **khoảng cách lớn nhất trên các cạnh**, không phải tổng khoảng cách của tất cả cạnh. Tên “bandwidth” ở đây cũng không phải băng thông mạng Internet.

### 2.2. Ví dụ rất nhỏ

Xét đồ thị đường đi `A — B — C — D`, gồm ba cạnh `(A,B)`, `(B,C)`, `(C,D)`.

| Cách xếp | Vị trí của A, B, C, D | Khoảng cách trên ba cạnh | Bandwidth |
| --- | --- | --- | --- |
| Xếp chưa tốt | `1, 3, 4, 2` | `2, 1, 2` | `2` |
| Xếp tốt | `1, 2, 3, 4` | `1, 1, 1` | `1` |

Cách xếp thứ hai có bandwidth `1`, và không thể thấp hơn `1` vì đồ thị có cạnh, còn hai đỉnh khác nhau phải nhận hai vị trí khác nhau. Vậy `B* = 1`.

### 2.3. Vì sao bài báo nói đến ma trận?

Một đồ thị có thể biểu diễn bằng **ma trận kề**: ô `A[i,j]` khác 0 nếu hai đỉnh `i, j` có cạnh. Khi ta đổi thứ tự các đỉnh, ta đồng thời đổi thứ tự hàng và cột. Mục tiêu là đưa mọi phần tử khác 0 của ma trận đến gần đường chéo chính nhất có thể. Khoảng cách xa nhất tới đường chéo chính chính là bandwidth của cách sắp xếp đó.

Bài báo tham khảo nghiên cứu một thuật toán **simulated annealing** cho BMP và dùng các ma trận thưa Harwell–Boeing để thực nghiệm. Nó giúp hiểu định nghĩa, bối cảnh và cách viết phần thực nghiệm. **Bài tập không yêu cầu nhóm cài simulated annealing**; yêu cầu thực hiện của nhóm là SAT và các phương pháp chính xác được nêu trong file assignment. Bài báo cũng nói rằng trọng số cạnh không ảnh hưởng đến BMP không trọng số đang xét; khi chuyển ma trận thành đồ thị, cần ghi rõ cách xử lý giá trị khác 0, đường chéo và ma trận không đối xứng.

## 3. Tại sao lại dùng SAT?

SAT hỏi: **có cách gán đúng/sai cho các biến Boolean để mọi ràng buộc đều đúng không?** Solver SAT thường nhận công thức dạng **CNF**, tức phép `AND` của nhiều *clause*; mỗi clause là phép `OR` của các literal. Ví dụ `(¬a ∨ ¬b)` cấm `a` và `b` cùng đúng.

BMP là bài toán tối ưu, còn SAT trả lời câu hỏi có/không. Ta chuyển BMP thành câu hỏi quyết định:

> Với một ngưỡng `k`, có cách xếp nào mà **mọi cạnh** đều có độ dài `≤ k` hay không?

- **SAT:** có ít nhất một cách xếp hợp lệ với bandwidth `≤ k`.
- **UNSAT:** không có cách xếp nào đạt bandwidth `≤ k`.

Nếu đã biết `k` khả thi và chứng minh `k - 1` không khả thi, thì `k` là **tối ưu**. Trạng thái hết thời gian chạy hoặc chưa chứng minh xong **không được xem là UNSAT**.

Một **encoding** là cách chọn biến Boolean và viết các ràng buộc BMP thành CNF. Encoding đúng phải bảo đảm cả hai chiều: mọi cách xếp hợp lệ đều có thể tạo ra một nghiệm SAT, và mọi nghiệm SAT khi giải mã đều là một cách xếp hợp lệ.

## 4. Hai SAT encoding nhóm phải cài đặt

File yêu cầu chỉ nêu tên “pairwise encoding” và “order encoding”, chưa cho công thức chi tiết. Hai mô hình dưới đây là một cách hiện thực rõ ràng để nhóm bắt đầu; khi trao đổi với giảng viên, nên xác nhận cách hiểu “pairwise encoding” mà môn học mong muốn.

### 4.1. Pairwise encoding: biến “đỉnh ở vị trí nào”

Đặt `x[v,p] = True` nếu đỉnh `v` được xếp ở vị trí `p` (`p = 1, ..., n`). Với ví dụ trên, `x[A,1] = True` nghĩa là `A` mang nhãn `1`.

Cần ba nhóm ràng buộc:

1. **Mỗi đỉnh có đúng một vị trí.** “Ít nhất một” (*ALO*) là clause `x[v,1] ∨ ... ∨ x[v,n]`. “Nhiều nhất một” (*AMO*) theo pairwise là, với mọi `p < q`, thêm `(¬x[v,p] ∨ ¬x[v,q])`.
2. **Mỗi vị trí có đúng một đỉnh.** Tương tự, tạo ALO và AMO trên các biến `x[v,p]` khi cố định `p` và thay đổi `v`. Có thể bỏ một số clause ALO dư thừa nếu đã chứng minh tương đương, nhưng bản đầu nên giữ cho dễ kiểm tra.
3. **Hai đầu một cạnh không cách nhau quá `k`.** Với mỗi cạnh `(u,v)` và mỗi cặp vị trí `p,q` có `|p-q| > k`, thêm clause `(¬x[u,p] ∨ ¬x[v,q])`.

Ví dụ nếu `k = 1`, `(A,B)` là cạnh thì `A` ở vị trí 1 và `B` ở vị trí 4 phải bị cấm bằng `(¬x[A,1] ∨ ¬x[B,4])`.

Tên **pairwise** ở đây thể hiện trực tiếp qua các clause AMO cấm từng *cặp* lựa chọn trùng nhau. Phần ràng buộc cạnh cũng cấm từng cặp vị trí không hợp lệ. Cách này dễ hiểu và dễ kiểm chứng, nhưng số clause có thể tăng mạnh khi `n` và số cạnh lớn.

### 4.2. Order encoding: biến “đỉnh đã nằm trước mốc nào”

Đặt `t[v,i] = True` nếu `π(v) ≤ i`, với `i = 1, ..., n-1`. Để viết công thức gọn, quy ước `t[v,0] = False` và `t[v,n] = True` (đây là hằng, không phải biến cần tạo).

Ví dụ, nếu `π(A) = 3` trong đồ thị 4 đỉnh, thì `t[A,1]` và `t[A,2]` sai, còn `t[A,3]` và `t[A,4]` đúng. Như vậy vị trí của một đỉnh là điểm dãy giá trị chuyển từ sai sang đúng.

Các ràng buộc chính:

1. **Dãy đơn điệu:** `t[v,i] ⇒ t[v,i+1]`, tức `(¬t[v,i] ∨ t[v,i+1])`. Điều này làm cho mỗi đỉnh có đúng một điểm chuyển, hay đúng một vị trí.
2. **Không có hai đỉnh chung vị trí `p`:** đỉnh `v` ở `p` khi `t[v,p] ∧ ¬t[v,p-1]`. Với mọi hai đỉnh khác nhau `u,v`, cấm chúng cùng chuyển tại `p` bằng clause `(¬t[u,p] ∨ t[u,p-1] ∨ ¬t[v,p] ∨ t[v,p-1])`. Vì có `n` đỉnh, `n` vị trí và mỗi đỉnh nhận một vị trí, điều kiện không trùng bảo đảm đây là hoán vị.
3. **Cạnh có độ dài không quá `k`:** với mỗi cạnh `(u,v)`, thêm `t[u,i] ⇒ t[v,i+k]` và `t[v,i] ⇒ t[u,i+k]` cho các mốc có `i+k < n`. Chẳng hạn nếu `u` đã ở không quá vị trí `i`, thì `v` phải ở không quá `i+k`; viết chiều ngược lại để khống chế khoảng cách tuyệt đối.

Các hằng ở biên `0` và `n` phải được thay bằng đúng/sai khi sinh CNF. Có thể viết một order encoding tương đương theo mốc “`π(v) ≥ i`”; khi đó công thức đổi chiều. Điều quan trọng là nhóm ghi **rõ ý nghĩa biến và chứng minh ràng buộc đúng**.

### 4.3. Phân biệt “encoding BMP” với “encoding AMO/ALO”

**Pairwise** và **order** là hai cách chính nhóm cần so sánh cho BMP. Bên trong mỗi cách, ta còn có thể chọn cách viết các ràng buộc đếm như AMO/ALO. File yêu cầu **khuyến khích** thử thêm binary, commander, product, sequential counter qua PySAT. Đây là phần mở rộng để đánh giá ảnh hưởng của cách mã hóa ràng buộc; nó không thay cho việc phải có cả hai encoding BMP.

## 5. Hai cách sử dụng SAT solver nhóm phải thực nghiệm

### SAT nhiều lần

Với mỗi ngưỡng `k` cần thử, nhóm tạo công thức CNF cho ngưỡng đó và gọi solver. Có thể kiểm tra từ cận trên đi xuống, hoặc dùng tìm kiếm nhị phân vì tính khả thi có tính đơn điệu: nếu `k` khả thi thì mọi ngưỡng lớn hơn cũng khả thi. Khi báo cáo, cần ghi rõ chiến lược duyệt ngưỡng, vì nó ảnh hưởng số lần gọi solver.

### Incremental SAT

Nhóm giữ **cùng một solver** và tận dụng các ràng buộc/tri thức đã có qua nhiều lần thử ngưỡng. Một cách dễ hiểu là bắt đầu từ cận trên khả thi, rồi **siết ngưỡng giảm dần**: thêm các clause cần thiết khi chuyển từ `k` sang `k-1`, gọi lại solver, và dừng ở ngưỡng đầu tiên UNSAT. Vì chỉ thêm ràng buộc, mô hình incremental này hợp với cả hai encoding ở trên. Có thể dùng *assumption literals* nếu muốn kiểm tra ngưỡng linh hoạt mà không tích lũy vĩnh viễn clause; cần giải thích rõ phương án chọn trong báo cáo.

**Lưu ý thực nghiệm:** “SAT nhiều lần” và “Incremental SAT” là hai cách tổ chức việc giải cùng bài toán, không phải hai định nghĩa khác của BMP. Nên dùng cùng dữ liệu, cùng giới hạn thời gian và cùng chính sách tiền xử lý để so sánh công bằng; tách thời gian **sinh CNF** và thời gian **solver chạy**, đồng thời báo cáo tổng thời gian.

## 6. So sánh với các bộ giải chính xác khác

Yêu cầu chung của assignment nói phải so sánh SAT Solving với các phương pháp chính xác khác: **CPLEX CP, CPLEX MIP, Gurobi và CP-SAT**. Đây là bốn hướng/bộ giải nhóm cần đưa vào kế hoạch thực nghiệm, tùy mô hình tương ứng:

| Hướng | Ý tưởng mô hình cơ bản |
| --- | --- |
| CPLEX CP | Biến nguyên `pos[v]` cho vị trí, `AllDifferent(pos)`, và `|pos[u]-pos[v]| ≤ B` cho mỗi cạnh; tối thiểu hóa `B`. |
| CPLEX MIP | Biến nhị phân gán đỉnh–vị trí (hoặc biến nguyên cùng tuyến tính hóa), ràng buộc hoán vị và ràng buộc biên độ cạnh; tối thiểu hóa `B`. |
| Gurobi | Mô hình MIP cho cùng mục tiêu, có thể dùng cấu trúc tương tự CPLEX MIP. |
| CP-SAT | Biến nguyên vị trí, `AllDifferent`, ràng buộc độ lệch tuyệt đối và mục tiêu `min B`. |

**CP-SAT là tên một bộ giải tối ưu hóa ràng buộc**; dù có SAT bên trong, trong báo cáo nó là phương pháp đối chiếu với encoding CNF + SAT solver của nhóm. Với bộ giải MIP/CP, cần ghi rõ nghiệm tốt nhất, cận chứng minh và trạng thái tối ưu/hết giờ; một nghiệm tìm được chưa đủ để kết luận tối ưu.

## 7. Cụ thể nhóm cần làm gì?

### Việc bắt buộc theo file assignment

1. **Nhóm 2–3 sinh viên**, chọn/đăng ký BMP và thống nhất với giảng viên nếu cách hiểu đề hoặc encoding chưa rõ.
2. **Hiểu bài toán và biểu diễn dữ liệu:** đọc ma trận/đồ thị, định nghĩa phép gán vị trí, tính lại bandwidth của một lời giải để kiểm tra độc lập.
3. **Cài hai SAT encoding:** pairwise và order; giải mã nghiệm SAT ra thứ tự đỉnh; kiểm tra tất cả vị trí khác nhau và mọi cạnh thỏa ngưỡng.
4. **Thực nghiệm cả hai kiểu SAT:** SAT nhiều lần và Incremental SAT cho **mỗi encoding**. Như vậy có ít nhất bốn cấu hình SAT chính: `pairwise × nhiều lần`, `pairwise × incremental`, `order × nhiều lần`, `order × incremental`.
5. **Cài và so sánh các solver chính xác còn lại:** CPLEX CP, CPLEX MIP, Gurobi, CP-SAT, trên cùng bộ dữ liệu và với quy tắc đo thống nhất.
6. **Thử trên các ma trận có kích thước lớn**, trình bày kết quả bằng bảng/đồ thị; file yêu cầu chỉ nói “kích thước lớn”, không ấn định số đỉnh hay bắt dùng toàn bộ 113 instance trong bài báo.
7. **Viết báo cáo dạng bài báo khoa học bằng LaTeX**, theo mẫu/hướng dẫn môn học và lớp Elsevier `\documentclass[a4paper,fleqn]{cas-sc}` được nêu trong assignment.
8. **Nộp mã nguồn, kết quả thực nghiệm** và ghi link repository ở mục **Data Availability** của báo cáo. File yêu cầu cũng chỉ định dùng thư viện Python [cnsplots](https://cnsplots.farid.one/latest/) để trực quan hóa kết quả.

### Phần được khuyến khích thêm

- So sánh thêm các cách mã hóa AMO/ALO như binary, commander, product, sequential counter qua PySAT.
- Tự thiết kế cấu trúc trình bày báo cáo sao cho kết quả rõ ràng.

File yêu cầu cho phép dùng [PySAT](https://pysathq.github.io/) để gọi solver và tạo encoding, hoặc gọi SAT solver trực tiếp. Các solver được nêu làm ví dụ gồm CaDiCaL, Glucose, Kissat, CryptoMiniSat. **Đây là lựa chọn công cụ, không có nghĩa nhóm phải dùng tất cả.**

## 8. Nên triển khai và kiểm tra theo thứ tự nào?

1. **Làm ví dụ nhỏ bằng tay:** đường đi, chu trình, đồ thị đầy đủ, đồ thị không cạnh. Ghi bandwidth tối ưu dự kiến. Ví dụ đồ thị đầy đủ `K_n` luôn có bandwidth `n-1`, vì hai đỉnh ở hai đầu vị trí 1 và `n` chắc chắn có cạnh.
2. **Viết hàm đọc dữ liệu và kiểm tra lời giải:** từ thứ tự đỉnh tính `max |π(u)-π(v)|`. Dùng hàm này để xác thực mọi solver, tránh tin hoàn toàn vào giá trị solver trả về.
3. **Làm pairwise với một ngưỡng cố định**, đối chiếu SAT/UNSAT với vét cạn trên đồ thị rất nhỏ; sau đó làm order và đối chiếu hai encoding.
4. **Viết vòng tìm tối ưu:** thử nhiều `k`, phân biệt SAT, UNSAT và timeout; chỉ tuyên bố tối ưu khi có chứng cứ đủ.
5. **Thêm incremental**, giữ đúng solver qua các lần siết ngưỡng và kiểm tra kết quả tối ưu phải trùng với cách nhiều lần trên bài nhỏ.
6. **Xây mô hình CPLEX CP/MIP, Gurobi, CP-SAT** và kiểm tra chúng trả cùng giá trị tối ưu trên tập nhỏ.
7. **Chạy benchmark lớn:** khóa cùng phiên bản dữ liệu, máy, giới hạn thời gian, số luồng và cách ghi thời gian. Lưu dữ liệu thô trước khi tạo hình.
8. **Viết báo cáo khi đã có số liệu kiểm chứng**, kèm mô hình toán, công thức encoding, môi trường thực nghiệm, bảng so sánh và phân tích nguyên nhân chênh lệch.

### Một bảng kết quả tối thiểu nên có

| Trường | Mục đích |
| --- | --- |
| Tên instance, `n`, số cạnh `m` | Biết độ lớn và độ dày của đồ thị. |
| Phương pháp/solver | Phân biệt 4 cấu hình SAT và 4 phương pháp đối chiếu. |
| Bandwidth tốt nhất, cận dưới, trạng thái | Biết nghiệm có tối ưu được chứng minh hay chưa. |
| Thời gian tạo mô hình/CNF, thời gian giải, tổng thời gian | So sánh công bằng và giải thích chi phí encoding. |
| Số biến, số clause đối với SAT | Giải thích vì sao encoding nhanh/chậm hoặc tốn bộ nhớ. |
| Số lần gọi SAT, số lần SAT/UNSAT/timeout | Làm rõ chiến lược tìm ngưỡng. |

Nếu một cấu hình timeout, ghi **timeout** cùng nghiệm/cận đã biết; không điền giả một giá trị tối ưu. Với dữ liệu ma trận, báo cáo rõ cách tạo cạnh từ phần tử khác 0, bỏ đường chéo, xử lý ma trận không đối xứng, và việc không dùng trọng số nếu theo BMP không trọng số.

## 9. Báo cáo LaTeX nên có nội dung gì?

Một dàn ý hợp lý cho bài báo của nhóm:

1. **Title, Abstract, Keywords:** bài toán, bốn cấu hình SAT, các solver đối chiếu và kết quả chính.
2. **Introduction:** BMP là gì, vì sao khó, mục tiêu và đóng góp của nhóm.
3. **Problem definition / Related work:** đồ thị, bandwidth, bài báo BMP tham khảo và những phương pháp liên quan; trích dẫn đúng nguồn.
4. **Methods:** pairwise, order, cách tìm tối ưu bằng SAT nhiều lần/incremental, và mô hình CP/MIP/CP-SAT. Ghi rõ công thức để người đọc kiểm tra tính đúng.
5. **Experimental setup:** dữ liệu, tiền xử lý, máy/phiên bản phần mềm, giới hạn thời gian, tham số solver, cách đo.
6. **Results and discussion:** bảng, đồ thị, tỷ lệ giải được, thời gian, kích thước CNF, phân tích trường hợp thắng/thua và giới hạn của thực nghiệm.
7. **Conclusion, references, Data Availability:** kết luận bám theo số liệu; link repository chứa mã nguồn và dữ liệu/kết quả.

Bài báo BMP có cấu trúc bài nghiên cứu (giới thiệu, công trình liên quan, phương pháp, thí nghiệm, kết luận), nhưng **không phải template LaTeX của assignment**. File assignment còn nhắc tới “Mau xay dung Bao cao BTL so 1 và BTL so 2.pdf”; file đó **hiện không có trong thư mục dự án**, nên nhóm cần lấy từ giảng viên/lớp để đối chiếu định dạng cuối cùng.

## 10. Những câu hỏi cần tự trả lời trước khi nộp

- Giá trị `B*` của một instance được **chứng minh tối ưu**, hay mới chỉ là nghiệm tốt nhất tìm được trong thời gian cho phép?
- Với mỗi encoding, mọi nghiệm SAT giải mã ra đúng một hoán vị và thỏa mọi cạnh chưa?
- Hai encoding và các solver đối chiếu có trả cùng tối ưu trên bộ instance nhỏ đã biết đáp án không?
- Incremental có thực sự tái sử dụng cùng solver và việc thêm ràng buộc có đúng chiều khi giảm `k` không?
- Bảng/đồ thị có so sánh trên cùng tập instance và cùng giới hạn tài nguyên không?
- Repository có đủ mã chạy, dữ liệu/kết quả và hướng dẫn tái hiện; báo cáo có link ở **Data Availability** không?

## Nguồn đọc tiếp

- [Yêu cầu Assignment 2 của môn học](Assignment%202%20-%20requirements.pdf) — nguồn quyết định phạm vi phải làm.
- [Bài báo BMP đi kèm](2%20-%20Bandwidth%20Minimization%20Problem%20-%20%20BMP.pdf) — định nghĩa BMP, quan hệ với ma trận thưa và ví dụ cách trình bày thực nghiệm. Bài báo gốc: Torres-Jimenez và cộng sự, *Information Sciences* 303 (2015), 33–49, [DOI: 10.1016/j.ins.2014.12.041](https://doi.org/10.1016/j.ins.2014.12.041).
- [Tài liệu PySAT về cardinality encoding](https://pysathq.github.io/docs/html/api/card.html) và [SAT solver/incremental assumptions](https://pysathq.github.io/docs/html/api/solvers.html) — tham khảo khi cài AMO/ALO và Incremental SAT.
