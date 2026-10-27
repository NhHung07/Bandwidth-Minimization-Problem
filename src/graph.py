"""Đọc các file ``.mtx.rnd`` và tạo đồ thị vô hướng dùng chung cho mọi solver.

Mã đỉnh vẫn bắt đầu từ 1 như trong file dữ liệu. Số đỉnh không đổi, kể cả
đỉnh cô lập và các thành phần liên thông tách rời. Self-loop được bỏ vì không
ảnh hưởng đến bandwidth; cạnh trùng hoặc viết ngược chiều được gộp lại.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class GraphFormatError(ValueError):
    """Báo file ``.mtx.rnd`` có nội dung sai định dạng hoặc sai số liệu header."""


@dataclass(frozen=True, slots=True)
class Graph:
    """Một instance sau khi chuẩn hóa thành đồ thị vô hướng đơn.

    ``n`` là số đỉnh; ``edges`` chứa các cạnh dạng (đỉnh nhỏ, đỉnh lớn).
    ``raw_edge_count`` là số dòng cạnh ghi trong header. ``m`` là số cạnh
    thực sự đưa cho solver sau khi bỏ self-loop và gộp cạnh trùng:
    ``raw_edge_count == m + duplicate_edge_count + self_loop_count``.

    ``frozen=True`` giữ dữ liệu không bị sửa ngoài ý muốn giữa các solver;
    ``slots=True`` giúp đối tượng gọn hơn trong bộ nhớ.
    """

    name: str
    n: int
    edges: tuple[tuple[int, int], ...]
    source_path: Path
    raw_edge_count: int
    duplicate_edge_count: int
    self_loop_count: int

    @property
    def m(self) -> int:
        """Trả số cạnh sau chuẩn hóa; có thể khác số ghi trong file gốc."""
        return len(self.edges)


def list_instance_paths(data_dir: str | Path | None = None) -> tuple[Path, ...]:
    """Liệt kê các file ``.mtx.rnd`` theo thứ tự cố định.

    Nếu không truyền ``data_dir``, hàm dùng thư mục ``data/`` của dự án.
    """
    # Tìm thư mục dữ liệu dựa trên vị trí file code, không phụ thuộc terminal đang ở đâu.
    root = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data"
    if not root.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục dữ liệu: {root}")
    # sort để lần chạy sau luôn duyệt các instance theo cùng một thứ tự.
    return tuple(sorted(root.rglob("*.mtx.rnd")))


def load_graph(path: str | Path) -> Graph:
    """Đọc một file ``.mtx.rnd``, kiểm tra định dạng và chuẩn hóa các cạnh.

    Dòng 1 chứa tên file; dòng 2 là ``n n m``; tiếp theo phải có đúng ``m``
    dòng, mỗi dòng gồm hai mã đỉnh từ 1 đến n. Nếu sai, lỗi GraphFormatError
    ghi rõ đường dẫn và số dòng để dễ tìm chỗ cần sửa.
    """
    source = Path(path).resolve()

    def invalid(line_number: int, message: str) -> GraphFormatError:
        # Gom định dạng thông báo lỗi vào một chỗ: file:dòng:nội dung lỗi.
        return GraphFormatError(f"{source}:{line_number}: {message}")

    # utf-8-sig đọc được cả file UTF-8 thường và file có BOM ở đầu.
    with source.open("r", encoding="utf-8-sig") as stream:
        # Tên khai báo trong dòng đầu phải đúng tên file đang mở.
        first_line = stream.readline().strip()
        prefix = "Nombre del problema:"
        if not first_line.startswith(prefix):
            raise invalid(1, f"cần dòng đầu dạng '{prefix} <tên file>'")
        declared_filename = first_line[len(prefix) :].strip()
        if declared_filename != source.name:
            raise invalid(1, f"tên khai báo {declared_filename!r} khác tên file {source.name!r}")

        # Header n n m cho biết số đỉnh và số dòng cạnh phải đọc tiếp.
        header = stream.readline().split()
        if len(header) != 3:
            raise invalid(2, "dòng thứ hai phải gồm ba số nguyên: n n m")
        try:
            rows, columns, raw_edge_count = (int(value) for value in header)
        except ValueError as exc:
            raise invalid(2, "n, n và m phải là số nguyên") from exc
        if rows < 1 or columns != rows or raw_edge_count < 0:
            raise invalid(2, "n phải dương, ma trận phải vuông và m không âm")

        # Set giúp nhận ra cạnh trùng; ba bộ đếm giúp đối chiếu với header.
        edges: set[tuple[int, int]] = set()
        seen_lines = duplicate_edge_count = self_loop_count = 0
        for line_number, line in enumerate(stream, start=3):
            seen_lines += 1
            if seen_lines > raw_edge_count:
                raise invalid(line_number, f"có nhiều hơn {raw_edge_count} dòng cạnh")
            parts = line.split()
            if len(parts) != 2:
                raise invalid(line_number, "mỗi dòng cạnh phải gồm hai mã đỉnh")
            try:
                u, v = (int(value) for value in parts)
            except ValueError as exc:
                raise invalid(line_number, "mã đỉnh phải là số nguyên") from exc
            if not (1 <= u <= rows and 1 <= v <= rows):
                raise invalid(line_number, f"mã đỉnh phải nằm trong 1..{rows}")
            if u == v:
                # Cạnh từ một đỉnh tới chính nó có khoảng cách vị trí bằng 0.
                self_loop_count += 1
                continue
            # Chuẩn hóa để (u, v) và (v, u) được xem là cùng một cạnh.
            edge = (min(u, v), max(u, v))
            if edge in edges:
                duplicate_edge_count += 1
            else:
                edges.add(edge)

        if seen_lines != raw_edge_count:
            raise invalid(seen_lines + 3, f"cần {raw_edge_count} dòng cạnh, thực tế có {seen_lines}")

    # Sắp xếp cạnh để mọi solver nhận cùng dữ liệu theo cùng thứ tự.
    return Graph(
        name=source.name.removesuffix(".mtx.rnd"),
        n=rows,
        edges=tuple(sorted(edges)),
        source_path=source,
        raw_edge_count=raw_edge_count,
        duplicate_edge_count=duplicate_edge_count,
        self_loop_count=self_loop_count,
    )
