"""나라장터 입찰 자동화 - Streamlit 웹 대시보드"""

import os
import json
import glob
import subprocess
import threading
from datetime import datetime
from dotenv import load_dotenv

import streamlit as st

load_dotenv()

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="나라장터 입찰 자동화",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

IS_GITHUB = os.getenv("GITHUB_ACTIONS") == "true"
if IS_GITHUB:
    OUTPUT_DIR = "output"
else:
    OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "나라장터결과")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────
def load_latest_result() -> list:
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "recommended_bids_*.json")), reverse=True)
    if not files:
        return []
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)

def load_all_results() -> dict:
    """날짜별 결과 파일 목록"""
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "recommended_bids_*.json")), reverse=True)
    result = {}
    for f in files:
        date_str = os.path.basename(f).replace("recommended_bids_", "").replace(".json", "")
        try:
            date_label = datetime.strptime(date_str, "%Y%m%d").strftime("%Y년 %m월 %d일")
        except Exception:
            date_label = date_str
        result[date_label] = f
    return result

def load_log_today() -> str:
    log_file = os.path.join(OUTPUT_DIR, f"log_{datetime.now().strftime('%Y%m%d')}.txt")
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def price_str(val) -> str:
    try:
        return f"{int(float(str(val).replace(',', ''))):,}원"
    except Exception:
        return str(val)

def status_badge(status: str) -> str:
    colors = {"추천": "🟢", "보류": "🟡", "강력추천": "🔵"}
    return colors.get(status, "⚪")

# ─────────────────────────────────────────────
# 사이드바 네비게이션
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🏆 나라장터 자동화")
    st.caption("(주)미미 입찰 관리 시스템")
    st.divider()

    page = st.radio(
        "메뉴",
        ["📊 오늘의 공고", "📋 공고 상세 분석", "🚀 수동 실행", "⚙️ 설정", "📅 이력 조회"],
        label_visibility="collapsed",
    )

    st.divider()
    # 최신 결과 요약
    bids = load_latest_result()
    rec = [b for b in bids if b.get("평가", {}).get("추천여부") == "추천"]
    held = [b for b in bids if b.get("평가", {}).get("추천여부") == "보류"]
    st.metric("✅ 추천", f"{len(rec)}건")
    st.metric("⏸ 보류", f"{len(held)}건")
    if bids:
        files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "recommended_bids_*.json")), reverse=True)
        date_str = os.path.basename(files[0]).replace("recommended_bids_", "").replace(".json", "")
        try:
            st.caption(f"기준: {datetime.strptime(date_str, '%Y%m%d').strftime('%Y.%m.%d')}")
        except Exception:
            st.caption(f"기준: {date_str}")


# ─────────────────────────────────────────────
# 페이지 1: 오늘의 공고
# ─────────────────────────────────────────────
if page == "📊 오늘의 공고":
    st.title("📊 오늘의 공고 현황")

    if not bids:
        st.info("결과 파일이 없습니다. 수동 실행 또는 GitHub Actions 결과를 확인하세요.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 공고", f"{len(bids)}건")
        with col2:
            st.metric("✅ 추천", f"{len(rec)}건", delta="입찰 검토 필요")
        with col3:
            st.metric("⏸ 보류", f"{len(held)}건")

        # 추천 공고
        if rec:
            st.subheader("✅ 추천 공고")
            for bid in rec:
                eval_info = bid.get("평가", {})
                chk = bid.get("세밀점검", {})
                final_rec = chk.get("최종권고", "추천") if chk else "추천"

                with st.expander(
                    f"{status_badge(final_rec)} **{bid['공고명']}** — {price_str(bid.get('추정가격', 0))} | {bid['발주기관']}",
                    expanded=True,
                ):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"**발주기관:** {bid['발주기관']}")
                        st.write(f"**추정가격:** {price_str(bid.get('추정가격', 0))}")
                    with c2:
                        st.write(f"**마감일:** {bid.get('입찰마감일시', '정보없음')}")
                        st.write(f"**AI점수:** {eval_info.get('점수', 0)}점")
                    with c3:
                        url = bid.get("공고URL", "")
                        if url:
                            st.link_button("📎 공고 바로가기", url)

                    st.caption(f"**AI 판단:** {eval_info.get('이유', '')}")

                    # 입찰가 추천
                    rec_price = bid.get("입찰가추천", {})
                    if rec_price:
                        st.divider()
                        st.write("**💰 입찰가 추천**")
                        pc1, pc2, pc3 = st.columns(3)
                        with pc1:
                            st.metric("안정형", f"{rec_price.get('안정형입찰가', 0):,}원")
                        with pc2:
                            st.metric("중간형", f"{rec_price.get('중간형입찰가', 0):,}원")
                        with pc3:
                            st.metric("공격형", f"{rec_price.get('공격형입찰가', 0):,}원")
                        st.caption(f"근거: {rec_price.get('근거', '')}")

        # 보류 공고
        if held:
            st.subheader("⏸ 보류 공고")
            for bid in held:
                eval_info = bid.get("평가", {})
                st.write(f"• **{bid['공고명']}** ({bid['발주기관']}) — {price_str(bid.get('추정가격', 0))}")
                st.caption(f"  {eval_info.get('이유', '')}")


