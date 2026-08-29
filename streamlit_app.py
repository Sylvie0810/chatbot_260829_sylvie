import json
from datetime import datetime

import streamlit as st
from openai import OpenAI


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="GrantMate | 공공데이터 사업계획서 AI Coach",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

/* ----------------------------------------------------------
   전체 화면
---------------------------------------------------------- */

.block-container {
    max-width: 1160px;
    padding-top: 5.2rem !important;
    padding-bottom: 6rem;
}


/* ----------------------------------------------------------
   Streamlit 상단 헤더
---------------------------------------------------------- */

[data-testid="stHeader"] {
    background: rgba(255,255,255,0.96);
}


/* ----------------------------------------------------------
   Sidebar
---------------------------------------------------------- */

[data-testid="stSidebar"] {
    background: #f7f8fb;
    border-right: 1px solid #e6e8ee;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 2rem;
}

.gm-brand {
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: -0.035em;
    color: #252a34;
}

.gm-brand-sub {
    color: #7b818d;
    font-size: 0.85rem;
    line-height: 1.5;
    margin-top: 4px;
    margin-bottom: 1.3rem;
}


/* ----------------------------------------------------------
   Stepper
---------------------------------------------------------- */

.gm-stepper {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin: 0 0 10px 0;
}

.gm-step {
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 9px;
    color: #a0a6b1;
    font-size: 0.9rem;
    font-weight: 700;
}

.gm-step.active {
    color: #222832;
}

.gm-step.done {
    color: #2f80ed;
}

.gm-step-number {
    flex: 0 0 auto;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: #eef0f4;
    color: #8c939e;

    display: flex;
    align-items: center;
    justify-content: center;

    font-size: 0.78rem;
    font-weight: 800;
}

.gm-step.active .gm-step-number,
.gm-step.done .gm-step-number {
    background: #2f80ed;
    color: #ffffff;
}

.gm-progress {
    width: 100%;
    height: 7px;
    background: #eef0f4;
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 2.4rem;
}

.gm-progress-bar {
    height: 100%;
    background: #2f80ed;
    border-radius: 999px;
}


/* ----------------------------------------------------------
   Hero
---------------------------------------------------------- */

.gm-hero {
    margin-bottom: 1.6rem;
}

.gm-hero h1 {
    margin: 0 0 0.7rem 0;
    color: #252a34;
    font-size: 2.15rem;
    line-height: 1.25;
    letter-spacing: -0.045em;
}

.gm-hero p {
    margin: 0;
    color: #747a85;
    font-size: 1rem;
    line-height: 1.7;
}


/* ----------------------------------------------------------
   안내 박스
---------------------------------------------------------- */

.gm-info-box {
    padding: 15px 17px;
    margin: 0.4rem 0 1.3rem 0;

    background: #f8fafc;
    border: 1px solid #e5e8ed;
    border-radius: 13px;

    color: #505763;
    font-size: 0.92rem;
    line-height: 1.65;
}


/* ----------------------------------------------------------
   상태
---------------------------------------------------------- */

.gm-status-ok {
    color: #177245;
    font-weight: 700;
}

.gm-status-warn {
    color: #9a6400;
    font-weight: 700;
}


/* ----------------------------------------------------------
   Chat
---------------------------------------------------------- */

div[data-testid="stChatMessage"] {
    border: 1px solid #eceff3;
    border-radius: 15px;
    padding: 0.35rem 0.6rem;
    margin-bottom: 0.55rem;
}


/* ----------------------------------------------------------
   Form
---------------------------------------------------------- */

div[data-testid="stForm"] {
    border: 1px solid #e4e7ec;
    border-radius: 15px;
    padding: 1rem 1rem 0.5rem 1rem;
}


/* ----------------------------------------------------------
   Buttons
---------------------------------------------------------- */

.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button {
    border-radius: 10px;
    min-height: 42px;
    font-weight: 700;
}


/* ----------------------------------------------------------
   모바일
---------------------------------------------------------- */

