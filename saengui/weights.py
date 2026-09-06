"""생의 무늬 — 해석 가중치의 단일 진실 원천.

이 파일은 VPS `/opt/data/saengui-munui/backend/engines/weights.py` 로 배치된다.
가중치를 바꾸려면 여기를 바꾸고 다시 옮긴다. 다른 곳에 숫자를 적지 않는다.

────────────────────────────────────────────────────────────
왜 표를 둘로 나눴는가

이전 표는 이랬다:  행동 45 + 맥락 30 + MBTI 20 + 사주 5

숫자가 틀린 게 아니라 표의 구조가 틀렸다. 성격이 다른 것들이 한 표에 섞여 있었다.

  · 행동과 맥락은 **근거**다. 사용자가 실제로 한 일이고 지금 처한 상황이다.
  · MBTI와 주역은 근거가 아니라 **말하는 방식**이다.
    MBTI는 그 사람이 자기를 어떤 언어로 설명하는지고,
    주역은 이 이야기를 64가지 상황 중 어느 형태로 들려줄지다.
    둘 다 "무엇이 사실인가"에 기여하지 않는다.

기여하지 않는 것에 가중치를 주면 비중 싸움이 된다.
그리고 "주역이 몇 퍼센트 맞았나" 같은, 답할 수 없는 질문이 생긴다.

그래서 가중치는 증거에만 붙인다(EVIDENCE_WEIGHTS).
말하는 방식은 가중치 없이 역할만 갖는다(FORM_LAYERS).

형식 층으로 내려가면 역할이 줄지 않는다. 오히려 커진다 —
주역은 모든 리포트의 뼈대가 되고, MBTI는 모든 문장의 톤이 된다.
────────────────────────────────────────────────────────────
"""

from __future__ import annotations


# ─────────────────────────────────────────────
# ① 증거 축 — 해석의 근거. 합 100.
# ─────────────────────────────────────────────
EVIDENCE_WEIGHTS: dict[str, int] = {
    # 사용자가 실제로 한 것·기록한 것. 가장 무겁다.
    "행동": 40,          # 이전 45
    # 타인과의 생(生)·극(剋)·합(合)·충(沖). 이번에 신설된 축.
    # 인생을 흔드는 변수는 혼자짜리 속성이 아니라 주고받음이다.
    "관계": 25,          # 신설
    # 지금의 상황·감정·관심 주제.
    "맥락": 25,          # 이전 30
    # 타고난 것·고정된 것·검증 불가한 것. 사주 5 + 손금 5.
    # 사주와 손금은 같은 종류다. 따로 다투게 두지 않고 한 칸에 넣는다.
    "타고난지표": 10,     # 이전 사주 단독 5
}

# 타고난지표 칸의 내부 배분. 리포트에 근거를 밝힐 때 쓴다.
INNATE_SPLIT: dict[str, int] = {"사주명식": 5, "손금측정": 5}


# ─────────────────────────────────────────────
# ② 형식 층 — 말하는 방식. 가중치 없음.
# ─────────────────────────────────────────────
FORM_LAYERS: dict[str, str] = {
    "주역64괘": "이 상황이 어느 괘에 닮았는가 → 리포트의 서사 골격",
    "MBTI": "자기서술 → 어휘와 톤 조정",
    "손금오버레이": "내 손 사진 위의 내 선 → 물증·개인화 지각(신뢰)",
}

# 증거 축에 절대 들어와서는 안 되는 이름들.
# 여기 있는 말이 EVIDENCE_WEIGHTS 의 키에 나타나면 import 시점에 터진다.
# 조용히 섞이는 것을 막는 것이 이 목록의 유일한 목적이다.
FORBIDDEN_IN_EVIDENCE = (
    "mbti", "엠비티아이",
    "주역", "iching", "i-ching", "괘", "팔괘", "64괘",
)


class WeightConfigError(ValueError):
    """가중치 표가 규칙을 어겼다. 앱을 띄우지 않는다."""


def _validate() -> None:
    """import 시점에 검사한다. 틀린 표로 리포트가 나가는 것보다 안 뜨는 게 낫다."""
    total = sum(EVIDENCE_WEIGHTS.values())
    if total != 100:
        raise WeightConfigError(
            f"증거 축 합이 100이 아니다: {total} ({EVIDENCE_WEIGHTS})"
        )

    for key in EVIDENCE_WEIGHTS:
        low = key.lower().replace(" ", "")
        for banned in FORBIDDEN_IN_EVIDENCE:
            if banned in low:
                raise WeightConfigError(
                    f"'{key}' 는 증거가 아니라 형식이다. "
                    f"EVIDENCE_WEIGHTS 에서 빼고 FORM_LAYERS 로 옮겨라. "
                    f"(걸린 말: '{banned}')"
                )

    if any(v <= 0 for v in EVIDENCE_WEIGHTS.values()):
        raise WeightConfigError(f"0 이하 가중치가 있다: {EVIDENCE_WEIGHTS}")

    innate = sum(INNATE_SPLIT.values())
    if innate != EVIDENCE_WEIGHTS["타고난지표"]:
        raise WeightConfigError(
            f"타고난지표 내부 배분 합({innate})이 축 가중치"
            f"({EVIDENCE_WEIGHTS['타고난지표']})와 다르다"
        )


