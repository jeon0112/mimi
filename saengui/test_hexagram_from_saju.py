"""조합 경로 — 효 여섯 → 괘 번호.

★ pytest 로도 돌고 직접 실행도 된다 (E-418).
"""

import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])

import itertools
import hexagram_from_saju as H

results: list[bool] = []


def check(label: str, cond: bool, note: str = "") -> bool:
    results.append(bool(cond))
    print(("✅ " if cond else "❌ ") + label + ("  — " + note if note else ""))
    return bool(cond)


def test_8괘():
    print("\n[8괘] 효 셋 → 팔괘")
    check("여덟 가지가 다 있다", len(H.TRIGRAM_BY_LINES) == 8)
    check("팔괘 이름이 중복 없이 여덟", len(set(H.TRIGRAM_BY_LINES.values())) == 8)
    # 모양으로 확인 — 아래에서 위로 읽는다
    m = H.TRIGRAM_BY_LINES
    check("乾 은 셋 다 양", m[(True, True, True)] == "乾")
    check("坤 은 셋 다 음", m[(False, False, False)] == "坤")
    check("震 은 맨 아래만 양", m[(True, False, False)] == "震")
    check("艮 은 맨 위만 양", m[(False, False, True)] == "艮")
    check("坎 은 가운데만 양", m[(False, True, False)] == "坎")
    check("離 는 가운데만 음", m[(True, False, True)] == "離")
    check("兌 는 맨 위만 음", m[(True, True, False)] == "兌")
    check("巽 은 맨 아래만 음", m[(False, True, True)] == "巽")


def test_64괘표():
    print("\n[64괘] 표 자체가 성한가")
    check("64개다", len(H.HEXAGRAM_TRIGRAMS) == 64)
    check("번호가 1~64 로 빈틈없다",
          sorted(H.HEXAGRAM_TRIGRAMS) == list(range(1, 65)))
    check("★ 조합에 중복이 0 이다", len(set(H.HEXAGRAM_TRIGRAMS.values())) == 64,
          "중복이 있으면 서로 잘못 불린다")
    # 8×8 이 다 나오는가
    pairs = {f"{u}/{l}" for u in H.TRIGRAM_BY_LINES.values()
             for l in H.TRIGRAM_BY_LINES.values()}
    check("8×8 = 64 조합이 빠짐없이 있다",
          pairs == set(H.HEXAGRAM_TRIGRAMS.values()))


def test_자가검증():
    print("\n[자가검증] 데이터와 맞는가 · 틀리면 죽는가")
    check("★ import 시점에 37개를 대조하고 통과했다", True,
          f"KNOWN {len(H.KNOWN)}개")
    check("어제 확정한 방향과 맞다 — 5=坎/乾 · 6=乾/坎",
          H.HEXAGRAM_TRIGRAMS[5] == "坎/乾" and H.HEXAGRAM_TRIGRAMS[6] == "乾/坎",
          "E-338 음성 대조로 확정한 그 둘")
    check("오늘 고친 37 家人 = 巽/離 와 맞다",
          H.HEXAGRAM_TRIGRAMS[37] == "巽/離",
          "50 鼎 = 離/巽 과 다르다")
    check("50 鼎 = 離/巽", H.HEXAGRAM_TRIGRAMS[50] == "離/巽")

    # ★ 음성 대조 — 표를 망가뜨리면 죽어야 한다
    saved = H.HEXAGRAM_TRIGRAMS[5]
    H.HEXAGRAM_TRIGRAMS[5] = "乾/乾"
    try:
        H._self_check()
        check("★★ 표를 망가뜨리면 죽는다  (음성 대조)", False, "안 죽었다")
    except AssertionError as e:
        check("★★ 표를 망가뜨리면 죽는다  (음성 대조)", True, str(e)[:55])
    finally:
        H.HEXAGRAM_TRIGRAMS[5] = saved
        H._self_check()


def test_효배치():
    print("\n[효 배치] 시저님 결정 E-133 대로인가")
    f = H.SajuLines.__dataclass_fields__
    order = list(f)
    check("여섯 개다", len(order) == 6)
    check("순서가 초효→상효 다",
          order == ["ilgan_yang", "singang", "month_warm",
                    "daeun_forward", "cheoneul", "daeun_branch_yang"])
    # 하괘는 명식 셋, 상괘는 운 셋
    allyang = H.SajuLines(True, True, True, False, False, False)
    check("하괘가 명식 셋에서 나온다 (다 양 → 乾)", allyang.lower() == "乾")
    check("상괘가 운 셋에서 나온다 (다 음 → 坤)", allyang.upper() == "坤")
    check("★ 표기는 상괘가 앞이다 (E-338)", allyang.trigrams() == "坤/乾",
          "地天泰 11 — 하괘 명식이 뒤에 온다")
    check("그 조합이 11 泰 다", H.match(allyang, set(H.KNOWN)).number == 11)


