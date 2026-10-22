# Dữ liệu đầu vào Harwell–Boeing

- `hb_33/`: 33 instance thuộc nhóm nhỏ trong bảng 6 của bài báo BMP.
- `hb_80/`: 80 instance thuộc nhóm lớn, được trình bày ở bảng 7 và 8.
- Tổng cộng: 113 file `.mtx.rnd`.

Các file hiện có là **edge list**, không phải Matrix Market `.mtx` chuẩn. Dòng đầu là tên; dòng thứ hai là `n n m`; `m` dòng còn lại chứa hai đỉnh của từng cạnh, đánh số từ 1. Ví dụ `hb_33/bcspwr01.mtx.rnd` bắt đầu bằng `39 39 46`, tức 39 đỉnh và 46 dòng cạnh. Parser cần kiểm tra header, miền chỉ số và chính sách với cạnh trùng/self-loop. Xem [WORKFLOW.md](../WORKFLOW.md) để hiểu vì sao tất cả solver phải dùng cùng cách chuẩn hóa.

Khi viết báo cáo, bổ sung nguồn tải chính xác và ngày lấy bộ file `.mtx.rnd` này; không suy đoán nguồn chỉ từ tên file.
