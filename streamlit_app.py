import hmac
from datetime import datetime, timezone

import streamlit as st
from openai import OpenAI
from supabase import create_client


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="GrantMate | 공공데이터 사업계획서 AI Coach",
    page_icon="📄",
    layout="wide",
)


# ============================================================
# HELPERS
# ============================================================

def get_secret(name, default=""):
    try:
        return st.secrets[name]
    except Exception:
        return default


# ============================================================
# REQUIRED SECRETS
# ============================================================

OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET_KEY = get_secret("SUPABASE_SECRET_KEY")
APP_PASSWORD = get_secret("APP_PASSWORD")
CHAT_OWNER_ID = get_secret("CHAT_OWNER_ID")


missing_secrets = []

if not SUPABASE_URL:
    missing_secrets.append("SUPABASE_URL")

if not SUPABASE_SECRET_KEY:
    missing_secrets.append("SUPABASE_SECRET_KEY")

if not APP_PASSWORD:
    missing_secrets.append("APP_PASSWORD")

if not CHAT_OWNER_ID:
    missing_secrets.append("CHAT_OWNER_ID")


if missing_secrets:
    st.error(
        "Streamlit Secrets 설정이 필요합니다: "
        + ", ".join(missing_secrets)
    )
    st.stop()


# ============================================================
# PASSWORD GATE
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


if not st.session_state.authenticated:

    st.title("🔒 GrantMate")

    st.write(
        "저장된 사업계획서 상담 내용을 보호하기 위해 "
        "접속 비밀번호가 필요합니다."
    )

    with st.form("login_form"):

        entered_password = st.text_input(
            "비밀번호",
            type="password",
        )

        login_button = st.form_submit_button(
            "입장하기",
            use_container_width=True,
        )

    if login_button:

        if hmac.compare_digest(
            entered_password,
            APP_PASSWORD,
        ):
            st.session_state.authenticated = True
            st.rerun()

        else:
            st.error("비밀번호가 올바르지 않습니다.")

    st.stop()


# ============================================================
# CLIENTS
# ============================================================

@st.cache_resource
def get_supabase_client(url, secret_key):
    return create_client(url, secret_key)


supabase = get_supabase_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


if OPENAI_API_KEY:

    openai_api_key = OPENAI_API_KEY

else:

    openai_api_key = st.text_input(
        "🔑 OpenAI API Key",
        type="password",
    )

    if not openai_api_key:

        st.info(
            "OpenAI API Key를 입력하세요.",
            icon="🗝️",
        )

        st.stop()


client = OpenAI(
    api_key=openai_api_key
)


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def list_chat_sessions():

    result = (
        supabase
        .table("chat_sessions")
        .select(
            "id, title, company_info, created_at, updated_at"
        )
        .eq(
            "owner_id",
            CHAT_OWNER_ID,
        )
        .order(
            "updated_at",
            desc=True,
        )
        .limit(20)
        .execute()
    )

    return result.data or []


