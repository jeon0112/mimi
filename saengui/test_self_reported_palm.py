"""손금 자기보고 판 — 계약·판정·프롬프트·검사.

★ 이 파일은 **pytest 로도 돌고 직접 실행도 된다.**
  기존 테스트 다섯은 모듈 맨 끝에 `sys.exit()` 이 있어 pytest 가 import 하는
  순간 SystemExit 으로 죽고 **"no tests ran" 인데 종료코드 0** 이 된다.
  「0개 통과」와 「28개 통과」가 같은 신호를 내면 감시는 눈이 없다.
  그래서 여기서는 `sys.exit` 을 `__main__` 안으로 넣는다. 한 줄 차이다.
"""

import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])

import palm_features as PF
import self_reported_palm as S
from palm_features import PalmContractError

results: list[bool] = []


def check(label: str, cond: bool, note: str = "") -> bool:
    results.append(bool(cond))
    print(("✅ " if cond else "❌ ") + label + ("  — " + note if note else ""))
    return bool(cond)


def raises(fn) -> tuple[bool, str]:
    try:
        fn()
    except PalmContractError as e:
        return True, str(e)[:70]
    except Exception as e:       # 다른 예외로 죽으면 그것도 실패다
        return False, f"엉뚱한 예외: {type(e).__name__}"
    return False, "예외가 안 났다"


def good_palm() -> S.SelfReportedPalm:
    return S.SelfReportedPalm(handedness="오른손", lines={
        "감정선": S.SelfLine("감정선", True, "김", "완만", "뚜렷"),
        "두뇌선": S.SelfLine("두뇌선", True, "보통", "직선형", "보통"),
        "생명선": S.SelfLine("생명선", True, "김", "깊은곡선", "뚜렷"),
        "운명선": S.SelfLine("운명선", False),
    })


# ─────────────────────────────────────────────
def test_계약():
    print("\n[계약] 담을 수 없는 것은 담기지 않는다")

    ok, msg = raises(lambda: S.SelfLine("감정선", False, length_band="김"))
    check("모른다고 한 선에 밴드를 넣으면 막는다", ok, msg)

    ok, msg = raises(lambda: S.SelfLine("감정선", True, "아주김", "완만", "뚜렷"))
    check("허용 안 된 밴드를 막는다", ok, msg)

    ok, msg = raises(lambda: S.SelfLine("감정선", True, "김", "완만"))
    check("밴드가 비면 막는다 (present=True)", ok, msg)

    ok, msg = raises(lambda: S.SelfLine("손금선", True, "김", "완만", "뚜렷"))
    check("정의 안 된 선 이름을 막는다", ok, msg)

    ok, msg = raises(lambda: S.SelfReportedPalm("양손", {}))
    check("handedness 를 막는다", ok, msg)

    # ★ 설계의 핵심 — 사람이 못 내는 값은 필드 자체가 없어야 한다
    flds = S.SelfLine.__dataclass_fields__
    check("confidence 필드가 아예 없다", "confidence" not in flds,
          "사람이 낼 수 없는 값은 담지 않는다")
    check("breaks/branches 필드가 아예 없다",
          "breaks" not in flds and "branches" not in flds,
          "persistent 릿지는 사람이 못 센다")
    check("Quality 를 안 받는다",
          "quality" not in S.SelfReportedPalm.__dataclass_fields__,
          "사진이 없다")


def test_결론가드():
    print("\n[가드] 결론이 재료 자리에 들어오면 막는다")
    line = S.SelfLine("감정선", True, "김", "완만", "뚜렷")
    object.__setattr__(line, "length_band", "이상주의")   # 자유 입력이 붙은 상황을 흉내
    ok, msg = raises(lambda: S.SelfReportedPalm("오른손", {"감정선": line}))
    check("성격 단정이 섞이면 막는다", ok, msg)

    # 음성 대조 — 정상 밴드는 안 걸려야 한다. '직선형'의 '형'이 금칙어다
    try:
        S.SelfReportedPalm("오른손", {
            "두뇌선": S.SelfLine("두뇌선", True, "보통", "직선형", "보통")})
        check("정상 밴드는 안 잡는다  (음성 대조)", True, "'직선형'의 '형'을 오검출하지 않는다")
    except PalmContractError as e:
        check("정상 밴드는 안 잡는다  (음성 대조)", False, str(e)[:60])


def test_판정():
    print("\n[판정] 사진이 없어도 주선 규칙은 산다")
    v = S.decide(good_palm())
    check("주선 3종이 다 있으면 통과한다", v.ok)

    none = S.SelfReportedPalm("왼손", {
        "감정선": S.SelfLine("감정선", False),
        "두뇌선": S.SelfLine("두뇌선", False),
        "생명선": S.SelfLine("생명선", False)})
    v2 = S.decide(none)
    check("주선을 하나도 못 고르면 거절한다", not v2.ok)
    check("거절은 반드시 행동을 준다", len(v2.actions) > 0,
          " / ".join(v2.actions)[:60])

    part = S.SelfReportedPalm("왼손", {
        "감정선": S.SelfLine("감정선", True, "보통", "완만", "보통"),
        "두뇌선": S.SelfLine("두뇌선", False),
        "생명선": S.SelfLine("생명선", False)})
    v3 = S.decide(part)
    check("일부만 없으면 거절하지 않는다", v3.ok, "없는 것은 없다고 적고 간다")
    check("빠진 선을 결과에 남긴다", v3.missing_lines == ["두뇌선", "생명선"])


