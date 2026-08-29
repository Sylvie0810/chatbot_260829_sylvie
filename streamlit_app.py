from datetime import datetime

import streamlit as st
from openai import OpenAI


# ============================================================
# 1. PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="GrantMate | 공공데이터 사업계획서 AI Coach",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. STYLE
# ============================================================

# 복잡한 HTML UI는 사용하지 않습니다.
# CSS는 레이아웃/간격/기본 스타일 보완에만 사용합니다.

st.markdown(
    """
    <style>

    /* 메인 영역 */
    .block-container {
        max-width: 1120px;
        padding-top: 4.5rem !important;
        padding-bottom: 6rem !important;
    }

    /* Streamlit 상단 헤더 */
    [data-testid="stHeader"] {
        background: rgba(255, 255, 255, 0.97);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f7f8fb;
        border-right: 1px solid #e7e9ee;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.8rem;
    }

    /* Form */
    div[data-testid="stForm"] {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1rem 1rem 0.5rem 1rem;
    }

    /* Chat */
    div[data-testid="stChatMessage"] {
        border: 1px solid #eceef2;
        border-radius: 14px;
        padding: 0.35rem 0.6rem;
        margin-bottom: 0.55rem;
    }

    /* Buttons */
    .stButton > button,
    .stFormSubmitButton > button,
    .stDownloadButton > button {
        border-radius: 10px;
        min-height: 42px;
        font-weight: 650;
    }

    /* Inputs */
    .stTextInput input,
    .stTextArea textarea {
        border-radius: 9px;
    }

    /* 모바일 */
    @media (max-width: 700px) {
        .block-container {
            padding-top: 4rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. HELPERS
# ============================================================

def get_secret(name, default=""):
    """
    Streamlit Secrets가 없더라도 앱이 죽지 않도록 안전하게 읽습니다.
    """
    try:
        return st.secrets[name]
    except Exception:
        return default


def profile_to_text(profile):
    """
    사용자가 입력한 사업 정보를 AI용 텍스트로 변환합니다.
    """

    labels = {
        "company_name": "기업명",
        "stage": "현재 단계",
        "business_item": "사업 아이템",
        "problem": "해결하려는 문제",
        "development": "현재 개발단계 / 보유 기능",
        "needed_data": "필요한 공공데이터",
        "needed_fields": "필요 데이터 항목",
        "data_holder": "예상 데이터 보유기관",
        "request_date": "공공데이터 제공 신청일",
        "data_result": "처리 결과",
        "refusal_reason": "제공 불가 사유",
        "customers": "주요 고객",
        "business_model": "사업화 / 수익모델",
        "team": "대표자 / 팀 역량",
        "extra_context": "추가 정보",
    }

    result = []

    for key, label in labels.items():
        value = profile.get(key, "")

        if value:
            result.append(f"{label}: {value}")

    if not result:
        return "아직 입력된 기업 / 사업 정보가 없습니다."

    return "\n".join(result)


def conversation_markdown(messages):
    """
    상담 내용을 다운로드하기 위한 Markdown 생성
    """

    lines = [
        "# GrantMate 상담 기록",
        "",
        f"저장 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    for message in messages:

        if message["role"] == "user":
            name = "사용자"
        else:
            name = "GrantMate"

        lines.append(f"## {name}")
        lines.append("")
        lines.append(message["content"])
        lines.append("")

    return "\n".join(lines)


# ============================================================
# 4. SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "company_profile" not in st.session_state:
    st.session_state.company_profile = {}

if "profile_saved" not in st.session_state:
    st.session_state.profile_saved = False


# ============================================================
# 5. OPENAI API KEY
# ============================================================

# Streamlit Secrets에 OPENAI_API_KEY가 있으면 자동 사용합니다.
# 없으면 방문자가 자신의 API Key를 입력할 수 있습니다.

shared_api_key = get_secret("OPENAI_API_KEY", "")


# ============================================================
# 6. PROGRAM KNOWLEDGE
# ============================================================

PROGRAM_KNOWLEDGE = """
[사업명]

2026 민관협력 오픈이노베이션 지원
'공공데이터 활용 지원'
창업기업 제안 협업 과제(Bottom-Up)


[사업 목적]

공공기관이 보유한 데이터를 창업기업에 개방하고
활용을 지원하여 공공서비스 혁신과
창업기업의 성장(Scale-up)을 촉진한다.


[선정 규모]

공공기관 제안 협업 과제와 통합하여
총 20개 과제 내외.


[지원 내용]

- 미개방 공공데이터 확보 지원
- 공공기관과 데이터 제공 조건 협의
- 공공데이터 분석 및 처리
- 공공데이터 활용 기술검증(PoC)
- 제품·서비스 개발
- 과제별 최대 1억원 사업화 자금
- 후속 기술개발 지원사업 연계


[협약 기간]

협약 시작일로부터 5개월 이내.
2026년 11월 ~ 2027년 3월 예정.


[핵심 신청 요건]

1.
공고에서 정하는 창업기업 자격을 충족해야 한다.

2.
공공데이터포털을 통해 공고 마감일 이전에
필요한 공공데이터 제공을 신청한 경험이 있어야 한다.

3.
해당 데이터 보유기관으로부터
'제공 불가' 통보를 받은 경우여야 한다.

4.
데이터 미개방 또는 확보 곤란으로
실제 사업 추진에 어려움이 있어야 한다.

5.
데이터 확보 이후
제품·서비스 개발 또는 연구개발에 활용하는
구체적인 계획이 필요하다.

6.
단순 정보수집, 열람, 출판 등은 지원 대상이 아니다.


[공식 평가 영역]

1. 공공데이터 활용계획

- 기존 제공거부 경험
- 미개방 데이터 활용목적
- 활용내용
- 필요 데이터 요구항목의 구체성


2. 팀(기업) 구성

- 보유 기술
- 전문 인력
- 관련 프로젝트 또는 연구 수행 경험


3. 실현 가능성 및 구체성

- 데이터 확보 이후 사업화 추진계획
- 기술·서비스 구현계획
- 구체성
- 차별성


4. 지속가능성

- 사업화 가능성
- 협업 종료 후 지속·유지 가능성
- 수익성 검증


공식 세부 배점은 공개되어 있지 않다.


[대체 개방 방식]

원자료 제공이 어려운 경우 다음 방식도 검토할 수 있다.

1. 합성데이터
2. 통계데이터
3. 익명데이터
4. 진위확인서비스


[핵심 사업 논리]

실제 문제
→ 기존 방식의 한계
→ 필요한 공공데이터
→ 데이터가 반드시 필요한 이유
→ 데이터 활용방법
→ 구현되는 제품/서비스 기능
→ 5개월 PoC
→ 공공기관 가치
→ 고객 가치
→ 사업화
→ 지속가능성


[작성 원칙]

- 존재하지 않는 실적을 만들지 않는다.
- 존재하지 않는 고객을 만들지 않는다.
- 존재하지 않는 매출을 만들지 않는다.
- 존재하지 않는 계약을 만들지 않는다.
- 존재하지 않는 특허를 만들지 않는다.
- 존재하지 않는 인력·기술을 만들지 않는다.
- 확인되지 않은 내용은 '확인 필요'라고 표시한다.
- 공고에 없는 요건을 공식 요건처럼 말하지 않는다.
- 공개되지 않은 배점을 공식 평가점수처럼 말하지 않는다.
"""


# ============================================================
# 7. 상담 모드
# ============================================================

MODE_INSTRUCTIONS = {

    "💬 자유 상담":
    """
사용자의 질문에 먼저 직접 답한다.

중요한 정보가 부족해서 정확한 판단이 어려운 경우에만
필요한 질문을 추가한다.
""",

    "✍️ 사업계획서 작성":
    """
사용자가 제공한 사실만을 기반으로
실제 사업계획서에 활용할 수 있는 문안을 작성한다.

없는 정보를 만들지 않는다.

중요 정보가 부족하면
반드시 필요한 부분만 질문한다.
""",

    "🔎 심사위원 평가":
    """
이 지원사업의 가상 심사위원으로 평가한다.

공식 평가영역을 기준으로:

- 강점
- 약점
- 심사위원이 의심할 부분
- 탈락 위험
- 개선방법

을 분석한다.

마지막에 반드시
'수정 우선순위 TOP 3'를 제시한다.
""",

    "✅ 제출 전 점검":
    """
정부지원사업 제출 직전 QA를 수행한다.

결과를:

✅ 확인 완료
⚠️ 확인 필요
❌ 중대한 누락 또는 위험

으로 구분한다.

마지막에 제출 전 해야 할 일을
우선순위 순으로 정리한다.
""",
}


SECTIONS = [
    "전체",
    "공공데이터 활용계획",
    "과제 해결방안",
    "기술 경쟁력",
    "산출물 및 개발단계",
    "사업화 방안",
    "대표자·팀 역량",
    "협약기간 추진계획",
    "정부지원사업비",
    "기업 현황",
]


# ============================================================
# 8. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("📄 GrantMate")

    st.caption(
        "공공데이터 활용 지원사업\n"
        "사업계획서 AI Coach"
    )

    st.divider()

    # --------------------------------------------------------
    # API 연결
    # --------------------------------------------------------

    st.subheader("🔑 AI 연결")

    if shared_api_key:

        openai_api_key = shared_api_key

        st.success(
            "AI가 연결되어 있습니다.",
            icon="✅",
        )

    else:

        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help=(
                "입력한 API Key는 현재 브라우저 세션에서만 "
                "사용하며 앱 코드에는 저장하지 않습니다."
            ),
        )

        if openai_api_key:
            st.success(
                "이번 세션에서 AI가 연결되었습니다.",
                icon="✅",
            )
        else:
            st.warning(
                "AI 답변을 사용하려면 API Key가 필요합니다.",
                icon="🔑",
            )

    st.divider()

    # --------------------------------------------------------
    # Flow
    # --------------------------------------------------------

    st.subheader("📌 준비 흐름")

    st.caption("① 기업 / 사업 이해")
    st.caption("② 공공데이터 필요성")
    st.caption("③ 과제 해결방안")
    st.caption("④ 사업화·실행계획")
    st.caption("⑤ 제출 전 QA")

    st.divider()

    # --------------------------------------------------------
    # Mode
    # --------------------------------------------------------

    mode = st.selectbox(
        "상담 모드",
        list(MODE_INSTRUCTIONS.keys()),
    )

    section = st.selectbox(
        "집중 검토 항목",
        SECTIONS,
    )

    st.divider()

    # --------------------------------------------------------
    # New chat
    # --------------------------------------------------------

    if st.button(
        "＋ 새 상담",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.session_state.company_profile = {}
        st.session_state.profile_saved = False
        st.rerun()

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    if st.session_state.messages:

        transcript = conversation_markdown(
            st.session_state.messages
        )

        st.download_button(
            "⬇ 상담 내용 저장",
            data=transcript,
            file_name="grantmate_chat.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.caption(
        "공개 데모 버전에서는 대화가 "
        "현재 브라우저 세션 동안 유지됩니다."
    )


# ============================================================
# 9. TOP PROGRESS
# ============================================================

profile = st.session_state.company_profile


has_profile = bool(
    profile.get("business_item")
    or profile.get("problem")
    or profile.get("needed_data")
)


has_chat = bool(
    st.session_state.messages
)


if has_chat:
    current_step = 3
elif has_profile:
    current_step = 2
else:
    current_step = 1


step_col1, step_col2, step_col3 = st.columns(3)


with step_col1:

    if current_step >= 1:
        st.markdown("### 🔵 ① 사업 정보")
    else:
        st.markdown("### ⚪ ① 사업 정보")


with step_col2:

    if current_step >= 2:
        st.markdown("### 🔵 ② 데이터 전략")
    else:
        st.markdown("### ⚪ ② 데이터 전략")


with step_col3:

    if current_step >= 3:
        st.markdown("### 🔵 ③ AI 작성")
    else:
        st.markdown("### ⚪ ③ AI 작성")


progress_value = {
    1: 0.33,
    2: 0.67,
    3: 1.00,
}[current_step]


st.progress(
    progress_value
)


# ============================================================
# 10. HERO
# ============================================================

st.write("")

if not has_chat:

    st.title(
        "👋 공공데이터 지원사업, 같이 준비해볼까요?"
    )

    st.write(
        "사업의 문제와 필요한 공공데이터를 입력하면 "
        "AI가 공고 요건과 심사 관점에서 부족한 부분을 찾고, "
        "사업계획서 문안까지 함께 정리합니다."
    )

else:

    st.title(
        "💬 사업계획서 AI 코칭"
    )

    st.write(
        "현재 입력된 사업정보를 바탕으로 "
        "질문·작성·심사위원 검토를 계속할 수 있습니다."
    )


st.info(
    "아는 내용만 입력하시면 됩니다. "
    "아직 정하지 못한 항목은 비워 두셔도 됩니다. "
    "AI가 필요한 내용만 추가로 질문합니다.",
    icon="💡",
)


# ============================================================
# 11. COMPANY / BUSINESS FORM
# ============================================================

with st.expander(
    "🏢 1. 기업 / 사업 정보 입력",
    expanded=not has_profile,
):

    profile = st.session_state.company_profile

    with st.form(
        "business_profile_form"
    ):

        # ----------------------------------------------------
        # 기본 사업정보
        # ----------------------------------------------------

        st.subheader(
            "기본 사업정보"
        )

        col1, col2 = st.columns(2)

        with col1:

            company_name = st.text_input(
                "기업명 (선택)",
                value=profile.get(
                    "company_name",
                    "",
                ),
                placeholder="기업명을 입력하세요.",
            )

        with col2:

            stages = [
                "아이디어 구상 중",
                "시장 조사 중",
                "준비/세팅 중",
                "초기 제품·서비스 개발 중",
                "시범 운영 / PoC 중",
                "정식 운영 중",
            ]

            saved_stage = profile.get(
                "stage",
                "준비/세팅 중",
            )

            if saved_stage in stages:
                stage_index = stages.index(
                    saved_stage
                )
            else:
                stage_index = 2

            stage = st.selectbox(
                "현재 단계",
                stages,
                index=stage_index,
            )


        business_item = st.text_input(
            "사업 아이템",
            value=profile.get(
                "business_item",
                "",
            ),
            placeholder=(
                "예: 공공데이터를 활용한 "
                "지역 소상공인 운영지원 서비스"
            ),
        )


        problem = st.text_area(
            "해결하려는 문제",
            value=profile.get(
                "problem",
                "",
            ),
            height=100,
            placeholder=(
                "누가 어떤 문제를 겪고 있으며, "
                "현재 방식으로 왜 해결하기 어려운지 적어주세요."
            ),
        )


        development = st.text_area(
            "현재 개발단계 / 보유 기능 (선택)",
            value=profile.get(
                "development",
                "",
            ),
            height=85,
            placeholder=(
                "현재 개발된 기능, 시제품, "
                "PoC 또는 서비스 운영 현황 등을 적어주세요."
            ),
        )


        # ----------------------------------------------------
        # 데이터 정보
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "공공데이터 정보"
        )


        needed_data = st.text_area(
            "필요한 공공데이터",
            value=profile.get(
                "needed_data",
                "",
            ),
            height=95,
            placeholder=(
                "사업 수행을 위해 필요한 "
                "공공데이터가 무엇인지 적어주세요."
            ),
        )


        needed_fields = st.text_area(
            "필요한 주요 데이터 항목 (선택)",
            value=profile.get(
                "needed_fields",
                "",
            ),
            height=80,
            placeholder=(
                "예: 지역, 기준연월, 상태코드, "
                "처리결과, 변경이력 등"
            ),
        )


        col3, col4 = st.columns(2)

        with col3:

            data_holder = st.text_input(
                "예상 데이터 보유기관",
                value=profile.get(
                    "data_holder",
                    "",
                ),
                placeholder=(
                    "관련 중앙부처 또는 공공기관"
                ),
            )


        with col4:

            request_date = st.text_input(
                "공공데이터 제공 신청일 (선택)",
                value=profile.get(
                    "request_date",
                    "",
                ),
                placeholder="YYYY-MM-DD",
            )


        col5, col6 = st.columns(2)

        data_results = [
            "아직 신청 전",
            "처리 중",
            "제공",
            "제공 불가",
            "기타",
        ]


        current_result = profile.get(
            "data_result",
            "아직 신청 전",
        )


        if current_result in data_results:
            result_index = data_results.index(
                current_result
            )
        else:
            result_index = 0


        with col5:

            data_result = st.selectbox(
                "처리 결과",
                data_results,
                index=result_index,
            )


        with col6:

            refusal_reason = st.text_input(
                "제공 불가 사유 (해당 시)",
                value=profile.get(
                    "refusal_reason",
                    "",
                ),
                placeholder=(
                    "공공기관에서 안내받은 "
                    "제공 불가 사유"
                ),
            )


        # ----------------------------------------------------
        # 사업화
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "사업화 정보"
        )


        col7, col8 = st.columns(2)

        with col7:

            customers = st.text_area(
                "주요 고객 (선택)",
                value=profile.get(
                    "customers",
                    "",
                ),
                height=80,
                placeholder=(
                    "누가 제품 또는 서비스를 "
                    "구매하거나 사용할지 적어주세요."
                ),
            )


        with col8:

            business_model = st.text_area(
                "사업화 / 수익모델 (선택)",
                value=profile.get(
                    "business_model",
                    "",
                ),
                height=80,
                placeholder=(
                    "예: 구독, 기관 계약, "
                    "사용량 기반 과금 등"
                ),
            )


        team = st.text_area(
            "대표자 / 팀 역량 (선택)",
            value=profile.get(
                "team",
                "",
            ),
            height=80,
            placeholder=(
                "관련 경력, 기술역량, "
                "프로젝트 수행 경험 등을 적어주세요."
            ),
        )


        extra_context = st.text_area(
            "추가 정보 (선택)",
            value=profile.get(
                "extra_context",
                "",
            ),
            height=80,
            placeholder=(
                "AI가 사업을 검토할 때 "
                "추가로 알아야 할 내용을 적어주세요."
            ),
        )


        profile_submit = st.form_submit_button(
            "정보 저장하고 AI 코칭 시작 →",
            use_container_width=True,
            type="primary",
        )


    if profile_submit:

        st.session_state.company_profile = {
            "company_name": company_name.strip(),
            "stage": stage,
            "business_item": business_item.strip(),
            "problem": problem.strip(),
            "development": development.strip(),
            "needed_data": needed_data.strip(),
            "needed_fields": needed_fields.strip(),
            "data_holder": data_holder.strip(),
            "request_date": request_date.strip(),
            "data_result": data_result,
            "refusal_reason": refusal_reason.strip(),
            "customers": customers.strip(),
            "business_model": business_model.strip(),
            "team": team.strip(),
            "extra_context": extra_context.strip(),
        }

        st.session_state.profile_saved = True

        st.success(
            "입력한 사업정보를 반영했습니다."
        )

        st.rerun()


# ============================================================
# 12. PROFILE SUMMARY
# ============================================================

profile = st.session_state.company_profile


if profile.get("business_item"):

    st.success(
        "사업정보 입력 완료"
    )

    summary1, summary2, summary3 = st.columns(3)

    with summary1:

        st.metric(
            "현재 단계",
            profile.get(
                "stage",
                "-",
            ),
        )

    with summary2:

        st.metric(
            "데이터 진행상태",
            profile.get(
                "data_result",
                "-",
            ),
        )

    with summary3:

        st.metric(
            "집중 검토",
            section,
        )


# ============================================================
# 13. OPENAI CLIENT
# ============================================================

client = None


if openai_api_key:

    try:

        client = OpenAI(
            api_key=openai_api_key
        )

    except Exception as exc:

        st.error(
            "OpenAI 연결을 초기화하지 못했습니다."
        )

        with st.expander(
            "오류 상세"
        ):
            st.code(str(exc))


# ============================================================
# 14. SYSTEM PROMPT
# ============================================================

def build_system_prompt():

    return f"""
당신은 대한민국 정부지원사업 전문 컨설턴트다.

특히 다음 사업의 사업계획서 작성과
평가를 돕는 AI Coach 역할을 한다.

2026년 민관협력 오픈이노베이션
'공공데이터 활용 지원'
창업기업 제안 협업 과제(Bottom-Up)


[공식 사업 정보]

{PROGRAM_KNOWLEDGE}


[현재 상담 모드]

{mode}

{MODE_INSTRUCTIONS[mode]}


[현재 집중 검토 항목]

{section}


[사용자가 입력한 사업 정보]

{profile_to_text(
    st.session_state.company_profile
)}


[검토 원칙]

1.
공고문 내용과 사용자가 제공한 사실을 구분한다.

2.
사용자가 제공하지 않은 사실은 만들지 않는다.

3.
실적, 매출, 고객, 계약, 특허,
인력 또는 기술을 임의로 추가하지 않는다.

4.
판단에 꼭 필요한 정보가 부족한 경우에만
추가 질문한다.

5.
다음 논리를 가장 중요하게 검토한다.

실제 문제
→ 기존 방식의 한계
→ 필요한 공공데이터
→ 공공데이터가 반드시 필요한 이유
→ 데이터 활용
→ 구현 기능
→ 5개월 PoC
→ 공공기관 가치
→ 고객 가치
→ 사업화
→ 지속가능성

6.
공공데이터 없이도
동일한 제품이나 서비스를 만들 수 있다는
심사위원의 반론을 항상 검토한다.

7.
단순히 AI를 활용한다는 이유만으로
기술적 차별성이 있다고 평가하지 않는다.

8.
5개월 협약기간 내 실제 구현 가능한지 검토한다.

9.
지원사업 종료 후에도
지속 가능한 사업인지 검토한다.

10.
확인되지 않은 내용은
[확인 필요]로 표시한다.

11.
공식 평가영역별 세부 배점은 공개되지 않았으므로
임의의 점수를 공식점수처럼 제시하지 않는다.

12.
답변은 한국어로 작성한다.

13.
불필요하게 길게 설명하지 않는다.

14.
가능하면 다음 구조를 사용한다.

현재 판단
강점
보완 필요사항
구체적인 개선방안
필요한 경우 사업계획서 문안
"""


# ============================================================
# 15. QUICK ACTIONS
# ============================================================

st.write("")

st.subheader(
    "무엇을 도와드릴까요?"
)


q1, q2, q3, q4 = st.columns(4)


quick_prompt = None


with q1:

    if st.button(
        "🧩 데이터 필요성",
        use_container_width=True,
    ):

        quick_prompt = """
현재 사업에서 요청하는 공공데이터가
왜 반드시 필요한지 평가해 주세요.

특히

'이 데이터 없이도 서비스를 만들 수 있는 것 아닌가?'

라는 심사위원의 반론까지 포함하여
레드팀 관점으로 분석해 주세요.
"""


with q2:

    if st.button(
        "✍️ 문안 작성",
        use_container_width=True,
    ):

        quick_prompt = f"""
현재 사용자가 제공한 사실만 사용하여
사업계획서의 '{section}' 항목 초안을 작성해 주세요.

확인되지 않은 사실은 만들지 말고
필요한 경우 [확인 필요]라고 표시해 주세요.
"""


with q3:

    if st.button(
        "🔎 심사위원 평가",
        use_container_width=True,
    ):

        quick_prompt = """
현재 사업을 이 지원사업의 심사위원 관점에서 평가해 주세요.

공식 평가영역을 기준으로

- 강점
- 약점
- 탈락 위험
- 심사위원이 질문할 사항

을 분석하고

마지막에
'수정 우선순위 TOP 3'
를 제시해 주세요.
"""


with q4:

    if st.button(
        "✅ 제출 전 QA",
        use_container_width=True,
    ):

        quick_prompt = """
현재까지 입력된 내용을 기준으로
지원사업 제출 전 QA를 수행해 주세요.

✅ 확인 완료
⚠️ 확인 필요
❌ 중대한 위험

으로 나누고

마지막에 제출 전 해야 할 일을
우선순위 순으로 정리해 주세요.
"""


# ============================================================
# 16. CHAT
# ============================================================

st.write("")

st.subheader(
    "💬 AI 상담"
)


if not openai_api_key:

    st.warning(
        "AI 답변을 받으려면 왼쪽 사이드바에 "
        "OpenAI API Key를 입력해 주세요. "
        "채팅 입력창 자체는 사용할 수 있습니다.",
        icon="🔑",
    )


if not st.session_state.messages:

    with st.chat_message(
        "assistant"
    ):

        st.markdown(
            """
안녕하세요. 저는 **GrantMate**입니다.

사업 아이디어, 필요한 공공데이터,
사업계획서 작성 또는 심사 관점에 대해
자유롭게 질문해 주세요.

기업/사업 정보를 아직 모두 작성하지 않아도 괜찮습니다.
"""
        )


for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# 중요:
# API Key가 없어도 chat_input 자체는 disable하지 않습니다.

chat_prompt = st.chat_input(
    "사업계획서, 공공데이터, 심사 기준 등에 대해 질문해 주세요."
)


prompt = (
    quick_prompt
    if quick_prompt
    else chat_prompt
)


# ============================================================
# 17. HANDLE CHAT
# ============================================================

if prompt:

    # API Key가 없는 경우에도 입력창은 동작합니다.
    # 단, API 호출 전에 안내합니다.

    if not openai_api_key:

        st.warning(
            "질문을 AI에게 보내려면 "
            "왼쪽 사이드바에서 OpenAI API Key를 입력해 주세요.",
            icon="🔑",
        )

    else:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )


        with st.chat_message(
            "user"
        ):

            st.markdown(
                prompt
            )


        try:

            with st.chat_message(
                "assistant"
            ):

                with st.spinner(
                    "공고 기준으로 검토하고 있습니다..."
                ):

                    response = (
                        client.responses.create(
                            model="gpt-5.6-luna",
                            instructions=build_system_prompt(),
                            input=[
                                {
                                    "role": message["role"],
                                    "content": message["content"],
                                }
                                for message
                                in st.session_state.messages
                            ],
                            max_output_tokens=2500,
                        )
                    )


                    answer = (
                        response.output_text
                    )


                    st.markdown(
                        answer
                    )


            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )


        except Exception as exc:

            st.error(
                "AI 답변을 생성하지 못했습니다."
            )

            st.write(
                "API Key, API 사용한도 또는 "
                "OpenAI 프로젝트의 모델 접근권한을 확인해 주세요."
            )

            with st.expander(
                "오류 상세 보기"
            ):

                st.code(
                    str(exc)
                )


# ============================================================
# 18. BOTTOM CONTROLS
# ============================================================

if st.session_state.messages:

    st.divider()

    col_download, col_reset = st.columns(2)


    with col_download:

        transcript = conversation_markdown(
            st.session_state.messages
        )

        st.download_button(
            "⬇ 상담 내용 다운로드",
            data=transcript,
            file_name="grantmate_chat.md",
            mime="text/markdown",
            use_container_width=True,
        )


    with col_reset:

        if st.button(
            "🗑 대화만 초기화",
            use_container_width=True,
        ):

            st.session_state.messages = []

            st.rerun()


# ============================================================
# 19. FOOTER
# ============================================================

st.divider()

st.caption(
    "GrantMate는 사업계획 수립을 돕는 교육용 AI 도구입니다. "
    "최종 신청 자격 및 제출 내용은 공식 모집공고와 "
    "K-Startup 안내를 반드시 확인하세요."
)
