"""weights.py 검증.

핵심은 마지막 두 개다 — MBTI나 주역을 증거 축에 넣으면 앱이 안 떠야 한다.
그 가드가 없으면 몇 달 뒤 누군가 "MBTI도 비중 좀 주자"며 조용히 되돌린다.

실행:  python3 test_weights.py
"""

import sys

import weights as W


def check(name, cond, detail=""):
    mark = "✅" if cond else "❌"
    print(f"{mark} {name}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


results = []
print("=" * 66)
print("생의 무늬 가중치 검증")
print("=" * 66)

# ── 표 자체 ──────────────────────────────────
total = sum(W.EVIDENCE_WEIGHTS.values())
results.append(check("증거 축 합이 100", total == 100, f"합 {total}"))

results.append(check(
    "새 표대로 값이 들어갔다",
    W.EVIDENCE_WEIGHTS == {"행동": 40, "관계": 25, "맥락": 25, "타고난지표": 10},
    str(W.EVIDENCE_WEIGHTS)))

results.append(check(
    "관계 축이 신설돼 있다", "관계" in W.EVIDENCE_WEIGHTS,
    "인생을 흔드는 건 혼자짜리 속성이 아니라 주고받음이다"))

results.append(check(
    "타고난지표 = 사주5 + 손금5",
    sum(W.INNATE_SPLIT.values()) == W.EVIDENCE_WEIGHTS["타고난지표"],
    str(W.INNATE_SPLIT)))

# ── 형식 층 ──────────────────────────────────
results.append(check(
    "MBTI가 증거 축에 없다", "MBTI" not in W.EVIDENCE_WEIGHTS))
results.append(check(
    "MBTI가 형식 층에 있다", "MBTI" in W.FORM_LAYERS))
results.append(check(
    "주역이 증거 축에 없다",
    not any("주역" in k for k in W.EVIDENCE_WEIGHTS)))
results.append(check(
    "주역이 형식 층에 있다", "주역64괘" in W.FORM_LAYERS))

# ── 빈 축 처리 ───────────────────────────────
w, missing = W.resolve({"행동", "맥락", "타고난지표"})
results.append(check(
    "관계 데이터가 없으면 나머지로 재정규화",
    abs(sum(w.values()) - 100) < 0.05, f"{w} 합 {round(sum(w.values()),1)}"))
results.append(check(
    "빠진 축을 조용히 숨기지 않는다", missing == ["관계"], f"missing={missing}"))

w2, m2 = W.resolve({"행동"})
results.append(check(
    "축 하나만 있어도 100으로 정규화",
    abs(sum(w2.values()) - 100) < 0.05, str(w2)))

try:
    W.resolve(set())
    results.append(check("증거가 하나도 없으면 거부", False, "예외가 안 났다"))
except W.WeightConfigError:
    results.append(check("증거가 하나도 없으면 거부", True, "해석하지 않고 멈춘다"))

# ── 가드: 이게 이 파일의 핵심 ─────────────────
def guard_rejects(bad_key):
    """증거 축에 형식 층 이름을 넣으면 _validate 가 막아야 한다."""
    saved = dict(W.EVIDENCE_WEIGHTS)
    try:
        W.EVIDENCE_WEIGHTS.clear()
        W.EVIDENCE_WEIGHTS.update({"행동": 40, "관계": 25, "맥락": 20,
                                   "타고난지표": 10, bad_key: 5})
        W._validate()
        return False
    except W.WeightConfigError:
        return True
    finally:
        W.EVIDENCE_WEIGHTS.clear()
        W.EVIDENCE_WEIGHTS.update(saved)

results.append(check(
    "가드: MBTI를 증거 축에 넣으면 터진다", guard_rejects("MBTI"),
    "몇 달 뒤 조용히 되돌리는 것을 막는다"))
results.append(check(
    "가드: 주역을 증거 축에 넣으면 터진다", guard_rejects("주역"), ""))
results.append(check(
    "가드: '64괘' 같은 변형 이름도 막힌다", guard_rejects("64괘비중"), ""))

# 합이 안 맞는 표도 막혀야 한다
saved = dict(W.EVIDENCE_WEIGHTS)
try:
    W.EVIDENCE_WEIGHTS["행동"] = 99
    W._validate()
    results.append(check("가드: 합이 100이 아니면 터진다", False, "예외가 안 났다"))
except W.WeightConfigError:
    results.append(check("가드: 합이 100이 아니면 터진다", True))
finally:
    W.EVIDENCE_WEIGHTS.clear()
    W.EVIDENCE_WEIGHTS.update(saved)

# ── 캐시 키 ──────────────────────────────────
k1 = W.cache_key()
saved = dict(W.EVIDENCE_WEIGHTS)
W.EVIDENCE_WEIGHTS["행동"] = 41
k2 = W.cache_key()
W.EVIDENCE_WEIGHTS.clear()
W.EVIDENCE_WEIGHTS.update(saved)
results.append(check(
    "가중치가 바뀌면 캐시 키도 바뀐다", k1 != k2,
    "표를 고쳤는데 옛 리포트가 나오는 게 제일 찾기 어렵다"))

print("=" * 66)
print(f"{sum(results)}/{len(results)} 통과")
print("=" * 66)
print()
print(W.prompt_block({"행동", "맥락", "타고난지표"}))

sys.exit(0 if all(results) else 1)
