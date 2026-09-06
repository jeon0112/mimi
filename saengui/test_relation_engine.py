"""relation_engine.py 검증.

십성 표를 손으로 검산하고, 5단계가 문서대로 도는지 확인하고,
태그 가드가 실제로 막는지 시험한다.

실행:  python3 test_relation_engine.py
"""

import sys

import relation_engine as R


def check(name, cond, detail=""):
    mark = "✅" if cond else "❌"
    print(f"{mark} {name}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


results = []
print("=" * 70)
print("관계 엔진 검증")
print("=" * 70)

# ── 천간 정규화 ──────────────────────────────
results.append(check("한자·한글 모두 받는다",
                     R.normalize_stem("甲") == "갑" and R.normalize_stem("갑") == "갑"))
for bad in ("", "X", "자"):
    try:
        R.normalize_stem(bad)
        results.append(check(f"천간 아닌 입력 거부 ({bad!r})", False, "통과돼 버렸다"))
        break
    except R.RelationInputError:
        pass
else:
    results.append(check("천간 아닌 입력은 거부한다", True, "추측해서 진행하지 않는다"))

# ── 십성 — 손으로 검산한 값 ───────────────────
# 규칙: 음양이 같으면 편(偏), 다르면 정(正)
cases = [
    # (일간, 상대, 기대, 근거)
    ("갑", "갑", "비견", "같은 오행·같은 음양"),
    ("갑", "을", "겁재", "같은 오행·다른 음양"),
    ("갑", "병", "식신", "목생화, 양·양"),
    ("갑", "정", "상관", "목생화, 양·음"),
    ("갑", "무", "편재", "목극토, 양·양"),
    ("갑", "기", "정재", "목극토, 양·음"),
    ("갑", "경", "편관", "금극목, 양·양"),
    ("갑", "신", "정관", "금극목, 양·음"),
    ("갑", "임", "편인", "수생목, 양·양"),
    ("갑", "계", "정인", "수생목, 양·음"),
    ("기", "갑", "정관", "목극토, 음·양"),
    ("기", "을", "편관", "목극토, 음·음"),
]
ten_ok = True
for day, other, want, why in cases:
    got = R.ten_god(day, other)
    if got != want:
        ten_ok = False
        print(f"   ❌ {day}일간이 본 {other}: {got} (기대 {want} — {why})")
results.append(check(f"십성 {len(cases)}종 검산", ten_ok, "음양 같으면 편, 다르면 정"))

# ── 문서의 사례 ──────────────────────────────
# advanced analysis methods: 시저님(己 음토) × 1969년 여성(甲 양목)
시저 = R.Person("시저", "己")
여성 = R.Person("1969여성", "甲")
rel = R.analyze(시저, 여성)

results.append(check("문서 사례: 甲己合 성립", "천간합" in rel.tags))
results.append(check("문서 사례: 극중생합 (목극토가 합으로 전환)",
                     "극중생합" in rel.tags))
results.append(check("문서 사례: 음(己) × 양(甲) → 보완적", "보완적" in rel.tags))
results.append(check("문서 사례: 양이 밀고 음이 받는다",
                     "1969여성(양)이 밀고 시저(음)이 받는다" in rel.steps[2].result,
                     rel.steps[2].result))
results.append(check("문서 사례: 십성이 비대칭", "비대칭" in rel.tags, rel.asymmetry))

# ── 대운 ─────────────────────────────────────
results.append(check("대운 없으면 판정하지 않는다",
                     rel.timing is None and "대운 교차" in rel.missing
                     and "결실기미상" in rel.tags,
                     "모르는 것을 0으로 채우지 않는다"))
results.append(check("대운 없는 단계는 known=False 로 표시된다",
                     rel.steps[4].known is False))

a = R.Person("A", "己", daeun={2024: "토", 2025: "화", 2026: "화"})
b = R.Person("B", "甲", daeun={2024: "금", 2025: "토", 2026: "화"})
rel2 = R.analyze(a, b)
results.append(check("대운 교차 연도를 찾는다", rel2.timing == [2026], str(rel2.timing)))
results.append(check("교차가 있으면 결실기있음", "결실기있음" in rel2.tags))
results.append(check("교차 있으면 missing 이 비어야 한다", rel2.missing == []))

c = R.Person("C", "갑", daeun={2024: "목"})
d = R.Person("D", "병", daeun={2024: "수"})
rel3 = R.analyze(c, d)
results.append(check("겹치는 시기 없으면 timing=None, 미상 태그는 안 붙는다",
                     rel3.timing is None and "결실기미상" not in rel3.tags,
                     "'모른다'와 '없다'는 다른 상태다"))

# ── 같은 음양 ────────────────────────────────
e = R.Person("E", "갑")   # 양목
f = R.Person("F", "병")   # 양화
rel4 = R.analyze(e, f)
results.append(check("둘 다 양이면 경쟁적", "경쟁적" in rel4.tags))
results.append(check("목생화면 상생 태그", "상생" in rel4.tags, str(rel4.tags)))

g = R.Person("G", "갑")   # 양목
h = R.Person("H", "무")   # 양토
rel5 = R.analyze(g, h)
results.append(check("목극토면 상극 태그", "상극" in rel5.tags, str(rel5.tags)))
results.append(check("합 없는 상극은 극중생합이 아니다",
                     "극중생합" not in rel5.tags))

i2 = R.Person("I", "갑")
j2 = R.Person("J", "갑")
rel6 = R.analyze(i2, j2)
results.append(check("같은 일간이면 대칭", "대칭" in rel6.tags and "비대칭" not in rel6.tags))
results.append(check("같은 오행이면 동기 태그", "동기" in rel6.tags))

# ── 5단계가 모두 나오는가 ─────────────────────
results.append(check("항상 5단계를 낸다", len(rel.steps) == 5,
                     f"{len(rel.steps)}단계"))
results.append(check("단계 번호가 1..5", [s.no for s in rel.steps] == [1, 2, 3, 4, 5]))

# ── 가드: 이 파일의 핵심 ─────────────────────
try:
    R._assert_tags(["보완적", "리더형"])
    results.append(check("가드: 성격 단정 태그를 막는다", False, "통과돼 버렸다"))
except R.RelationInputError:
    results.append(check("가드: 성격 단정 태그를 막는다", True,
                         "오행을 성격으로 직접 매핑하지 않는다"))

try:
    R._assert_tags(["보완적", "성장형"])
    results.append(check("가드: '성장형' 같은 말도 막는다", False))
except R.RelationInputError:
    results.append(check("가드: '성장형' 같은 말도 막는다", True,
                         '"목이 많으면 성장형이다" 금지'))

results.append(check("모든 산출 태그가 허용 목록 안에 있다",
                     all(t in R.TAGS for rl in (rel, rel2, rel3, rel4, rel5, rel6)
                         for t in rl.tags)))

# ── 5합 표 검산 ──────────────────────────────
combos = [("갑", "기", "토"), ("을", "경", "금"), ("병", "신", "수"),
          ("정", "임", "목"), ("무", "계", "화")]
combo_ok = all(R.FIVE_COMBOS.get(frozenset((x, y))) == z for x, y, z in combos)
results.append(check("천간 5합 5종", combo_ok))
results.append(check("5합은 5개뿐", len(R.FIVE_COMBOS) == 5))

# ── 오행 생극 표 ─────────────────────────────
results.append(check("상생 고리가 닫혀 있다",
                     len(set(R.GENERATES.values())) == 5 and
                     all(R.GENERATES[R.GENERATES[R.GENERATES[R.GENERATES[R.GENERATES[e2]]]]] == e2
                         for e2 in R.GENERATES)))
results.append(check("상극 고리가 닫혀 있다",
                     len(set(R.CONTROLS.values())) == 5))

print("=" * 70)
print(f"{sum(results)}/{len(results)} 통과")
print("=" * 70)
print()
print(rel.summary())
print()
print(rel2.summary())

sys.exit(0 if all(results) else 1)