def get_chat_session(session_id):

    result = (
        supabase
        .table("chat_sessions")
        .select(
            "id, title, company_info, created_at, updated_at"
        )
        .eq(
            "id",
            session_id,
        )
        .eq(
            "owner_id",
            CHAT_OWNER_ID,
        )
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def create_chat_session():

    now = datetime.now(
        timezone.utc
    ).isoformat()

    result = (
        supabase
        .table("chat_sessions")
        .insert(
            {
                "owner_id": CHAT_OWNER_ID,
                "title": "새 상담",
                "company_info": "",
                "created_at": now,
                "updated_at": now,
            }
        )
        .execute()
    )

    return result.data[0]["id"]


def load_messages(session_id):

    result = (
        supabase
        .table("chat_messages")
        .select(
            "role, content, created_at"
        )
        .eq(
            "session_id",
            session_id,
        )
        .eq(
            "owner_id",
            CHAT_OWNER_ID,
        )
        .order(
            "created_at"
        )
        .execute()
    )

    return [
        {
            "role": row["role"],
            "content": row["content"],
        }
        for row in (result.data or [])
    ]


def save_message(
    session_id,
    role,
    content,
):

    now = datetime.now(
        timezone.utc
    ).isoformat()

    (
        supabase
        .table("chat_messages")
        .insert(
            {
                "session_id": session_id,
                "owner_id": CHAT_OWNER_ID,
                "role": role,
                "content": content,
                "created_at": now,
            }
        )
        .execute()
    )

    (
        supabase
        .table("chat_sessions")
        .update(
            {
                "updated_at": now,
            }
        )
        .eq(
            "id",
            session_id,
        )
        .eq(
            "owner_id",
            CHAT_OWNER_ID,
        )
        .execute()
    )


def update_session_title(
    session_id,
    title,
):

    (
        supabase
        .table("chat_sessions")
        .update(
            {
                "title": title,
            }
        )
        .eq(
            "id",
            session_id,
        )
        .eq(
            "owner_id",
            CHAT_OWNER_ID,
        )
        .execute()
    )


def save_company_info(
    session_id,
    company_info,
):

    now = datetime.now(
        timezone.utc
    ).isoformat()

    (
        supabase
        .table("chat_sessions")
        .update(
            {
                "company_info": company_info,
                "updated_at": now,
            }
        )
        .eq(
            "id",
            session_id,
        )
        .eq(
            "owner_id",
            CHAT_OWNER_ID,
        )
        .execute()
    )


# ============================================================
# INITIAL CHAT SESSION
# ============================================================

if "active_session_id" not in st.session_state:

    existing_sessions = list_chat_sessions()

    if existing_sessions:

        st.session_state.active_session_id = (
            existing_sessions[0]["id"]
        )

    else:

        st.session_state.active_session_id = (
            create_chat_session()
        )


# ============================================================
# LOAD SESSION
# ============================================================

def load_active_session():

    session_id = (
        st.session_state.active_session_id
    )

    session = get_chat_session(
        session_id
    )

    if not session:
        session_id = create_chat_session()

        st.session_state.active_session_id = (
            session_id
        )

        session = get_chat_session(
            session_id
        )

    st.session_state.messages = (
        load_messages(session_id)
    )

    st.session_state.company_info = (
        session.get(
            "company_info",
            "",
        )
        or ""
    )

    st.session_state.loaded_session_id = (
        session_id
    )


if (
    st.session_state.get(
        "loaded_session_id"
    )
    != st.session_state.active_session_id
):
    load_active_session()


# ============================================================
# PROGRAM KNOWLEDGE
# ============================================================

PROGRAM_KNOWLEDGE = """
사업명:
2026 민관협력 오픈이노베이션 지원
'공공데이터 활용 지원'
창업기업 제안 협업 과제(Bottom-Up)

사업 목적:
공공기관이 보유한 데이터를 창업기업에 개방하고
활용을 지원하여 공공서비스 혁신과 창업기업의
성장(Scale-up)을 촉진한다.

선정 규모:
공공기관 제안 과제와 통합하여 총 20개 과제 내외

지원 내용:
- 미개방 공공데이터 확보 지원
- 공공기관과 데이터 제공 조건 협의
- 공공데이터 분석·처리
- 기술검증(PoC)
- 제품·서비스 개발
- 사업화 자금 과제별 최대 1억원
- 후속 기술개발 사업 연계

협약기간:
협약 시작일로부터 5개월 이내
예정: 2026년 11월 ~ 2027년 3월

핵심 신청요건:

1.
공고에서 정하는 창업기업 자격을 충족해야 한다.

2.
공공데이터포털(data.go.kr)을 통해
공고 마감일 이전 데이터 제공신청을 했어야 한다.

3.
보유기관으로부터 '제공 불가' 통보를 받은
경험이 있어야 한다.

4.
필요 데이터가 미개방 또는 확보 곤란하여
사업 추진에 실제 어려움이 있어야 한다.

5.
데이터 확보 후 제품·서비스 개발 또는
연구개발 등에 활용할 구체적인 계획이 필요하다.

6.
단순 정보수집·열람·출판 목적은 제외된다.


공고문 공식 평가영역:

1. 공공데이터 활용계획

- 기존 제공거부 경험
- 미개방 데이터 활용목적
- 활용내용
- 필요 데이터 요구항목의 구체성

2. 팀(기업) 구성

- 보유기술
- 인력 전문성
- 관련 프로젝트 또는 연구 경험

3. 실현 가능성 및 구체성

- 데이터 확보 이후 사업화 추진계획
- 기술·서비스 구현계획
- 구체성
- 차별성

4. 지속가능성

- 사업화 가능성
- 협업 종료 후 지속·유지 가능성
- 수익성 검증


공식 평가항목별 배점은 공개되어 있지 않다.


사업계획서 주요 항목:

- 필요 데이터명
- 필요 항목
- 예상 보유기관
- 데이터 제공신청 경험
- 신청 기관
- 신청 일자
- 제공거부 사유
- 데이터 형식
- 제공 주기
- 제공 범위
- 대체 개방형태
- 과제 해결방안
- 기술 경쟁력
- 최종 산출물
- 현재 개발단계
- 사업화 방안
- 대표자 및 팀 역량
- 협약기간 추진계획
- 정부지원사업비
- 기업현황


대체 개방형태:

1. 합성데이터
2. 통계데이터
3. 익명데이터
4. 진위확인서비스


핵심 사업 논리:

시장 또는 공공서비스의 실제 문제
→ 왜 현재 방식으로 해결되지 않는가
→ 어떤 공공데이터가 필요한가
→ 왜 그 데이터가 반드시 필요한가
→ 데이터를 받아 무엇을 분석/구현하는가
→ 어떤 제품 또는 서비스 기능이 만들어지는가
→ 5개월 동안 무엇을 검증하는가
→ 공공기관에는 어떤 가치가 생기는가
→ 고객에게 어떤 가치가 생기는가
→ 협약 종료 후 어떻게 사업화·확장되는가


작성 원칙:

- 존재하지 않는 실적을 만들지 않는다.
- 존재하지 않는 고객을 만들지 않는다.
- 존재하지 않는 매출을 만들지 않는다.
- 존재하지 않는 특허를 만들지 않는다.
- 사용자가 제공하지 않은 사실을 만들지 않는다.
- 모르는 정보는 '확인 필요'라고 표시한다.
- 공고에 없는 요건을 공식 요건처럼 말하지 않는다.
- 공고에 없는 배점을 공식 점수처럼 말하지 않는다.
"""


# ============================================================
# MODE SETTINGS
# ============================================================

MODE_INSTRUCTIONS = {

    "💬 자유 상담":
    """
사용자의 질문에 정부지원사업 전문 컨설턴트처럼 답한다.

질문에 직접 답할 수 있으면 먼저 답한다.
중요 정보가 부족하면 추측하지 말고 질문한다.
""",

    "✍️ 사업계획서 작성":
    """
사업계획서 작성 코치 역할을 한다.

정보가 부족하다면:
1. 현재 확인된 정보
2. 부족한 정보
3. 반드시 확인할 질문

순으로 제시한다.

충분한 정보가 있다면
실제 사업계획서에 사용할 수 있는 문안 초안을 작성한다.
""",

    "🔎 심사위원 평가":
    """
가상의 심사위원 역할을 한다.

다음 공식 평가영역으로 검토한다.

1. 공공데이터 활용계획
2. 팀(기업) 구성
3. 실현 가능성 및 구체성
4. 지속가능성

각 영역별로:

- 강점
- 약점
- 심사위원이 의심할 부분
- 탈락 위험
- 개선방법

을 제시한다.

마지막에는
'가장 먼저 수정할 TOP 3'을 제시한다.

공식 배점은 공개되지 않았으므로
임의 점수를 공식점수처럼 표현하지 않는다.
""",

    "✅ 제출 전 점검":
    """
정부지원사업 제출 전 QA 담당자로 행동한다.

결과를:

✅ 확인 완료
⚠️ 확인 필요
❌ 중대한 누락 또는 위험

으로 구분한다.

마지막에는
'제출 전 해야 할 일'을
우선순위로 정리한다.
"""
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

    st.header("💬 상담 기록")

    if st.button(
        "➕ 새 상담",
        use_container_width=True,
    ):

        new_id = create_chat_session()

        st.session_state.active_session_id = (
            new_id
        )

        st.session_state.loaded_session_id = None

        st.rerun()


    sessions = list_chat_sessions()

    st.caption("최근 상담")

    for session in sessions:

        title = (
            session.get("title")
            or "새 상담"
        )

        session_id = session["id"]

        if st.button(
            title,
            key=f"session_{session_id}",
            use_container_width=True,
        ):

            st.session_state.active_session_id = (
                session_id
            )

            st.session_state.loaded_session_id = None

            st.rerun()


    st.divider()

    st.header("⚙️ 상담 설정")

    mode = st.selectbox(
        "상담 모드",
        list(
            MODE_INSTRUCTIONS.keys()
        ),
    )

    section = st.selectbox(
        "검토할 사업계획서 항목",
        SECTIONS,
    )


    st.divider()

    st.header("🏢 기업 / 사업 정보")

    st.text_area(
        "알고 있는 내용을 자유롭게 입력하세요.",
        height=300,
        key="company_info",
        placeholder="""예시

기업명:
사업 아이템:
해결하려는 문제:
필요한 공공데이터:
데이터 보유기관:
공공데이터 신청일:
처리 결과:
제공거부 사유:
개발할 서비스:
현재 개발단계:
기존 실적:
팀 구성:
고객:
수익모델:
""",
    )

    if st.button(
        "💾 기업 정보 저장",
        use_container_width=True,
    ):

        save_company_info(
            st.session_state.active_session_id,
            st.session_state.company_info,
        )

        st.success("저장되었습니다.")


    st.divider()

    st.caption(
        "☁️ 대화 내용은 Supabase에 자동 저장됩니다."
    )


# ============================================================
# TITLE
# ============================================================

st.title("📄 GrantMate")

st.write(
    "### 공공데이터 활용 지원사업 사업계획서 AI Coach"
)

st.info(
    "💾 대화 내용이 자동 저장됩니다. "
    "브라우저를 닫았다 다시 접속해도 "
    "왼쪽의 최근 상담에서 이전 대화를 다시 열 수 있습니다."
)


# ============================================================
# DISPLAY CHAT
# ============================================================

if not st.session_state.messages:

    st.subheader("무엇을 물어볼 수 있나요?")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            """
**사업 검토**

- 이 아이디어가 사업 취지에 맞나요?
- 공공데이터가 정말 필요한가요?
- 데이터 요청 내용이 적절한가요?
"""
        )

    with col2:

        st.markdown(
            """
**사업계획서 작성**

- 공공데이터 활용계획을 작성해 주세요.
- 과제 해결방안을 검토해 주세요.
- 심사위원 입장에서 평가해 주세요.
"""
        )


for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):
        st.markdown(
            message["content"]
        )