# ─────────────────────────────────────────────
# 페이지 2: 공고 상세 분석
# ─────────────────────────────────────────────
elif page == "📋 공고 상세 분석":
    st.title("📋 공고 세밀 점검")

    if not rec:
        st.info("추천 공고가 없습니다.")
    else:
        bid_names = [b["공고명"] for b in rec]
        selected = st.selectbox("공고 선택", bid_names)
        bid = next(b for b in rec if b["공고명"] == selected)
        eval_info = bid.get("평가", {})
        chk = bid.get("세밀점검", {})

        st.subheader(selected)
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**발주기관:** {bid['발주기관']}")
            st.write(f"**추정가격:** {price_str(bid.get('추정가격', 0))}")
            st.write(f"**계약방법:** {bid.get('계약방법', '정보없음')}")
        with col2:
            st.write(f"**입찰마감:** {bid.get('입찰마감일시', '정보없음')}")
            st.write(f"**AI점수:** {eval_info.get('점수', 0)}점")
            url = bid.get("공고URL", "")
            if url:
                st.link_button("📎 공고 원문", url)

        if chk:
            st.divider()
            rc_col, _ = st.columns([1, 3])
            with rc_col:
                final = chk.get("최종권고", "")
                color = {"강력추천": "🔵", "추천": "🟢", "신중검토": "🟡"}.get(final, "⚪")
                st.metric("최종권고", f"{color} {final}")

            # 체크리스트
            st.subheader("☑️ 체크리스트")
            checklist = chk.get("체크리스트", [])
            for item in checklist:
                state = item.get("상태", "")
                st.write(f"{state} **{item.get('항목', '')}** — {item.get('설명', '')}")

            # 자격요건
            qual = chk.get("자격요건", {})
            if qual:
                st.divider()
                st.subheader("📋 자격요건")
                q1, q2 = st.columns(2)
                with q1:
                    val = qual.get("장애인기업우선구매")
                    st.write(f"장애인기업 우선구매: {'✅ 해당' if val else '❌ 미해당'}")
                    st.write(f"지역 제한: {qual.get('지역제한', '없음')}")
                with q2:
                    st.write(f"자격증: {qual.get('자격증필요', '없음')}")
                    st.write(f"기업규모: {qual.get('기업규모제한', '없음')}")

            # 장단점
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("👍 장점")
                for item in chk.get("장점", []):
                    st.write(f"• {item}")
            with col_b:
                st.subheader("👎 단점")
                for item in chk.get("단점", []):
                    st.write(f"• {item}")

            # 주의사항
            if chk.get("주의사항"):
                st.divider()
                st.subheader("⚠️ 반드시 확인할 것")
                for item in chk.get("주의사항", []):
                    st.warning(item)

            # 입찰전략
            if chk.get("입찰전략"):
                st.divider()
                st.subheader("💡 입찰 전략")
                st.info(chk["입찰전략"])

        else:
            st.info("세밀 점검 데이터가 없습니다. 다음 실행 시 생성됩니다.")

        # 입찰가 추천
        rec_price = bid.get("입찰가추천", {})
        if rec_price:
            st.divider()
            st.subheader("💰 입찰가 추천")
            p1, p2, p3 = st.columns(3)
            with p1:
                st.metric("안정형 (낙찰 가능성 높음)", f"{rec_price.get('안정형입찰가', 0):,}원")
            with p2:
                st.metric("중간형 (균형)", f"{rec_price.get('중간형입찰가', 0):,}원")
            with p3:
                st.metric("공격형 (마진 최대)", f"{rec_price.get('공격형입찰가', 0):,}원")
            st.caption(f"📊 근거: {rec_price.get('근거', '')}")


