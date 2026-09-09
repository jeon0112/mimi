"""십성표.md 와 코드가 갈리지 않는지 지킨다.

십성표.md 는 이렇게 약속한다 —
    "표를 코드로 생성했으므로, 코드를 고치면 표도 함께 바뀐다."

그 문장은 **사실이 아니었다.** 표는 생성해서 붙인 정적 마크다운이고,
다시 생성하는 것을 부르는 것이 없었다. 코드를 고쳐도 표는 그대로다.

우리는 이 병을 여러 번 봤다 —
    E-26  data_fetcher 를 부르는 것이 조용했다
    E-40  보고서를 만들었으나 닿지 않는 곳에 썼다
    그래프 재적재  스크립트는 있는데 부르는 것이 없다

**부르는 것이 없으면 낡는다. 그리고 낡아도 표는 표처럼 보인다.**

이 시험이 그 약속을 코드로 바꾼다.
표와 코드가 한 칸이라도 갈리면 여기서 빨간불이 난다.

실행:  python3 test_십성표.py
"""

import io
import os
import re
import sys

import relation_engine as R

STEMS = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "십성표.md")


def parse_doc(path):
    """십성표.md 의 10×10 표를 읽는다. 형식이 깨지면 조용히 넘기지 않는다."""
    table = {}
    for lineno, line in enumerate(io.open(path, encoding="utf-8"), 1):
        m = re.match(r"\|\s*\*\*([가-힣])[甲乙丙丁戊己庚辛壬癸]\(", line)
        if not m:
            continue
        day = m.group(1)
        cells = [c.strip() for c in line.split("|")[2:-1]]
        if len(cells) != 10:
            raise SystemExit(
                f"❌ 십성표.md {lineno}행 — '{day}' 행의 칸이 {len(cells)}개다. 10개여야 한다.\n"
                f"   표 모양이 깨졌다. 고치기 전에 왜 깨졌는지 먼저 본다."
            )
        for other, v in zip(STEMS, cells):
            table[(day, other)] = v
    return table


print("=" * 70)
print("십성표 ↔ 코드 대조")
print("=" * 70)

doc = parse_doc(DOC)
code = {(d, o): R.ten_god(d, o) for d in STEMS for o in STEMS}

ok = True

# ── 칸 수 ────────────────────────────────────
if len(doc) != 100:
    print(f"❌ 십성표.md 에서 읽은 칸이 {len(doc)}개다. 100개여야 한다")
    print("   일간 행이 빠졌거나 표 형식이 바뀌었다")
    ok = False
else:
    print("✅ 십성표.md 에서 100칸을 읽었다")

# ── 한 칸씩 대조 ──────────────────────────────
diff = [(k, doc[k], code[k]) for k in sorted(code) if k in doc and doc[k] != code[k]]
missing = sorted(k for k in code if k not in doc)

if missing:
    ok = False
    print(f"❌ 문서에 없는 칸 {len(missing)}개")
    for d, o in missing[:5]:
        print(f"     {d}일간 × {o}  (코드: {code[(d, o)]})")

if diff:
    ok = False
    print(f"❌ 표와 코드가 {len(diff)}칸 어긋난다")
    for (d, o), dv, cv in diff[:10]:
        print(f"     {d}일간 × {o} :  문서={dv}   코드={cv}")
    print()
    print("   ★ 표를 손으로 고치지 마라.")
    print("     코드가 옳으면 표를 다시 생성해 붙이고,")
    print("     표가 옳으면 코드가 틀린 것이다. 어느 쪽인지 먼저 정한다.")
else:
    print("✅ 표와 코드가 100칸 전부 일치한다")

# ── 규칙이 살아 있는가 (표를 안 보고 규칙만으로 검산) ──
# 일간과 상대의 음양이 같으면 편(偏), 다르면 정(正).
# 비견/겁재·식신/상관 은 이 규칙의 이름만 다른 짝이다.
PAIRS = {
    "동일": ("비견", "겁재"),
    "내가생": ("식신", "상관"),
    "내가극": ("편재", "정재"),
    "나를극": ("편관", "정관"),
    "나를생": ("편인", "정인"),
}
bad = []
for d in STEMS:
    for o in STEMS:
        _, dy = R.STEMS[d]
        _, oy = R.STEMS[o]
        v = code[(d, o)]
        same_yy = dy == oy
        for _, (a, b) in PAIRS.items():
            if v == a and not same_yy:
                bad.append((d, o, v, "음양이 다른데 앞엣것"))
            if v == b and same_yy:
                bad.append((d, o, v, "음양이 같은데 뒤엣것"))
if bad:
    ok = False
    print(f"❌ 음양 규칙과 어긋나는 칸 {len(bad)}개")
    for d, o, v, why in bad[:5]:
        print(f"     {d} × {o} = {v}  ({why})")
else:
    print("✅ 100칸 전부 음양 규칙(같으면 편·다르면 정)과 맞는다")

# ── 2026-09-06 정정이 되돌아가지 않았는가 ──────────
# 己(음토) 일간이 본 甲(양목) = 정관,  甲 일간이 본 己 = 정재
CASES = [(("기", "갑"), "정관"), (("갑", "기"), "정재")]
back = [(k, code[k], want) for k, want in CASES if code[k] != want]
if back:
    ok = False
    print("❌ 2026-09-06 정정이 되돌아갔다")
    for (d, o), got, want in back:
        print(f"     {d}일간 × {o} :  지금={got}   정정값={want}")
    print("   원문의 '편관/편재' 는 편·정 규칙을 반대로 적용한 것이었다")
else:
    print("✅ 2026-09-06 정정이 유지되고 있다 (기×갑=정관 · 갑×기=정재)")

print("=" * 70)
print("통과" if ok else "실패 — 위 항목을 먼저 해결한다")
sys.exit(0 if ok else 1)