# ============================================================
# SYSTEM PROMPT
# ============================================================

def build_system_prompt():

    company_info = (
        st.session_state.get(
            "company_info",
            "",
        )
    )

    return f"""
당신은 대한민국 정부지원사업 전문 컨설턴트이며,
특히 2026년 민관협력 오픈이노베이션
'공공데이터 활용 지원' Bottom-Up 사업의
사업계획서 작성과 평가를 돕는 AI Coach다.

목표는 사용자의 사업을 무조건 좋게 평가하는 것이 아니다.

사업의 논리적 약점과 심사 위험을 찾아내고,
필요한 정보를 질문하고,
실제 평가 경쟁력을 높이도록 돕는다.


[공식 사업 정보]

{PROGRAM_KNOWLEDGE}


[현재 상담 모드]

{mode}

{MODE_INSTRUCTIONS[mode]}


[현재 검토 항목]

{section}


[기업 / 사업 정보]

{company_info if company_info.strip() else "입력된 기업 정보 없음."}


[반드시 지켜야 할 규칙]

1.
공고문 사실과 사용자가 제공한 정보를 구분한다.

2.
사용자가 제공하지 않은 실적, 매출,
고객, 계약, 특허, 기술 등을 만들어내지 않는다.

3.
판단할 정보가 부족하면 추측하지 않고 질문한다.

4.
다음 연결관계를 가장 중요하게 검토한다.

문제
→ 필요한 공공데이터
→ 데이터 활용
→ 구현 기능
→ PoC
→ 고객 가치
→ 공공기관 가치
→ 사업화

5.
공공데이터 없이 동일 서비스를 쉽게 만들 수 있다면
그 점을 명확하게 지적한다.

6.
단순히 'AI를 사용한다'는 이유만으로
기술적 차별성이 있다고 평가하지 않는다.

7.
5개월 협약기간에 실제 구현 가능한 범위인지 검토한다.

8.
지원금을 위한 억지 사업이 아니라
협약 종료 후에도 지속 가능한 사업인지 검토한다.

9.
과장된 표현보다 구체적인 문제,
데이터, 기능, 산출물, 검증방법을 우선한다.

10.
확인되지 않은 내용은 '확인 필요'라고 표시한다.

11.
공식 배점이 공개되지 않았으므로
임의 점수를 공식점수처럼 표현하지 않는다.

12.
답변은 한국어로 명확하고 구조적으로 작성한다.

13.
사용자가 이미 충분한 정보를 제공했다면
불필요한 질문을 반복하지 않는다.
"""