def test_전수():
    print("\n[전수] 2^6 = 64 가 전부 다른 괘로 가는가")
    seen: dict[str, tuple] = {}
    nums = set()
    for bits in itertools.product([True, False], repeat=6):
        L = H.SajuLines(*bits)
        t = L.trigrams()
        if t in seen:
            check(f"★ 두 입력이 같은 조합으로 간다: {t}", False,
                  f"{seen[t]} vs {bits}")
            return
        seen[t] = bits
        nums.add(H.NUMBER_BY_TRIGRAMS[t])
    check("★★★ 64가지 입력이 64가지 조합으로 간다  (겹침 0)", len(seen) == 64)
    check("★★ 괘 번호도 64개 전부 다르다", len(nums) == 64,
          "하나라도 겹치면 매핑이 틀린 것이다")
    check("결정론 — 같은 입력이면 같은 괘",
          H.SajuLines(True, False, True, False, True, False).trigrams()
          == H.SajuLines(True, False, True, False, True, False).trigrams())


def test_없는괘():
    print("\n[없는 괘] 지어내지 않는가")
    # 巽/兌 = 61 中孚 — 데이터에 없다
    L = H.SajuLines(ilgan_yang=True, singang=True, month_warm=False,
                    daeun_forward=False, cheoneul=True, daeun_branch_yang=True)
    m = H.match(L, set(H.KNOWN))
    check("조합은 나온다", m.trigrams == "巽/兌")
    check("★ 글이 없으면 number 가 None 이다", m.number is None,
          "가까운 괘로 대신하지 않는다")
    check("covered 가 False 다", m.covered is False)

    # available 을 주면 그것을 쓴다
    m2 = H.match(L, {61})
    check("available 을 주면 그것으로 판정한다", m2.number == 61 and m2.covered)


def test_available_필수():
    print("\n[available] 기본값이 없다 — 낡은 표가 조용히 쓰이지 않는다")
    # ★★★★★ 2026-09-14 — 여기가 실제로 당한 자리다 (E-488)
    #   예전에는 available 이 선택이었고 기본값이 KNOWN 이었다.
    #   그래서 데이터가 41괘가 되어도 37개짜리 표로 재어 71.7% 가 그대로 나왔다.
    #   에러는 한 줄도 안 났다.
    L = H.SajuLines(True, True, True, True, True, True)
    for name, fn in (("match", lambda: H.match(L)), ("coverage", lambda: H.coverage())):
        try:
            fn()
            check(f"★★ {name}() 를 available 없이 부르면 죽는다", False, "안 죽었다")
        except TypeError:
            check(f"★★ {name}() 를 available 없이 부르면 죽는다", True,
                  "부르는 쪽이 「지금 무엇이 있나」를 대야 한다")

    # ★ 그리고 available 이 늘면 덮임도 늘어야 한다 — 그때 안 늘었다
    c37 = H.coverage(set(H.KNOWN))
    c41 = H.coverage(set(H.KNOWN) | {18, 19, 22, 52})
    check("★★★ available 이 늘면 덮임도 는다  (그때 안 늘었다)",
          c41["글이_있는_조합"] == c37["글이_있는_조합"] + 4,
          f"{c37['덮임']}% → {c41['덮임']}%")


def test_덮임():
    print("\n[덮임] 숫자가 정직한가")
    c = H.coverage(set(H.KNOWN))
    check("37개가 덮인다", c["글이_있는_조합"] == 37)
    check("덮임 57.8%", c["덮임"] == 57.8, "37/64")
    check("빈 조합이 27개다", len(c["빈_조합"]) == 27)
    check("★ 빈 조합 + 덮인 조합 = 64", len(c["빈_조합"]) + c["글이_있는_조합"] == 64)
    # 24괘였을 때와 견준다
    old24 = {1,2,3,4,5,6,11,12,13,14,15,24,25,29,30,34,40,41,42,51,55,56,63,64}
    c24 = H.coverage(old24)
    check("★★ 24괘였을 때는 37.5% 였다", c24["덮임"] == 37.5,
          f"24/64 · 지금 {c['덮임']}% 로 올랐다")


def _run_all():
    for fn in (test_8괘, test_64괘표, test_자가검증, test_효배치,
               test_전수, test_없는괘, test_available_필수, test_덮임):
        fn()
    print("\n" + "=" * 70)
    print(f"{sum(results)}/{len(results)} 통과")
    print("=" * 70)
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