def test_프롬프트():
    print("\n[프롬프트] 출처를 소리내어 밝힌다")
    block = S.to_prompt_block(good_palm())
    check("출처 고지가 반드시 들어간다",
          "본인이 직접 고른 것이며, 측정된 값이 아닙니다" in block)
    check("끊김·갈래가 없다는 것을 밝힌다", "끊김·갈래는 포함되어 있지 않습니다" in block)
    check("고르지 않은 선은 언급 금지를 달아 둔다",
          "운명선: 고르지 않음" in block)
    check("금칙(예언·의료)이 블록 안에 있다",
          "예언이나 의료 판단을 하지 마라" in block)
    check("손금이 입구임을 말한다", "이야기의 입구" in block)

    none = S.SelfReportedPalm("왼손", {"감정선": S.SelfLine("감정선", False)})
    ok, msg = raises(lambda: S.to_prompt_block(none))
    check("거절된 입력으로 프롬프트를 만들지 않는다", ok, msg)


def test_캐시키():
    print("\n[캐시키] 측정판과 섞이면 안 된다")
    p = good_palm()
    k = S.reading_key(p)
    check("접두사가 palm-self 다", k.startswith("palm-self:"), k)

    # ★★★ 같은 밴드를 가진 측정판과 키가 달라야 한다
    measured = PF.PalmFeatures(
        handedness="오른손",
        quality=PF.Quality(score=0.9, is_palm_side=True),
        lines={
            "감정선": PF.Line("감정선", True, 0.9, "김", "완만", "뚜렷"),
            "두뇌선": PF.Line("두뇌선", True, 0.9, "보통", "직선형", "보통"),
            "생명선": PF.Line("생명선", True, 0.9, "김", "깊은곡선", "뚜렷"),
            "운명선": PF.Line("운명선", False, 0.9),
        })
    check("같은 밴드라도 측정판과 키가 다르다", k != PF.reading_key(measured),
          "캐시가 섞이면 자기보고가 측정 자리로 나온다")

    # 같은 입력이면 같은 키 — 결정론
    check("같은 입력이면 같은 키다", S.reading_key(good_palm()) == k)


def test_출력검사():
    print("\n[출력검사] 없는 재료를 말하면 잡는다")
    p = good_palm()

    check("끊김을 언급하면 잡는다  ★ 이 판만의 규칙",
          any("끊김" in v for v in S.verify_output("감정선에 끊김이 하나 보입니다.", p)))
    check("갈래를 언급하면 잡는다  ★ 이 판만의 규칙",
          any("갈래" in v for v in S.verify_output("두뇌선 끝이 갈래로 나뉩니다.", p)))
    check("고르지 않은 선을 언급하면 잡는다",
          len(S.verify_output("운명선이 뚜렷하게 올라갑니다.", p)) > 0)
    check("예언을 잡는다", len(S.verify_output("올해 안에 결혼하시겠습니다.", p)) > 0)

    # ★ 음성 대조 — 정상 문장은 통과해야 한다
    clean = ("감정선이 길고 완만하게 휩니다. 생명선은 깊은 곡선을 그립니다. "
             "이건 재료일 뿐이고, 무게는 그동안 하신 일과 만난 사람이 집니다.")
    check("정상 문장은 통과한다  (음성 대조)",
          S.verify_output(clean, p) == [], str(S.verify_output(clean, p))[:70])


def test_문답():
    print("\n[문답] 소리로 읽어도 되는 문장인가")
    # ★ 검사어를 정확히 골라야 한다. 「아래」 단독은 손의 해부학적 위치이지
    #   화면 위치가 아니다 — "중지 아래" 는 눈이 없어도 손으로 짚는다.
    SCREEN_WORDS = ("그림", "화면", "왼쪽", "오른쪽 것", "위 사진", "보기에서",
                    "아래 그림", "다음 중 그림", "아이콘", "버튼")
    offenders = [(n, f, q) for n, qs in S.QUESTIONS.items()
                 for f, opts in qs.items()
                 for _, q in opts
                 if any(w in q for w in SCREEN_WORDS)]
    for n, f, q in offenders:
        print(f"    · {n}.{f} — {q}")
    check("어느 문항도 화면을 전제하지 않는다", not offenders,
          "시각장애인도 답할 수 있다" if not offenders
          else f"{len(offenders)}개가 화면을 전제한다")
    check("주선 3종 문답이 다 있다",
          all(n in S.QUESTIONS for n in PF.MAIN_LINES))
    bands = {f: [b for b, _ in S.QUESTIONS["감정선"][f]] for f in
             ("length_band", "curvature_band", "depth_proxy_band")}
    check("문답의 선택지가 계약의 밴드와 같다",
          bands["length_band"] == list(PF.LENGTH_BANDS)
          and bands["curvature_band"] == list(PF.CURVATURE_BANDS)
          and bands["depth_proxy_band"] == list(PF.DEPTH_PROXY_BANDS))


def _run_all():
    for fn in (test_계약, test_결론가드, test_판정, test_프롬프트,
               test_캐시키, test_출력검사, test_문답):
        fn()
    print("\n" + "=" * 70)
    print(f"{sum(results)}/{len(results)} 통과")
    print("=" * 70)
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