# ============================================================
# CHAT INPUT
# ============================================================

prompt = st.chat_input(
    "사업계획서, 공공데이터, 심사 기준 등에 대해 질문해 주세요."
)


if prompt:

    session_id = (
        st.session_state.active_session_id
    )

    current_session = get_chat_session(
        session_id
    )


    # --------------------------------
    # First message -> auto title
    # --------------------------------

    if (
        current_session
        and current_session.get("title") == "새 상담"
    ):

        title = prompt.strip()

        if len(title) > 28:
            title = title[:28] + "…"

        update_session_title(
            session_id,
            title,
        )


    # --------------------------------
    # Save user message
    # --------------------------------

    user_message = {
        "role": "user",
        "content": prompt,
    }

    st.session_state.messages.append(
        user_message
    )

    save_message(
        session_id,
        "user",
        prompt,
    )


    with st.chat_message("user"):
        st.markdown(prompt)


    # --------------------------------
    # OpenAI response
    # --------------------------------

    try:

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "사업계획서를 검토하고 있습니다..."
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
                    )
                )

                answer = response.output_text

                st.markdown(answer)


        # --------------------------------
        # Save AI response
        # --------------------------------

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        save_message(
            session_id,
            "assistant",
            answer,
        )


    except Exception as e:

        st.error(
            "OpenAI API 호출 중 오류가 발생했습니다."
        )

        st.code(str(e))


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "GrantMate는 강좌 실습용 AI 도구입니다. "
    "최종 사업 신청 전에는 반드시 공식 모집공고와 "
    "K-Startup 제출 내용을 직접 확인하세요."
)