@media (max-width: 700px) {

    .block-container {
        padding-top: 4.5rem !important;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .gm-stepper {
        grid-template-columns: 1fr;
        gap: 7px;
    }

    .gm-progress {
        margin-top: 12px;
    }

    .gm-hero h1 {
        font-size: 1.65rem;
    }

    .gm-hero p {
        font-size: 0.92rem;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def get_secret(name, default=""):
    try:
        return st.secrets[name]
    except Exception:
        return default


def profile_to_text(profile):
    """AI에 전달할 기업/사업 정보를 읽기 쉬운 텍스트로 변환."""

    labels = {
        "company_name": "기업명",
        "business_item": "사업 아이템",
        "stage": "현재 단계",
        "problem": "해결하려는 문제",
        "needed_data": "필요한 공공데이터",
        "needed_fields": "필요 데이터 항목",
        "data_holder": "예상 데이터 보유기관",
        "request_date": "공공데이터 제공 신청일",
        "data_result": "처리 결과",
        "refusal_reason": "제공 불가 사유",
        "development": "현재 개발단계 / 보유 기능",
        "customers": "주요 고객",
        "business_model": "사업화 / 수익모델",
        "team": "팀 역량",
        "extra_context": "추가 정보",
    }

    lines = []

    for key, label in labels.items():
        value = profile.get(key, "")

        if value:
            lines.append(f"{label}: {value}")

    if not lines:
        return "아직 입력된 기업/사업 정보가 없습니다."

    return "\n".join(lines)


def conversation_markdown(messages):
    """다운로드용 Markdown 생성."""

    lines = [
        "# GrantMate 상담 기록",
        "",
        f"저장 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    for message in messages:
        if message["role"] == "user":
            speaker = "사용자"
        else:
            speaker = "GrantMate"

        lines.append(f"## {speaker}")
        lines.append("")
        lines.append(message["content"])
        lines.append("")

    return "\n".join(lines)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


if "company_profile" not in st.session_state:
    st.session_state.company_profile = {}


if "profile_saved" not in st.session_state:
    st.session_state.profile_saved = False


# ============================================================
# PUBLIC DEMO API POLICY
# ============================================================

# 공개 URL에서는 기본적으로 방문자가 자신의 API Key를 입력하도록 합니다.
# 개인 OpenAI API Key를 공개 앱에 자동 사용하면
# 방문자의 API 사용료가 앱 소유자에게 청구될 수 있기 때문입니다.

SHARED_OPENAI_API_KEY = get_secret("OPENAI_API_KEY")

USE_SHARED_OPENAI_KEY = (
    str(
        get_secret(
            "USE_SHARED_OPENAI_KEY",
            "false",
        )
    ).lower()
    == "true"
)


# ============================================================
# PROGRAM KNOWLEDGE
# ============================================================

PROGRAM_KNOWLEDGE = """
[사업 기본정보]

사업명:
2026 민관협력 오픈이노베이션 지원
'공공데이터 활용 지원'
창업기업 제안 협업 과제(Bottom-Up)

사업목적:
공공기관이 보유한 데이터를 창업기업에 개방하고
활용을 지원하여 공공서비스 혁신과
창업기업의 성장(Scale-up)을 촉진한다.

선정규모:
공공기관 제안 협업과제와 통합하여 총 20개 과제 내외.

지원내용:
- 미개방 공공데이터 확보 지원
- 공공기관과 데이터 제공 가능 조건 협의
- 데이터 분석 및 처리
- 공공데이터 활용 기술검증(PoC)
- 제품 및 서비스 개발
- 과제별 최대 1억원 사업화 자금
- 후속 기술개발 지원사업 연계

협약기간:
협약 시작일로부터 5개월 이내
2026년 11월 ~ 2027년 3월 예정.


[핵심 신청요건]

1.
공고에서 정하는 창업기업 자격을 충족해야 한다.

2.
공공데이터포털을 통해 공고 마감일 이전에
필요한 공공데이터의 제공을 신청한 경험이 있어야 한다.

3.
해당 데이터 보유기관으로부터
'제공 불가' 통보를 받은 경우여야 한다.

4.
필요 데이터가 미개방되어 있거나 확보가 어려워
사업 추진에 실질적인 어려움이 있어야 한다.

5.
데이터 확보 이후
제품·서비스 개발 또는 연구개발 등에 활용하는
구체적인 계획이 필요하다.

6.
단순 정보수집, 열람, 출판 목적은 지원 대상이 아니다.


[공식 평가영역]

1. 공공데이터 활용계획
- 기존 제공거부 경험
- 미개방 데이터의 활용목적
- 활용내용
- 필요한 데이터 요구항목의 구체성

2. 팀(기업) 구성
- 보유 기술
- 인력 전문성
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

공식 평가항목별 세부 배점은 공개되어 있지 않다.


[대체 개방형태]

원자료 제공이 어려운 경우 다음 방식도 검토할 수 있다.

1. 합성데이터
2. 통계데이터
3. 익명데이터
4. 진위확인서비스


[사업계획서 핵심 논리]

시장 또는 공공서비스의 실제 문제
→ 기존 방식의 한계
→ 어떤 공공데이터가 필요한가
→ 그 데이터가 왜 반드시 필요한가
→ 확보한 데이터를 어떻게 활용하는가
→ 어떤 제품·서비스 기능을 구현하는가
→ 5개월 동안 무엇을 검증하는가
→ 공공기관에 어떤 가치가 생기는가
→ 고객에게 어떤 가치가 생기는가
→ 협약 종료 후 어떻게 사업화·확장되는가


[작성 원칙]

- 존재하지 않는 실적을 만들지 않는다.
- 존재하지 않는 고객을 만들지 않는다.
- 존재하지 않는 매출을 만들지 않는다.
- 존재하지 않는 계약을 만들지 않는다.
- 존재하지 않는 특허를 만들지 않는다.
- 존재하지 않는 인력이나 기술을 만들지 않는다.
- 확인되지 않은 정보는 '확인 필요'라고 표시한다.
- 공고에 없는 요건을 공식 요건처럼 말하지 않는다.
- 공고에 없는 평가 배점을 공식 점수처럼 말하지 않는다.
"""


# ============================================================
# MODE
# ============================================================

MODE_INSTRUCTIONS = {
    "💬 자유 상담": """
사용자의 질문에 정부지원사업 전문 컨설턴트처럼 답한다.

답할 수 있는 내용은 먼저 직접 답한다.
중요한 정보가 부족할 때만 필요한 질문을 한다.
""",

    "✍️ 사업계획서 작성": """
사용자가 제공한 사실을 기반으로
실제 사업계획서에 활용할 수 있는 문안을 작성한다.

정보가 부족한 경우 없는 정보를 만들지 않는다.
필요한 정보만 간결하게 추가 질문한다.
""",

    "🔎 심사위원 평가": """
가상의 심사위원 관점에서 검토한다.

공식 평가영역별로:
- 강점
- 약점
- 심사위원이 의심할 부분
- 탈락 위험
- 개선방안

을 제시한다.

마지막에 수정 우선순위 TOP 3를 제공한다.

공식 배점이 공개되지 않았으므로
AI 가상점수를 공식점수처럼 제시하지 않는다.
""",

    "✅ 제출 전 점검": """
정부지원사업 제출 전 QA 담당자처럼 검토한다.

결과를:
✅ 확인 완료
⚠️ 확인 필요
❌ 중대한 누락 또는 위험

으로 구분한다.

마지막에 제출 전 해야 할 일을 우선순위로 정리한다.
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
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
<div class="gm-brand">
📄 GrantMate
</div>

<div class="gm-brand-sub">
공공데이터 활용 지원사업<br>
사업계획서 AI Coach
</div>
""",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # API
    # --------------------------------------------------------

    st.markdown("### 🔑 AI 연결")

    if (
        USE_SHARED_OPENAI_KEY
        and SHARED_OPENAI_API_KEY
    ):
        openai_api_key = SHARED_OPENAI_API_KEY

        st.markdown(
            '<span class="gm-status-ok">'
            '● AI 사용 가능'
            '</span>',
            unsafe_allow_html=True,
        )

    else:
        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help=(
                "입력한 API Key는 이 앱의 코드나 "
                "대화내용에 저장하지 않습니다."
            ),
        )

        if openai_api_key:
            st.markdown(
                '<span class="gm-status-ok">'
                '● 이번 세션에서 연결됨'
                '</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="gm-status-warn">'
                '● API Key를 입력해 주세요'
                '</span>',
                unsafe_allow_html=True,
            )

    st.caption(
        "공개 데모에서는 방문자가 자신의 "
        "API Key를 입력하는 방식입니다."
    )

    # --------------------------------------------------------
    # Progress
    # --------------------------------------------------------

    st.divider()

    st.markdown("### 📌 준비 흐름")

    st.caption("① 기업 / 사업 이해")
    st.caption("② 공공데이터 필요성")
    st.caption("③ 과제 해결방안")
    st.caption("④ 사업화·실행계획")
    st.caption("⑤ 제출 전 QA")

    # --------------------------------------------------------
    # Mode
    # --------------------------------------------------------

    st.divider()

    mode = st.selectbox(
        "상담 모드",
        list(MODE_INSTRUCTIONS.keys()),
    )

    section = st.selectbox(
        "집중 검토 항목",
        SECTIONS,
    )

    # --------------------------------------------------------
    # Conversation controls
    # --------------------------------------------------------

    st.divider()

    if st.button(
        "＋ 새 상담",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.session_state.company_profile = {}
        st.session_state.profile_saved = False
        st.rerun()

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
        "현재 공개 데모에서는 대화가 "
        "브라우저 세션 동안만 유지됩니다."
    )


# ============================================================
# STEP STATUS
# ============================================================

profile = st.session_state.company_profile

has_profile = bool(
    profile.get("business_item")
    or profile.get("problem")
    or profile.get("needed_data")
)

has_messages = bool(
    st.session_state.messages
)


if has_messages:
    current_step = 3
elif has_profile:
    current_step = 2
else:
    current_step = 1


progress_percent = {
    1: 34,
    2: 67,
    3: 100,
}[current_step]


def step_class(step_number):
    if step_number < current_step:
        return "done"

    if step_number == current_step:
        return "active"

    return ""


# ============================================================
# TOP STEPPER
# ============================================================

st.markdown(
    f"""
<div class="gm-stepper">

    <div class="gm-step {step_class(1)}">
        <div class="gm-step-number">1</div>
        <div>사업 정보 입력</div>
    </div>

    <div class="gm-step {step_class(2)}">
        <div class="gm-step-number">2</div>
        <div>공공데이터 전략 점검</div>
    </div>

    <div class="gm-step {step_class(3)}">
        <div class="gm-step-number">3</div>
        <div>AI와 함께 작성</div>
    </div>

</div>

<div class="gm-progress">
    <div
        class="gm-progress-bar"
        style="width:{progress_percent}%"
    ></div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HERO
# ============================================================

if not has_messages:

    st.markdown(
        """
<div class="gm-hero">

<h1>
👋 공공데이터 지원사업, 같이 준비해볼까요?
</h1>

<p>
사업의 문제와 필요한 공공데이터를 입력하면
AI가 공고 요건과 심사 관점에서 부족한 부분을 찾고,
사업계획서 문안까지 함께 정리합니다.
</p>

</div>
""",
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
<div class="gm-hero">

<h1>
💬 사업계획서 AI 코칭
</h1>

<p>
현재 입력한 사업정보를 바탕으로
질문, 작성, 심사위원 검토를 계속할 수 있습니다.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# INFO MESSAGE
# ============================================================

st.markdown(
    """
<div class="gm-info-box">

<b>처음 사용하시나요?</b><br>

아는 내용만 입력하시면 됩니다.
아직 정하지 못한 항목은 비워 두어도 됩니다.
AI가 필요한 내용만 추가로 질문합니다.

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# PROFILE FORM
# ============================================================

profile = st.session_state.company_profile


with st.expander(
    "🏢 1. 기업 / 사업 정보 입력",
    expanded=not has_profile,
):

    with st.form("company_profile_form"):

        col1, col2 = st.columns(2)

        with col1:
            company_name = st.text_input(
                "기업명 (선택)",
                value=profile.get(
                    "company_name",
                    "",
                ),
                placeholder="예: ABC테크",
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

            try:
                stage_index = stages.index(
                    saved_stage
                )
            except ValueError:
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
                "소상공인 업무지원 서비스"
            ),
        )


        problem = st.text_area(
            "해결하려는 문제",
            value=profile.get(
                "problem",
                "",
            ),
            height=110,
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
            height=90,
            placeholder=(
                "현재 개발된 기능, 시제품, "
                "PoC 또는 서비스 운영 현황 등을 적어주세요."
            ),
        )


        st.markdown("#### 공공데이터 정보")


        needed_data = st.text_area(
            "필요한 공공데이터",
            value=profile.get(
                "needed_data",
                "",
            ),
            height=100,
            placeholder=(
                "사업 수행에 필요한 데이터가 무엇인지 적어주세요."
            ),
        )


        needed_fields = st.text_area(
            "필요한 주요 데이터 항목 (선택)",
            value=profile.get(
                "needed_fields",
                "",
            ),
            height=85,
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
                placeholder="예: 관련 중앙부처 또는 공공기관",
            )

        with col4:
            request_date = st.text_input(
                "공공데이터 제공 신청일 (선택)",
                value=profile.get(
                    "request_date",
                    "",
                ),
                placeholder="예: 2026-08-20",
            )


        col5, col6 = st.columns(2)

        with col5:

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

            try:
                result_index = (
                    data_results.index(
                        current_result
                    )
                )
            except ValueError:
                result_index = 0

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
                    "예: 미개방 데이터, 추가 가공 필요 등"
                ),
            )


        st.markdown("#### 사업화 정보")


        col7, col8 = st.columns(2)

        with col7:
            customers = st.text_area(
                "주요 고객 (선택)",
                value=profile.get(
                    "customers",
                    "",
                ),
                height=85,
                placeholder=(
                    "누가 이 제품 또는 서비스를 구매하거나 "
                    "사용할지 적어주세요."
                ),
            )

        with col8:
            business_model = st.text_area(
                "사업화 / 수익모델 (선택)",
                value=profile.get(
                    "business_model",
                    "",
                ),
                height=85,
                placeholder=(
                    "예: SaaS 구독, 기관 계약, "
                    "사용량 기반 과금 등"
                ),
            )


        team = st.text_area(
            "대표자 / 팀 역량 (선택)",
            value=profile.get(
                "team",
                "",
            ),
            height=85,
            placeholder=(
                "관련 경력, 개발역량, "
                "프로젝트 수행경험 등을 적어주세요."
            ),
        )


        extra_context = st.text_area(
            "추가 정보 (선택)",
            value=profile.get(
                "extra_context",
                "",
            ),
            height=85,
            placeholder=(
                "데이터 제공불가 상세사유, "
                "기존 실적 또는 AI가 참고해야 할 내용을 적어주세요."
            ),
        )


        submitted = st.form_submit_button(
            "정보 저장하고 AI 코칭 시작 →",
            use_container_width=True,
            type="primary",
        )


    if submitted:

        st.session_state.company_profile = {
            "company_name": company_name.strip(),
            "business_item": business_item.strip(),
            "stage": stage,
            "problem": problem.strip(),
            "needed_data": needed_data.strip(),
            "needed_fields": needed_fields.strip(),
            "data_holder": data_holder.strip(),
            "request_date": request_date.strip(),
            "data_result": data_result,
            "refusal_reason": refusal_reason.strip(),
            "development": development.strip(),
            "customers": customers.strip(),
            "business_model": business_model.strip(),
            "team": team.strip(),
            "extra_context": extra_context.strip(),
        }

        st.session_state.profile_saved = True

        st.success(
            "입력한 정보를 반영했습니다."
        )

        st.rerun()


# ============================================================
# PROFILE SUMMARY
# ============================================================

profile = st.session_state.company_profile


if profile.get("business_item"):

    summary_items = []

    if profile.get("business_item"):
        summary_items.append(
            f"<b>사업</b> {profile['business_item']}"
        )

    if profile.get("data_holder"):
        summary_items.append(
            f"<b>예상 보유기관</b> {profile['data_holder']}"
        )

    if profile.get("data_result"):
        summary_items.append(
            f"<b>데이터 상태</b> {profile['data_result']}"
        )

    st.markdown(
        '<div class="gm-info-box">'
        + " &nbsp;&nbsp;·&nbsp;&nbsp; ".join(
            summary_items
        )
        + "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# AI CLIENT
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
        st.code(str(exc))


else:

    st.info(
        "AI 상담을 사용하려면 왼쪽에서 "
        "OpenAI API Key를 입력해 주세요."
    )


# ============================================================
# SYSTEM PROMPT
# ============================================================

def build_system_prompt():

    return f"""
당신은 대한민국 정부지원사업 전문 컨설턴트다.

특히 2026년
민관협력 오픈이노베이션
'공공데이터 활용 지원'
창업기업 제안 협업과제(Bottom-Up)의
사업계획서 작성과 검토를 지원하는 AI Coach다.

목표는 사용자의 사업을 무조건 좋게 평가하는 것이 아니다.

심사위원이 이해하기 어려운 부분,
논리적 약점,
데이터 필요성이 약한 부분,
5개월 안에 구현하기 어려운 부분,
사업화 지속성이 부족한 부분을 찾아내어
실제 사업계획서를 개선하도록 돕는다.


==================================================
공식 사업 정보
==================================================

{PROGRAM_KNOWLEDGE}


==================================================
현재 상담 모드
==================================================

{mode}

{MODE_INSTRUCTIONS[mode]}


==================================================
현재 집중 검토 항목
==================================================

{section}


==================================================
사용자가 입력한 기업 / 사업 정보
==================================================

{profile_to_text(st.session_state.company_profile)}


==================================================
반드시 지켜야 할 규칙
==================================================

1.
공고에 명시된 내용과
사용자가 제공한 사실을 명확히 구분한다.

2.
사용자가 제공하지 않은
실적, 매출, 고객, 계약, 특허,
인력, 기술을 만들어내지 않는다.

3.
정보가 부족하더라도
불필요하게 많은 질문을 하지 않는다.

판단에 반드시 필요한 정보만 질문한다.

4.
다음 연결을 가장 중요하게 평가한다.

실제 문제
→ 기존 방식의 한계
→ 필요한 공공데이터
→ 데이터가 반드시 필요한 이유
→ 데이터 활용 방법
→ 구현되는 제품/서비스 기능
→ 5개월 PoC
→ 공공기관 가치
→ 고객 가치
→ 사업화 및 지속가능성

5.
공공데이터가 없어도 동일한 서비스를
쉽게 구현할 수 있다는 반론을 반드시 검토한다.

6.
단순히 AI를 사용한다는 이유로
기술적 차별성이 있다고 판단하지 않는다.

7.
협약기간 5개월 안에
실제로 구현 가능한 범위인지 검토한다.

8.
지원사업을 받기 위한 일회성 아이디어가 아니라
협약 종료 후에도 사업으로 지속할 수 있는지 검토한다.

9.
과장된 정부지원사업식 표현보다
구체적인 데이터, 기능, 산출물,
고객, 검증방법을 우선한다.

10.
확인되지 않은 내용은
'확인 필요'라고 명확하게 표시한다.

11.
공식 평가영역별 세부 배점이 공개되지 않았으므로
임의의 점수를 공식 평가점수처럼 표현하지 않는다.

12.
답변은 한국어로 작성한다.

13.
가급적 다음 방식으로 답한다.

- 현재 판단
- 강점 또는 확인된 부분
- 문제점 또는 보완 필요사항
- 구체적인 개선방안
- 필요할 경우 실제 사업계획서 문안

14.
사용자가 이미 충분한 정보를 제공했다면
같은 내용을 반복해서 질문하지 않는다.
"""


# ============================================================
# QUICK ACTIONS
# ============================================================

st.markdown("### 무엇을 도와드릴까요?")


q1, q2, q3, q4 = st.columns(4)


quick_prompt = None


with q1:

    if st.button(
        "🧩 데이터 필요성 점검",
        use_container_width=True,
        disabled=client is None,
    ):

        quick_prompt = """
현재 사업에서 요청한 공공데이터가
왜 반드시 필요한지 검토해줘.

특히
'이 데이터 없이도 서비스를 만들 수 있는 것 아닌가?'
라는 심사위원의 반론까지 포함하여
레드팀 관점에서 평가해줘.
"""


with q2:

    if st.button(
        "✍️ 사업계획서 문안",
        use_container_width=True,
        disabled=client is None,
    ):

        quick_prompt = f"""
현재 입력된 사실만 이용해서
사업계획서의 '{section}' 부분을 작성해줘.

확인되지 않은 사실을 만들지 말고,
정보가 부족한 부분은 [확인 필요]로 표시해줘.
"""


with q3:

    if st.button(
        "🔎 심사위원 평가",
        use_container_width=True,
        disabled=client is None,
    ):

        quick_prompt = """
현재 입력된 사업을
이 지원사업의 심사위원이라고 가정하고 평가해줘.

공식 평가영역을 기준으로
강점, 약점, 탈락 위험,
심사위원이 질문할 부분을 분석하고

마지막에
'가장 먼저 수정할 TOP 3'
를 제시해줘.
"""


with q4:

    if st.button(
        "✅ 제출 전 QA",
        use_container_width=True,
        disabled=client is None,
    ):

        quick_prompt = """
현재까지 입력된 정보를 기준으로
지원사업 제출 전 QA를 해줘.

각 내용을

✅ 확인 완료
⚠️ 확인 필요
❌ 중대한 위험

으로 구분하고

마지막에
제출 전 해야 할 일을
우선순위 순으로 정리해줘.
"""


# ============================================================
# CHAT
# ============================================================

st.markdown("### 💬 AI 상담")


if not st.session_state.messages:

    st.caption(
        "위 빠른 시작 버튼을 누르거나 "
        "아래 입력창에서 자유롭게 질문할 수 있습니다."
    )


for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


chat_prompt = st.chat_input(
    "사업계획서, 공공데이터, 심사 기준 등에 대해 질문해 주세요.",
    disabled=client is None,
)


prompt = (
    quick_prompt
    if quick_prompt
    else chat_prompt
)


# ============================================================
# CALL OPENAI
# ============================================================

if prompt and client:

    # User message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )


    with st.chat_message("user"):

        st.markdown(prompt)


    try:

        with st.chat_message("assistant"):

            with st.spinner(
                "공고 기준으로 검토하고 있습니다..."
            ):

                response = client.responses.create(
                    model="gpt-5.6-luna",
                    instructions=build_system_prompt(),
                    input=[
                        {
                            "role": message["role"],
                            "content": message["content"],
                        }
                        for message in st.session_state.messages
                    ],
                    max_output_tokens=3000,
                )


                answer = response.output_text


                st.markdown(answer)


        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )


    except Exception as exc:

        st.error(
            "AI 답변을 생성하는 중 오류가 발생했습니다."
        )

        st.write(
            "API Key가 유효한지, "
            "API 결제/사용한도가 설정되어 있는지 확인해 주세요."
        )

        with st.expander(
            "오류 상세 보기"
        ):
            st.code(str(exc))


# ============================================================
# BOTTOM ACTIONS
# ============================================================

if st.session_state.messages:

    st.divider()

    bottom1, bottom2 = st.columns(2)


    with bottom1:

        transcript = conversation_markdown(
            st.session_state.messages
        )

        st.download_button(
            "⬇ 현재 상담 내용 다운로드",
            data=transcript,
            file_name="grantmate_chat.md",
            mime="text/markdown",
            use_container_width=True,
        )


    with bottom2:

        if st.button(
            "🗑 대화만 초기화",
            use_container_width=True,
        ):

            st.session_state.messages = []

            st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider
