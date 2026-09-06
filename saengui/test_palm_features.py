"""palm_features.py 검증.

가장 중요한 시험은 두 개다.
  · 같은 손의 두 장이 같은 키를 만드는가 (결정론)
  · 밴드가 다르면 다른 키를 만드는가 (band-flip — 특징을 실제로 쓰는가)

둘째가 없으면 첫째는 "아무것도 안 보고 항상 같은 답"으로도 통과한다.

실행:  python3 test_palm_features.py
"""

import sys

import palm_features as P


def check(name, cond, detail=""):
    mark = "✅" if cond else "❌"
    print(f"{mark} {name}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


def make(**over):
    lines = {
        "감정선": P.Line("감정선", True, 0.88, "김", "완만", "뚜렷", breaks=0, branches=2),
        "두뇌선": P.Line("두뇌선", True, 0.79, "보통", "직선형", "보통", breaks=1, branches=0),
        "생명선": P.Line("생명선", True, 0.91, "김", "깊은곡선", "뚜렷"),
        "운명선": P.Line("운명선", False, 0.31),
    }
    lines.update(over.pop("lines", {}))
    kw = dict(handedness="오른손",
              quality=P.Quality(score=0.82, is_palm_side=True),
              lines=lines)
    kw.update(over)
    return P.PalmFeatures(**kw)


results = []
print("=" * 70)
print("손금 계약 검증")
print("=" * 70)

good = make()

# ── 결정론 ───────────────────────────────────
k1 = P.reading_key(good)
k2 = P.reading_key(make())
results.append(check("같은 밴드 → 같은 키", k1 == k2, k1))

# 조명이 조금 달라 confidence 만 흔들린 두 번째 사진
jitter = make(lines={
    "감정선": P.Line("감정선", True, 0.71, "김", "완만", "뚜렷", breaks=0, branches=2),
    "두뇌선": P.Line("두뇌선", True, 0.93, "보통", "직선형", "보통", breaks=1, branches=0),
    "생명선": P.Line("생명선", True, 0.66, "김", "깊은곡선", "뚜렷"),
})
results.append(check("confidence 가 흔들려도 키는 같다",
                     P.reading_key(jitter) == k1,
                     "같은 손을 두 번 찍은 경우 — 여기서 갈리면 앱이 지워진다"))

results.append(check("손 좌우가 다르면 키가 다르다",
                     P.reading_key(make(handedness="왼손")) != k1))
results.append(check("막쥔손금 유무가 키를 바꾼다",
                     P.reading_key(make(simian=True)) != k1))

# ── band-flip: 특징을 실제로 쓰는가 ───────────
flips = [
    ("감정선 길이 김→짧음",
     P.Line("감정선", True, 0.88, "짧음", "완만", "뚜렷", breaks=0, branches=2)),
    ("두뇌선 곡선 직선형→깊은곡선",
     P.Line("두뇌선", True, 0.79, "보통", "깊은곡선", "보통", breaks=1, branches=0)),
    ("생명선 선명도 뚜렷→옅음",
     P.Line("생명선", True, 0.91, "김", "깊은곡선", "옅음")),
]
flip_ok, prompt_ok = True, True
for label, line in flips:
    f2 = make(lines={line.name: line})
    if P.reading_key(f2) == k1:
        flip_ok = False
        print(f"   ❌ {label}: 키가 그대로다")
    if P.to_prompt_block(f2) == P.to_prompt_block(good):
        prompt_ok = False
        print(f"   ❌ {label}: 프롬프트가 그대로다")
results.append(check(f"band-flip {len(flips)}종 → 키가 바뀐다", flip_ok,
                     "안 바뀌면 '항상 같은 답'으로도 결정론 시험을 통과한다"))
results.append(check(f"band-flip {len(flips)}종 → 프롬프트가 바뀐다", prompt_ok,
                     "LLM 이 특징을 볼 기회 자체가 있어야 한다"))

results.append(check("persistent 끊김 수가 키에 반영된다",
                     P.reading_key(make(lines={
                         "두뇌선": P.Line("두뇌선", True, 0.79, "보통", "직선형",
                                       "보통", breaks=3, branches=0)})) != k1))

# ── 거절 ─────────────────────────────────────
back = make(quality=P.Quality(score=0.85, is_palm_side=False))
v = P.decide(back)
results.append(check("손등을 찍으면 거절한다", not v.ok and "손등이 찍혔다" in v.reasons))
results.append(check("거절할 때 할 일을 알려준다", bool(v.actions), v.actions[0]))

blur = make(quality=P.Quality(score=0.40, is_palm_side=True,
                              issues=["초점이 흐립니다"]))
v2 = P.decide(blur)
results.append(check("품질 미달이면 거절한다", not v2.ok))
results.append(check("품질 문제는 사용자 문구를 그대로 쓴다",
                     "초점이 흐립니다" in v2.actions))

lowconf = make(lines={"생명선": P.Line("생명선", True, 0.42, "김", "깊은곡선", "뚜렷")})
v3 = P.decide(lowconf)
results.append(check("주선 신뢰도가 낮으면 거절한다",
                     not v3.ok and "생명선" in v3.missing_lines,
                     "그럴듯한 오답보다 정직한 거절"))

absent = make(lines={"두뇌선": P.Line("두뇌선", False, 0.30)})
results.append(check("주선이 없으면 거절한다", not P.decide(absent).ok))

# 운명선은 선택 — 없어도 통과
results.append(check("선택 선(운명선)이 없어도 통과한다", P.decide(good).ok))

# 거절된 측정값으로는 프롬프트를 만들 수 없다
try:
    P.to_prompt_block(blur)
    results.append(check("거절된 값으로 프롬프트를 못 만든다", False, "만들어져 버렸다"))
except P.PalmContractError:
    results.append(check("거절된 값으로 프롬프트를 못 만든다", True))

# ── 계약 가드 ────────────────────────────────
try:
    P.Line("감정선", False, 0.2, length_band="김")
    results.append(check("가드: 없는 선에 밴드를 못 채운다", False))
except P.PalmContractError:
    results.append(check("가드: 없는 선에 밴드를 못 채운다", True, "없으면 비운다"))

try:
    P.Line("감정선", True, 0.9, "아주김", "완만", "뚜렷")
    results.append(check("가드: 정의 밖 밴드를 막는다", False))
except P.PalmContractError:
    results.append(check("가드: 정의 밖 밴드를 막는다", True))

try:
    P.Line("사랑선", True, 0.9, "김", "완만", "뚜렷")
    results.append(check("가드: 정의 밖 선 이름을 막는다", False))
except P.PalmContractError:
    results.append(check("가드: 정의 밖 선 이름을 막는다", True))

try:
    P.Line("감정선", True, 1.4, "김", "완만", "뚜렷")
    results.append(check("가드: confidence 범위를 막는다", False))
except P.PalmContractError:
    results.append(check("가드: confidence 범위를 막는다", True))

# 성격 단정이 측정값으로 들어오는 경로
try:
    bad = P.Line("감정선", True, 0.9, "김", "완만", "뚜렷")
    bad.curvature_band = "이상주의적"          # CV 계층이 결론을 실어 보낸 상황
    P.PalmFeatures(handedness="오른손",
                   quality=P.Quality(0.8, True),
                   lines={"감정선": bad,
                          "두뇌선": P.Line("두뇌선", True, 0.8, "보통", "직선형", "보통"),
                          "생명선": P.Line("생명선", True, 0.8, "김", "완만", "뚜렷")})
    results.append(check("가드: 측정값에 성격 단정이 못 들어온다", False, "통과돼 버렸다"))
except P.PalmContractError:
    results.append(check("가드: 측정값에 성격 단정이 못 들어온다", True,
                         "손금 태그는 결론이 아니라 재료다"))

results.append(check("'직선형'은 정상 밴드로 통과한다",
                     P.decide(good).ok, "부분문자열 금지어에 걸리면 안 된다"))

# ── 프롬프트 ─────────────────────────────────
block = P.to_prompt_block(good)
results.append(check("프롬프트에 원본 이미지·좌표가 없다",
                     "px" not in block and "base64" not in block and "좌표" not in block))
results.append(check("관측 안 된 선은 '관측되지 않음'으로 명시된다",
                     "운명선: 관측되지 않음" in block))
results.append(check("직접 매핑 금지가 프롬프트에 들어간다",
                     "직접 매핑하지 마라" in block))
results.append(check("손금은 근거가 아니라 입구임을 프롬프트가 말한다",
                     "무게는 행동과 관계가 진다" in block))

# ── 산출물 검증 ──────────────────────────────
bad_texts = [
    ("수명이 길겠습니다", "수명"),
    ("반드시 성공합니다", "반드시"),
    ("질병을 조심하세요", "질병"),
    ("결혼할 나이는 서른입니다", "결혼할 나이"),
]
ban_ok = all(any(t in vi.detail for vi in P.verify_output(txt, good))
             for txt, t in bad_texts)
results.append(check(f"금칙어 {len(bad_texts)}종을 잡는다", ban_ok,
                     "예언·의료·단정"))

viol = P.verify_output("운명선이 뚜렷하게 뻗어 있습니다", good)
results.append(check("관측 안 된 선을 언급하면 잡는다",
                     any(v.kind == "근거없음" for v in viol),
                     "운명선은 present=False 였다"))

results.append(check("정상 문장은 통과한다",
                     P.verify_output("두뇌선이 곧게 뻗어 있습니다", good) == [],
                     "잡을 것만 잡는다"))

print("=" * 70)
print(f"{sum(results)}/{len(results)} 통과")
print("=" * 70)
print()
print(block)
print()
bad_shot = make(quality=P.Quality(0.41, False, ["초점이 흐립니다", "그림자가 있습니다"]))
bv = P.decide(bad_shot)
print("거절 예시")
print("  사유:", " / ".join(bv.reasons))
print("  안내:", " / ".join(bv.actions))

sys.exit(0 if all(results) else 1)
