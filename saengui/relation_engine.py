"""관계 엔진 — 두 사람 사이의 오행 교환을 읽는다.

증거 축에서 25%를 배정받은 축(`weights.EVIDENCE_WEIGHTS["관계"]`)이지만
지금까지 코드가 없었다. 이 파일이 그 자리를 채운다.

────────────────────────────────────────────────────────────
왜 필요한가

지금 엔진은 사주를 **혼자짜리 속성**으로만 쓴다 — 내 오행이 몇 개인가.
그런데 사람의 삶을 실제로 바꾸는 건 자기 명식이 아니라
**누구와 어떤 기운을 주고받았는가**다. 이건 상징 이전에 관찰 가능한 사실이다.

방법론은 이미 문서에 있었다.
`advanced analysis methods` → "다인물 관계 심화 — 음양 방향성 분석"의 5단계.
이 파일은 그 다섯 단계를 그대로 옮긴 것이고, 새로 지어낸 규칙은 없다.

────────────────────────────────────────────────────────────
이 엔진이 하지 않는 것

**성격을 말하지 않는다.** `behavior_mapper.py` 의 첫 원칙이 여기에도 적용된다 —
"목이 많으면 성장형이다" 같은 직접 매핑은 금지다.

그래서 출력은 자유 문장이 아니라 **정해진 태그 상수**뿐이다.
구조(보완/경쟁·합·미는쪽/받는쪽·비대칭·시기)만 내놓고,
그것이 사람에게 무엇을 뜻하는지는 해석 계층이 맡는다.
코드가 문장을 못 만들게 막아두면 매핑이 새어 들어오지 못한다.
────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ─────────────────────────────────────────────
# 천간 — 오행과 음양
# ─────────────────────────────────────────────
STEMS: dict[str, tuple[str, str]] = {
    "갑": ("목", "양"), "을": ("목", "음"),
    "병": ("화", "양"), "정": ("화", "음"),
    "무": ("토", "양"), "기": ("토", "음"),
    "경": ("금", "양"), "신": ("금", "음"),
    "임": ("수", "양"), "계": ("수", "음"),
}

_HANJA = {"甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무",
          "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계"}

# 오행 상생: 목→화→토→금→수→목
GENERATES = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
# 오행 상극: 목극토, 토극수, 수극화, 화극금, 금극목
CONTROLS = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}

# 천간 5합 — 합하면 새 오행으로 화(化)한다
FIVE_COMBOS: dict[frozenset[str], str] = {
    frozenset(("갑", "기")): "토",
    frozenset(("을", "경")): "금",
    frozenset(("병", "신")): "수",
    frozenset(("정", "임")): "목",
    frozenset(("무", "계")): "화",
}


class RelationInputError(ValueError):
    """입력이 명식으로 성립하지 않는다. 추측해서 진행하지 않는다."""


def normalize_stem(gan: str) -> str:
    """'甲' 도 '갑' 도 '갑'으로 만든다. 모르는 글자는 조용히 넘기지 않는다."""
    if not gan:
        raise RelationInputError("일간이 비어 있다. 없는 값을 채우지 않는다.")
    g = gan.strip()[0]
    g = _HANJA.get(g, g)
    if g not in STEMS:
        raise RelationInputError(
            f"'{gan}' 은 천간이 아니다. 갑을병정무기경신임계 또는 甲乙丙丁戊己庚辛壬癸 중 하나여야 한다."
        )
    return g


# ─────────────────────────────────────────────
# 십성 — 일간 기준으로 상대 천간이 무엇인가
# ─────────────────────────────────────────────
# 음양이 **같으면 편(偏), 다르면 정(正)** — 명리 표준 규칙이다.
# 아래 각 쌍은 (음양 같을 때, 음양 다를 때) 순서다.
_TEN_GOD_PAIRS = {
    "동일": ("비견", "겁재"),   # 상대가 나와 같은 오행
    "내가생": ("식신", "상관"),  # 내가 생하는 오행
    "내가극": ("편재", "정재"),  # 내가 극하는 오행 — 재(財)
    "나를극": ("편관", "정관"),  # 나를 극하는 오행 — 관살(官殺)
    "나를생": ("편인", "정인"),  # 나를 생하는 오행 — 인(印)
}


def ten_god(day_gan: str, other_gan: str) -> str:
    """`day_gan` 일간이 볼 때 `other_gan` 이 어떤 십성인가."""
    d = normalize_stem(day_gan)
    o = normalize_stem(other_gan)
    de, dy = STEMS[d]
    oe, oy = STEMS[o]

    if oe == de:
        kind = "동일"
    elif GENERATES[de] == oe:
        kind = "내가생"
    elif CONTROLS[de] == oe:
        kind = "내가극"
    elif CONTROLS[oe] == de:
        kind = "나를극"
    elif GENERATES[oe] == de:
        kind = "나를생"
    else:  # 오행 5개의 생극은 위 다섯으로 전부 덮인다. 여기 오면 표가 깨진 것이다.
        raise RelationInputError(f"오행 관계를 판정할 수 없다: {de} vs {oe}")

    same_polarity = (dy == oy)
    pair = _TEN_GOD_PAIRS[kind]
    return pair[0] if same_polarity else pair[1]


# ─────────────────────────────────────────────
# 입력
# ─────────────────────────────────────────────
@dataclass
class Person:
    """관계 계산에 필요한 최소 정보.

    `daeun` 은 {연도: 오행} 이다. 없으면 None 으로 둔다 —
    **모르는 것을 0이나 빈 dict 로 채우지 않는다.**
    None 과 {} 는 다른 상태다. 전자는 '모른다', 후자는 '대운이 없다'.
    """
    name: str
    day_gan: str
    daeun: dict[int, str] | None = None

    def __post_init__(self):
        self.day_gan = normalize_stem(self.day_gan)

    @property
    def element(self) -> str:
        return STEMS[self.day_gan][0]

    @property
    def polarity(self) -> str:
        return STEMS[self.day_gan][1]


# ─────────────────────────────────────────────
# 출력 — 정해진 태그만 나간다
# ─────────────────────────────────────────────
TAGS = {
    "보완적", "경쟁적",
    "천간합", "극중생합",
    "상생", "상극", "동기",
    "비대칭", "대칭",
    "결실기있음", "결실기미상",
}


@dataclass
class Step:
    no: int
    name: str
    result: str            # 사람이 읽는 한 줄. 구조만 말한다.
    tags: list[str] = field(default_factory=list)
    known: bool = True     # 계산 못 했으면 False


@dataclass
class Relation:
    a: str
    b: str
    steps: list[Step]
    tags: list[str]
    asymmetry: str
    timing: list[int] | None       # 결실기 연도들. 모르면 None
    missing: list[str]             # 계산 못 한 단계 이름

    def summary(self) -> str:
        lines = [f"[{self.a} ↔ {self.b}] 관계 구조"]
        for s in self.steps:
            mark = " " if s.known else "?"
            lines.append(f" {mark}{s.no}. {s.name}: {s.result}")
        lines.append(f"   태그: {', '.join(self.tags) if self.tags else '없음'}")
        lines.append(f"   비대칭: {self.asymmetry}")
        if self.timing:
            lines.append(f"   결실기: {', '.join(str(y) for y in self.timing)}")
        if self.missing:
            lines.append(f"   ※ 계산 못 한 단계: {', '.join(self.missing)}"
                         f" — 추측해서 채우지 않는다")
        return "\n".join(lines)


# ─────────────────────────────────────────────
# 5단계
# ─────────────────────────────────────────────
def analyze(a: Person, b: Person) -> Relation:
    """문서의 5단계 체크리스트를 그대로 실행한다."""
    steps: list[Step] = []
    tags: list[str] = []
    missing: list[str] = []

    # 1. 양일간 vs 음일간 — 다르면 보완적, 같으면 경쟁적
    if a.polarity != b.polarity:
        steps.append(Step(1, "일간 음양", f"{a.polarity}({a.day_gan}) × {b.polarity}({b.day_gan}) — 다름",
                          ["보완적"]))
        tags.append("보완적")
    else:
        steps.append(Step(1, "일간 음양", f"둘 다 {a.polarity} — 같음", ["경쟁적"]))
        tags.append("경쟁적")

    # 2. 천간 5합 — 합이면 극이 합으로 전환(극중생합)
    combo = FIVE_COMBOS.get(frozenset((a.day_gan, b.day_gan)))
    controlling = (CONTROLS[a.element] == b.element
                   or CONTROLS[b.element] == a.element)
    if combo:
        if controlling:
            steps.append(Step(2, "천간 5합",
                              f"{a.day_gan}{b.day_gan}합 → {combo}. 극이 합으로 전환(극중생합)",
                              ["천간합", "극중생합"]))
            tags += ["천간합", "극중생합"]
        else:
            steps.append(Step(2, "천간 5합", f"{a.day_gan}{b.day_gan}합 → {combo}",
                              ["천간합"]))
            tags.append("천간합")
    else:
        steps.append(Step(2, "천간 5합", "성립하지 않음", []))

    # 오행 생극 자체도 기록한다 (합이 없을 때 이게 관계의 뼈대다)
    if GENERATES[a.element] == b.element or GENERATES[b.element] == a.element:
        tags.append("상생")
    elif controlling:
        tags.append("상극")
    elif a.element == b.element:
        tags.append("동기")

    # 3. 음양 방향성 — 양은 밀고 음은 받는다
    if a.polarity != b.polarity:
        pusher, receiver = (a, b) if a.polarity == "양" else (b, a)
        steps.append(Step(3, "음양 방향",
                          f"{pusher.name}(양)이 밀고 {receiver.name}(음)이 받는다"))
    else:
        d = "둘 다 양 — 함께 밀어낸다(부딪힘)" if a.polarity == "양" \
            else "둘 다 음 — 함께 거둔다(고임)"
        steps.append(Step(3, "음양 방향", d))

    # 4. 서로에게 어떤 십성인가 — 비대칭 파악
    a_sees_b = ten_god(a.day_gan, b.day_gan)
    b_sees_a = ten_god(b.day_gan, a.day_gan)
    asym = f"{a.name}→{b.name}: {a_sees_b} / {b.name}→{a.name}: {b_sees_a}"
    if a_sees_b != b_sees_a:
        steps.append(Step(4, "상호 십성", asym + " — 비대칭", ["비대칭"]))
        tags.append("비대칭")
    else:
        steps.append(Step(4, "상호 십성", asym + " — 대칭", ["대칭"]))
        tags.append("대칭")

    # 5. 대운 교차점 — 두 사람 대운이 같은 오행을 향하는 시기
    if a.daeun is None or b.daeun is None:
        who = [p.name for p in (a, b) if p.daeun is None]
        steps.append(Step(5, "대운 교차",
                          f"대운 정보 없음 ({', '.join(who)}) — 판정하지 않음",
                          ["결실기미상"], known=False))
        tags.append("결실기미상")
        missing.append("대운 교차")
        timing = None
    else:
        shared = sorted(y for y in set(a.daeun) & set(b.daeun)
                        if a.daeun[y] == b.daeun[y])
        if shared:
            spans = ", ".join(f"{y}({a.daeun[y]})" for y in shared)
            steps.append(Step(5, "대운 교차", f"같은 오행을 향하는 시기: {spans}",
                              ["결실기있음"]))
            tags.append("결실기있음")
        else:
            steps.append(Step(5, "대운 교차", "겹치는 시기 없음", []))
        timing = shared or None

    _assert_tags(tags)
    return Relation(a=a.name, b=b.name, steps=steps,
                    tags=list(dict.fromkeys(tags)),
                    asymmetry=asym, timing=timing, missing=missing)


def _assert_tags(tags: list[str]) -> None:
    """정해진 태그 밖의 말이 새어 나가지 못하게 한다.

    이 가드가 이 파일의 핵심이다. 태그를 자유 문자열로 두면
    언젠가 "리더형" "예민한 편" 같은 성격 단정이 섞여 들어온다.
    그 순간 behavior_mapper 의 첫 원칙(직접 매핑 금지)이 깨진다.
    """
    unknown = [t for t in tags if t not in TAGS]
    if unknown:
        raise RelationInputError(
            f"허용되지 않은 태그: {unknown}. 관계 엔진은 구조만 내놓는다. "
            f"성격·기질 단정은 해석 계층의 몫이고, 오행을 성격으로 직접 매핑하지 않는다."
        )


if __name__ == "__main__":
    시저 = Person("시저", "己")
    상대 = Person("1969여성", "甲")
    print(analyze(시저, 상대).summary())
    print()
    시저2 = Person("시저", "己", daeun={2024: "토", 2025: "화", 2026: "화"})
    상대2 = Person("1969여성", "甲", daeun={2024: "금", 2025: "토", 2026: "화"})
    print(analyze(시저2, 상대2).summary())
