# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Phạm Thị Tuyết Nga - 2A202600877
**Nhóm:** C2-C401
**Ngày:** 2026-06-05

> **Domain nhóm:** Tin tức Công nghệ & Khoa học tiếng Việt (kiểu VnExpress – Số Hóa / Khoa Học).
> Corpus gồm 8 bài báo trong thư mục `data/` (file `01_…` đến `13_…`), đã ở định dạng `.md` nên **không cần chuyển đổi** từ PDF.

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> Hai đoạn văn bản có vector embedding gần như chỉ về **cùng một hướng** trong không gian nhiều chiều, tức chúng nói về **cùng chủ đề / cùng ý nghĩa**, bất kể câu chữ cụ thể có khác nhau.

**Ví dụ HIGH similarity:**
- Sentence A: "iPhone 18 Pro bản Mỹ có pin 4.288 mAh."
- Sentence B: "Bản iPhone tại Mỹ dùng dung lượng pin lớn hơn nhờ bỏ khay SIM."
- Tại sao tương đồng: cùng nói về **dung lượng pin của iPhone bản Mỹ**, chia sẻ chủ đề và thực thể.

**Ví dụ LOW similarity:**
- Sentence A: "Tên lửa New Glenn của Blue Origin phát nổ trên bệ phóng."
- Sentence B: "Cá chép xâm hại bị loại bỏ khỏi sông Illinois."
- Tại sao khác: hai lĩnh vực hoàn toàn rời nhau (hàng không vũ trụ vs. sinh thái), không chung thực thể hay chủ đề.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Cosine chỉ quan tâm **hướng** của vector chứ không quan tâm **độ dài**. Văn bản dài có magnitude lớn hơn văn bản ngắn, nên Euclidean sẽ phạt oan các đoạn dài dù cùng nghĩa; cosine chuẩn hóa độ dài nên so sánh ngữ nghĩa công bằng hơn.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> `num_chunks = ceil((10000 − 50) / (500 − 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
> **Đáp án: 23 chunks.**

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> `ceil((10000 − 100) / (500 − 100)) = ceil(9900 / 400) = ceil(24.75) = 25 chunks` → **tăng lên 25**. Overlap lớn hơn giúp giữ **ngữ cảnh ở ranh giới chunk** (một câu/ý bị cắt giữa hai chunk vẫn xuất hiện trọn vẹn ở ít nhất một chunk), giảm rủi ro retrieval trả về mảnh thiếu thông tin — đổi lại tốn nhiều chunk và lưu trữ hơn.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Tin tức Công nghệ & Khoa học tiếng Việt.

**Tại sao nhóm chọn domain này?**
> (1) Tài liệu **tiếng Việt thật**, kiểm chứng được khả năng chunking/embedding với dấu tiếng Việt. (2) Mỗi bài là một chủ đề tách bạch (AI, phần cứng, vũ trụ, sinh học, môi trường) nên **dễ gán metadata** và dễ tạo benchmark query có gold answer rõ ràng. (3) Văn bản có cấu trúc **đoạn văn ngăn cách bằng dòng trống**, lý tưởng để so sánh các chiến lược chunking.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | 01 — Microsoft lộ 'kế hoạch khiến người dùng nghiện Scout' | 404Media / NYPost (tổng hợp) | 4.620 | category=`ai`, entity=`Microsoft`, date=`2026-06-02`, lang=`vi` |
| 2 | 04 — Mỹ loại bỏ 23 triệu kg cá chép xâm hại | Popular Science / MSN | 2.732 | category=`environment`, entity=`USFWS/NOAA`, date=`2026-06`, lang=`vi` |
| 3 | 05 — Lần đầu chỉnh sửa chính xác gene phôi người | bioRxiv / NYTimes | 6.269 | category=`bio-health`, entity=`ĐH Columbia`, date=`2026-06`, lang=`vi` |
| 4 | 06 — AI giúp Apple App Store đạt quy mô kỷ lục 1,4 nghìn tỷ USD | Apple / Analysis Group | 2.658 | category=`ai`, entity=`Apple`, date=`2026-06-04`, lang=`vi` |
| 5 | 07 — iPhone 18 Pro lộ dung lượng pin | Digital Chat Station (Weibo) | 1.819 | category=`hardware`, entity=`Apple`, date=`2026-06`, lang=`vi` |
| 6 | 09 — Blue Origin muốn phóng lại tên lửa trước cuối năm nay | Space / Reuters | 2.736 | category=`space`, entity=`Blue Origin`, date=`2026-06-02`, lang=`vi` |
| 7 | 11 — Mô hình ngôn ngữ lớn tiếng Việt với 120 tỷ tham số | Viettel AI | 3.676 | category=`ai`, entity=`Viettel`, date=`2026-06-04`, lang=`vi` |
| 8 | 13 — Tàu quỹ đạo Sao Hỏa của NASA dừng hoạt động sau 11 năm | Space / AP | 2.552 | category=`space`, entity=`NASA`, date=`2026-06-03`, lang=`vi` |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `category` | enum (str) | `ai`, `hardware`, `space`, `bio-health`, `environment` | Lọc theo lĩnh vực — gom đúng nhóm bài vũ trụ (`space`) hay bài AI khi query trùng từ khóa. Dùng trực tiếp trong `filter={"category": "space"}` của benchmark #3. |
| `entity` | str | `Apple`, `Microsoft`, `Viettel`, `NASA` | Lọc theo công ty/tổ chức — ví dụ "tin về Apple" chỉ giữ doc 06 và 07. |
| `date` | str (ISO) | `2026-06-02` | Lọc/sắp theo thời gian, ưu tiên tin mới nhất. |
| `lang` | str | `vi` | Định danh ngôn ngữ; hữu ích khi corpus đa ngôn ngữ. |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare(text, chunk_size=500)` trên 3 tài liệu (số liệu thực đo từ `src`):

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| 01 (4.620 ký tự) | FixedSizeChunker (`fixed_size`) | 11 | 465 | Trung bình — cắt giữa câu/đoạn |
| 01 | SentenceChunker (`by_sentences`) | 13 | 353 | Tốt — theo ranh giới câu |
| 01 | RecursiveChunker (`recursive`) | 19 | 241 | Tốt nhất — theo đoạn rồi câu |
| 05 (6.269 ký tự) | FixedSizeChunker | 14 | 494 | Trung bình |
| 05 | SentenceChunker | 16 | 390 | Tốt |
| 05 | RecursiveChunker | 27 | 230 | Tốt nhất |
| 07 (1.819 ký tự) | FixedSizeChunker | 4 | 492 | Trung bình |
| 07 | SentenceChunker | 5 | 362 | Tốt |
| 07 | RecursiveChunker | 7 | 258 | Tốt nhất |

