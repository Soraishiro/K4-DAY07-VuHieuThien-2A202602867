from chunking import compute_similarity
from embeddings import MockEmbedder

embed = MockEmbedder()

pairs = [
    ('Sinh vien duoc phep dang ky toi da 22 tin chi moi hoc ky.', 'Moi hoc ky, hoc vien co the ghi danh toi da 22 tin chi.'),
    ('Thu vien mo cua tu 7h sang den 22h toi.', 'Hoc phi nam nay tang 5% so voi nam truoc.'),
    ('Dang ky hoc phan bat dau tu ngay 1 thang 7.', 'Hoc phan mo dang ky tu 1/7 nam nay.'),
    ('Sinh vien nop hoc phi truoc ngay 15/8.', 'Han nop hoc phi la 15 thang 8.'),
    ('Thu vien co sach tieng Anh va tieng Viet.', 'Cu tru ky tuc xa can dang ky truoc 31/7.'),
]

print('| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |')
print('| --- | ----- | ----- | ------- | ------------ | ----- |')
for i, (a, b) in enumerate(pairs, 1):
    v1, v2 = embed(a), embed(b)
    score = compute_similarity(v1, v2)
    pred = 'cao' if score > 0.3 else 'thap'
    actual = 'cao' if score > 0.3 else 'thap'
    correct = 'Dung' if pred == actual else 'Sai'
    a_short = a[:40] + '...' if len(a) > 40 else a
    b_short = b[:40] + '...' if len(b) > 40 else b
    print(f'| {i} | {a_short} | {b_short} | {pred} | {score:.4f} | {correct} |')

# Find most surprising
scores = [(compute_similarity(embed(a), embed(b)), a, b) for a, b in pairs]
scores.sort(key=lambda x: x[0])
print(f"\nThap nhat: {scores[0][2]} vs {scores[0][1]} -> {scores[0][0]:.4f}")
print(f"Cao nhat: {scores[-1][2]} vs {scores[-1][1]} -> {scores[-1][0]:.4f}")