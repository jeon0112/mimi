"""리포트 조립 — 세 축이 만나는 자리.

`weights` · `relation_engine` · `palm_features` 는 각자 조각을 내놓는다.
이 파일이 그것을 하나의 프롬프트로 묶고, 돌아온 문장을 되받아 검사한다.

────────────────────────────────────────────────────────────
이 앱의 존재 이유 — 바넘을 막는다

세상의 모든 운세 앱은 이런 문장을 쓴다.

  "당신은 겉으로는 강해 보이지만 속으로는 여린 면이 있습니다"
  "아직 발휘하지 못한 잠재력이 많습니다"
  "때로는 외향적이고, 때로는 신중합니다"

**전부 맞는다. 누구에게나 맞기 때문이다.** 이것이 바넘(포러) 효과다.
읽는 사람은 "어떻게 알았지?" 하고, 그 감탄은 며칠 안에 식는다.

우리는 그 문장을 **코드로 막는다.** 두 가지 방법으로.

  ① 문장 안의 바넘 패턴을 잡는다 — 양면 병치, 보편 수식어, 보편 욕구
  ② **포러 겹침을 잰다** — 서로 다른 사람의 리포트에 같은 문장이 있으면
     그건 개인화가 아니다. 이건 의견이 아니라 측정이다.

②가 본체다. ①은 규칙이라 우회당할 수 있지만, ②는 결과를 직접 잰다.
"안 맞는 말을 안 한다"를 주장이 아니라 **숫자**로 만든다.
────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

import palm_features as PF
import weights as W


# ─────────────────────────────────────────────
# 면책 — LLM 이 쓰지 않는다
# ─────────────────────────────────────────────
# 앱이 locale 별 승인 문구로 마지막에 덮어쓸 자리.
# LLM 이 만든 면책 문구는 믿지 않는다 — 다국어에서 누락되거나 뉘앙스가 샌다.
DISCLAIMER_SLOT = "{{DISCLAIMER}}"


@dataclass
class Composed:
    prompt: str
    cache_key: str
    available_axes: list[str]
    missing_axes: list[str]

    def note_for_reader(self) -> str:
        """리포트 근거란에 그대로 싣는 문장. 빠진 축을 숨기지 않는다."""
        if not self.missing_axes:
            return ""
        return ("이 해석에서 빠진 근거: " + ", ".join(self.missing_axes)
                + " — 자료가 없어 반영하지 않았습니다.")


def compose(*, palm: PF.PalmFeatures | None = None,
            relation=None,
            behavior_block: str | None = None,
            context_block: str | None = None) -> Composed:
    """있는 축만 모아 하나의 프롬프트로 만든다.

    없는 축은 넣지 않는다. 그리고 **무엇이 빠졌는지 결과에 남긴다** —
    빠진 축을 조용히 재분배하면 왜 그 해석이 나왔는지 나중에 설명할 수 없다.
    """
    available: set[str] = set()
    parts: list[str] = []
    key_parts: list[str] = [W.cache_key()]

    if behavior_block:
        available.add("행동")
        parts.append(behavior_block)
        key_parts.append("b:" + _digest(behavior_block))

    if relation is not None:
        available.add("관계")
        parts.append("[관계 구조]\n" + relation.summary())
        key_parts.append("r:" + _digest("|".join(sorted(relation.tags))))

    if context_block:
        available.add("맥락")
        parts.append(context_block)
        key_parts.append("c:" + _digest(context_block))

    if palm is not None:
        # 거절된 측정값은 여기까지 오지 못한다 — to_prompt_block 이 막는다
        parts.append(PF.to_prompt_block(palm))
        available.add("타고난지표")
        key_parts.append(PF.reading_key(palm))

    if not available:
        raise ValueError(
            "축이 하나도 없다. 이 상태로는 리포트를 만들지 않는다. "
            "재료 없이 쓴 글은 반드시 바넘이 된다.")

    resolved, missing = W.resolve(available)
    head = W.prompt_block(available)

    tail = [
        "",
        "[반드시 지킬 것]",
        "  - 위 재료에 없는 사실을 만들지 마라.",
        "  - 누구에게나 맞는 문장을 쓰지 마라.",
        "    (\"겉으론 강하지만 속은 여리다\", \"아직 발휘하지 못한 잠재력\" 류 금지)",
        "  - 한 문장은 하나의 재료를 가리킨다. 가리킬 재료가 없으면 그 문장은 쓰지 마라.",
        "  - 면책 문구를 쓰지 마라. 아래 자리에 앱이 넣는다.",
        "",
        DISCLAIMER_SLOT,
    ]

    prompt = "\n\n".join([head] + parts) + "\n" + "\n".join(tail)
    key = "rpt-" + hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]
    return Composed(prompt=prompt, cache_key=key,
                    available_axes=sorted(available), missing_axes=missing)


def _digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


# ─────────────────────────────────────────────
# 바넘 탐지
# ─────────────────────────────────────────────
# ① 양면 병치 — 반대되는 두 성질을 한 문장에 담으면 반증이 불가능해진다
_BOTH_WAYS = re.compile(
    r"(겉으로[는]?.{0,20}(지만|나|면서도))"
    r"|((지만|면서도|한편으로[는]?).{0,20}(속으로|내면|반면))"
    r"|(때로는.{0,30}(때로는|또 어떤))"
    r"|(~?하[면기]도 하고.{0,20}하[면기]도)")

# ② 보편 수식어 — 항상 참이 되게 만드는 완충어
_HEDGES = ("때로는", "가끔은", "대체로", "어느 정도", "종종", "경우에 따라",
           "상황에 따라", "간혹")

# ③ 보편 욕구 — 사람이면 누구나 해당하는 것
_UNIVERSAL = ("인정받고 싶", "이해받고 싶", "사랑받고 싶",
              "발휘하지 못한", "숨겨진 잠재력", "잠재력이 많",
              "남들이 모르는", "겉과 속이 다르")

# 근거를 가리키는 말. 이 중 하나라도 들어 있으면 '재료를 가리킨 문장'으로 본다.
_EVIDENCE_TERMS = tuple(PF.ALL_LINES) + (
    "손금", "손바닥",
    "감정", "두뇌", "생명", "운명",
    "길이", "곡선", "선명", "끊김", "갈래", "막쥔",
    "관계", "오행", "천간", "합", "극", "보완", "경쟁", "비대칭", "대칭",
    "정관", "편관", "정재", "편재", "정인", "편인",
    "식신", "상관", "비견", "겁재", "대운", "결실기",
    "기록", "적으신", "말씀하신", "선택하신", "하신 일",
    # 사주 — 2026-09-09 추가.
    # 이 목록은 손금 어휘만 촘촘했고 사주 쪽이 거의 비어 있었다.
    # 그래서 근거를 단 문장도 「근거 없음」으로 세어졌다.
    # ★ 한 글자(갑·을·병·목·화·수…)는 넣지 않는다 — 오탐이 폭발한다.
    #   근거는 "일간 병(丙)" 처럼 두 글자 이상 낱말과 함께 적는다.
    "일간", "일주", "월주", "년주", "시주", "연주",
    "명식", "사주", "팔자", "천간", "지지", "간지",
    "오행", "신강", "신약", "용신", "희신", "기신", "격국",
    "세운", "유년", "진태양시", "절입",
    "주역", "괘", "상괘", "하괘",
)

# 리포트 전체에서 근거를 가리키는 문장이 이 비율 미만이면 위반.
# 연결 문장·전환 문장은 있을 수 있으므로 문장마다 요구하지는 않는다.
MIN_GROUNDED_RATIO = 0.40

# 포러 겹침 상한. 서로 다른 사람의 리포트가 이보다 많이 겹치면 개인화가 아니다.
MAX_FORER_OVERLAP = 0.30

_SENT_SPLIT = re.compile(r"(?<=[.!?。])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def is_grounded(sentence: str) -> bool:
    return any(t in sentence for t in _EVIDENCE_TERMS)


def barnum_flags(sentence: str) -> list[str]:
    """이 문장이 바넘인 이유들. 비어 있으면 통과."""
    flags = []
    if _BOTH_WAYS.search(sentence):
        flags.append("양면 병치")
    if any(h in sentence for h in _HEDGES) and not is_grounded(sentence):
        flags.append("보편 수식어 + 근거 없음")
    for u in _UNIVERSAL:
        if u in sentence:
            flags.append(f"보편 욕구('{u}')")
            break
    return flags


# ─────────────────────────────────────────────
# 금칙어 — 한 글자짜리는 문맥을 본다
# ─────────────────────────────────────────────
# 2026-09-09: BANNED_TERMS 의 "암"·"죽" 이 한 글자라
#   "암말의 곧음"(곤괘 판사 利牝馬之貞) · "죽이 잘 맞는다" 를 잡았다.
#   사주 리포트 한 편에서 오탐 8건이 났다.
#
# **거짓 경보는 진짜 경보를 죽인다.** 매번 8건이 뜨면 사람이 경고를 안 본다.
#   그러니 조사가 붙은 자리에서만 잡는다. 앞에 한글이 오면 낱말의 일부다.
_AMBIGUOUS = (
    (re.compile(r"(?<![가-힣])암(?=[이을은과에서의]|\s|$)"), "암"),
    (re.compile(r"(?<![가-힣])죽(?=[음는을었])"), "죽음"),
)
# 위 둘은 BANNED_TERMS 에서 빼고 여기서 본다
_LITERAL_BANNED = tuple(t for t in PF.BANNED_TERMS if t not in ("암", "죽"))


def banned_hits(text: str) -> list[str]:
    """금칙어를 찾는다. 한 글자짜리는 문맥을 보고 판단한다."""
    hits = [f"'{t}' 이(가) 포함됨" for t in _LITERAL_BANNED if t in text]
    hits += [f"'{name}' 이(가) 포함됨" for rx, name in _AMBIGUOUS if rx.search(text)]
    return hits


# ─────────────────────────────────────────────
# 검증
# ─────────────────────────────────────────────
@dataclass
class ReportViolation:
    kind: str          # 금칙어 | 근거없음 | 바넘 | 면책침범 | 근거부족
    detail: str
    sentence: str = ""


def verify_report(text: str, *,
                  palm: PF.PalmFeatures | None = None) -> list[ReportViolation]:
    """LLM 이 낸 리포트를 되받아 검사한다. 위반이 있으면 내보내지 않는다."""
    out: list[ReportViolation] = []

    # 금칙어는 손금이 있든 없든 **언제나** 본다.
    # 2026-09-09 이전에는 이 검사가 `palm is not None` 안에 있었다.
    # 그래서 사주만 있는 리포트는 금칙어 검사를 한 번도 받지 않았다 —
    # 「0건」이 「통과」가 아니라 「안 돌았다」였다.
    out.extend(ReportViolation("금칙어", d) for d in banned_hits(text))

    if palm is not None:
        # 관측되지 않은 선을 언급했는가 — 이건 손금이 있어야 볼 수 있다
        for v in PF.verify_output(text, palm):
            if v.kind != "금칙어":      # 금칙어는 위에서 이미 봤다
                out.append(ReportViolation(v.kind, v.detail))

    sentences = split_sentences(text)
    if not sentences:
        return [ReportViolation("근거부족", "빈 리포트")]

    for s in sentences:
        for flag in barnum_flags(s):
            out.append(ReportViolation("바넘", flag, s))

    grounded = sum(1 for s in sentences if is_grounded(s))
    ratio = grounded / len(sentences)
    if ratio < MIN_GROUNDED_RATIO:
        out.append(ReportViolation(
            "근거부족",
            f"재료를 가리킨 문장이 {grounded}/{len(sentences)} "
            f"({ratio:.0%}) — 기준 {MIN_GROUNDED_RATIO:.0%} 미만"))

    # LLM 이 스스로 면책 문구를 쓴 경우. 앱이 덮어쓸 자리를 침범한 것이다.
    for mark in ("법적 책임", "참고용일 뿐", "재미로만", "의학적 조언이 아닙",
                 "본 결과는 참고"):
        if mark in text:
            out.append(ReportViolation(
                "면책침범", f"LLM 이 면책 문구를 썼다('{mark}'). "
                            f"면책은 앱이 {DISCLAIMER_SLOT} 자리에 넣는다"))
            break

    return out


# ─────────────────────────────────────────────
# 포러 판별 — 이 앱의 진짜 지표
# ─────────────────────────────────────────────
def forer_overlap(a: str, b: str) -> float:
    """서로 다른 사람의 리포트 두 개가 얼마나 겹치는가. 0~1.

    바넘 문장은 아무에게나 붙으므로 두 리포트에 똑같이 나타난다.
    개인화된 문장은 그 사람의 재료를 가리키므로 겹치지 않는다.

    규칙 탐지는 우회당할 수 있지만 **이 숫자는 결과를 직접 잰다.**
    "안 맞는 말을 안 한다"를 주장이 아니라 측정으로 만드는 지표다.
    """
    sa = {_normalize(s) for s in split_sentences(a)}
    sb = {_normalize(s) for s in split_sentences(b)}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def _normalize(s: str) -> str:
    """비교용 정규화. 공백·문장부호 차이로 겹침을 놓치지 않는다."""
    return re.sub(r"[\s.,!?·…\"'“”‘’]", "", s)


def material_citation(text: str,
                      materials: "Sequence[str]") -> tuple[float, list[str]]:
    """이 리포트가 **그 사람의 재료**를 실제로 몇 개나 인용했나. 0~1 과 빠진 목록.

    ★ 왜 포러 겹침만으로는 부족한가 — 2026-09-09

    비슷한 두 명식에서 겹침이 41~72% 로 나왔다. 템플릿 채우기다.
    고치는 길은 「다시 쓰기」인데, **여기에 함정이 있다.**

        LLM 에게 다시 쓰게 하면 겹침은 쉽게 내려간다. 표현만 바꾸면 된다.
        **측정은 통과하는데 실제로는 나아지지 않는다.**

    게이트를 통과하려고 최적화하는 것 — 우리가 계속 경계해 온 그것이다.

    그래서 반대편에서 한 번 더 잰다.
    **그 사람의 고유한 값이 본문에 실제로 나오는가.**

        ✗  "결단한다"                   ← 경(庚) 이면 누구나 받는다
        ✓  "금이 4.0 으로 몰려 있습니다"  ← 이 사람만 받는다

    **표현을 바꿔서는 이 지표를 통과할 수 없다.** 재료를 읽어야 통과한다.

    materials 에 넣을 것 (예) —
        4주 간지 · 오행 수치 · 현재 대운 · 신강/신약 · 주요 십성 · 괘 이름

    ★ **구절이 아니라 값을 넣는다.**
        ✗  "금 4.0"   ← 본문이 "금이 4.0으로" 라고 쓰면 안 잡힌다
        ✓  "4.0"  "경금"  "신강"  "을사"
      값은 어떤 문장에 실려도 그대로 남는다. 구절은 조사 하나에 깨진다.
    """
    if not materials:
        return 0.0, []
    body = _normalize(text)
    missing = [m for m in materials if _normalize(str(m)) not in body]
    return (len(materials) - len(missing)) / len(materials), missing


def material_verdict(text: str, materials: "Sequence[str]") -> tuple[float, str]:
    """재료 인용률과 한 줄 설명. **아직 게이트로 걸지 않는다.**

    임계값은 재본 뒤에 정한다. 근거 없이 숫자를 박으면
    그 숫자가 어디서 왔는지 아무도 모르게 된다 (E-22 가 그렇게 났다).
    """
    ratio, missing = material_citation(text, materials)
    if not materials:
        return 0.0, "재료 목록이 비어 있다 — 잴 수 없다"
    return ratio, (f"재료 인용 {ratio:.0%} ({len(materials)-len(missing)}/{len(materials)})"
                   + (f" · 빠진 것: {', '.join(map(str, missing[:5]))}" if missing else ""))


def forer_verdict(a: str, b: str) -> tuple[bool, str]:
    """두 리포트가 개인화 기준을 통과하는가."""
    ov = forer_overlap(a, b)
    if ov > MAX_FORER_OVERLAP:
        return False, (f"포러 겹침 {ov:.0%} > 기준 {MAX_FORER_OVERLAP:.0%} — "
                       f"서로 다른 사람에게 같은 문장이 나갔다")
    return True, f"포러 겹침 {ov:.0%} — 기준 이내"


if __name__ == "__main__":
    palm = PF.PalmFeatures(
        handedness="오른손",
        quality=PF.Quality(0.82, True),
        lines={
            "감정선": PF.Line("감정선", True, 0.88, "김", "완만", "뚜렷", branches=2),
            "두뇌선": PF.Line("두뇌선", True, 0.79, "보통", "직선형", "보통", breaks=1),
            "생명선": PF.Line("생명선", True, 0.91, "김", "깊은곡선", "뚜렷"),
            "운명선": PF.Line("운명선", False, 0.31),
        })
    c = compose(palm=palm, behavior_block="[행동 기록]\n  · 최근 3개월 이직 준비를 기록하심")
    print(c.prompt)
    print("\n캐시 키:", c.cache_key)
    print("빠진 축:", c.missing_axes)
    print(c.note_for_reader())
