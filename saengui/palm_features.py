"""손금 — 측정 계층과 서사 계층 사이의 계약.

이 파일은 사진을 보지 않는다. CV 파이프라인이 만든 값을 받아
**LLM에게 넘겨도 되는 형태인지 판정하고, 넘길 형태로 바꾼다.**

────────────────────────────────────────────────────────────
설계 근거 — Model Council(GPT-5.6 Sol × Claude Opus 5) 합의

두 모델이 서로 다른 논리 경로로 같은 결론에 도달한 지점이 골격이다.

  · CV(측정) 계층과 LLM(서사) 계층을 **물리적으로 분리**하고,
    그 사이를 **수치 JSON 하나로만** 잇는다.
    멀티모달 LLM에 손 사진을 그대로 던지는 "쉬운 길"은 두 모델 모두 반대했다.
  · 신뢰도가 임계 미달이면 **해석을 만들지 말고 재촬영을 요구한다.**
    그럴듯한 오답보다 정직한 거절이 신뢰를 만든다.
  · 같은 손이면 같은 결과가 나와야 한다. 사용자는 반드시 두 번 찍어보고,
    결과가 다르면 앱을 지운다.

────────────────────────────────────────────────────────────
이 파일이 지키는 세 가지

① 연속값을 LLM에 넘기지 않는다 — **밴드로만**
   길이 187.3px 과 188.1px 은 같은 손의 두 장에서 흔히 나온다.
   그대로 넘기면 문장이 흔들린다. 밴드로 양자화하면 흔들리지 않는다.
   결정론은 캐시로 덧칠하는 게 아니라 **계약에서 확보한다.**

② 손금 태그는 결론이 아니라 재료다
   "감정선 종료점이 검지 아래 → 이상주의적" 같은 직접 매핑은 금지다.
   `behavior_mapper.py` 의 "목이 많으면 성장형이다" 금지와 같은 원칙이고,
   `relation_engine.py` 의 태그 가드와 같은 방식으로 코드가 막는다.

③ 이름을 정직하게 짓는다
   `depth` 가 아니라 `depth_proxy` 다. 실제 3D 깊이를 잰 적이 없다.
   계약의 정직성이 이후 해석과 마케팅의 과장을 막는다.

────────────────────────────────────────────────────────────
저장하지 않는 것

원본 이미지, EXIF, 그리고 **개인을 식별할 수 있는 팜코드**.
"내 손 기억하기" 같은 매칭 기능을 붙이는 순간 생체인식 특징정보를
다루게 된다. 이 파일은 그런 값을 만들지도 반환하지도 않는다.
(일반 정보이며 법률 자문이 아니다. 출시 전 법률 검토가 필요하다.)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


SCHEMA_VERSION = "palm-1"

# 주선 3종. 이 셋이 안 잡히면 해석하지 않는다.
MAIN_LINES = ("감정선", "두뇌선", "생명선")
# 있으면 쓰고 없으면 없다고 쓴다. 없다고 감점하지 않는다.
OPTIONAL_LINES = ("운명선",)
ALL_LINES = MAIN_LINES + OPTIONAL_LINES

# 밴드 — 연속값은 여기서 끊는다. LLM 은 밴드만 본다.
LENGTH_BANDS = ("짧음", "보통", "김")
CURVATURE_BANDS = ("직선형", "완만", "깊은곡선")
DEPTH_PROXY_BANDS = ("옅음", "보통", "뚜렷")   # depth 아님 — 3D 깊이를 잰 적 없다

_BAND_SETS = {
    "length_band": LENGTH_BANDS,
    "curvature_band": CURVATURE_BANDS,
    "depth_proxy_band": DEPTH_PROXY_BANDS,
}

# 거절 임계 — 낮추지 않는다. 낮추면 이 파일의 존재 이유가 사라진다.
MIN_LINE_CONFIDENCE = 0.60
MIN_IMAGE_QUALITY = 0.60

# 특징 값에 절대 들어와서는 안 되는 말.
# 측정값이 성격 단정으로 변해 들어오는 경로를 막는다.
FORBIDDEN_IN_FEATURES = (
    "형", "적", "성격", "기질", "운명", "재물", "수명", "건강",
    "이상주의", "현실주의", "리더", "예민", "낙천",
)
# 위 목록은 부분 문자열로 검사하므로, 밴드 이름에 '형'이 들어가는
# '직선형'은 예외로 둔다. 예외는 여기 명시된 것뿐이다.
_FEATURE_VALUE_ALLOWLIST = set(LENGTH_BANDS) | set(CURVATURE_BANDS) | set(DEPTH_PROXY_BANDS)


class PalmContractError(ValueError):
    """계약을 어긴 값이다. 해석 단계로 넘기지 않는다."""


# ─────────────────────────────────────────────
# 측정 결과
# ─────────────────────────────────────────────
@dataclass
class Line:
    """선 하나의 측정 결과. **연속값은 담지 않는다.**

    breaks/branches 는 persistent feature 만 센 값이어야 한다 —
    릿지 임계값을 ±10% 흔들어도 살아남은 것만. 임계값에 따라
    3개였다 7개였다 하는 숫자를 넘기면 문장이 매번 달라진다.
    """
    name: str
    present: bool
    confidence: float
    length_band: str | None = None
    curvature_band: str | None = None
    depth_proxy_band: str | None = None
    breaks: int | None = None       # persistent 만
    branches: int | None = None     # persistent 만

    def __post_init__(self):
        if self.name not in ALL_LINES:
            raise PalmContractError(
                f"'{self.name}' 은 정의된 선이 아니다. {ALL_LINES} 중 하나여야 한다.")
        if not 0.0 <= self.confidence <= 1.0:
            raise PalmContractError(f"confidence 는 0~1 이어야 한다: {self.confidence}")
        if not self.present:
            # 없는 선에 밴드를 채워 넣지 않는다. 없으면 비운다.
            for f in ("length_band", "curvature_band", "depth_proxy_band"):
                if getattr(self, f) is not None:
                    raise PalmContractError(
                        f"{self.name}: present=False 인데 {f} 가 채워져 있다. "
                        f"없는 선의 값을 지어내지 않는다.")
            return
        for f, allowed in _BAND_SETS.items():
            v = getattr(self, f)
            if v is None:
                raise PalmContractError(f"{self.name}: {f} 가 비어 있다 (present=True)")
            if v not in allowed:
                raise PalmContractError(
                    f"{self.name}.{f} = '{v}' 는 허용된 밴드가 아니다. {allowed}")
        for f in ("breaks", "branches"):
            v = getattr(self, f)
            if v is not None and v < 0:
                raise PalmContractError(f"{self.name}.{f} 가 음수다: {v}")


@dataclass
class Quality:
    """촬영 품질. 이게 낮으면 아래 단계를 아예 돌리지 않는다."""
    score: float                 # 0~1
    is_palm_side: bool           # 손등을 찍으면 False. 상당수가 첫 시도에 손등을 찍는다
    issues: list[str] = field(default_factory=list)   # 사용자에게 보여줄 조치


@dataclass
class PalmFeatures:
    handedness: str              # "왼손" / "오른손"
    quality: Quality
    lines: dict[str, Line]
    simian: bool = False         # 막쥔손금
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        if self.handedness not in ("왼손", "오른손"):
            raise PalmContractError(f"handedness 는 왼손/오른손 이어야 한다: {self.handedness}")
        for key, line in self.lines.items():
            if key != line.name:
                raise PalmContractError(f"키 '{key}' 와 Line.name '{line.name}' 이 다르다")
        _assert_no_conclusions(self)


def _assert_no_conclusions(f: PalmFeatures) -> None:
    """측정값에 성격 단정이 섞여 들어오는 것을 막는다.

    이 가드가 이 파일의 핵심이다. 손금 문서의 L2 규칙 엔진은
    "감정선 종료점이 검지 아래 → 이상주의적" 형태였다. 그건 매핑이지 측정이 아니다.
    측정 계층은 잰 것만 담는다. 의미는 해석 계층이 붙인다.
    """
    for line in f.lines.values():
        for fld in ("length_band", "curvature_band", "depth_proxy_band"):
            v = getattr(line, fld)
            if v is None or v in _FEATURE_VALUE_ALLOWLIST:
                continue
            for bad in FORBIDDEN_IN_FEATURES:
                if bad in v:
                    raise PalmContractError(
                        f"{line.name}.{fld} = '{v}' 에 결론이 섞여 있다('{bad}'). "
                        f"손금 태그는 결론이 아니라 재료다. 측정값만 담아라.")


# ─────────────────────────────────────────────
# 판정 — 해석할 것인가, 다시 찍으라 할 것인가
# ─────────────────────────────────────────────
@dataclass
class Verdict:
    ok: bool
    reasons: list[str]           # 거절 사유
    actions: list[str]           # 사용자가 할 수 있는 것. 거절은 반드시 행동을 준다
    missing_lines: list[str]     # 못 읽은 주선


def decide(f: PalmFeatures) -> Verdict:
    """해석을 진행할지 판정한다.

    거절할 때는 **무엇을 하면 되는지** 함께 준다.
    "분석할 수 없습니다"만 주는 거절은 거절이 아니라 방치다.
    """
    reasons: list[str] = []
    actions: list[str] = []

    if not f.quality.is_palm_side:
        reasons.append("손등이 찍혔다")
        actions.append("손바닥이 보이도록 손을 뒤집어 다시 찍어주세요")

    if f.quality.score < MIN_IMAGE_QUALITY:
        reasons.append(f"사진 품질이 기준 미달 ({f.quality.score:.2f} < {MIN_IMAGE_QUALITY})")
        actions.extend(f.quality.issues or ["밝은 곳에서 손바닥을 펴고 다시 찍어주세요"])

    missing = []
    for name in MAIN_LINES:
        line = f.lines.get(name)
        if line is None or not line.present:
            missing.append(name)
        elif line.confidence < MIN_LINE_CONFIDENCE:
            missing.append(name)
            reasons.append(f"{name} 신뢰도 부족 ({line.confidence:.2f})")

    if missing:
        if not any("신뢰도" in r for r in reasons):
            reasons.append(f"주선을 읽지 못했다: {', '.join(missing)}")
        actions.append("손바닥을 완전히 펴고 그림자가 지지 않게 다시 찍어주세요")

    ok = not reasons
    # 중복 제거하되 순서는 유지한다
    return Verdict(ok=ok,
                   reasons=list(dict.fromkeys(reasons)),
                   actions=list(dict.fromkeys(actions)),
                   missing_lines=missing)


# ─────────────────────────────────────────────
# 결정론 — 같은 손이면 같은 결과
# ─────────────────────────────────────────────
def reading_key(f: PalmFeatures) -> str:
    """해석 캐시 키. **밴드만으로** 만든다.

    연속값이 들어가면 같은 손의 두 번째 사진이 다른 키를 만들고,
    사용자는 다른 운세를 본다. 그 순간 앱이 지워진다.
    confidence 도 넣지 않는다 — 같은 손인데 조명이 조금 달랐을 뿐이다.
    """
    parts = [f.schema_version, f.handedness, f"simian={int(f.simian)}"]
    for name in ALL_LINES:
        line = f.lines.get(name)
        if line is None or not line.present:
            parts.append(f"{name}:없음")
            continue
        parts.append(
            f"{name}:{line.length_band}/{line.curvature_band}/{line.depth_proxy_band}"
            f"/b{line.breaks or 0}/f{line.branches or 0}")
    raw = "|".join(parts)
    return "palm-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────
# LLM 에 넘기는 형태
# ─────────────────────────────────────────────
def to_prompt_block(f: PalmFeatures) -> str:
    """LLM 프롬프트에 그대로 끼우는 텍스트.

    사진은 넘어가지 않는다. 밴드와 유무만 넘어간다.
    """
    v = decide(f)
    if not v.ok:
        raise PalmContractError(
            "판정에서 거절된 측정값을 프롬프트로 만들 수 없다. "
            f"사유: {', '.join(v.reasons)}")

    lines = ["[손금 측정값 — 이 목록 밖의 것을 언급하지 마라]",
             f"  손: {f.handedness}"]
    for name in ALL_LINES:
        line = f.lines.get(name)
        if line is None or not line.present:
            lines.append(f"  · {name}: 관측되지 않음 — 없다고 쓰거나 언급하지 마라")
            continue
        extra = []
        if line.breaks:
            extra.append(f"끊김 {line.breaks}")
        if line.branches:
            extra.append(f"갈래 {line.branches}")
        tail = f" ({', '.join(extra)})" if extra else ""
        lines.append(
            f"  · {name}: 길이 {line.length_band} · 곡선 {line.curvature_band}"
            f" · 선명도 {line.depth_proxy_band}{tail}")
    if f.simian:
        lines.append("  · 막쥔손금(감정선과 두뇌선이 하나로 이어진 형태) 관측됨")

    lines += [
        "",
        "규칙:",
        "  - 위에 없는 선·특징을 만들어 언급하지 마라.",
        "  - 측정값을 성격으로 직접 매핑하지 마라",
        "    (\"감정선이 길다 → 정이 많다\" 같은 단정 금지). 재료로만 쓴다.",
        "  - 수명·질병·사망·결혼 시기·임신 등 예언이나 의료 판단을 하지 마라.",
        "  - 손금은 해석의 근거가 아니라 이야기의 입구다. 무게는 행동과 관계가 진다.",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 산출물 검증 — LLM 이 낸 문장을 되받아 검사한다
# ─────────────────────────────────────────────
BANNED_TERMS = (
    # 예언·단정
    "수명", "죽", "사망", "명이 짧", "요절",
    "반드시", "틀림없이", "확실히", "100%",
    # 의료
    "질병", "암", "진단", "치료", "완치", "발병",
    # 시기 단정
    "결혼할 나이", "이혼", "임신",
)


@dataclass
class Violation:
    kind: str      # "금칙어" | "근거없음"
    detail: str


def verify_output(text: str, f: PalmFeatures) -> list[Violation]:
    """LLM 문장을 검사한다. 위반이 있으면 그 문장을 내보내지 않는다.

    Structured Output 은 형태만 보장한다. 내용은 여기서 본다.
    면책 문구는 검사하지 않는다 — 앱이 locale 별 승인 문구로 마지막에 덮어쓴다.
    LLM 이 만든 면책 문구를 믿지 않는다.
    """
    out: list[Violation] = []

    for term in BANNED_TERMS:
        if term in text:
            out.append(Violation("금칙어", f"'{term}' 이(가) 포함됨"))

    # 관측되지 않은 선을 언급했는가
    for name in ALL_LINES:
        line = f.lines.get(name)
        if (line is None or not line.present) and name in text:
            out.append(Violation("근거없음", f"'{name}' 은 관측되지 않았는데 언급됨"))

    return out


if __name__ == "__main__":
    good = PalmFeatures(
        handedness="오른손",
        quality=Quality(score=0.82, is_palm_side=True),
        lines={
            "감정선": Line("감정선", True, 0.88, "김", "완만", "뚜렷", breaks=0, branches=2),
            "두뇌선": Line("두뇌선", True, 0.79, "보통", "직선형", "보통", breaks=1, branches=0),
            "생명선": Line("생명선", True, 0.91, "김", "깊은곡선", "뚜렷"),
            "운명선": Line("운명선", False, 0.31),
        })
    print(to_prompt_block(good))
    print("\n캐시 키:", reading_key(good))

    bad = PalmFeatures(
        handedness="왼손",
        quality=Quality(score=0.41, is_palm_side=False,
                        issues=["초점이 흐립니다", "손바닥에 그림자가 있습니다"]),
        lines={"감정선": Line("감정선", False, 0.22)})
    v = decide(bad)
    print("\n거절 사유:", v.reasons)
    print("안내:", v.actions)
