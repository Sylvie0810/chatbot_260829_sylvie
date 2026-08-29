import hmac
import json
from datetime import date, datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import streamlit as st
from openai import OpenAI


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="GrantMate | 공공데이터 사업계획서 AI Coach",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# UI STYLE
# ============================================================

st.markdown(
    """
<style>

.block-container {
    max-width: 1120px;
    padding-top: 1.7rem;
    padding-bottom: 4rem;
}

[data-testid="stSidebar"] {
    background: #f6f7fb;
    border-right: 1px solid #e6e8ee;
}


/* Sidebar brand */

.gm-brand {
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.gm-sub {
    color: #747987;
    font-size: .86rem;
    margin-bottom: 1rem;
}


/* Top stepper */

.gm-stepper {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: .3rem 0 .6rem;
}

.gm-step {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #9aa0aa;
    font-weight: 700;
    font-size: .92rem;
}

.gm-step.active,
.gm-step.done {
    color: #303642;
}

.gm-step.done {
    color: #2f80ed;
}

.gm-num {
    width: 24px;
    height: 24px;
    border-radius: 7px;

    display: inline-flex;
    align-items: center;
    justify-content: center;

    background: #edf0f5;
    color: #8d94a1;

    font-size: .78rem;
}

.gm-step.active .gm-num,
.gm-step.done .gm-num {
    background: #2f80ed;
    color: white;
}


/* Progress */

.gm-progress {
    height: 7px;

    background: #edf0f5;

    border-radius: 999px;
    overflow: hidden;

    margin-bottom: 2rem;
}

.gm-progress div {
    height: 100%;
    background: #2f80ed;
    border-radius: 999px;
}


/* Hero */

.gm-hero h1 {
    font-size: 2.05rem;
    line-height: 1.2;
    letter-spacing: -0.04em;

    margin: .5rem 0 .5rem;

    color: #252a34;
}

.gm-hero p {
    color: #686f7b;

    margin: 0 0 1.4rem;
}


/* Summary */

.gm-summary {
    background: #fafbfc;

    border: 1px solid #e1e5ec;
    border-radius: 14px;

    padding: 15px 17px;

    margin: .5rem 0 1.2rem;

    line-height: 1.6;

    color: #424854;
}


/* Status */

.gm-ok {
    color: #197144;
    font-weight: 700;
}

.gm-warn {
    color: #a06400;
    font-weight: 700;
}


/* Chat */

div[data-testid="stChatMessage"] {
    border: 1px solid #edf0f3;

    border-radius: 14px;

    padding: .35rem .6rem;

    margin-bottom: .5rem;
}


/* Buttons */

.stButton > button,
.stFormSubmitButton > button {
    border-radius: 10px;
    font-weight: 700;
}


/* Mobile */

@media(max-width:700px) {

    .gm-stepper {
        grid-template-columns: 1fr;
    }

    .gm-hero h1 {
        font-size: 1.65rem;
    }

}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPER
# ============================================================

def secret(name, default=""):

    try:
        return st.secrets[name]

    except Exception:
        return default


def parse_profile(raw):

    if not raw:
        return {}

    try:

        value = json.loads(raw)

        return value if isinstance(value, dict) else {}

    except Exception:

        # 이전 버전 plain text 데이터가 있어도 살려둔다.
        return {
            "extra_context": raw
        }


def profile_text(profile):

    labels = {

        "company_name":
            "기업명",

        "business_item":
            "사업 아이템",

        "stage":
            "현재 단계",

        "problem":
            "해결하려는 문제",

        "needed_data":
            "필요한 공공데이터",

        "data_holder":
            "데이터 보유기관",

        "request_date":
            "공공데이터 신청일",

        "data_result":
            "처리 결과",

        "refusal_reason":
            "제공거부 사유",

        "development":
            "현재 개발단계",

        "extra_context":
            "추가 정보",
    }


    text = "\n".join(

        f"{label}: {profile.get(key)}"

        for key, label in labels.items()

        if profile.get(key)
    )


    return (
        text
        if text
        else "입력된 기업/사업 정보 없음."
    )


def safe_date(
    value,
    fallback=date(2026, 8, 20),
):

    try:

        if value:
            return date.fromisoformat(
                str(value)
            )

        return fallback

    except Exception:

        return fallback


# ============================================================
# SECRETS
# ============================================================

OPENAI_API_KEY = secret(
    "OPENAI_API_KEY"
)

SUPABASE_URL = secret(
    "SUPABASE_URL"
).rstrip("/")

SUPABASE_SECRET_KEY = secret(
    "SUPABASE_SECRET_KEY"
)

APP_PASSWORD = secret(
    "APP_PASSWORD"
)

CHAT_OWNER_ID = secret(
    "CHAT_OWNER_ID",
    "sylvie",
)


DB_ENABLED = bool(
    SUPABASE_URL
    and
    SUPABASE_SECRET_KEY
)


# ============================================================
# OPTIONAL PASSWORD
# ============================================================

# APP_PASSWORD를 Secrets에 넣은 경우에만
# 로그인 화면이 나온다.
#
# APP_PASSWORD를 설정하지 않으면
# 이 과정은 자동으로 생략된다.

if APP_PASSWORD:

    if "authenticated" not in st.session_state:

        st.session_state.authenticated = False


    if not st.session_state.authenticated:

        st.title(
            "🔒 GrantMate"
        )


        with st.form(
            "login"
        ):

            pw = st.text_input(
                "접속 비밀번호",
                type="password",
            )

            submitted = (
                st.form_submit_button(
                    "입장하기",
                    use_container_width=True,
                )
            )


        if submitted:

            if hmac.compare_digest(
                pw,
                APP_PASSWORD,
            ):

                st.session_state.authenticated = True

                st.rerun()

            else:

                st.error(
                    "비밀번호가 올바르지 않습니다."
                )


        st.stop()


# ============================================================
# SUPABASE REST API
# ============================================================

# 중요:
#
# supabase Python 패키지를 사용하지 않는다.
#
# 따라서 requirements.txt에
# supabase를 추가할 필요가 없다.
#
# Streamlit 서버 → Supabase REST API
# 방식으로 직접 저장한다.


def db_request(
    method,
    table,
    query="",
    payload=None,
    prefer="return=representation",
):

    url = (
        f"{SUPABASE_URL}"
        f"/rest/v1/"
        f"{table}"
        f"{query}"
    )


    if payload is not None:

        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode(
            "utf-8"
        )

    else:

        body = None


    headers = {

        "apikey":
            SUPABASE_SECRET_KEY,

        "Authorization":
            f"Bearer {SUPABASE_SECRET_KEY}",

        "Content-Type":
            "application/json",

        "Accept":
            "application/json",

        "Prefer":
            prefer,
    }


    request = Request(

        url=url,

        data=body,

        headers=headers,

        method=method,
    )


    try:

        with urlopen(
            request,
            timeout=12,
        ) as response:

            text = (
                response
                .read()
                .decode("utf-8")
            )


            if text:

                return json.loads(
                    text
                )


            return []


    except (
        HTTPError,
        URLError,
        TimeoutError,
    ) as exc:

        # 앱 전체를 죽이지 않는다.
        # 저장만 비활성화/오류표시한다.

        st.session_state.db_error = (
            str(exc)
        )

        return None


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def list_sessions():

    if not DB_ENABLED:
        return []


    owner = quote(
        CHAT_OWNER_ID,
        safe="",
    )


    data = db_request(

        "GET",

        "chat_sessions",

        (
            f"?owner_id=eq.{owner}"
            "&select="
            "id,title,company_info,"
            "created_at,updated_at"
            "&order=updated_at.desc"
            "&limit=20"
        ),
    )


    return (
        data
        if isinstance(data, list)
        else []
    )


def create_session():

    if not DB_ENABLED:
        return "local"


    now = datetime.now(
        timezone.utc
    ).isoformat()


    data = db_request(

        "POST",

        "chat_sessions",

        payload={

            "owner_id":
                CHAT_OWNER_ID,

            "title":
                "새 상담",

            "company_info":
                "",

            "created_at":
                now,

            "updated_at":
                now,
        },
    )


    if data:

        return data[0]["id"]


    return "local"


def get_session(
    session_id
):

    if (
        not DB_ENABLED
        or
        session_id == "local"
    ):
        return None


    sid = quote(
        str(session_id),
        safe="",
    )

    owner = quote(
        CHAT_OWNER_ID,
        safe="",
    )


    data = db_request(

        "GET",

        "chat_sessions",

        (
            f"?id=eq.{sid}"
            f"&owner_id=eq.{owner}"
            "&select="
            "id,title,company_info,"
            "created_at,updated_at"
            "&limit=1"
        ),
    )


    if data:

        return data[0]


    return None


def load_messages(
    session_id
):

    if (
        not DB_ENABLED
        or
        session_id == "local"
    ):

        return (
            st.session_state.get(
                "local_messages",
                [],
            )
        )


    sid = quote(
        str(session_id),
        safe="",
    )

    owner = quote(
        CHAT_OWNER_ID,
        safe="",
    )


    data = db_request(

        "GET",

        "chat_messages",

        (
            f"?session_id=eq.{sid}"
            f"&owner_id=eq.{owner}"
            "&select="
            "role,content,created_at"
            "&order=created_at.asc"
        ),
    )


    if not data:

        return []


    return [

        {
            "role":
                row["role"],

            "content":
                row["content"],
        }

        for row in data
    ]


def save_message(
    session_id,
    role,
    content,
):

    if (
        not DB_ENABLED
        or
        session_id == "local"
    ):

        st.session_state.local_messages = (
            list(
                st.session_state.messages
            )
        )

        return


    now = datetime.now(
        timezone.utc
    ).isoformat()


    db_request(

        "POST",

        "chat_messages",

        payload={

            "session_id":
                session_id,

            "owner_id":
                CHAT_OWNER_ID,

            "role":
                role,

            "content":
                content,

            "created_at":
                now,
        },
    )


    sid = quote(
        str(session_id),
        safe="",
    )

    owner = quote(
        CHAT_OWNER_ID,
        safe="",
    )


    db_request(

        "PATCH",

        "chat_sessions",

        (
            f"?id=eq.{sid}"
            f"&owner_id=eq.{owner}"
        ),

        payload={
            "updated_at":
                now
        },

        prefer="return=minimal",
    )


def save_profile(
    session_id,
    profile,
):

    raw = json.dumps(
        profile,
        ensure_ascii=False,
    )


    if (
        not DB_ENABLED
        or
        session_id == "local"
    ):

        st.session_state.local_profile = (
            raw
        )

        return


    sid = quote(
        str(session_id),
        safe="",
    )

    owner = quote(
        CHAT_OWNER_ID,
        safe="",
    )


    db_request(

        "PATCH",

        "chat_sessions",

        (
            f"?id=eq.{sid}"
            f"&owner_id=eq.{owner}"
        ),

        payload={

            "company_info":
                raw,

            "updated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        },

        prefer="return=minimal",
    )


def update_title(
    session_id,
    title,
):

    if (
        not DB_ENABLED
        or
        session_id == "local"
    ):

        st.session_state.local_title = (
            title
        )

        return


    sid = quote(
        str(session_id),
        safe="",
    )

    owner = quote(
        CHAT_OWNER_ID,
        safe="",
    )


    db_request(

        "PATCH",

        "chat_sessions",

        (
            f"?id=eq.{sid}"
            f"&owner_id=eq.{owner}"
        ),

        payload={
            "title":
                title
        },

        prefer="return=minimal",
    )


# ============================================================
# INIT SESSION
# ============================================================

if "active_session_id" not in st.session_state:

    if DB_ENABLED:

        sessions = list_sessions()

    else:

        sessions = []


    if sessions:

        st.session_state.active_session_id = (
            sessions[0]["id"]
        )

    else:

        st.session_state.active_session_id = (
            create_session()
        )


def load_active():

    sid = (
        st.session_state
        .active_session_id
    )


    if (
        DB_ENABLED
        and
        sid != "local"
    ):

        session = get_session(
            sid
        )


        if not session:

            sid = create_session()

            st.session_state.active_session_id = (
                sid
            )

            session = get_session(
                sid
            )


        st.session_state.messages = (
            load_messages(
                sid
            )
        )


        st.session_state.company_profile = (
            parse_profile(
                (
                    session
                    or {}
                ).get(
                    "company_info",
                    "",
                )
            )
        )


    else:

        st.session_state.messages = (
            st.session_state.get(
                "local_messages",
                [],
            )
        )


        st.session_state.company_profile = (
            parse_profile(
                st.session_state.get(
                    "local_profile",
                    "",
                )
            )
        )


    st.session_state.loaded_session_id = (
        sid
    )


if (
    st.session_state.get(
        "loaded_session_id"
    )
    !=
    st.session_state.active_session_id
):

    load_active()


if "messages" not in st.session_state:

    st.session_state.messages = []


if "company_profile" not in st.session_state:

    st.session_state.company_profile = {}


# ============================================================
# PROGRAM KNOWLEDGE
# ============================================================

PROGRAM_KNOWLEDGE = """
사업명:
2026 민관협력 오픈이노베이션 지원
'공공데이터 활용 지원'
창업기업 제안 협업 과제(Bottom-Up)

사업목적:
공공기관 보유 데이터를 창업기업에 개방하고
활용하도록 지원해 공공서비스 혁신과
창업기업 성장(Scale-up)을 촉진한다.

선정규모:
공공기관 제안 협업과제와 통합해
총 20개 과제 내외.

지원내용:
- 미개방 공공데이터 확보 지원
- 데이터 분석·처리
- 기술검증(PoC)
- 제품·서비스 개발
- 과제별 최대 1억원 사업화 자금
- 후속 연계 지원

협약기간:
협약 시작일로부터 5개월 이내
2026년 11월 ~ 2027년 3월 예정.

핵심 신청요건:
1. 공고상 창업기업 자격 충족
2. 공공데이터포털을 통해 마감 전 제공신청
3. 보유기관으로부터 '제공 불가' 통보
4. 데이터 미개방/확보 곤란으로 사업 추진 어려움 존재
5. 데이터 확보 후 구체적인 제품·서비스 개발 또는 연구개발 활용계획 제시

공식 평가영역:
1. 공공데이터 활용계획
2. 팀(기업) 구성
3. 실현 가능성 및 구체성
4. 지속가능성

공식 항목별 배점은 공개되어 있지 않다.

대체 개방형태:
- 합성데이터
- 통계데이터
- 익명데이터
- 진위확인서비스

핵심 논리:
문제
→ 필요한 공공데이터
→ 데이터의 필수성
→ 활용방법
→ 구현기능
→ 5개월 PoC
→ 공공기관 가치
→ 고객 가치
→ 사업화·확장

작성원칙:
- 없는 실적을 만들지 않는다.
- 없는 고객을 만들지 않는다.
- 없는 매출을 만들지 않는다.
- 없는 계약을 만들지 않는다.
- 없는 특허를 만들지 않는다.
- 없는 인력이나 기술을 만들지 않는다.
- 확인되지 않은 내용은 '확인 필요'로 표시한다.
- 공고에 없는 요건·배점을 공식 사실처럼 말하지 않는다.
"""


MODE_INSTRUCTIONS = {

    "💬 자유 상담":
        """
질문에 먼저 직접 답한다.
핵심 정보가 부족하면 필요한 정보만 추가 질문한다.
""",

    "✍️ 사업계획서 작성":
        """
현재 확인된 사실만 사용한다.
실제 사업계획서에 붙여 넣을 수 있는 문안을 작성한다.
핵심 정보가 부족하면 그 부분만 먼저 확인한다.
""",

    "🔎 심사위원 평가":
        """
공식 평가영역을 기준으로
강점, 약점, 심사위원의 의심 지점,
탈락 위험, 개선방법을 평가한다.

마지막에 수정 우선순위 TOP 3를 제시한다.
""",

    "✅ 제출 전 점검":
        """
신청자격, 필수 증빙,
사업계획서 논리,
공공데이터 신청 및 거부 이력을 QA한다.

결과는
✅ 확인 완료
⚠️ 확인 필요
❌ 중대한 위험
으로 구분한다.
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

    st.markdown(
        '<div class="gm-brand">📄 GrantMate</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="gm-sub">'
        '공공데이터 사업계획서 AI Coach'
        '</div>',
        unsafe_allow_html=True,
    )


    # --------------------------------
    # OpenAI
    # --------------------------------

    st.markdown(
        "#### 🔑 AI 연결"
    )


    if OPENAI_API_KEY:

        openai_key = (
            OPENAI_API_KEY
        )


        st.markdown(
            '<span class="gm-ok">'
            '● OpenAI 연결됨'
            '</span>',
            unsafe_allow_html=True,
        )


    else:

        openai_key = (
            st.text_input(
                "OpenAI API Key",
                type="password",
                placeholder="sk-...",
            )
        )


        if openai_key:

            status = (
                "● 이번 세션에서 연결됨"
            )

            css_class = (
                "gm-ok"
            )

        else:

            status = (
                "● API 키를 입력해 주세요"
            )

            css_class = (
                "gm-warn"
            )


        st.markdown(
            f'<span class="{css_class}">'
            f'{status}'
            '</span>',
            unsafe_allow_html=True,
        )


    # --------------------------------
    # Progress
    # --------------------------------

    st.divider()

    st.markdown(
        "#### 📌 진행 현황"
    )

    st.caption(
        "1  기업 / 사업 정보"
    )

    st.caption(
        "2  공공데이터 활용계획"
    )

    st.caption(
        "3  과제 해결방안"
    )

    st.caption(
        "4  사업화·실행계획"
    )

    st.caption(
        "5  제출 전 QA"
    )


    # --------------------------------
    # Mode
    # --------------------------------

    st.divider()


    mode = st.selectbox(
        "상담 모드",
        list(
            MODE_INSTRUCTIONS
        ),
    )


    section = st.selectbox(
        "집중 검토 항목",
        SECTIONS,
    )


    # --------------------------------
    # Storage
    # --------------------------------

    st.divider()


    if DB_ENABLED:

        st.markdown(
            '<span class="gm-ok">'
            '☁ 대화 자동 저장 ON'
            '</span>',
            unsafe_allow_html=True,
        )


        if st.button(
            "＋ 새 상담",
            use_container_width=True,
        ):

            st.session_state.active_session_id = (
                create_session()
            )

            st.session_state.loaded_session_id = None

            st.rerun()


        sessions = list_sessions()


        if sessions:

            st.caption(
                "최근 상담"
            )


            for row in sessions[:8]:

                if (
                    row["id"]
                    ==
                    st.session_state.active_session_id
                ):

                    prefix = "● "

                else:

                    prefix = ""


                title = (
                    row.get("title")
                    or
                    "새 상담"
                )


                if st.button(
                    prefix + title,
                    key=f"hist_{row['id']}",
                    use_container_width=True,
                ):

                    st.session_state.active_session_id = (
                        row["id"]
                    )

                    st.session_state.loaded_session_id = None

                    st.rerun()


    else:

        st.markdown(
            '<span class="gm-warn">'
            '☁ 영구 저장 OFF'
            '</span>',
            unsafe_allow_html=True,
        )


        st.caption(
            "SUPABASE_URL / "
            "SUPABASE_SECRET_KEY를 "
            "Streamlit Secrets에 넣으면 "
            "자동 저장이 켜집니다."
        )


        if st.button(
            "＋ 새 상담",
            use_container_width=True,
        ):

            st.session_state.local_messages = []

            st.session_state.local_profile = ""

            st.session_state.messages = []

            st.session_state.company_profile = {}

            st.rerun()


    if st.session_state.get(
        "db_error"
    ):

        with st.expander(
            "저장 연결 오류"
        ):

            st.code(
                st.session_state.db_error
            )


# ============================================================
# TOP STEPPER
# ============================================================

profile = (
    st.session_state.company_profile
)

has_profile = bool(
    profile.get("business_item")
    or
    profile.get("needed_data")
)

has_messages = bool(
    st.session_state.messages
)


if has_messages:

    step = 3

elif has_profile:

    step = 2

else:

    step = 1


progress = {
    1: 33,
    2: 66,
    3: 100,
}[step]


classes = [

    (
        "done"
        if i < step
        else
        "active"
        if i == step
        else
        ""
    )

    for i in (
        1,
        2,
        3,
    )
]


st.markdown(
    f"""
<div class="gm-stepper">

<div class="gm-step {classes[0]}">
<span class="gm-num">1</span>
기업 / 사업 입력
</div>

<div class="gm-step {classes[1]}">
<span class="gm-num">2</span>
공공데이터 전략 점검
</div>

<div class="gm-step {classes[2]}">
<span class="gm-num">3</span>
AI와 함께 작성
</div>

</div>

<div class="gm-progress">
<div style="width:{progress}%"></div>
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
먼저 사업과 필요한 데이터를 알려주세요.
부족한 부분은 AI가 질문하고,
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
공고 요건과 평가 관점에 맞춰
질문·작성·레드팀 검토를 이어가세요.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# PROFILE FORM
# ============================================================

with st.expander(
    "🏢 기업 / 사업 정보",
    expanded=not has_profile,
):

    p = (
        st.session_state
        .company_profile
    )


    with st.form(
        f"profile_"
        f"{st.session_state.active_session_id}"
    ):

        c1, c2 = (
            st.columns(2)
        )


        with c1:

            company_name = (
                st.text_input(
                    "기업명",
                    value=p.get(
                        "company_name",
                        "",
                    ),
                    placeholder="예: 수미헬스",
                )
            )


        with c2:

            stages = [

                "아이디어 구상 중",

                "시장 조사 중",

                "준비/세팅 중",

                "운영 시작 (1년 미만)",

                "운영 중 (1년 이상)",
            ]


            current_stage = p.get(
                "stage",
                "준비/세팅 중",
            )


            if current_stage in stages:

                stage_index = (
                    stages.index(
                        current_stage
                    )
                )

            else:

                stage_index = 2


            stage = (
                st.selectbox(
                    "현재 단계",
                    stages,
                    index=stage_index,
                )
            )


        business_item = (
            st.text_input(
                "사업 아이템",
                value=p.get(
                    "business_item",
                    "",
                ),
                placeholder=(
                    "예: 공공데이터 기반 "
                    "양압기 환자관리·행정업무 "
                    "지원 AI 서비스"
                ),
            )
        )


        problem = (
            st.text_area(
                "해결하려는 문제",
                value=p.get(
                    "problem",
                    "",
                ),
                height=100,
                placeholder=(
                    "누가 어떤 업무에서 "
                    "어떤 문제를 겪고 있는지 "
                    "적어주세요."
                ),
            )
        )


        needed_data = (
            st.text_area(
                "필요한 공공데이터",
                value=p.get(
                    "needed_data",
                    "",
                ),
                height=95,
                placeholder=(
                    "필요 데이터명과 "
                    "주요 항목을 적어주세요."
                ),
            )
        )


        c3, c4 = (
            st.columns(2)
        )


        with c3:

            data_holder = (
                st.text_input(
                    "데이터 보유기관",
                    value=p.get(
                        "data_holder",
                        "",
                    ),
                    placeholder=(
                        "예: 국민건강보험공단"
                    ),
                )
            )


        with c4:

            request_date = (
                st.date_input(
                    "공공데이터 신청일",
                    value=safe_date(
                        p.get(
                            "request_date"
                        )
                    ),
                )
            )


        c5, c6 = (
            st.columns(2)
        )


        with c5:

            results = [

                "제공 불가",

                "처리 중",

                "제공",

                "기타",
            ]


            current_result = (
                p.get(
                    "data_result",
                    "제공 불가",
                )
            )


            if current_result in results:

                result_index = (
                    results.index(
                        current_result
                    )
                )

            else:

                result_index = 0


            data_result = (
                st.selectbox(
                    "처리 결과",
                    results,
                    index=result_index,
                )
            )


        with c6:

            refusal_reason = (
                st.text_input(
                    "제공거부 사유",
                    value=p.get(
                        "refusal_reason",
                        "",
                    ),
                    placeholder=(
                        "예: 추가 가공 필요"
                    ),
                )
            )


        development = (
            st.text_area(
                "현재 개발단계 / 보유 기능",
                value=p.get(
                    "development",
                    "",
                ),
                height=95,
            )
        )


        extra_context = (
            st.text_area(
                "추가 정보 (선택)",
                value=p.get(
                    "extra_context",
                    "",
                ),
                height=90,
                placeholder=(
                    "제공불가 상세사유, "
                    "팀 역량, 고객, "
                    "수익모델 등"
                ),
            )
        )


        save = (
            st.form_submit_button(
                "정보 저장하고 AI 코칭 시작 →",
                use_container_width=True,
                type="primary",
            )
        )


    if save:

        new_profile = {

            "company_name":
                company_name.strip(),

            "business_item":
                business_item.strip(),

            "stage":
                stage,

            "problem":
                problem.strip(),

            "needed_data":
                needed_data.strip(),

            "data_holder":
                data_holder.strip(),

            "request_date":
                request_date.isoformat(),

            "data_result":
                data_result,

            "refusal_reason":
                refusal_reason.strip(),

            "development":
                development.strip(),

            "extra_context":
                extra_context.strip(),
        }


        st.session_state.company_profile = (
            new_profile
        )


        save_profile(
            st.session_state.active_session_id,
            new_profile,
        )


        st.success(
            "기업 / 사업 정보를 저장했습니다."
        )


        st.rerun()


# ============================================================
# PROFILE SUMMARY
# ============================================================

profile = (
    st.session_state
    .company_profile
)


has_profile = bool(
    profile.get("business_item")
    or
    profile.get("needed_data")
)


if has_profile:

    items = []


    if profile.get(
        "company_name"
    ):

        items.append(
            f"<b>기업</b> "
            f"{profile['company_name']}"
        )


    if profile.get(
        "business_item"
    ):

        items.append(
            f"<b>아이템</b> "
            f"{profile['business_item']}"
        )


    if profile.get(
        "data_holder"
    ):

        items.append(
            f"<b>데이터</b> "
            f"{profile['data_holder']}"
        )


    if profile.get(
        "data_result"
    ):

        items.append(
            f"<b>처리결과</b> "
            f"{profile['data_result']}"
        )


    st.markdown(
        (
            '<div class="gm-summary">'
            +
            " &nbsp;·&nbsp; ".join(
                items
            )
            +
            '</div>'
        ),
        unsafe_allow_html=True,
    )


# ============================================================
# OPENAI
# ============================================================

if openai_key:

    client = OpenAI(
        api_key=openai_key
    )

else:

    client = None


    st.info(
        "왼쪽 사이드바에 "
        "OpenAI API Key를 입력하면 "
        "AI 상담을 시작할 수 있습니다."
    )


# ============================================================
# SYSTEM PROMPT
# ============================================================

def system_prompt():

    return f"""
당신은 대한민국 정부지원사업 전문 컨설턴트이며,
2026년 민관협력 오픈이노베이션
'공공데이터 활용 지원' Bottom-Up 사업계획서
작성·평가를 돕는 AI Coach다.

무조건 긍정적으로 평가하지 않는다.
심사 위험과 논리적 약점을 찾아
실제 선정 가능성을 높인다.


[공식 사업 정보]

{PROGRAM_KNOWLEDGE}


[상담 모드]

{mode}

{MODE_INSTRUCTIONS[mode]}


[집중 검토 항목]

{section}


[기업 / 사업 정보]

{profile_text(
    st.session_state.company_profile
)}


[반드시 지킬 규칙]

1.
공고 사실과 사용자가 제공한 사실을 구분한다.

2.
확인되지 않은 사실을 만들지 않는다.

3.
정보가 부족하면 필요한 최소 질문만 한다.

4.
다음 연결을 가장 중요하게 본다.

문제
→ 공공데이터
→ 데이터 필수성
→ 구현 기능
→ PoC
→ 공공기관 가치
→ 고객 가치
→ 사업화

5.
공공데이터 없이도
동일한 서비스를 만들 수 있다는
반론을 항상 점검한다.

6.
5개월 협약기간 내
실현 가능성을 검토한다.

7.
단순히 'AI를 활용한다'는 이유만으로
차별성이 있다고 판단하지 않는다.

8.
공식 배점이 공개되지 않았으므로
임의 점수를 공식 평가점수처럼 표현하지 않는다.

9.
한국어로 간결하고 구체적으로 답한다.
"""


# ============================================================
# QUICK ACTIONS
# ============================================================

st.markdown(
    "#### 빠른 시작"
)


q1, q2, q3, q4 = (
    st.columns(4)
)


quick = None


with q1:

    if st.button(
        "🧩 데이터 필요성",
        use_container_width=True,
    ):

        quick = (
            "요청한 공공데이터가 왜 반드시 필요한지, "
            "데이터 없이도 만들 수 있다는 반론까지 포함해 "
            "레드팀 평가해줘."
        )


with q2:

    if st.button(
        "✍️ 문안 작성",
        use_container_width=True,
    ):

        quick = (
            f"사업계획서의 '{section}' 항목을 "
            "현재 확인된 사실만 사용해서 작성해줘."
        )


with q3:

    if st.button(
        "🔎 심사위원 평가",
        use_container_width=True,
    ):

        quick = (
            "공고의 공식 평가영역 기준으로 "
            "현재 사업계획을 평가하고, "
            "가장 큰 탈락 위험과 "
            "수정 우선순위 TOP 3를 알려줘."
        )


with q4:

    if st.button(
        "✅ 제출 전 QA",
        use_container_width=True,
    ):

        quick = (
            "현재까지 입력된 내용을 기준으로 "
            "제출 전 QA를 해줘. "
            "확인 완료/확인 필요/중대한 위험으로 "
            "구분해줘."
        )


# ============================================================
# CHAT
# ============================================================

st.markdown(
    "#### AI 상담"
)


for message in (
    st.session_state.messages
):

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


chat = st.chat_input(
    (
        "사업계획서, 공공데이터, "
        "심사 기준 등에 대해 질문해 주세요."
    ),
    disabled=client is None,
)


prompt = (
    quick
    or
    chat
)


if (
    prompt
    and
    client
):

    sid = (
        st.session_state
        .active_session_id
    )


    first = (
        len(
            st.session_state.messages
        )
        ==
        0
    )


    st.session_state.messages.append(
        {
            "role":
                "user",

            "content":
                prompt,
        }
    )


    save_message(
        sid,
        "user",
        prompt,
    )


    if first:

        title = (
            prompt
            .strip()
            .replace(
                "\n",
                " ",
            )
        )


        if len(title) > 30:

            title = (
                title[:30]
                +
                "…"
            )


        update_title(
            sid,
            title,
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

                        instructions=(
                            system_prompt()
                        ),

                        input=[

                            {
                                "role":
                                    message["role"],

                                "content":
                                    message["content"],
                            }

                            for message
                            in
                            st.session_state.messages
                        ],
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
                "role":
                    "assistant",

                "content":
                    answer,
            }
        )


        save_message(
            sid,
            "assistant",
            answer,
        )


    except Exception as exc:

        st.error(
            "OpenAI API 호출 중 오류가 발생했습니다."
        )

        st.code(
            str(exc)
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "GrantMate는 강좌 실습용 AI 도구입니다. "
    "최종 신청 전에는 반드시 공식 모집공고와 "
    "K-Startup 제출 내용을 직접 확인하세요."
)
