"""report_composer.py 검증.

가장 중요한 시험은 포러 판별이다 —
서로 다른 사람의 리포트에 같은 문장이 나가면 잡아야 한다.
바넘 패턴 탐지는 우회당할 수 있지만, 겹침 측정은 결과를 직접 잰다.

실행:  python3 test_report_composer.py
"""

import sys

import palm_features as PF
import report_composer as RC
import relation_engine as RE


def check(name, cond, detail=""):
    mark = "✅" if cond else "❌"
    print(f"{mark} {name}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


def palm_ok(**over):
    lines = {
        "감정선": PF.Line("감정선", True, 0.88, "김", "완만", "뚜렷", branches=2),
        "두뇌선": PF.Line("두뇌선", True, 0.79, "보통", "직선형", "보통", breaks=1),
        "생명선": PF.Line("생명선", True, 0.91, "김", "깊은곡선", "뚜렷"),
        "운명선": PF.Line("운명선", False, 0.31),
    }
    lines.update(over.pop("lines", {}))
    return PF.PalmFeatures(handedness=over.pop("handedness", "오른손"),
                           quality=PF.Quality(0.82, True), lines=lines)


results = []
print("=" * 70)
print("리포트 조립 검증")
print("=" * 70)

BEHAV = "[행동 기록]\n  · 최근 3개월 이직 준비를 기록하심"
CTX = "[지금의 맥락]\n  · 진로 전환을 고민 중이라 적으심"

# ── 조립 ─────────────────────────────────────
c = RC.compose(palm=palm_ok(), behavior_block=BEHAV)
results.append(check("있는 축만 모은다",
                     set(c.available_axes) == {"행동", "타고난지표"},
                     str(c.available_axes)))
results.append(check("없는 축을 결과에 남긴다",
                     set(c.missing_axes) == {"관계", "맥락"}, str(c.missing_axes)))
results.append(check("빠진 축을 독자에게 밝히는 문장을 만든다",
                     "관계" in c.note_for_reader() and "빠진" in c.note_for_reader(),
                     c.note_for_reader()))

rel = RE.analyze(RE.Person("나", "己"), RE.Person("상대", "甲"))
c2 = RC.compose(palm=palm_ok(), behavior_block=BEHAV, relation=rel, context_block=CTX)
results.append(check("네 축이 다 있으면 빠진 축이 없다", c2.missing_axes == [],
                     str(c2.missing_axes)))
results.append(check("관계 구조가 프롬프트에 들어간다", "극중생합" in c2.prompt))
results.append(check("손금 측정값이 프롬프트에 들어간다", "감정선" in c2.prompt))

results.append(check("면책 자리를 표시하고 LLM 에게 쓰지 말라 한다",
                     RC.DISCLAIMER_SLOT in c2.prompt and "면책 문구를 쓰지 마라" in c2.prompt))
results.append(check("바넘 금지가 프롬프트에 들어간다",
                     "누구에게나 맞는 문장을 쓰지 마라" in c2.prompt))

# 축이 하나도 없으면 만들지 않는다
try:
    RC.compose()
    results.append(check("재료가 없으면 리포트를 만들지 않는다", False, "만들어져 버렸다"))
except ValueError:
    results.append(check("재료가 없으면 리포트를 만들지 않는다", True,
                         "재료 없이 쓴 글은 반드시 바넘이 된다"))

# 거절된 손금은 여기까지 못 온다
bad_palm = PF.PalmFeatures(handedness="왼손",
                           quality=PF.Quality(0.4, False),
                           lines={"감정선": PF.Line("감정선", False, 0.2)})
try:
    RC.compose(palm=bad_palm)
    results.append(check("거절된 손금으로는 조립되지 않는다", False))
except PF.PalmContractError:
    results.append(check("거절된 손금으로는 조립되지 않는다", True, "문이 하나뿐이다"))

# ── 캐시 키 ──────────────────────────────────
results.append(check("같은 재료 → 같은 키",
                     RC.compose(palm=palm_ok(), behavior_block=BEHAV).cache_key
                     == c.cache_key))
results.append(check("손금 밴드가 바뀌면 키가 바뀐다",
                     RC.compose(palm=palm_ok(lines={
                         "감정선": PF.Line("감정선", True, 0.88, "짧음", "완만",
                                        "뚜렷", branches=2)}),
                         behavior_block=BEHAV).cache_key != c.cache_key))
results.append(check("행동 기록이 바뀌면 키가 바뀐다",
                     RC.compose(palm=palm_ok(),
                                behavior_block=BEHAV + " 그리고 자격증 준비").cache_key
                     != c.cache_key))

# ── 바넘 탐지 ────────────────────────────────
barnum = [
    ("겉으로는 강해 보이지만 속으로는 여린 면이 있습니다", "양면 병치"),
    ("때로는 외향적이고 때로는 조용해집니다", "양면 병치"),
    ("남들에게 인정받고 싶은 마음이 있습니다", "보편 욕구"),
    ("아직 발휘하지 못한 잠재력이 많습니다", "보편 욕구"),
    ("대체로 신중한 편입니다", "보편 수식어"),
]
b_ok = True
for s, why in barnum:
    if not RC.barnum_flags(s):
        b_ok = False
        print(f"   ❌ 못 잡음: {s}  ({why})")
results.append(check(f"바넘 문장 {len(barnum)}종을 잡는다", b_ok,
                     "누구에게나 맞는 말"))

grounded = [
    "두뇌선이 직선형으로 뻗어 있습니다.",
    "감정선에 갈래가 둘 보입니다.",
    "관계에서 정관과 정재가 비대칭으로 맞물립니다.",
    "때로는 감정선이 흐려 보일 수 있습니다.",   # 완충어지만 근거를 가리킴
]
g_ok = all(not RC.barnum_flags(s) for s in grounded)
results.append(check("재료를 가리킨 문장은 통과시킨다", g_ok,
                     "완충어가 있어도 근거가 있으면 바넘이 아니다"))

results.append(check("근거 참조를 판정한다",
                     RC.is_grounded("감정선이 깁니다")
                     and not RC.is_grounded("좋은 날이 올 것입니다")))

# ── 리포트 검증 ──────────────────────────────
good_report = (
    "두뇌선이 직선형으로 곧게 뻗어 있습니다. "
    "감정선은 길고 갈래가 둘 보입니다. "
    "생명선은 깊은곡선으로 뚜렷합니다. "
    "이 셋이 함께 놓이면 판단과 감정을 따로 두는 결이 읽힙니다.")
v = RC.verify_report(good_report, palm=palm_ok())
results.append(check("정상 리포트는 통과한다", v == [],
                     f"위반 {len(v)}건" if v else "근거 비율 충족"))

bad_report = (
    "겉으로는 강해 보이지만 속으로는 여린 면이 있습니다. "
    "남들에게 인정받고 싶은 마음이 큽니다. "
    "좋은 날이 올 것입니다. "
    "본 결과는 참고용입니다.")
v2 = RC.verify_report(bad_report, palm=palm_ok())
kinds = {x.kind for x in v2}
results.append(check("바넘 리포트를 잡는다", "바넘" in kinds, str(sorted(kinds))))
results.append(check("근거 부족을 잡는다", "근거부족" in kinds))
results.append(check("LLM 이 쓴 면책 문구를 잡는다", "면책침범" in kinds,
                     "면책은 앱이 넣는다"))

v3 = RC.verify_report("운명선이 뚜렷하게 뻗어 있습니다. "
                      "감정선도 길고 두뇌선도 곧습니다. "
                      "생명선이 깊습니다.", palm=palm_ok())
results.append(check("관측 안 된 선 언급을 잡는다",
                     any(x.kind == "근거없음" for x in v3),
                     "운명선은 present=False 였다"))

v4 = RC.verify_report("수명이 길겠습니다. 감정선이 깁니다. 두뇌선도 곧습니다.",
                      palm=palm_ok())
results.append(check("금칙어를 잡는다", any(x.kind == "금칙어" for x in v4)))

results.append(check("빈 리포트를 잡는다",
                     RC.verify_report("", palm=palm_ok())[0].kind == "근거부족"))

# ── 포러 판별 — 이 파일의 핵심 ────────────────
person_a = ("감정선이 길고 갈래가 둘입니다. "
            "두뇌선은 직선형입니다. "
            "생명선이 깊은곡선으로 뚜렷합니다.")
person_b = ("감정선이 짧고 갈래가 없습니다. "
            "두뇌선은 깊은곡선입니다. "
            "생명선이 옅게 보입니다.")
ok_p, msg_p = RC.forer_verdict(person_a, person_b)
results.append(check("개인화된 두 리포트는 겹치지 않는다", ok_p, msg_p))

barnum_a = ("겉으로는 강해 보이지만 속은 여립니다. "
            "인정받고 싶은 마음이 있습니다. "
            "좋은 시기가 다가옵니다.")
barnum_b = ("겉으로는 강해 보이지만 속은 여립니다. "
            "인정받고 싶은 마음이 있습니다. "
            "새로운 기회가 옵니다.")
ok_b, msg_b = RC.forer_verdict(barnum_a, barnum_b)
results.append(check("서로 다른 사람에게 같은 문장이 나가면 잡는다",
                     not ok_b, msg_b))

results.append(check("완전히 같은 리포트는 겹침 100%",
                     abs(RC.forer_overlap(person_a, person_a) - 1.0) < 1e-9))
results.append(check("겹침이 없으면 0%",
                     RC.forer_overlap("감정선이 깁니다.", "두뇌선이 곧습니다.") == 0.0))
results.append(check("공백·문장부호 차이로 겹침을 놓치지 않는다",
                     RC.forer_overlap("감정선이 깁니다.", "감정선이  깁니다") == 1.0,
                     "정규화 후 비교"))
results.append(check("빈 입력에서 터지지 않는다",
                     RC.forer_overlap("", "감정선이 깁니다.") == 0.0))

print("=" * 70)
print(f"{sum(results)}/{len(results)} 통과")
print("=" * 70)
print()
print("── 포러 판별 실제 값 ──")
print(f"  개인화된 두 사람 : {RC.forer_overlap(person_a, person_b):.0%}  {msg_p}")
print(f"  바넘 두 사람     : {RC.forer_overlap(barnum_a, barnum_b):.0%}  {msg_b}")
print()
print("── 조립된 프롬프트 (일부) ──")
print("\n".join(c2.prompt.splitlines()[:6]))
print("  ...")

sys.exit(0 if all(results) else 1)