# ─────────────────────────────────────────────
# 페이지 3: 수동 실행
# ─────────────────────────────────────────────
elif page == "🚀 수동 실행":
    st.title("🚀 공고 수집 수동 실행")

    st.info("이 버튼을 누르면 나라장터 공고 수집부터 이메일 발송까지 전체 파이프라인이 실행됩니다.")

    # API 키 상태 확인
    st.subheader("🔑 API 키 상태")
    keys = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "NARA_API_KEY": os.getenv("NARA_API_KEY"),
        "GMAIL_PASSWORD": os.getenv("GMAIL_PASSWORD"),
        "NAVER_CLIENT_ID": os.getenv("NAVER_CLIENT_ID"),
    }
    k1, k2, k3, k4 = st.columns(4)
    for col, (key, val) in zip([k1, k2, k3, k4], keys.items()):
        with col:
            label = key.replace("_", " ").title()
            st.metric(label, "✅ 설정됨" if val else "❌ 미설정")

    st.divider()

    if "running" not in st.session_state:
        st.session_state.running = False
    if "log_output" not in st.session_state:
        st.session_state.log_output = ""

    if st.button("▶️ 지금 실행", type="primary", disabled=st.session_state.running):
        st.session_state.running = True
        st.session_state.log_output = "실행 중...\n"
        st.rerun()

    if st.session_state.running:
        with st.spinner("실행 중... (2~5분 소요)"):
            try:
                result = subprocess.run(
                    ["python", "-X", "utf8", "run_collection.py"],
                    capture_output=True, text=True, timeout=600,
                    encoding="utf-8", errors="replace",
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                st.session_state.log_output = (result.stdout or "") + ("\n[STDERR]\n" + result.stderr if result.stderr else "")
                st.session_state.running = False
                if result.returncode == 0:
                    st.success("✅ 실행 완료!")
                else:
                    st.error("❌ 실행 중 오류 발생")
            except subprocess.TimeoutExpired:
                st.session_state.log_output = "시간 초과 (10분)"
                st.session_state.running = False
                st.error("시간 초과")
            st.rerun()

    if st.session_state.log_output and not st.session_state.running:
        st.subheader("📄 실행 로그")
        st.code(st.session_state.log_output, language="text")

    # 오늘 로그
    today_log = load_log_today()
    if today_log:
        st.divider()
        st.subheader("📄 오늘 자동 실행 로그")
        st.code(today_log[-3000:] if len(today_log) > 3000 else today_log, language="text")


# ─────────────────────────────────────────────
# 페이지 4: 설정
# ─────────────────────────────────────────────
elif page == "⚙️ 설정":
    st.title("⚙️ 회사 설정")

    # 현재 설정 읽기
    config_file = os.path.join(OUTPUT_DIR, "company_config.json")
    default_config = {
        "company_name": "(주)미미",
        "rep_name": "",
        "phone": "",
        "address": "",
        "email": os.getenv("NOTIFY_EMAIL", ""),
        "qualifications": ["장애인기업", "예비사회적기업"],
        "categories": [
            "사무소모품 (A4용지, 복사용지, 토너)",
            "생활·위생용품 (화장지, 세정제, 방역소모품)",
            "에어컨·냉난방기 세척",
            "홍보용 인쇄물 (현수막, 브로슈어, 리플렛)",
        ],
        "suui_limit": 20000000,
        "margin_rate": 20,
        "keywords": ["A4용지", "복사용지", "토너", "화장지", "세정제", "방역", "홍보물", "현수막", "에어컨세척"],
    }
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = {**default_config, **json.load(f)}
    else:
        config = default_config

    with st.form("company_form"):
        st.subheader("🏢 기본 정보")
        c1, c2 = st.columns(2)
        with c1:
            company_name = st.text_input("회사명", value=config["company_name"])
            rep_name = st.text_input("대표자명", value=config.get("rep_name", ""))
        with c2:
            phone = st.text_input("연락처", value=config.get("phone", ""))
            notify_email = st.text_input("결과 수신 이메일", value=config.get("email", ""))

        address = st.text_input("주소", value=config.get("address", ""))

        st.subheader("🏷️ 자격 / 업종")
        qualifications = st.text_area(
            "보유 자격 (한 줄에 하나)",
            value="\n".join(config.get("qualifications", [])),
        )
        categories = st.text_area(
            "취급 업종/품목 (한 줄에 하나)",
            value="\n".join(config.get("categories", [])),
        )
        keywords = st.text_area(
            "수집 키워드 (한 줄에 하나)",
            value="\n".join(config.get("keywords", [])),
        )

        st.subheader("💰 입찰 기준")
        c3, c4 = st.columns(2)
        with c3:
            suui_limit = st.number_input(
                "수의계약 금액 기준 (원)",
                value=config.get("suui_limit", 20000000),
                step=1000000, format="%d",
            )
        with c4:
            margin_rate = st.number_input(
                "기본 마진율 (%)",
                value=config.get("margin_rate", 20),
                min_value=5, max_value=50,
            )

        submitted = st.form_submit_button("💾 저장", type="primary")

    if submitted:
        new_config = {
            "company_name": company_name,
            "rep_name": rep_name,
            "phone": phone,
            "address": address,
            "email": notify_email,
            "qualifications": [q.strip() for q in qualifications.splitlines() if q.strip()],
            "categories": [c.strip() for c in categories.splitlines() if c.strip()],
            "keywords": [k.strip() for k in keywords.splitlines() if k.strip()],
            "suui_limit": int(suui_limit),
            "margin_rate": int(margin_rate),
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(new_config, f, ensure_ascii=False, indent=2)
        st.success("✅ 저장 완료! 다음 실행부터 반영됩니다.")
        st.info("⚠️ 키워드 변경은 코드에도 반영하려면 `nara_collector.py`와 `nara_filter.py`를 직접 수정하거나 개발자에게 요청하세요.")


# ─────────────────────────────────────────────
# 페이지 5: 이력 조회
# ─────────────────────────────────────────────
elif page == "📅 이력 조회":
    st.title("📅 과거 수집 이력")

    all_results = load_all_results()

    if not all_results:
        st.info("저장된 이력이 없습니다.")
    else:
        selected_date = st.selectbox("날짜 선택", list(all_results.keys()))
        filepath = all_results[selected_date]

        with open(filepath, "r", encoding="utf-8") as f:
            history_bids = json.load(f)

        h_rec = [b for b in history_bids if b.get("평가", {}).get("추천여부") == "추천"]
        h_held = [b for b in history_bids if b.get("평가", {}).get("추천여부") == "보류"]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 공고", f"{len(history_bids)}건")
        with col2:
            st.metric("✅ 추천", f"{len(h_rec)}건")
        with col3:
            st.metric("⏸ 보류", f"{len(h_held)}건")

        st.divider()

        if h_rec:
            st.subheader("✅ 추천 공고")
            for bid in h_rec:
                eval_info = bid.get("평가", {})
                st.write(f"**{bid['공고명']}** | {bid['발주기관']} | {price_str(bid.get('추정가격', 0))}")
                st.caption(f"점수: {eval_info.get('점수', 0)}점 | {eval_info.get('이유', '')}")
                url = bid.get("공고URL", "")
                if url:
                    st.link_button("📎 공고 링크", url, key=f"link_{bid.get('공고번호','')}")
                st.divider()

        if h_held:
            with st.expander(f"⏸ 보류 공고 {len(h_held)}건"):
                for bid in h_held:
                    st.write(f"• {bid['공고명']} ({bid['발주기관']})")