> Nhận xét: `recursive` tạo nhiều chunk nhất nhưng mỗi chunk **bám sát ranh giới đoạn/câu** (avg ~230–260 ký tự), trong khi `fixed_size` đụng trần 500 ký tự và hay cắt ngang câu.

### Strategy Của Tôi

**Loại:** SentenceChunker (`max_sentences_per_chunk=3`).

**Mô tả cách hoạt động:**
> Strategy tách văn bản thành câu bằng regex lookbehind `(?<=[.!?])\s+` (cắt ngay sau dấu `. ! ?` rồi tới khoảng trắng), strip khoảng trắng thừa và loại câu rỗng, sau đó **gom mỗi 3 câu liền kề thành một chunk**. Mỗi chunk vì thế luôn bắt đầu và kết thúc ở **ranh giới câu tự nhiên**, không bao giờ cắt giữa câu.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Bài báo tiếng Việt giàu **câu trọn ý** (mỗi câu thường gói một số liệu hoặc một sự kiện). Gom 3 câu giữ cho chunk vừa **đủ ngữ cảnh** để trả lời query tổng hợp, vừa **dễ đọc/dễ kiểm chứng** khi debug retrieval — không có mảnh cụt như fixed-size. Đây cũng là strategy bám sát câu chữ gốc nhất, hợp với các query "tổng hợp tác động" ở Section 6.

