import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import streamlit as st


st.set_page_config(
    page_title="NOOKA | Ethiopian TRADITIONAL CLOTHES AND FOOD",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Colors Palette
GREEN = "#0F5132"
LIGHT_GREEN = "#198754"
ACCENT_GOLD = "#D4AF37"
DARK_BG = "#1A1A1A"
CARD_BG = "#FFFFFF"
CREAM = "#F9F8F3"

DEFAULT_ORDER_ITEMS = [
    {"id": "default-1", "category": "ልብስ", "name": "የወንዶች ባህላዊ ካባ", "price": 4000, "photo_filename": ""},
    {"id": "default-2", "category": "ልብስ", "name": "የልጆች ባህላዊ ልብስ", "price": 1800, "photo_filename": ""},
    {"id": "default-3", "category": "ምግብ", "name": "ዶሮ ወጥ ከእንጀራ ጋር", "price": 450, "photo_filename": ""},
    {"id": "default-4", "category": "ምግብ", "name": "የበዓል ምግብ ጥቅል", "price": 950, "photo_filename": ""},
]

HOME_DEFAULTS = {
    "hero_ribbon": "ETHIOPIAN HERITAGE · MADE WITH CARE",
    "hero_title": "የኢትዮጵያ ቅርስ<br>በአንድ ቦታ",
    "hero_body": "በባህላዊ ልብስ እና በጣፋጭ የኢትዮጵያ ምግቦች የቤተሰብ ትውስታዎችን እንፈጥራለን። ከእጅ የተሰሩ የባህል ልብሶችን እና በፍቅር የተዘጋጁ ምግቦችን ያግኙ።",
    "photo_filename": "",
}

ABOUT_DEFAULTS = {
    "title": "ስለ እኛ · About Us",
    "body": "ኖካ / NOOKA የተመሰረተው የኢትዮጵያን ባህላዊ ልብስ እና ምግብ ከቤተሰብ ወደ ቤተሰብ ለማድረስ ነው። እያንዳንዱ ምርት በጥንቃቄ እና በፍቅር የተዘጋጀ ነው።",
    "photo_filename": "",
}

CHATBOT_DEFAULTS = {
    "system_instruction": "ሰላም! ኖካ (NOOKA) እንኳን ደህና መጡ። ስለ ባህላዊ ልብሶቻችን እና ምግቦቻችን ምን ማወቅ ይፈልጋሉ?"
}

ADMIN_URL_PARAM = "admin_key"
ADMIN_SECRET_PASS = "nooka2026"

STORE_PATH = Path(__file__).with_name("storefront_data.json")
PHOTO_DIR = Path(__file__).with_name("product_photos")
STORE_LOCK = Lock()


def _default_store() -> dict[str, Any]:
    return {
        "items": list(DEFAULT_ORDER_ITEMS),
        "orders": [],
        "home": dict(HOME_DEFAULTS),
        "about": dict(ABOUT_DEFAULTS),
        "chatbot": dict(CHATBOT_DEFAULTS),
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
        "items": data.get("items", list(DEFAULT_ORDER_ITEMS)),
        "orders": data.get("orders", []),
        "home": data.get("home", dict(HOME_DEFAULTS)),
        "about": data.get("about", dict(ABOUT_DEFAULTS)),
        "chatbot": data.get("chatbot", dict(CHATBOT_DEFAULTS)),
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


def update_order_status(order_number: str, status: str) -> None:
    def mutate(store: dict[str, Any]) -> None:
        for order in store["orders"]:
            if order.get("number") == order_number:
                order["status"] = status
    update_store(mutate)


def save_product(item_id: str | None, category: str, name: str, price: int, photo_filename: str) -> None:
    def mutate(store: dict[str, Any]) -> None:
        if item_id:
            for item in store["items"]:
                if item["id"] == item_id:
                    item["category"] = category
                    item["name"] = name
                    item["price"] = price
                    if photo_filename:
                        item["photo_filename"] = photo_filename
        else:
            store["items"].append(
                {
                    "id": f"product-{uuid4().hex[:8]}",
                    "category": category,
                    "name": name,
                    "price": price,
                    "photo_filename": photo_filename,
                }
            )
    update_store(mutate)


def delete_product(item_id: str) -> None:
    def mutate(store: dict[str, Any]) -> None:
        store["items"] = [item for item in store["items"] if item["id"] != item_id]
    update_store(mutate)


def update_section_data(section_key: str, data: dict[str, str]) -> None:
    def mutate(store: dict[str, Any]) -> None:
        store[section_key] = data
    update_store(mutate)


def save_uploaded_photo(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"img_{uuid4().hex[:8]}_{uploaded_file.name}"
    file_path = PHOTO_DIR / filename
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filename


def _product_photo_path(filename: str) -> Path | None:
    if not filename:
        return None
    photo_path = PHOTO_DIR / Path(filename).name
    return photo_path if photo_path.exists() else None


# 🎨 ADVANCED PROFESSIONAL CSS STYLING
def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Noto+Sans+Ethiopic:wght@400;500;600;700;800&display=swap');

        /* App Main Background */
        .stApp {{
            background-color: {CREAM};
            font-family: 'Noto Sans Ethiopic', 'Plus Jakarta Sans', sans-serif;
            color: #2D3748;
        }}

        .block-container {{
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 5rem;
        }}

        /* Header Brand Styling */
        .brand-mark {{
            display: inline-flex;
            align-items: center;
            gap: .8rem;
            font-size: 1.4rem;
            font-weight: 800;
            color: {GREEN};
            padding: 0.5rem 1rem;
            background: rgba(15, 81, 50, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(15, 81, 50, 0.1);
        }}
        .brand-symbol {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 10px;
            color: #FFFFFF;
            background: linear-gradient(135deg, {GREEN}, {ACCENT_GOLD});
            box-shadow: 0 4px 10px rgba(15, 81, 50, 0.2);
        }}

        /* Hero Banner */
        .hero {{
            position: relative;
            margin: 1.5rem 0 2.5rem;
            padding: 3.5rem 2.5rem;
            border-radius: 24px;
            background: linear-gradient(135deg, {GREEN} 0%, #082E1C 100%);
            color: #FFFFFF;
            box-shadow: 0 20px 40px rgba(15, 81, 50, 0.15);
        }}
        .hero-ribbon {{
            display: inline-block;
            padding: 0.4rem 1rem;
            background: rgba(212, 175, 55, 0.2);
            border: 1px solid {ACCENT_GOLD};
            color: {ACCENT_GOLD};
            border-radius: 50px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 1rem;
        }}
        .hero h1 {{
            color: #FFFFFF !important;
            font-size: clamp(2.2rem, 4vw, 3.5rem);
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 1rem;
        }}
        .hero p {{
            font-size: 1.1rem;
            opacity: 0.9;
            max-width: 650px;
        }}

        /* Eyebrow Headings */
        .eyebrow {{
            display: inline-block;
            margin: 2rem 0 1rem;
            color: {GREEN};
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }}

        /* Streamlit Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 12px;
            background-color: transparent;
            border-bottom: 2px solid #E2E8F0;
            padding-bottom: 8px;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 48px;
            white-space: pre;
            border-radius: 12px;
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            color: #4A5568;
            font-weight: 600;
            padding: 0 20px;
            transition: all 0.25s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {GREEN} !important;
            color: #FFFFFF !important;
            border-color: {GREEN} !important;
            box-shadow: 0 4px 12px rgba(15, 81, 50, 0.25) !important;
        }}

        /* BUTTONS STYLING (Global & Admin) */
        .stButton>button {{
            width: 100%;
            border-radius: 12px !important;
            height: 46px !important;
            background: linear-gradient(135deg, {GREEN}, {LIGHT_GREEN}) !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(25, 135, 84, 0.2) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        .stButton>button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 18px rgba(25, 135, 84, 0.35) !important;
            background: linear-gradient(135deg, {LIGHT_GREEN}, {GREEN}) !important;
        }}
        .stButton>button:active {{
            transform: translateY(0) !important;
        }}

        /* Delete Button Specific */
        div[data-testid="stButton"] button:contains("ሰርዝ") {{
            background: linear-gradient(135deg, #DC3545, #BB2D3B) !important;
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.2) !important;
        }}

        /* Price Pill */
        .price-pill {{
            display: inline-block;
            margin: 0.8rem 0;
            padding: 0.4rem 1rem;
            border-radius: 50px;
            background: rgba(15, 81, 50, 0.08);
            color: {GREEN};
            font-size: 1.1rem;
            font-weight: 800;
            border: 1px solid rgba(15, 81, 50, 0.15);
        }}

        /* Input Fields & Text Areas */
        .stTextInput input, .stTextArea textarea, .stSelectbox select, .stNumberInput input {{
            border-radius: 10px !important;
            border: 1.5px solid #E2E8F0 !important;
            padding: 0.6rem 1rem !important;
            transition: all 0.2s ease !important;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: {GREEN} !important;
            box-shadow: 0 0 0 3px rgba(15, 81, 50, 0.1) !important;
        }}

        /* Expander & Cards */
        .streamlit-expanderHeader {{
            background-color: #FFFFFF !important;
            border-radius: 12px !important;
            border: 1px solid #E2E8F0 !important;
            font-weight: 700 !important;
            color: {GREEN} !important;
        }}
        .streamlit-expanderContent {{
            background-color: #FFFFFF !important;
            border-radius: 0 0 12px 12px !important;
            border: 1px solid #E2E8F0 !important;
            border-top: none !important;
            padding: 1.5rem !important;
        }}

        /* Chatbot Container */
        .stChatMessage {{
            border-radius: 16px !important;
            padding: 1rem !important;
            margin-bottom: 0.8rem !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03) !important;
        }}

        /* Gallery Empty Placeholder */
        .gallery-empty {{
            padding: 3rem 1rem;
            border: 2px dashed #CBD5E0;
            border-radius: 16px;
            text-align: center;
            color: #A0AEC0;
            background: #FFFFFF;
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
            <span>ኖካ <span style="opacity:.4;">/</span> NOOKA</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_order_form(item: dict[str, Any], key_prefix: str) -> None:
    with st.expander("🛒 አሁኑኑ ይዘዙ (Order Now)"):
        with st.form(f"{key_prefix}_order_{item['id']}"):
            quantity = st.number_input("ብዛት", min_value=1, max_value=50, value=1, step=1, key=f"{key_prefix}_qty_{item['id']}")
            name = st.text_input("ሙሉ ስም", key=f"{key_prefix}_name_{item['id']}")
            phone = st.text_input("ስልክ ቁጥር", key=f"{key_prefix}_phone_{item['id']}")
            submit = st.form_submit_button("ትዕዛዝ አረጋግጥ", use_container_width=True)

        if submit:
            clean_name = name.strip()
            clean_phone = phone.strip()
            if not clean_name or not clean_phone:
                st.error("እባክዎ ሙሉ ስምዎን እና ስልክ ቁጥርዎን ያስገቡ።")
            else:
                order = add_order({"item": item["name"], "category": item["category"], "quantity": int(quantity), "total": int(item["price"]) * int(quantity), "name": clean_name, "phone": clean_phone})
                st.success(f"🎉 ትዕዛዝዎ ተልኳል! የትዕዛዝ ቁጥርዎ፦ {order['number']}")


def render_home() -> None:
    store = read_store()
    home = store.get("home", HOME_DEFAULTS)

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
    
    home_photo_path = _product_photo_path(home.get("photo_filename", ""))
    if home_photo_path:
        st.image(str(home_photo_path), use_container_width=True)

    st.markdown('<div class="eyebrow">FEATURED PRODUCTS · ምርቶቻችን</div>', unsafe_allow_html=True)
    catalog_items = store.get("items", [])

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
                    st.markdown('<div class="gallery-empty">🖼️ ምስል አልተጫነም</div>', unsafe_allow_html=True)

                st.markdown(f'<span class="price-pill">{item["price"]:,} ETB</span>', unsafe_allow_html=True)
                _render_order_form(item, key_prefix="home")


def render_chatbot() -> None:
    store = read_store()
    chatbot_config = store.get("chatbot", CHATBOT_DEFAULTS)
    
    st.markdown('<div class="eyebrow">AI ASSISTANT · የደንበኞች ረዳት</div>', unsafe_allow_html=True)
    st.markdown("<h2>ስለ ኖካ / NOOKA ምርቶች ይጠይቁ</h2>", unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role": "assistant", "content": chatbot_config.get("system_instruction", CHATBOT_DEFAULTS["system_instruction"])}]

    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    if user_input := st.chat_input("ጥያቄዎን እዚህ ያስገቡ..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        items_summary = ", ".join([f"{item['name']} ({item['price']} ብር)" for item in store.get("items", [])])
        reply = f"ስለ ጥያቄዎ እናመሰግናለን! በኖካ አሁን የሚገኙ ምርቶች፦ {items_summary} ናቸው።"
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.chat_message("assistant").write(reply)


def render_about() -> None:
    about = read_store().get("about", ABOUT_DEFAULTS)
    st.markdown('<div class="eyebrow">ABOUT US · ስለ እኛ</div>', unsafe_allow_html=True)
    st.markdown(f"<h1>{about.get('title', '')}</h1>", unsafe_allow_html=True)
    
    about_photo_path = _product_photo_path(about.get("photo_filename", ""))
    if about_photo_path:
        st.image(str(about_photo_path), use_container_width=True)
        
    st.markdown(f"<p style='white-space:pre-line; font-size: 1.1rem; line-height: 1.8;'>{about.get('body', '')}</p>", unsafe_allow_html=True)


# --- 🛠️ PROFESSIONAL ADMIN DASHBOARD SYSTEM ---
def render_admin_dashboard() -> None:
    st.markdown('<div class="eyebrow">ADMIN CONTROL PANEL</div>', unsafe_allow_html=True)
    st.markdown("<h1>የኖካ (NOOKA) አስተዳዳሪ ገጽ</h1>", unsafe_allow_html=True)

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.warning("🔒 ይህ ገጽ ለአስተዳዳሪዎች ብቻ የተፈቀደ ነው። እባክዎ ሚስጥር ፓስወርድዎን ያስገቡ።")
        entered_pass = st.text_input("የአድሚን ፓስወርድ", type="password")
        if st.button("ግባ (Login)"):
            if entered_pass == ADMIN_SECRET_PASS:
                st.session_state.admin_authenticated = True
                st.success("በተካከለ ገብተዋል!")
                st.rerun()
            else:
                st.error("የተሳሳተ ፓስወርድ ነው!")
        return

    admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5 = st.tabs([
        "📦 ትዕዛዞች (Orders)", "🛍️ የምርት መቆጣጠሪያ", "🏠 Home ገፅ", "🤖 AI Chatbot", "ℹ️ About ገፅ"
    ])

    store = read_store()

    # Tab 1: Orders
    with admin_tab1:
        st.subheader("የደንበኞች ትዕዛዞች ዝርዝር")
        orders = store.get("orders", [])
        if not orders:
            st.info("እስካሁን ምንም ትዕዛዝ አልገባም።")
        else:
            for order in reversed(orders):
                st.write(f"**ትዕዛዝ ቁጥር፦ {order['number']}** | **ምርት፦** {order['item']} ({order['quantity']} አቃ) | **ጠቅላላ፦** {order['total']:,} ብር")
                st.caption(f"ደንበኛ፦ {order['name']} | ስልክ፦ {order['phone']} | ቀን፦ {order.get('created_at', '')}")
                c1, _ = st.columns([2, 3])
                with c1:
                    new_status = st.selectbox("የስራ ሁኔታ", ["pending", "completed"], index=0 if order.get("status") == "pending" else 1, key=f"ord_{order['number']}")
                    if st.button("ሁኔታውን አዘምን", key=f"btn_ord_{order['number']}"):
                        update_order_status(order["number"], new_status)
                        st.success("ተዘምኗል!")
                        st.rerun()
                st.divider()

    # Tab 2: Products
    with admin_tab2:
        st.subheader("አዲስ ምርት ጨምር ወይም የተመዘገቡትን ኤዲት አድርግ")
        with st.expander("➕ አዲስ ምርት መጨመሪያ ፎርም"):
            with st.form("add_prod_form", clear_on_submit=True):
                n_name = st.text_input("የምርት ስም")
                n_cat = st.selectbox("ዓይነት", ["ልብስ", "ምግብ"])
                n_price = st.number_input("ዋጋ (ብር)", min_value=0, step=50)
                n_photo = st.file_uploader("የምርት ምስል (Product Image)", type=["png", "jpg", "jpeg", "webp"])
                
                if st.form_submit_button("ምርት መዝግብ"):
                    if n_name.strip() and n_price > 0:
                        saved_photo = save_uploaded_photo(n_photo) if n_photo else ""
                        save_product(None, n_cat, n_name.strip(), int(n_price), saved_photo)
                        st.success("አዲስ ምርት ተጨምሯል!")
                        st.rerun()

        st.divider()
        st.write("### የተመዘገቡ ምርቶች ዝርዝር")
        for item in store.get("items", []):
            with st.expander(f"📝 {item['name']} ({item['price']} ብር)"):
                with st.form(f"edit_prod_{item['id']}"):
                    e_name = st.text_input("የምርት ስም", value=item["name"])
                    e_cat = st.selectbox("ዓይነት", ["ልብስ", "ምግብ"], index=0 if item["category"] == "ልብስ" else 1)
                    e_price = st.number_input("ዋጋ (ብር)", value=int(item["price"]), min_value=0, step=50)
                    e_photo = st.file_uploader("አዲስ የምርት ምስል (አሁን ያለውን ለመቀየር)", type=["png", "jpg", "jpeg", "webp"])
                    
                    col_save, col_del = st.columns(2)
                    with col_save:
                        if st.form_submit_button("ለውጦችን መዝግብ"):
                            new_photo_name = save_uploaded_photo(e_photo) if e_photo else item.get("photo_filename", "")
                            save_product(item["id"], e_cat, e_name.strip(), int(e_price), new_photo_name)
                            st.success("ምርቱ ተስተካክሏል!")
                            st.rerun()
                
                if st.button("🗑️ ምርቱን ሰርዝ (Delete)", key=f"del_{item['id']}"):
                    delete_product(item["id"])
                    st.warning("ምርቱ ተሰርዟል!")
                    st.rerun()

    # Tab 3: Home Page Content & Image Upload
    with admin_tab3:
        st.subheader("የመነሻ ገጽ (Home Page) ማስተካከያ")
        home_data = store.get("home", HOME_DEFAULTS)
        with st.form("home_edit_form"):
            h_ribbon = st.text_input("የላይኛው ሪበን ፅሁፍ (Ribbon)", value=home_data.get("hero_ribbon", ""))
            h_title = st.text_input("ዋናው ርዕስ (Title)", value=home_data.get("hero_title", ""))
            h_body = st.text_area("የመግቢያ ፅሁፍ (Body)", value=home_data.get("hero_body", ""), height=120)
            h_photo = st.file_uploader("የመነሻ ገፅ ምስል / Banner Image (አማራጭ)", type=["png", "jpg", "jpeg", "webp"])
            
            if st.form_submit_button("የ Home ገፅ ለውጦችን ሴቭ አድርግ"):
                new_photo_name = save_uploaded_photo(h_photo) if h_photo else home_data.get("photo_filename", "")
                update_section_data("home", {
                    "hero_ribbon": h_ribbon, 
                    "hero_title": h_title, 
                    "hero_body": h_body,
                    "photo_filename": new_photo_name
                })
                st.success("Home page ተዘምኗል!")
                st.rerun()

    # Tab 4: AI Chatbot
    with admin_tab4:
        st.subheader("የ AI Chatbot መመሪያ ኤዲተር")
        chat_data = store.get("chatbot", CHATBOT_DEFAULTS)
        with st.form("chat_edit_form"):
            c_msg = st.text_area("የቦቱ መጀመሪያ ሰላምታ (Greeting Message)", value=chat_data.get("system_instruction", ""), height=100)
            if st.form_submit_button("የ Chatbot መመሪያን ሴቭ አድርግ"):
                update_section_data("chatbot", {"system_instruction": c_msg})
                st.success("የ Chatbot መመሪያ ተዘምኗል!")
                st.rerun()

    # Tab 5: About Us Content & Image Upload
    with admin_tab5:
        st.subheader("የስለ እኛ (About Us) ገጽ ማስተካከያ")
        about_data = store.get("about", ABOUT_DEFAULTS)
        with st.form("about_edit_form"):
            a_title = st.text_input("ርዕስ (Title)", value=about_data.get("title", ""))
            a_body = st.text_area("ስለ ድርጅቱ ዝርዝር ፅሁፍ (Body)", value=about_data.get("body", ""), height=150)
            a_photo = st.file_uploader("የስለ እኛ ገፅ ምስል (About Us Image)", type=["png", "jpg", "jpeg", "webp"])
            
            if st.form_submit_button("የ About ገፅ ለውጦችን ሴቭ አድርግ"):
                new_photo_name = save_uploaded_photo(a_photo) if a_photo else about_data.get("photo_filename", "")
                update_section_data("about", {
                    "title": a_title, 
                    "body": a_body,
                    "photo_filename": new_photo_name
                })
                st.success("About page ተዘምኗል!")
                st.rerun()


def main() -> None:
    inject_styles()
    render_brand_header()

    query_params = st.query_params
    is_admin_path = query_params.get(ADMIN_URL_PARAM) == ADMIN_SECRET_PASS

    if is_admin_path:
        render_admin_dashboard()
    else:
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