_validate()


# ─────────────────────────────────────────────
# 축이 비었을 때
# ─────────────────────────────────────────────
def resolve(available: set[str] | list[str]) -> tuple[dict[str, float], list[str]]:
    """실제로 데이터가 있는 축만으로 가중치를 다시 정규화한다.

    관계 축은 신설이라 초기 사용자에게는 데이터가 없다. 그럴 때 25%를
    허공에 두면 나머지 축의 실제 비중이 조용히 달라진다.

    그래서 남은 축에 비례 배분하되, **무엇이 빠졌는지 함께 돌려준다.**
    호출자는 이 목록을 리포트 근거란에 그대로 남겨야 한다.
    조용히 채우면 "왜 이 해석이 나왔는지"를 나중에 설명할 수 없다.

    Returns:
        (정규화된 가중치, 빠진 축 이름 목록)
    """
    have = {k for k in available if k in EVIDENCE_WEIGHTS}
    missing = [k for k in EVIDENCE_WEIGHTS if k not in have]

    if not have:
        raise WeightConfigError(
            "증거 축이 하나도 없다. 이 상태로는 해석하지 않는다. "
            "행동·관계·맥락·타고난지표 중 최소 하나는 있어야 한다."
        )

    base = sum(EVIDENCE_WEIGHTS[k] for k in have)
    resolved = {k: round(EVIDENCE_WEIGHTS[k] * 100 / base, 1) for k in have}

    # 반올림 잔차를 가장 큰 축에 몰아 합을 정확히 100으로 맞춘다.
    drift = round(100 - sum(resolved.values()), 1)
    if drift:
        top = max(resolved, key=lambda k: resolved[k])
        resolved[top] = round(resolved[top] + drift, 1)

    return resolved, missing


# ─────────────────────────────────────────────
# LLM 프롬프트 조각
# ─────────────────────────────────────────────
def prompt_block(available: set[str] | list[str] | None = None) -> str:
    """llm_writer 가 프롬프트에 그대로 끼워 넣는 텍스트를 만든다.

    숫자를 프롬프트에 손으로 적지 않는다. 두 곳에 적힌 숫자는 반드시 갈라진다.
    """
    if available is None:
        weights, missing = dict(EVIDENCE_WEIGHTS), []
    else:
        weights, missing = resolve(available)

    lines = ["[해석 가중치 — 증거 축]"]
    for k, v in weights.items():
        note = ""
        if k == "타고난지표":
            inner = " + ".join(f"{a} {b}%" for a, b in INNATE_SPLIT.items())
            note = f"  ({inner})"
        lines.append(f"  · {k}: {v}%{note}")

    if missing:
        lines.append("")
        lines.append("[데이터가 없어 제외된 축 — 리포트 근거란에 그대로 밝힐 것]")
        for k in missing:
            lines.append(f"  · {k} (원래 {EVIDENCE_WEIGHTS[k]}%)")
        lines.append("  ※ 빠진 축의 내용을 추측해서 채우지 마라. 없는 것은 없다고 쓴다.")

    lines += [
        "",
        "[형식 층 — 가중치 없음. 무엇이 사실인지에 관여하지 않는다]",
    ]
    for k, role in FORM_LAYERS.items():
        lines.append(f"  · {k}: {role}")

    lines += [
        "",
        "규칙:",
        "  - 위 증거 축의 비중대로 분량과 강조를 배분한다.",
        "  - 형식 층은 '어떻게 말할지'만 정한다. 사실 판단의 근거로 쓰지 마라.",
        "  - 오행·손금 태그를 성격으로 직접 매핑하지 마라.",
        "    (\"목이 많으면 성장형이다\" 금지 — 상징 언어일 뿐이다)",
        "  - 새 정보를 만들지 마라. 주어진 재료 밖으로 나가지 않는다.",
    ]
    return "\n".join(lines)


def cache_key() -> str:
    """가중치가 바뀌면 캐시가 무효화되도록 하는 키.

    표를 고쳐놓고 예전 리포트가 계속 나오는 것이 가장 찾기 어려운 실패다.
    """
    parts = [f"{k}{v}" for k, v in sorted(EVIDENCE_WEIGHTS.items())]
    parts += [f"{k}{v}" for k, v in sorted(INNATE_SPLIT.items())]
    parts += sorted(FORM_LAYERS)
    return "w:" + "-".join(parts)


if __name__ == "__main__":
    print(prompt_block())
    print()
    print("전체 축:", EVIDENCE_WEIGHTS, "합", sum(EVIDENCE_WEIGHTS.values()))
    print("캐시 키:", cache_key())
    print()
    w, m = resolve({"행동", "맥락", "타고난지표"})
    print("관계 데이터가 없을 때:", w, "합", round(sum(w.values()), 1), "/ 빠짐", m)