**Code snippet (built-in, dùng nguyên):**
```python
from src.chunking import SentenceChunker
chunker = SentenceChunker(max_sentences_per_chunk=3)  # gom mỗi 3 câu thành 1 chunk
chunks = chunker.chunk(text)
```

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| 05 | baseline (`recursive`) | 27 | 230 | Chunk nhỏ, precision cao nhưng đôi khi thiếu ngữ cảnh liền mạch |
| 05 | **của tôi (`by_sentences`, max=3)** | 16 | 390 | Mỗi chunk = 3 câu trọn vẹn, dễ đọc; tốt cho query tổng hợp |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi — Phạm Thị Tuyết Nga | SentenceChunker (max=3) | 7 | Theo câu tự nhiên, dễ đọc/kiểm chứng, không cắt giữa câu | Độ dài chunk dao động; 3 câu dài có thể gộp 2 ý |
| Trần Hoàng Đạt — 2A202600807 | RecursiveChunker (size=300) | 9 | Giữ ngữ cảnh cấu trúc báo chí cực tốt, kích thước chunk ổn định | Đòi hỏi xử lý đệ quy tốn kém tài nguyên hơn |
| Nguyễn Văn Đoan — 2A202600795 | FixedSizeChunker (cs=200, ov=20) | 6 (1/5 query đúng) | Cực kỳ đơn giản, phân mảnh đều đặn, tốc độ xử lý nhanh | Cắt cứng ký tự nên dễ ngắt câu giữa chừng; overlap 20 ký tự chưa đủ bảo toàn ngữ cảnh → precision thấp |
| Tạ Duy Xuân — 2A202600970 | Custom (SciencePaper) | 2 | Giữ cấu trúc logic của tài liệu | Chunk quá dài → loãng ngữ cảnh, retrieval kém |
| Lê Duy Hùng — 2A202600718 | FixedSizeChunker (cs=600, ov=100) | 6 | Chunk tập trung vào chi tiết, ít nhiễu | Dễ mất ngữ cảnh khi câu trả lời cần nhiều thông tin liên tiếp |

**Strategy nào tốt nhất cho domain này? Tại sao?**
> **RecursiveChunker (size=300) của Trần Hoàng Đạt đạt cao nhất (9/10)**: ranh giới đoạn khớp với cấu trúc báo chí, kích thước chunk ổn định nên precision cao nhất trên query số liệu. SentenceChunker (max=3) của tôi (7/10) trọn-câu, mạnh ở query **tổng hợp đa-tài-liệu** (Section 6). Các biến thể FixedSizeChunker — Nguyễn Văn Đoan (cs=200/ov=20) và Lê Duy Hùng (cs=600/ov=100) — đều chỉ 6/10 vì cắt cứng theo ký tự làm ngắt câu giữa chừng; còn Custom SciencePaper của Tạ Duy Xuân (2/10) tạo chunk quá dài làm loãng tín hiệu. Minh họa rõ "strategy khác nhau thắng ở loại query khác nhau", và **cắt theo ranh giới ngữ nghĩa (câu/đoạn) luôn thắng cắt cứng theo ký tự lẫn chunk quá lớn**.

---

## 4. My Approach — Cá nhân (10 điểm)

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Dùng regex `re.split(r"(?<=[.!?])\s+", text)` (lookbehind) để cắt **ngay sau** dấu `. ! ?` rồi tới khoảng trắng, giữ nguyên dấu câu cuối. Strip khoảng trắng và loại câu rỗng, sau đó gom mỗi `max_sentences_per_chunk` câu thành một chunk.

**`RecursiveChunker.chunk` / `_split`** — approach:
> `_split` đệ quy: **base case 1** — đoạn ≤ `chunk_size` thì giữ nguyên; **base case 2** — hết separator (hoặc `sep == ""`) thì cắt cứng theo `chunk_size`. Ngược lại, `split` theo separator ưu tiên cao nhất; mảnh nào còn dài thì đệ quy với danh sách separator còn lại.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> Mỗi `Document` được chunk, mỗi chunk được embed và lưu kèm metadata + `doc_id`. `search` embed query rồi xếp hạng theo **dot product / cosine** giữa query và từng chunk, trả về top-k.

**`search_with_filter` + `delete_document`** — approach:
> `search_with_filter` **lọc metadata trước** (chỉ giữ chunk khớp filter) rồi mới tính similarity → tránh nhiễu xuyên lĩnh vực. `delete_document` xóa **mọi chunk** mang `doc_id` tương ứng.

### KnowledgeBaseAgent

**`answer`** — approach:
> Retrieve top-k chunk liên quan → ghép thành khối context → dựng prompt "trả lời **chỉ dựa trên** context sau" → gọi LLM. Nhờ vậy câu trả lời được grounding vào tài liệu, hạn chế bịa.

### Test Results

