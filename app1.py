import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import streamlit as st


st.set_page_config(
    page_title="NOOKA | Ethiopian SHINASHA TRADITIONAL CLOTHES AND FOOD",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


GREEN = "#16844A"
YELLOW = "#F2C94C"
RED = "#C53D3D"
INK = "#18322B"
CREAM = "#FBF8F1"

DEFAULT_ORDER_ITEMS = [
    {"category": "ልብስ", "name": "የወንዶች ባህላዊ ካባ", "price": 4000},
    {"category": "ልብስ", "name": "የሴቶች  ባህላዊ ልብስ", "price": 1800},
    {"category": "ምግብ", "name": "ዶሮ በ ሺናሻ ጩምቦ ተከሽኖ ", "price": 4500},
    {"category": "ምግብ", "name": "የበዓል ምግብ ጥቅል", "price": 950},
]

HOME_DEFAULTS: dict[str, str] = {
    "hero_ribbon": "Ethiopian heritage · made with care",
    "hero_title": "የኢትዮጵያ ቅርስ<br>በአንድ ቦታ",
    "hero_body": (
        "በባህላዊ ልብስ እና በጣፋጭ የኢትዮጵያ ምግቦች የቤተሰብ ትውስታዎችን "
        "እንፈጥራለን። ከእጅ የተሰሩ የባህል ልብሶችን እና በፍቅር የተዘጋጁ "
        "ምግቦችን ያግኙ።"
    ),
}

ABOUT_DEFAULTS: dict[str, str] = {
    "title": "ስለ እኛ · About Us",
    "body": (
        "ኖካ / NOOKA የተመሰረተው የኢትዮጵያን ባህላዊ ልብስ እና ምግብ ከቤተሰብ ወደ ቤተሰብ "
        "ለማድረስ ነው። እያንዳንዱ ምርት በጥንቃቄ እና በፍቅር የተዘጋጀ ነው።"
    ),
}

ADMIN_URL_PARAM = "admin_key"
ADMIN_SECRET_PASS = "nooka2026"  # የአድሚን መግቢያ ሚስጥር ቁጥር

STORE_PATH = Path(__file__).with_name("storefront_data.json")
PHOTO_DIR = Path(__file__).with_name("product_photos")
STORE_LOCK = Lock()


def _default_store() -> dict[str, Any]:
    return {
        "items": [
            {**item, "id": f"default-{index + 1}", "photo_filename": ""}
            for index, item in enumerate(DEFAULT_ORDER_ITEMS)
        ],
        "orders": [],
        "home": dict(HOME_DEFAULTS),
        "about": dict(ABOUT_DEFAULTS),
    }


def _read_store_unlocked() -> dict[str, Any]:
    if not STORE_PATH.exists():
        return _default_store()
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_store()

    if not isinstance(data, dict):
        return _default_store()

    return {
        "items": data.get("items", _default_store()["items"]),
        "orders": data.get("orders", []),
        "home": data.get("home", dict(HOME_DEFAULTS)),
        "about": data.get("about", dict(ABOUT_DEFAULTS)),
    }


def read_store() -> dict[str, Any]:
    with STORE_LOCK:
        return _read_store_unlocked()


def update_store(mutator: Any) -> Any:
    with STORE_LOCK:
        store = _read_store_unlocked()
        result = mutator(store)
        temporary_path = STORE_PATH.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(STORE_PATH)
        return result


def add_order(order: dict[str, Any]) -> dict[str, Any]:
    def mutate(store: dict[str, Any]) -> dict[str, Any]:
        order_number = f"KB-{len(store['orders']) + 1:04d}"
        created_order = {
            **order,
            "number": order_number,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        store["orders"].append(created_order)
        return created_order

    return update_store(mutate)


def update_order_status(order_number: str, status: str) -> bool:
    def mutate(store: dict[str, Any]) -> bool:
        for order in store["orders"]:
            if order.get("number") == order_number:
                order["status"] = status
                return True
        return False

    return update_store(mutate)


def add_catalog_item(category: str, name: str, price: int, photo_filename: str = "") -> None:
    def mutate(store: dict[str, Any]) -> None:
        store["items"].append(
            {
                "id": f"product-{uuid4().hex}",
                "category": category,
                "name": name,
                "price": price,
                "photo_filename": photo_filename,
            }
        )

    update_store(mutate)


def _product_photo_path(filename: str) -> Path | None:
    if not filename:
        return None
    photo_path = PHOTO_DIR / Path(filename).name
    return photo_path if photo_path.exists() else None


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Ethiopic:wght@400;500;600;700;800&display=swap');

        :root {{
            --green: {GREEN};
            --yellow: {YELLOW};
            --red: {RED};
            --ink: {INK};
            --cream: {CREAM};
        }}

        .stApp {{
            background:
                radial-gradient(circle at 94% 4%, rgba(242, 201, 76, .18), transparent 24rem),
                linear-gradient(180deg, #fffdf8 0%, var(--cream) 54%, #f5f0e5 100%);
            color: var(--ink);
        }}

        .block-container {{
            max-width: 1180px;
            padding-top: 2.5rem;
            padding-bottom: 4rem;
        }}

        h1, h2, h3, p, label, .stTabs {{
            font-family: 'Noto Sans Ethiopic', sans-serif;
        }}

        .brand-mark {{
            display: inline-flex;
            align-items: center;
            gap: .7rem;
            color: var(--ink);
            font-size: 1.15rem;
            font-weight: 800;
        }}

        .brand-symbol {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.35rem;
            height: 2.35rem;
            border-radius: .8rem;
            color: #fffdf8;
            background: conic-gradient(from 210deg, var(--green), var(--yellow), var(--red), var(--green));
        }}

        .eyebrow {{
            display: inline-block;
            margin: 1.6rem 0 .7rem;
            color: var(--green);
            font-size: .78rem;
            font-weight: 800;
            text-transform: uppercase;
        }}

        .hero {{
            position: relative;
            margin: 1.2rem 0 2.2rem;
            padding: clamp(2rem, 5vw, 4.5rem);
            border-radius: 2rem;
            background: linear-gradient(120deg, rgba(22, 132, 74, .96), rgba(24, 50, 43, .94));
            color: #fffdf8;
        }}

        .hero h1 {{
            color: #fffdf8;
            font-size: clamp(2rem, 5vw, 4.5rem);
        }}

        .price-pill {{
            display: inline-block;
            margin: .55rem 0;
            padding: .25rem .6rem;
            border-radius: 999px;
            background: rgba(22, 132, 74, .1);
            color: var(--green);
            font-weight: 800;
        }}

        .gallery-empty {{
            padding: 2.5rem 1rem;
            border: 1px dashed rgba(24, 50, 43, .22);
            border-radius: 1rem;
            text-align: center;
            color: rgba(24, 50, 43, .65);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header() -> None:
    st.markdown(
        """
        <div class="brand-mark">
            <span class="brand-symbol">✦</span>
            <span>ኖካ <span style="opacity:.55;">/</span> NOOKA</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_order_form(item: dict[str, Any], key_prefix: str) -> None:
    with st.expander("አሁኑኑ ይዘዙ · Order Now"):
        with st.form(f"{key_prefix}_order_{item['id']}"):
            quantity = st.number_input(
                "ብዛት", min_value=1, max_value=50, value=1, step=1,
                key=f"{key_prefix}_qty_{item['id']}",
            )
            name = st.text_input("ሙሉ ስም", key=f"{key_prefix}_name_{item['id']}")
            phone = st.text_input("ስልክ ቁጥር", key=f"{key_prefix}_phone_{item['id']}")
            submit = st.form_submit_button("ትዕዛዝ ላክ", use_container_width=True)

        if submit:
            clean_name = name.strip()
            clean_phone = phone.strip()
            if not clean_name or not clean_phone:
                st.error("እባክዎ ሙሉ ስምዎን እና ስልክ ቁጥርዎን ያስገቡ።")
            else:
                order = add_order(
                    {
                        "item": item["name"],
                        "category": item["category"],
                        "quantity": int(quantity),
                        "total": int(item["price"]) * int(quantity),
                        "name": clean_name,
                        "phone": clean_phone,
                    }
                )
                st.success(f"ትዕዛዝዎ ተልኳል! የትዕዛዝ ቁጥርዎ፦ {order['number']}")


def render_home() -> None:
    home = read_store().get("home", dict(HOME_DEFAULTS))

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-ribbon">{home.get('hero_ribbon', '')}</div>
            <h1>{home.get('hero_title', '')}</h1>
            <p>{home.get('hero_body', '')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="eyebrow">Products · ምርቶቻችን</div>', unsafe_allow_html=True)
    catalog_items = read_store()["items"]

    if catalog_items:
        cols = st.columns(min(3, len(catalog_items)))
        for idx, item in enumerate(catalog_items):
            with cols[idx % len(cols)]:
                st.subheader(item["name"])
                st.caption(f"ዓይነት፦ {item['category']}")

                photo_path = _product_photo_path(item.get("photo_filename", ""))
                if photo_path:
                    st.image(str(photo_path), use_container_width=True)
                else:
                    st.markdown(
                        '<div class="gallery-empty">ምስል አልተጫነም</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f'<span class="price-pill">{item["price"]:,} ብር</span>',
                    unsafe_allow_html=True,
                )

                _render_order_form(item, key_prefix="home")


def render_chatbot() -> None:
    st.markdown('<div class="eyebrow">AI Assistant · የደንበኞች ረዳት</div>', unsafe_allow_html=True)
    st.markdown("<h2>ስለ ኖካ / NOOKA ምርቶች ይጠይቁ</h2>", unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "ሰላም! ኖካ (NOOKA) እንኳን ደህና መጡ። ስለ ባህላዊ ልብሶቻችን እና ምግቦቻችን ምን ማወቅ ይፈልጋሉ?"}
        ]

    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    if user_input := st.chat_input("ጥያቄዎን እዚህ ያስገቡ..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        store = read_store()
        items_summary = ", ".join([f"{item['name']} ({item['price']} ብር)" for item in store["items"]])
        reply = f"ስለ ጥያቄዎ እናመሰግናለን! በኖካ አሁን የሚገኙ ምርቶች፦ {items_summary} ናቸው።"

        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.chat_message("assistant").write(reply)


def render_about() -> None:
    about = read_store().get("about", dict(ABOUT_DEFAULTS))
    st.markdown('<div class="eyebrow">About · ስለ እኛ</div>', unsafe_allow_html=True)
    st.markdown(f"<h1>{about.get('title', '')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='white-space:pre-line;'>{about.get('body', '')}</p>", unsafe_allow_html=True)


# --- የአድሚን ዳሽቦርድ (ADMIN DASHBOARD) ---
def render_admin_dashboard() -> None:
    st.markdown('<div class="eyebrow">Admin Panel · የአድሚን መቆጣጠሪያ ገጽ</div>', unsafe_allow_html=True)
    st.markdown("<h1>የኖካ (NOOKA) አስተዳዳሪ ገጽ</h1>", unsafe_allow_html=True)

    store = read_store()
    orders = store["orders"]
    items = store["items"]

    # 1. የትዕዛዞች ማጠቃለያ (Metrics)
    completed_count = sum(order.get("status") == "completed" for order in orders)
    col1, col2, col3 = st.columns(3)
    col1.metric("ጠቅላላ ትዕዛዞች", len(orders))
    col2.metric("በመጠባበቅ ላይ", len(orders) - completed_count)
    col3.metric("የተጠናቀቁ", completed_count)

    st.divider()

    # 2. የትዕዛዞች ዝርዝር (Orders List)
    st.subheader("የደንበኞች ትዕዛዞች")
    if not orders:
        st.info("እስካሁን ምንም የተላከ ትዕዛዝ የለም።")
    else:
        for order in reversed(orders):
            st.write(f"**ትዕዛዝ ቁጥር፦ {order['number']}** | **ምርት፦** {order['item']} ({order['quantity']} አቃ) | **ጠቅላላ፦** {order['total']:,} ብር")
            st.caption(f"ደንበኛ፦ {order['name']} | ስልክ፦ {order['phone']} | ሁኔታ፦ {order.get('status', 'pending')}")
            
            # የትዕዛዝ ሁኔታ መቀየሪያ
            c1, c2 = st.columns([1, 4])
            with c1:
                new_status = st.selectbox(
                    "ሁኔታ ቀይር",
                    ["pending", "completed"],
                    index=0 if order.get("status") == "pending" else 1,
                    key=f"status_{order['number']}"
                )
                if st.button("አዘምን", key=f"btn_{order['number']}"):
                    update_order_status(order["number"], new_status)
                    st.success("ሁኔታው ተዘምኗል!")
                    st.rerun()
            st.divider()

    # 3. አዲስ ምርት መጨመሪያ (Add Product)
    st.subheader("አዲስ ምርት መመዝገቢያ")
    with st.form("add_product_form"):
        p_name = st.text_input("የምርት ስም")
        p_cat = st.selectbox("ዓይነት", ["ልብስ", "ምግብ"])
        p_price = st.number_input("ዋጋ (በብር)", min_value=0, step=50)
        p_submit = st.form_submit_button("ምርት መዝግብ")

        if p_submit:
            if p_name.strip() and p_price > 0:
                add_catalog_item(p_cat, p_name.strip(), int(p_price))
                st.success(f"ምርት '{p_name}' ተመዝግቧል!")
                st.rerun()
            else:
                st.error("እባክዎ ትክክለኛ የምርት ስም እና ዋጋ ያስገቡ።")


def main() -> None:
    inject_styles()
    render_brand_header()

    # URL ላይ admin_key መኖሩን ማረጋገጫ (ለምሳሌ: yoursite.com/?admin_key=nooka2026)
    query_params = st.query_params
    is_admin = query_params.get(ADMIN_URL_PARAM) == ADMIN_SECRET_PASS

    if is_admin:
        # አድሚን ከሆነ Admin Dashboardን ብቻ ያሳየዋል
        render_admin_dashboard()
    else:
        # ተራ ተጠቃሚ ከሆነ የተለመዱትን ገጾች ያሳያል
        tab_home, tab_chatbot, tab_about = st.tabs(
            ["መነሻ ገጽ (Home)", "AI Chatbot", "ስለ እኛ (About)"]
        )

        with tab_home:
            render_home()
        with tab_chatbot:
            render_chatbot()
        with tab_about:
            render_about()


if __name__ == "__main__":
    main()
