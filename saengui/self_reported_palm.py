"""손금 — **사람이 직접 고른 판**(ⓑ). 측정값이 아니다.

설계: `saengui/01_사진없는판_설계.md` (2026-09-09) · 구현 2026-09-13.

────────────────────────────────────────────────────────────
왜 `PalmFeatures` 를 재사용하지 않는가

`PalmFeatures` 는 **CV 측정 결과**를 담는 그릇이다. 사람이 고른 값을
같은 그릇에 담으면 **나중에 어느 것이 측정이고 어느 것이 자기보고인지
구분이 안 된다.** 그래서 그릇을 나눈다.

  · `confidence` 를 담지 않는다 — 사람이 낼 수 없는 값이다.
    고정값 0.8 을 넣으면 거절 임계 0.60 을 **항상** 넘어,
    막으려고 만든 문이 아무것도 안 막는 문이 된다.
  · `breaks` / `branches` 를 담지 않는다 — persistent 릿지는 사람이 못 센다.
  · `Quality` 를 담지 않는다 — 사진이 없다.

**없는 필드를 0 이나 기본값으로 채우지 않는다. 아예 없다.**

────────────────────────────────────────────────────────────
접근성 — 이건 대체품이 아니다

사진을 못 찍는 사람이 있다. 손이 떨리는 사람, 한 손만 쓰는 사람,
그리고 자기 손 사진을 잘 찍기 어려운 시각장애인.

  > "시각장애인도 돈을 벌고 싶고 경제 상식을 알아야 한다.
  >  복지의 틀 안에만 가두면 안 된다." (시저님)

**ⓑ 는 CV 가 서고 나서도 남는다. 또 하나의 문이다.**
그래서 이 파일의 문답(`QUESTIONS`)은 **소리로 읽어도 되는 문장**으로 쓴다.
"아래 그림에서 고르세요"가 아니라 "손목까지 길게 내려오나요?"

────────────────────────────────────────────────────────────
무게는 낮추지 않는다. 대신 밝힌다

`weights.py` 의 타고난 지표 5% 를 3% 로 깎아봐야 읽는 사람은 모른다.
그러나 *"본인이 고른 것"* 이라는 한 줄은 **바로 안다.**

**숫자를 조용히 깎는 것보다 출처를 크게 밝히는 편이 정직하다.**
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from palm_features import (
    ALL_LINES, MAIN_LINES,
    LENGTH_BANDS, CURVATURE_BANDS, DEPTH_PROXY_BANDS,
    FORBIDDEN_IN_FEATURES,
    PalmContractError,
)

SCHEMA_VERSION = "palm-self-1"

# 측정판과 같은 밴드를 쓴다 — 나중에 둘을 견주려면 눈금이 같아야 한다.
_BAND_SETS = {
    "length_band": LENGTH_BANDS,
    "curvature_band": CURVATURE_BANDS,
    "depth_proxy_band": DEPTH_PROXY_BANDS,
}
_ALLOWLIST = set(LENGTH_BANDS) | set(CURVATURE_BANDS) | set(DEPTH_PROXY_BANDS)


# ─────────────────────────────────────────────
# 문답 — 소리로 읽어도 되는 문장이어야 한다
# ─────────────────────────────────────────────
QUESTIONS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "감정선": {
        "present": [("보인다", "네"), ("모르겠다", "아니오 · 잘 모르겠다")],
        "length_band": [
            ("짧음", "새끼손가락 쪽에서 시작해 중지 아래에 못 미치고 멈추나요"),
            ("보통", "중지와 검지 사이쯤에서 멈추나요"),
            ("김",   "검지 아래까지, 또는 손 반대편까지 길게 가나요"),
        ],
        "curvature_band": [
            ("직선형",   "거의 곧게 뻗나요"),
            ("완만",     "조금 휘나요"),
            ("깊은곡선", "위로 크게 휘어 올라가나요"),
        ],
        "depth_proxy_band": [
            ("옅음",   "희미해서 잘 안 보이나요"),
            ("보통",   "보통이나요"),
            ("뚜렷",   "또렷하게 파여 보이나요"),
        ],
    },
    "두뇌선": {
        "present": [("보인다", "네"), ("모르겠다", "아니오 · 잘 모르겠다")],
        "length_band": [
            ("짧음", "손바닥 절반에 못 미치고 멈추나요"),
            ("보통", "손바닥 한가운데쯤까지 가나요"),
            ("김",   "손바닥을 가로질러 반대편 가까이까지 가나요"),
        ],
        "curvature_band": [
            ("직선형",   "거의 곧게 가로지르나요"),
            ("완만",     "끝이 살짝 아래로 처지나요"),
            ("깊은곡선", "손목 쪽으로 뚜렷하게 휘어 내려가나요"),
        ],
        "depth_proxy_band": [
            ("옅음", "희미한가요"), ("보통", "보통인가요"), ("뚜렷", "또렷한가요"),
        ],
    },
    "생명선": {
        "present": [("보인다", "네"), ("모르겠다", "아니오 · 잘 모르겠다")],
        "length_band": [
            ("짧음", "중간쯤에서 흐려지거나 멈추나요"),
            ("보통", "손바닥 아래쪽까지 내려오나요"),
            ("김",   "손목 가까이까지 길게 내려오나요"),
        ],
        "curvature_band": [
            ("직선형",   "엄지 쪽에 바짝 붙어 곧게 내려오나요"),
            ("완만",     "조금 둥글게 감싸나요"),
            ("깊은곡선", "엄지 아래를 크게 감싸며 둥글게 내려오나요"),
        ],
        "depth_proxy_band": [
            ("옅음", "희미한가요"), ("보통", "보통인가요"), ("뚜렷", "또렷한가요"),
        ],
    },
    "운명선": {
        "present": [("보인다", "손목에서 가운뎃손가락 쪽으로 세로로 올라가는 선이 보이나요"),
                    ("모르겠다", "없거나 잘 모르겠다")],
        "length_band": [
            ("짧음", "손바닥 아래쪽에서 멈추나요"),
            ("보통", "손바닥 한가운데까지 오나요"),
            ("김",   "가운뎃손가락 아래까지 올라가나요"),
        ],
        "curvature_band": [
            ("직선형", "곧게 올라가나요"), ("완만", "조금 기우나요"),
            ("깊은곡선", "뚜렷하게 휘나요"),
        ],
        "depth_proxy_band": [
            ("옅음", "희미한가요"), ("보통", "보통인가요"), ("뚜렷", "또렷한가요"),
        ],
    },
}


@dataclass
class SelfLine:
    """사람이 고른 선 하나. **confidence 도 breaks/branches 도 없다.**"""
    name: str
    present: bool
    length_band: str | None = None
    curvature_band: str | None = None
    depth_proxy_band: str | None = None

    def __post_init__(self):
        if self.name not in ALL_LINES:
            raise PalmContractError(
                f"'{self.name}' 은 정의된 선이 아니다. {ALL_LINES} 중 하나여야 한다.")
        if not self.present:
            # 「모르겠다」에 밴드를 채워 넣지 않는다. 모르면 비운다.
            for f in _BAND_SETS:
                if getattr(self, f) is not None:
                    raise PalmContractError(
                        f"{self.name}: present=False 인데 {f} 가 채워져 있다. "
                        f"모른다고 한 선의 값을 지어내지 않는다.")
            return
        for f, allowed in _BAND_SETS.items():
            v = getattr(self, f)
            if v is None:
                raise PalmContractError(f"{self.name}: {f} 가 비어 있다 (present=True)")
            if v not in allowed:
                raise PalmContractError(
                    f"{self.name}.{f} = '{v}' 는 허용된 밴드가 아니다. {allowed}")


@dataclass
class SelfReportedPalm:
    """사람이 직접 고른 손금. **측정값이 아니다.**"""
    handedness: str
    lines: dict[str, SelfLine]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        if self.handedness not in ("왼손", "오른손"):
            raise PalmContractError(f"handedness 는 왼손/오른손 이어야 한다: {self.handedness}")
        for key, line in self.lines.items():
            if key != line.name:
                raise PalmContractError(f"키 '{key}' 와 SelfLine.name '{line.name}' 이 다르다")
        _assert_no_conclusions(self)


def _assert_no_conclusions(p: SelfReportedPalm) -> None:
    """결론이 섞여 들어오는 것을 막는다 — 측정판과 같은 가드.

    지금은 3택이라 자유 입력이 없지만, 나중에 "기타" 칸이 붙으면
    바로 여기로 들어온다. 가드를 먼저 세워 둔다.
    """
    for line in p.lines.values():
        for fld in _BAND_SETS:
            v = getattr(line, fld)
            if v is None or v in _ALLOWLIST:
                continue
            for bad in FORBIDDEN_IN_FEATURES:
                if bad in v:
                    raise PalmContractError(
                        f"{line.name}.{fld} = '{v}' 에 결론이 섞여 있다('{bad}'). "
                        f"손금 태그는 결론이 아니라 재료다.")


# ─────────────────────────────────────────────
# 판정 — 사진이 없으니 품질 거절은 없다. 그러나 주선 규칙은 그대로다
# ─────────────────────────────────────────────
@dataclass
class SelfVerdict:
    ok: bool
    reasons: list[str]
    actions: list[str]
    missing_lines: list[str]


def decide(p: SelfReportedPalm) -> SelfVerdict:
    """해석을 진행할지 판정한다.

    측정판의 품질 게이트는 여기 없다 — **사진이 없으므로 잴 것이 없다.**
    없는 게이트를 흉내 내지 않는다. 대신 **주선 규칙은 그대로 산다.**

    거절할 때는 무엇을 하면 되는지 함께 준다.
    """
    missing = [n for n in MAIN_LINES
               if n not in p.lines or not p.lines[n].present]
    reasons: list[str] = []
    actions: list[str] = []

    if len(missing) == len(MAIN_LINES):
        reasons.append("주선 세 개를 하나도 못 고르셨습니다")
        actions.append("손바닥을 밝은 곳에서 펴고, 가장 굵고 긴 선 하나부터 찾아보세요")
        actions.append("세 선 중 하나만 고르셔도 시작할 수 있습니다")
    elif missing:
        # 일부만 없는 것은 거절 사유가 아니다. 없다고 적고 간다.
        actions.append("못 고르신 선(" + " · ".join(missing) + ")은 해석에서 빠집니다")

    return SelfVerdict(ok=not reasons, reasons=reasons,
                       actions=actions, missing_lines=missing)


# ─────────────────────────────────────────────
# 프롬프트 — 출처를 반드시 소리내어 밝힌다
# ─────────────────────────────────────────────
SOURCE_NOTICE = (
    "이 손금 정보는 본인이 직접 고른 것이며, 측정된 값이 아닙니다.\n"
    "끊김·갈래는 포함되어 있지 않습니다."
)


def to_prompt_block(p: SelfReportedPalm) -> str:
    """LLM 에게 넘길 블록. **거절된 입력은 여기까지 오지 못한다.**"""
    v = decide(p)
    if not v.ok:
        raise PalmContractError(
            "거절된 입력으로 프롬프트를 만들지 않는다: " + " / ".join(v.reasons))

    out = ["[손금 — 본인이 고른 값. 이 목록 밖의 것을 언급하지 마라]",
           f"  손: {p.handedness}"]
    for name in ALL_LINES:
        line = p.lines.get(name)
        if line is None or not line.present:
            out.append(f"  · {name}: 고르지 않음 — 없다고 쓰거나 언급하지 마라")
            continue
        out.append(f"  · {name}: 길이 {line.length_band} · 곡선 {line.curvature_band}"
                   f" · 선명도 {line.depth_proxy_band}")

    out += [
        "",
        "출처:",
        "  " + SOURCE_NOTICE.replace("\n", "\n  "),
        "",
        "규칙:",
        "  - 위에 없는 선·특징을 만들어 언급하지 마라.",
        "  - 끊김·갈래를 언급하지 마라 — 이 판에는 그 값이 없다.",
        "  - 측정값을 성격으로 직접 매핑하지 마라",
        '    ("감정선이 길다 → 정이 많다" 같은 단정 금지). 재료로만 쓴다.',
        "  - 수명·질병·사망·결혼 시기·임신 등 예언이나 의료 판단을 하지 마라.",
        "  - 손금은 해석의 근거가 아니라 이야기의 입구다. 무게는 행동과 관계가 진다.",
    ]
    return "\n".join(out)


def reading_key(p: SelfReportedPalm) -> str:
    """캐시 키.

    ★ 접두사가 측정판과 **달라야 한다.** 같은 밴드 조합이면 측정판과
    자기보고판이 같은 키를 내고, 그러면 캐시가 섞여 **자기보고 리포트가
    측정 리포트 자리로 나올 수 있다.** 출처를 키에 넣어 막는다.
    """
    bits = [SCHEMA_VERSION, p.handedness]
    for name in ALL_LINES:
        line = p.lines.get(name)
        if line is None or not line.present:
            bits.append(f"{name}:x")
            continue
        bits.append(f"{name}:{line.length_band}/{line.curvature_band}"
                    f"/{line.depth_proxy_band}")
    return "palm-self:" + hashlib.sha256("|".join(bits).encode()).hexdigest()[:16]


def verify_output(text: str, p: SelfReportedPalm) -> list[str]:
    """출력 검사 — 측정판 `verify_output` 에 **이 판만의 두 가지**를 더한다.

    ① 고르지 않은 선을 언급하면 잡는다 (측정판과 같은 규율)
    ② ★ 끊김·갈래를 언급하면 잡는다 — 이 판에는 그 값이 **아예 없다**
    """
    import palm_features as PF

    # 측정판 검사기를 그대로 쓰기 위해 최소한의 어댑터를 만든다.
    # confidence 는 검사에 안 쓰이므로 1.0 을 넣되, 이 값은 **밖으로 나가지 않는다.**
    adapted_lines = {}
    for name in ALL_LINES:
        line = p.lines.get(name)
        if line is None or not line.present:
            adapted_lines[name] = PF.Line(name=name, present=False, confidence=1.0)
        else:
            adapted_lines[name] = PF.Line(
                name=name, present=True, confidence=1.0,
                length_band=line.length_band,
                curvature_band=line.curvature_band,
                depth_proxy_band=line.depth_proxy_band)
    shim = PF.PalmFeatures(
        handedness=p.handedness,
        quality=PF.Quality(score=1.0, is_palm_side=True),
        lines=adapted_lines)

    out = [f"{v.kind}: {v.detail}" for v in PF.verify_output(text, shim)]

    for word in ("끊김", "갈래", "끊어져", "갈라져"):
        if word in text:
            out.append(f"없는재료: '{word}' — 자기보고 판에는 끊김·갈래 값이 없다")
    return out