```
$ python -m pytest tests/ -q
..........................................                               [100%]
42 passed in 0.03s
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

> Backend embedding hiện tại: **mock embedder** (`_mock_embed`) — chưa cài `sentence-transformers`/OpenAI. Điểm dưới đây là **số thực đo được**.

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | iPhone 18 Pro bản Mỹ pin 4.288 mAh | Bản iPhone tại Mỹ pin lớn hơn nhờ bỏ khay SIM | high | −0.034 | ✗ |
| 2 | Viettel ra LLM tiếng Việt 120 tỷ tham số | Mô hình AI VT-Super tối ưu cho tiếng Việt | high | 0.115 | ✗ (thấp hơn kỳ vọng) |
| 3 | New Glenn của Blue Origin phát nổ | Cá chép xâm hại bị loại bỏ khỏi sông Illinois | low | −0.058 | ✓ |
| 4 | App Store đạt 1,4 nghìn tỷ USD năm 2025 | Tàu Maven của NASA ngừng hoạt động | low | 0.050 | ✓ |
| 5 | base editing chỉnh sửa chính xác gene phôi | CRISPR là công nghệ chỉnh sửa gene thế hệ trước | high | −0.226 | ✗ |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Bất ngờ nhất là **pair 5** (hai câu rõ ràng cùng chủ đề chỉnh sửa gene) lại cho điểm **âm**. Lý do: mock embedder chỉ là phép băm/chiếu ngẫu nhiên, **không nắm ngữ nghĩa** — nên cặp cùng nghĩa cũng có thể thấp. Bài học: chất lượng retrieval phụ thuộc trực tiếp vào **embedder thật**; với `all-MiniLM-L6-v2`/OpenAI ta kỳ vọng pair 1, 2, 5 cao và 3, 4 thấp đúng như dự đoán.

---

## 6. Results — Cá nhân (10 điểm)

> **Phạm vi:** 5 query benchmark dạng **tổng hợp đa-tài-liệu** chạy trên **toàn bộ corpus 20 bài** trong `data/` (không chỉ 8 bài inventory ở Section 2). Mỗi gold answer liệt kê các bài (theo số thứ tự file) chứa thông tin cần để trả lời.

### Benchmark Queries & Gold Answers (nhóm thống nhất)

```python
BENCHMARK_QUERIES = [
    {
        "query": "Trong bộ tài liệu, Microsoft đang phát triển hoặc công bố những sản phẩm AI nào và mục tiêu của chúng là gì?",
        "gold": "Microsoft Scout - trợ lý giữ chân người dùng (bài 01); chip lượng tử mới 'với sự trợ giúp của AI' (bài 16); tác nhân tự chủ tương tự OpenClaw (bài 19).",
        "filter": None,
    },
    {
        "query": "Những tổ chức hoặc doanh nghiệp nào đang đầu tư mạnh vào AI, và họ tập trung vào những lĩnh vực hoặc ứng dụng nào?",
        "gold": "Apple (App Store tích hợp AI - bài 06); Google X (AI thay lối làm cũ - bài 02); Microsoft (Scout, chip lượng tử, tác nhân tự chủ - bài 01/16/19); công ty châu Âu dùng AI mở rộng sang Mỹ (bài 20); Việt Nam phát triển LLM 120 tỷ tham số (bài 11).",
        "filter": None,
    },
    {
        "query": "Những dự án liên quan đến không gian vũ trụ trong tập tài liệu đang đối mặt với những cơ hội hoặc thách thức gì?",
        "gold": "Blue Origin muốn phóng lại tên lửa trước cuối năm (bài 09); tàu quỹ đạo Sao Hỏa của NASA dừng hoạt động sau 11 năm (bài 13); tham vọng trung tâm dữ liệu vũ trụ của Musk khó thành (bài 15); rủi ro nước sạch khi SpaceX IPO (bài 18).",
        "filter": {"category": "space"},  # <- query cần metadata filtering
    },
    {
        "query": "Những đột phá khoa học hoặc công nghệ mới nào được đề cập trong bộ tài liệu, và chúng có thể tạo ra những tác động gì trong tương lai?",
        "gold": "Lần đầu chỉnh sửa chính xác gene phôi người (bài 05); chip lượng tử mới của Microsoft (bài 16); LLM tiếng Việt 120 tỷ tham số (bài 11); lắp đặt lò phản ứng hạt nhân bằng cần cẩu lớn nhất thế giới (bài 14).",
        "filter": None,
    },
    {
        "query": "Những bài viết nào cho thấy AI đang tác động đến cách con người học tập, làm việc hoặc vận hành tổ chức? Hãy tổng hợp các tác động chính.",
        "gold": "Sinh viên hào hứng với AI nhưng bất định về tương lai (bài 17); Google X - không thể theo lối cũ khi AI làm tốt hơn (bài 02); ứng dụng mô hình 4 lớp trong chuyển đổi số cấp xã/phường (bài 10); AI giúp công ty châu Âu mở rộng sang Mỹ (bài 20).",
        "filter": None,
    },
]
```

> Query #3 cần `filter={"category": "space"}` để giới hạn ranking về các bài vũ trụ (09, 13, 15, 18) trước khi tính similarity — tránh kéo nhầm các bài AI/phần cứng có nhắc "vệ tinh/dữ liệu". Đây là loại query **recall đa-tài-liệu**: gold answer đúng khi top-k bao phủ được **nhiều** bài liên quan, không chỉ top-1.

### Kết Quả Của Tôi (SentenceChunker max=3, backend mock)

| # | Query (tóm tắt) | Filter | Bài liên quan kỳ vọng | Bài bắt được trong top-k? | Ghi chú |
|---|-----------------|--------|----------------------|---------------------------|---------|
| 1 | Sản phẩm AI của Microsoft | — | 01, 16, 19 | (kỳ vọng đủ 3 với embedder thật) | Agent tổng hợp Scout + chip lượng tử + tác nhân tự chủ |
| 2 | Tổ chức đầu tư mạnh vào AI | — | 06, 02, 01/16/19, 20, 11 | recall rộng — dễ sót bài với mock | Query bao phủ nhiều bài nhất |
| 3 | Dự án không gian vũ trụ | `category=space` | 09, 13, 15, 18 | filter giúp gom đúng nhóm | Filter tăng precision rõ rệt |
| 4 | Đột phá khoa học/công nghệ | — | 05, 16, 11, 14 | (kỳ vọng đủ với embedder thật) | Trộn sinh học + chip + LLM + hạt nhân |
| 5 | AI tác động học tập/làm việc | — | 17, 02, 10, 20 | recall đa-tài-liệu | Câu tổng hợp tác động |

**Bao nhiêu queries gom đủ bài liên quan trong top-k?** Vì đây là query **tổng hợp đa-tài-liệu**, tiêu chí là top-k có bao phủ phần lớn các bài gold hay không. Với **embedder thật**: kỳ vọng **4–5/5** (query #2 khó nhất vì cần recall 5+ bài). Với **mock embedder hiện tại**: thực tế chỉ ~1/5 vì điểm gần ngẫu nhiên (xem Section 5) — đây chính là failure case ở Section 7.

---

## 7. What I Learned (5 điểm — Demo) + Failure Analysis

### Failure Analysis (Ex 3.5)

- **Query thất bại:** Tất cả 5 query khi chạy với **mock embedder** — top-1 thường là chunk không liên quan.
- **Tại sao:** Không phải lỗi chunking hay metadata, mà do **embedder không nắm ngữ nghĩa**. Mock embed cho cosine gần ngẫu nhiên (Section 5: cặp cùng chủ đề vẫn ra điểm âm), nên ranking vô nghĩa → **grounding quality** sụp đổ dù chunk coherence tốt.
- **Đề xuất cải thiện:** (1) Cài `sentence-transformers` dùng `all-MiniLM-L6-v2` hoặc OpenAI `text-embedding-3-small`; (2) giữ SentenceChunker (max=3) cho chunk trọn câu, dễ đọc — hoặc tăng `max` nếu cần thêm ngữ cảnh cho query tổng hợp; (3) bật `search_with_filter` cho query #3 (`category=space`) để tăng precision; (4) re-chạy benchmark và kỳ vọng đạt 5/5 top-3.

### What I Learned

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> RecursiveChunker của bạn C cho precision cao hơn trên query số liệu, còn SentenceChunker (max=3) của tôi lại trọn ý hơn cho query tổng hợp — cùng một corpus, **strategy khác nhau thắng ở loại query khác nhau**.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> Metadata filter là "đòn bẩy" rẻ và mạnh: khi corpus có nhiều bài cùng lĩnh vực, lọc `category`/`entity` trước khi search cải thiện precision rõ rệt mà không cần đổi embedder.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> (1) Cấu hình embedder thật **ngay từ đầu** thay vì để mock — đây là yếu tố quyết định nhất. (2) Thêm metadata `section`/`heading` (vd. "Chặng đường dài" trong doc 05) để filter mịn hơn trong một bài dài.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 9 / 10 |
| Chunking strategy | Nhóm | 13 / 15 |
| My approach | Cá nhân | 9 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 8 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 4 / 5 |
| **Tổng** | | **83 / 100** |
