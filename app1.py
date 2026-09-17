import base64
import hmac
import json
import os
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import requests
import streamlit as st


st.set_page_config(
    page_title="NOOKA  | Ethiopian SHINASHA TRADITIONAL CLOTHES AND FOOD ",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


GREEN = "#16844A"
YELLOW = "#F2C94C"
RED = "#C53D3D"
INK = "#18322B"
CREAM = "#FBF8F1"
GROQ_MODEL = "qwen/qwen3.8-27b"
DEFAULT_ORDER_ITEMS = [
    
    {"category": "ልብስ", "name": "የወንዶች ባህላዊ ካባ", "price": 4000},
    {"category": "ልብስ", "name": "የልጆች ባህላዊ ልብስ", "price": 1800},
    
    {"category": "ምግብ", "name": "ዶሮ ወጥ ከእንጀራ ጋር", "price": 450},
    {"category": "ምግብ", "name": "የበዓል ምግብ ጥቅል", "price": 950},
]
HOME_DEFAULTS: dict[str, str] = {
    "hero_ribbon": "Ethiopian heritage · made with care",
    "hero_title": "የኢትዮጵያ ቅርስ<br>በአንድ ቦታ",
    "hero_body": (
        "በባህላዊ ልብስ እና በጣፋጭ የኢትዮጵያ ምግቦች የቤተሰብ ትውስታዎችን "
        "እንፈጥራለን። ከእጅ የተሰሩ የባህል ልብሶችን እና በፍቅር የተዘጋጁ "
        "ምግቦችን ያግኙ። ባህላችንን ከእርስዎ ጋር ማካፈል ደስታችን ነው።"
    ),
    "promise_title": "ባህል በጥራት እና በሙቀት",
    "promise_body": "እያንዳንዱ የምንመርጠው ልብስ እና የምናዘጋጀው ምግብ የኢትዮጵያን ታሪክ ይይዛል።",
    "banner_photo_filename": "",
}
ABOUT_DEFAULTS: dict[str, str] = {
    "title": "ስለ እኛ · About Us",
    "body": (
        "ቅርስ ቤት የተመሰረተው የኢትዮጵያን ባህላዊ ልብስ እና ምግብ ከቤተሰብ ወደ ቤተሰብ "
        "ለማድረስ ነው። እያንዳንዱ ምርት በጥንቃቄ እና በፍቅር የተዘጋጀ ነው። "
        "አላማችን ደንበኞቻችን የኢትዮጵያን ባህል በቀላሉ እንዲያገኙ ማድረግ ነው።"
    ),
    "photo_filename": "",
}
ADMIN_URL_PARAM = "admin_key"
STORE_PATH = Path(__file__).with_name("storefront_data.json")
PHOTO_DIR = Path(__file__).with_name("product_photos")
ALLOWED_PHOTO_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
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
        "faqs": [],
    }


def _read_store_unlocked() -> dict[str, Any]:
    if not STORE_PATH.exists():
        return _default_store()
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_store()

    if not isinstance(data, dict):
        return _default_store()
    items = data.get("items")
    orders = data.get("orders")
    if not isinstance(items, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("category"), str)
        and isinstance(item.get("price"), (int, float))
        for item in items
    ):
        items = _default_store()["items"]
    else:
        normalized_items = []
        for index, item in enumerate(items):
            normalized_item = item.copy()
            normalized_item.setdefault("id", f"legacy-{index + 1}")
            normalized_item.setdefault("photo_filename", "")
            normalized_items.append(normalized_item)
        items = normalized_items
    if not isinstance(orders, list):
        orders = []
    normalized_orders = []
    for order in orders:
        if isinstance(order, dict) and order.get("number"):
            normalized_order = order.copy()
            normalized_order.setdefault("status", "pending")
            normalized_orders.append(normalized_order)

    home = data.get("home")
    normalized_home = dict(HOME_DEFAULTS)
    if isinstance(home, dict):
        for key in HOME_DEFAULTS:
            value = home.get(key)
            if isinstance(value, str):
                normalized_home[key] = value

    about = data.get("about")
    normalized_about = dict(ABOUT_DEFAULTS)
    if isinstance(about, dict):
        for key in ABOUT_DEFAULTS:
            value = about.get(key)
            if isinstance(value, str):
                normalized_about[key] = value

    faqs = data.get("faqs")
    normalized_faqs = []
    if isinstance(faqs, list):
        for faq in faqs:
            if (
                isinstance(faq, dict)
                and isinstance(faq.get("question"), str)
                and isinstance(faq.get("answer"), str)
            ):
                normalized_faqs.append(
                    {
                        "id": faq.get("id") or f"faq-{uuid4().hex}",
                        "question": faq["question"],
                        "answer": faq["answer"],
                    }
                )

    return {
        "items": items,
        "orders": normalized_orders,
        "home": normalized_home,
        "about": normalized_about,
        "faqs": normalized_faqs,
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


def _save_product_photo(photo_bytes: bytes, original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_PHOTO_SUFFIXES:
        raise ValueError("Only PNG, JPG, JPEG, and WEBP product photos are supported.")
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    temporary_path = PHOTO_DIR / f"{filename}.tmp"
    temporary_path.write_bytes(photo_bytes)
    temporary_path.replace(PHOTO_DIR / filename)
    return filename


def _product_photo_path(filename: str) -> Path | None:
    if not filename:
        return None
    safe_filename = Path(filename).name
    photo_path = PHOTO_DIR / safe_filename
    return photo_path if photo_path.exists() else None


def _remove_product_photo(filename: str) -> None:
    photo_path = _product_photo_path(filename)
    if photo_path:
        photo_path.unlink(missing_ok=True)


def add_catalog_item(category: str, name: str, price: int, photo_filename: str) -> None:
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


def edit_catalog_item(
    item_id: str,
    category: str,
    name: str,
    price: int,
    photo_filename: str | None = None,
) -> str:
    def mutate(store: dict[str, Any]) -> str:
        for item in store["items"]:
            if item.get("id") == item_id:
                item["category"] = category
                item["name"] = name
                item["price"] = price
                if photo_filename is not None:
                    item["photo_filename"] = photo_filename
                return item.get("photo_filename", "")
        raise ValueError("Product not found.")

    return update_store(mutate)


def delete_catalog_item(item_id: str) -> str:
    def mutate(store: dict[str, Any]) -> str:
        for index, item in enumerate(store["items"]):
            if item.get("id") == item_id:
                removed = store["items"].pop(index)
                return removed.get("photo_filename", "")
        raise ValueError("Product not found.")

    old_photo_filename = update_store(mutate)
    _remove_product_photo(old_photo_filename)
    return old_photo_filename


def update_home_content(
    hero_ribbon: str,
    hero_title: str,
    hero_body: str,
    promise_title: str,
    promise_body: str,
    banner_photo_filename: str | None = None,
) -> str:
    def mutate(store: dict[str, Any]) -> str:
        home = store.setdefault("home", dict(HOME_DEFAULTS))
        home["hero_ribbon"] = hero_ribbon
        home["hero_title"] = hero_title
        home["hero_body"] = hero_body
        home["promise_title"] = promise_title
        home["promise_body"] = promise_body
        if banner_photo_filename is not None:
            home["banner_photo_filename"] = banner_photo_filename
        return home.get("banner_photo_filename", "")

    return update_store(mutate)


def update_about_content(title: str, body: str, photo_filename: str | None = None) -> str:
    def mutate(store: dict[str, Any]) -> str:
        about = store.setdefault("about", dict(ABOUT_DEFAULTS))
        about["title"] = title
        about["body"] = body
        if photo_filename is not None:
            about["photo_filename"] = photo_filename
        return about.get("photo_filename", "")

    return update_store(mutate)


def add_faq(question: str, answer: str) -> None:
    def mutate(store: dict[str, Any]) -> None:
        store.setdefault("faqs", []).append(
            {"id": f"faq-{uuid4().hex}", "question": question, "answer": answer}
        )

    update_store(mutate)


def edit_faq(faq_id: str, question: str, answer: str) -> None:
    def mutate(store: dict[str, Any]) -> None:
        for faq in store.get("faqs", []):
            if faq.get("id") == faq_id:
                faq["question"] = question
                faq["answer"] = answer
                return
        raise ValueError("FAQ not found.")

    update_store(mutate)


def delete_faq(faq_id: str) -> None:
    def mutate(store: dict[str, Any]) -> None:
        faqs = store.get("faqs", [])
        store["faqs"] = [faq for faq in faqs if faq.get("id") != faq_id]

    update_store(mutate)


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

        [data-testid="stHeader"] {{
            background: rgba(255, 253, 248, .84);
        }}

        [data-testid="stDecoration"] {{
            background-image: linear-gradient(90deg, var(--green) 0 33%, var(--yellow) 33% 66%, var(--red) 66% 100%);
        }}

        .block-container {{
            max-width: 1180px;
            padding-top: 2.5rem;
            padding-bottom: 4rem;
        }}

        h1, h2, h3, p, label, .stTabs {{
            font-family: 'Noto Sans Ethiopic', sans-serif;
        }}

        h1, h2, h3 {{
            color: var(--ink);
            letter-spacing: -.02em;
        }}

        .brand-mark {{
            display: inline-flex;
            align-items: center;
            gap: .7rem;
            color: var(--ink);
            font-size: 1.15rem;
            font-weight: 800;
            letter-spacing: .02em;
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
            box-shadow: 0 8px 22px rgba(24, 50, 43, .16);
        }}

        .eyebrow {{
            display: inline-block;
            margin: 1.6rem 0 .7rem;
            color: var(--green);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .14em;
            text-transform: uppercase;
        }}

        .hero {{
            position: relative;
            overflow: hidden;
            margin: 1.2rem 0 2.2rem;
            padding: clamp(2rem, 5vw, 4.5rem);
            border: 1px solid rgba(24, 50, 43, .1);
            border-radius: 2rem;
            background:
                linear-gradient(120deg, rgba(22, 132, 74, .96), rgba(24, 50, 43, .94)),
                var(--green);
            box-shadow: 0 18px 55px rgba(24, 50, 43, .16);
        }}

        .hero::after {{
            position: absolute;
            right: -8rem;
            bottom: -11rem;
            width: 25rem;
            height: 25rem;
            border: 1.6rem solid rgba(242, 201, 76, .33);
            border-radius: 50%;
            content: "";
        }}

        .hero::before {{
            position: absolute;
            top: -8rem;
            right: 20%;
            width: 17rem;
            height: 17rem;
            border: 1rem solid rgba(197, 61, 61, .25);
            border-radius: 50%;
            content: "";
        }}

        .hero-content {{
            position: relative;
            z-index: 1;
            max-width: 52rem;
        }}

        .hero h1 {{
            margin: 0;
            color: #fffdf8;
            font-size: clamp(2rem, 5vw, 4.5rem);
            line-height: 1.12;
        }}

        .hero p {{
            max-width: 44rem;
            margin: 1.2rem 0 0;
            color: rgba(255, 253, 248, .86);
            font-size: clamp(1rem, 2vw, 1.22rem);
            line-height: 1.9;
        }}

        .hero-ribbon {{
            display: inline-flex;
            margin-bottom: 1.3rem;
            padding: .42rem .75rem;
            border: 1px solid rgba(255, 253, 248, .25);
            border-radius: 999px;
            color: var(--yellow);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
        }}

        .section-intro {{
            max-width: 46rem;
            margin-bottom: 1.2rem;
        }}

        .section-intro p {{
            color: rgba(24, 50, 43, .72);
            line-height: 1.85;
        }}

        .feature-card {{
            height: 100%;
            padding: 1.2rem;
            border: 1px solid rgba(24, 50, 43, .1);
            border-radius: 1.1rem;
            background: rgba(255, 253, 248, .75);
            box-shadow: 0 10px 25px rgba(24, 50, 43, .06);
        }}

        .feature-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.8rem;
            height: 2.8rem;
            margin-bottom: .7rem;
            border-radius: .9rem;
            background: rgba(242, 201, 76, .22);
            color: var(--ink);
            font-size: 1.25rem;
        }}

        .feature-card h3 {{
            margin: 0 0 .4rem;
            font-size: 1.05rem;
        }}

        .feature-card p {{
            margin: 0;
            color: rgba(24, 50, 43, .7);
            font-size: .9rem;
            line-height: 1.7;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: .45rem;
            padding: .35rem;
            border: 1px solid rgba(24, 50, 43, .1);
            border-radius: 1rem;
            background: rgba(255, 253, 248, .82);
        }}

        .stTabs [data-baseweb="tab"] {{
            height: 3rem;
            padding: 0 1.15rem;
            border-radius: .7rem;
            color: rgba(24, 50, 43, .7);
            font-weight: 700;
        }}

        .stTabs [aria-selected="true"] {{
            background: var(--ink);
            color: #fffdf8;
        }}

        .stButton > button, .stDownloadButton > button {{
            border: 0;
            border-radius: .75rem;
            background: var(--green);
            color: #fffdf8;
            font-weight: 700;
        }}

        .stButton > button:hover, .stDownloadButton > button:hover {{
            border: 0;
            background: var(--ink);
            color: #fffdf8;
        }}

        .chat-note {{
            margin: 1rem 0;
            padding: 1rem 1.1rem;
            border-left: 4px solid var(--yellow);
            border-radius: .7rem;
            background: rgba(242, 201, 76, .14);
            color: rgba(24, 50, 43, .82);
            line-height: 1.75;
        }}

        .price-pill {{
            display: inline-block;
            margin-top: .55rem;
            padding: .25rem .6rem;
            border-radius: 999px;
            background: rgba(22, 132, 74, .1);
            color: var(--green);
            font-size: .8rem;
            font-weight: 800;
        }}

        .gallery-empty {{
            padding: 2.4rem 1rem;
            border: 1px dashed rgba(24, 50, 43, .22);
            border-radius: 1rem;
            text-align: center;
            color: rgba(24, 50, 43, .65);
        }}

        .footer {{
            margin-top: 3rem;
            padding-top: 1.25rem;
            border-top: 1px solid rgba(24, 50, 43, .12);
            color: rgba(24, 50, 43, .6);
            font-size: .85rem;
            text-align: center;
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
            <span>ቅርስ ቤት <span style="opacity:.55;">/</span> Qirss Bet</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_order_now(item: dict[str, Any], key_prefix: str) -> None:
    with st.expander("ይዘዙ · Order Now"):
        with st.form(f"{key_prefix}_order_{item['id']}"):
            quantity = st.number_input(
                "ብዛት", min_value=1, max_value=50, value=1, step=1,
                key=f"{key_prefix}_qty_{item['id']}",
            )
            name = st.text_input("ሙሉ ስም", key=f"{key_prefix}_name_{item['id']}")
            phone = st.text_input("ስልክ ቁጥር", key=f"{key_prefix}_phone_{item['id']}")
            notes = st.text_area(
                "ተጨማሪ መረጃ (አማራጭ)", height=70, key=f"{key_prefix}_notes_{item['id']}"
            )
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
                        "notes": notes.strip(),
                    }
                )
                st.success(f"ትዕዛዝዎ ተልኳል! የትዕዛዝ ቁጥርዎ፦ {order['number']}")


def render_home() -> None:
    home = read_store().get("home", dict(HOME_DEFAULTS))

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-content">
                <div class="hero-ribbon">{home['hero_ribbon']}</div>
                <h1>{home['hero_title']}</h1>
                <p>
                    {home['hero_body']}
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    banner_path = _product_photo_path(home.get("banner_photo_filename", ""))
    if banner_path:
        st.image(str(banner_path), use_container_width=True)

    st.markdown('<div class="eyebrow">Our promise · የእኛ ቃል</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-intro"><h2>{home["promise_title"]}</h2>'
        f'<p>{home["promise_body"]}</p></div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(3)
    features = [
        ("✧", "ባህላዊ ልብስ", "እውነተኛ የባህል ጨርቆች፣ በጥንቃቄ የተሰሩ እና ለልዩ ቀንዎ የሚመቹ።"),
        ("◉", "የኢትዮጵያ ምግብ", "እንጀራ፣ ሽሮ እና ሌሎች ተወዳጅ ጣዕሞችን በቤተሰብ ዘዴ እናዘጋጃለን።"),
        ("◇", "በፍቅር አገልግሎት", "ጥያቄዎን ለመመለስ እና ትዕዛዝዎን ለማዘጋጀት እዚህ ነን።"),
    ]
    for column, (icon, title, body) in zip(columns, features):
        with column:
            st.markdown(
                f'<div class="feature-card"><div class="feature-icon">{icon}</div>'
                f"<h3>{title}</h3><p>{body}</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="chat-note" style="margin-top:1.7rem;">'
        "የሚፈልጉትን ዋጋ ወይም የትዕዛዝ መረጃ ለማወቅ ወደ <b>AI ረዳት</b> ትር ይሂዱ።"
        "</div>",
        unsafe_allow_html=True,
    )

    catalog_items = read_store()["items"]
    if catalog_items:
        st.markdown(
            '<div class="eyebrow" style="margin-top:2.2rem;">Featured · ተወዳጅ ምርቶች</div>',
            unsafe_allow_html=True,
        )
        featured = catalog_items[:3]
        featured_columns = st.columns(len(featured))
        for column, item in zip(featured_columns, featured):
            with column:
                photo_path = _product_photo_path(item.get("photo_filename", ""))
                if photo_path:
                    st.image(str(photo_path), use_container_width=True)
                else:
                    st.markdown(
                        '<div class="gallery-empty" style="padding:3.5rem 1rem;">'
                        "ምስል አልተጫነም</div>",
                        unsafe_allow_html=True,
                    )
                st.subheader(item["name"])
                st.markdown(
                    f'<span class="price-pill">{item["price"]:,} ብር</span>',
                    unsafe_allow_html=True,
                )
                _render_order_now(item, key_prefix="home")




def render_about() -> None:
    about = read_store().get("about", dict(ABOUT_DEFAULTS))
    st.markdown('<div class="eyebrow">About · ስለ እኛ</div>', unsafe_allow_html=True)
    st.markdown(f"<h1>{about['title']}</h1>", unsafe_allow_html=True)

    photo_path = _product_photo_path(about.get("photo_filename", ""))
    if photo_path:
        st.image(str(photo_path), use_container_width=True)

    st.markdown(
        f'<div class="section-intro"><p style="white-space:pre-line;">{about["body"]}</p></div>',
        unsafe_allow_html=True,
    )


def render_order() -> None:
    st.markdown('<div class="eyebrow">Order · ትዕዛዝ</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-intro"><h2>ትዕዛዝዎን ያስገቡ</h2>'
        "<p>የሚፈልጉትን ልብስ ወይም ምግብ ይምረጡ፣ መጠኑን ያስገቡ እና የመገናኛ መረጃዎን ያካፍሉ።</p></div>",
        unsafe_allow_html=True,
    )
    st.info("ይህ የትዕዛዝ ጥያቄ ነው። የመጨረሻ ዋጋና ማድረሻ ለማረጋገጥ በስልክ እንገናኛለን።")

    category = st.radio(
        "የምርት ዓይነት",
        ["ሁሉም", "ልብስ", "ምግብ"],
        horizontal=True,
    )
    catalog_items = read_store()["items"]
    available_items = [
        item for item in catalog_items if category == "ሁሉም" or item["category"] == category
    ]

    with st.form("order_request_form", clear_on_submit=False):
        item = st.selectbox(
            "የሚፈልጉትን ይምረጡ",
            available_items,
            format_func=lambda product: f"{product['name']} · {product['price']:,} ብር",
        )
        quantity = st.number_input(
            "ብዛት",
            min_value=1,
            max_value=100,
            value=1,
            step=1,
        )
        total = item["price"] * quantity
        st.markdown(
            f'<div class="price-pill">ጠቅላላ ግምታዊ ዋጋ · {total:,} ብር</div>',
            unsafe_allow_html=True,
        )

        name_col, phone_col = st.columns(2)
        with name_col:
            customer_name = st.text_input("ሙሉ ስም *", placeholder="ለምሳሌ፦ ሀና አበበ")
        with phone_col:
            phone = st.text_input("ስልክ ቁጥር *", placeholder="ለምሳሌ፦ 09XXXXXXXX")

        submitted = st.form_submit_button("የትዕዛዝ ጥያቄ ላክ", use_container_width=True)

    if submitted:
        errors = []
        clean_name = customer_name.strip()
        clean_phone = phone.strip()
        phone_digits = re.sub(r"\D", "", clean_phone)
        if not clean_name:
            errors.append("ሙሉ ስምዎን ያስገቡ።")
        if not clean_phone or len(phone_digits) < 7 or len(phone_digits) > 15:
            errors.append("ትክክለኛ የስልክ ቁጥር ያስገቡ።")

        if errors:
            st.session_state.last_order = None
            st.error("እባክዎ የተጠየቁትን መረጃዎች ያሟሉ።\n\n" + "\n".join(f"- {error}" for error in errors))
        else:
            order = {
                "item": item["name"],
                "category": item["category"],
                "quantity": quantity,
                "total": total,
                "name": clean_name,
                "phone": clean_phone,
            }
            st.session_state.last_order = add_order(order)

    last_order = st.session_state.get("last_order")
    if last_order:
        st.success(f"ትዕዛዝ ጥያቄዎ ተቀብሏል። የጥያቄ ቁጥርዎ: {last_order['number']}")
        st.markdown(
            f'<div class="feature-card"><h3>የትዕዛዝ ማጠቃለያ</h3>'
            f"<p><b>ምርት:</b> {last_order['item']}<br>"
            f"<b>ብዛት:</b> {last_order['quantity']}<br>"
            f"<b>ግምታዊ ዋጋ:</b> {last_order['total']:,} ብር<br>"
            f"<b>ስም:</b> {last_order['name']}<br>"
            f"<b>ስልክ:</b> {last_order['phone']}</p></div>",
            unsafe_allow_html=True,
        )

def _order_status_label(status: str) -> str:
    return "ተጠናቋል · Completed" if status == "completed" else "በመጠባበቅ ላይ · Pending"


def render_admin_dashboard() -> None:
    notice = st.session_state.pop("admin_notice", None)
    if notice:
        st.success(notice)

    store = read_store()
    orders = store["orders"]
    items = store["items"]
    completed_count = sum(order.get("status") == "completed" for order in orders)
    metric_columns = st.columns(3)
    metric_columns[0].metric("ጠቅላላ ትዕዛዞች", len(orders))
    metric_columns[1].metric("በመጠባበቅ ላይ", len(orders) - completed_count)
    metric_columns[2].metric("የተጠናቀቁ", completed_count)

    st.markdown('<div class="eyebrow">Orders · ትዕዛዞች</div>', unsafe_allow_html=True)
    st.markdown("<h2>የደንበኞች ትዕዛዞች</h2>", unsafe_allow_html=True)
    if not orders:
        st.info("እስካሁን የተላከ የትዕዛዝ ጥያቄ የለም።")
    else:
        for order in reversed(orders):
            order_status = order.get("status", "pending")
            st.markdown(
                f"**{order['number']}** · {order['item']} · "
                f"{order['quantity']} · {order['total']:,} ብር · "
                f"{_order_status_label(order_status)}"
            )
            details_col, status_col = st.columns([2.2, 1])
            with details_col:
                created_at = order.get("created_at", "").replace("T", " ")
                st.caption(
                    f"ደንበኛ: {order['name']} · ስልክ: {order['phone']} · "
                    f"የተላከ: {created_at} UTC"
                )
            with status_col:
                with st.form(f"order_status_{order['number']}"):
                    status = st.selectbox(
                        "ሁኔታ",
                        ["pending", "completed"],
                        index=0 if order_status != "completed" else 1,
                        format_func=_order_status_label,
                        key=f"order-status-{order['number']}",
                    )
                    save_status = st.form_submit_button("ሁኔታ አዘምን")
                if save_status:
                    update_order_status(order["number"], status)
                    st.session_state.admin_notice = f"{order['number']} የትዕዛዝ ሁኔታ ተዘምኗል።"
                    st.rerun()
            st.divider()

    st.markdown('<div class="eyebrow">Catalog · ምናሌ</div>', unsafe_allow_html=True)
    st.markdown("<h2>ልብስ እና ምግብ ማስተካከያ</h2>", unsafe_allow_html=True)
    st.caption("እዚህ የሚደረጉ የምርት እና ዋጋ ለውጦች በደንበኛው የትዕዛዝ ገጽ እና AI ረዳት ላይ ይታያሉ።")
    add_col, edit_col = st.columns(2)
    with add_col:
        with st.form("admin_add_item"):
            st.markdown("**አዲስ ምርት ጨምር**")
            new_category = st.selectbox("ዓይነት", ["ልብስ", "ምግብ"], key="new_item_category")
            new_name = st.text_input("የምርት ስም", key="new_item_name")
            new_price = st.number_input(
                "ዋጋ (ብር)",
                min_value=1,
                max_value=1_000_000,
                value=100,
                step=50,
                key="new_item_price",
            )
            new_photo = st.file_uploader(
                "የምርቱ ፎቶ *",
                type=["png", "jpg", "jpeg", "webp"],
                help="ይህ ፎቶ ከዚህ ምርት ጋር ተያይዞ በShop/Gallery ላይ ይታያል።",
                key="new_item_photo",
            )
            add_item = st.form_submit_button("ምርት ጨምር", use_container_width=True)
        if add_item:
            clean_name = new_name.strip()
            if not clean_name:
                st.error("የምርት ስም ያስገቡ።")
            elif any(existing["name"].casefold() == clean_name.casefold() for existing in items):
                st.error("ይህ የምርት ስም አስቀድሞ አለ።")
            elif not new_photo:
                st.error("ለዚህ ምርት ፎቶ ያስገቡ።")
            else:
                saved_photo = _save_product_photo(new_photo.getvalue(), new_photo.name)
                try:
                    add_catalog_item(new_category, clean_name, int(new_price), saved_photo)
                except Exception:
                    _remove_product_photo(saved_photo)
                    raise
                st.session_state.admin_notice = f"{clean_name} ተጨምሯል።"
                st.rerun()

    with edit_col:
        if items:
            selected_index = st.selectbox(
                "የሚስተካከለውን ምርት ይምረጡ",
                range(len(items)),
                format_func=lambda index: f"{items[index]['name']} · {items[index]['price']:,} ብር",
                key="admin_edit_item_selector",
            )
            selected_item = items[selected_index]
            current_photo_path = _product_photo_path(selected_item.get("photo_filename", ""))
            if current_photo_path:
                st.image(str(current_photo_path), caption="የአሁኑ ፎቶ", use_container_width=True)
            else:
                st.caption("ይህ ምርት እስካሁን ፎቶ የለውም።")
            with st.form("admin_edit_item"):
                st.markdown("**ምርት አስተካክል**")
                edit_category = st.selectbox(
                    "ዓይነት",
                    ["ልብስ", "ምግብ"],
                    index=0 if selected_item["category"] == "ልብስ" else 1,
                    key="edit_item_category",
                )
                edit_name = st.text_input("የምርት ስም", value=selected_item["name"], key="edit_item_name")
                edit_price = st.number_input(
                    "ዋጋ (ብር)",
                    min_value=1,
                    max_value=1_000_000,
                    value=int(selected_item["price"]),
                    step=50,
                    key="edit_item_price",
                )
                replacement_photo = st.file_uploader(
                    "አዲስ ፎቶ (ከፈለጉ ብቻ)",
                    type=["png", "jpg", "jpeg", "webp"],
                    help="አዲስ ፎቶ ካልመረጡ የአሁኑ ፎቶ ይቀጥላል።",
                    key="edit_item_photo",
                )
                save_item = st.form_submit_button("ለውጡን አስቀምጥ", use_container_width=True)
            if save_item:
                clean_name = edit_name.strip()
                duplicate = any(
                    index != selected_index and existing["name"].casefold() == clean_name.casefold()
                    for index, existing in enumerate(items)
                )
                if not clean_name:
                    st.error("የምርት ስም ያስገቡ።")
                elif duplicate:
                    st.error("ይህ የምርት ስም አስቀድሞ አለ።")
                else:
                    old_photo = selected_item.get("photo_filename", "")
                    new_photo_filename = None
                    if replacement_photo:
                        new_photo_filename = _save_product_photo(
                            replacement_photo.getvalue(), replacement_photo.name
                        )
                    try:
                        edit_catalog_item(
                            selected_item["id"],
                            edit_category,
                            clean_name,
                            int(edit_price),
                            new_photo_filename,
                        )
                    except Exception:
                        if new_photo_filename:
                            _remove_product_photo(new_photo_filename)
                        raise
                    if new_photo_filename and new_photo_filename != old_photo:
                        _remove_product_photo(old_photo)
                    st.session_state.admin_notice = f"{clean_name} ተዘምኗል።"
                    st.rerun()
            if st.button("ምርቱን ሰርዝ", key=f"delete-item-{selected_item['id']}"):
                delete_catalog_item(selected_item["id"])
                st.session_state.admin_notice = f"{selected_item['name']} ተሰርዟል።"
                st.rerun()

    st.markdown('<div class="eyebrow">Home Page · መነሻ ገጽ</div>', unsafe_allow_html=True)
    st.markdown("<h2>የመነሻ ገጽ ይዘት ማስተካከያ</h2>", unsafe_allow_html=True)
    st.caption("እዚህ የሚደረጉ ለውጦች ደንበኞች መጀመሪያ በሚያዩት 'መነሻ · Home' ገጽ ላይ ወዲያውኑ ይታያሉ።")

    home = read_store().get("home", dict(HOME_DEFAULTS))
    current_banner_path = _product_photo_path(home.get("banner_photo_filename", ""))
    if current_banner_path:
        st.image(str(current_banner_path), caption="የአሁኑ የመነሻ ገጽ ፎቶ", use_container_width=True)
    else:
        st.caption("የመነሻ ገጽ ፎቶ እስካሁን አልተጨመረም።")

    with st.form("admin_edit_home"):
        edit_ribbon = st.text_input(
            "አጭር መለያ ጽሁፍ (Ribbon)", value=home["hero_ribbon"], key="home_ribbon"
        )
        edit_title = st.text_input(
            "ዋና ርዕስ (Title) — <br> ለአዲስ መስመር ይጠቀሙ",
            value=home["hero_title"],
            key="home_title",
        )
        edit_body = st.text_area(
            "የመግቢያ ጽሁፍ (Description)",
            value=home["hero_body"],
            key="home_body",
            height=120,
        )
        edit_promise_title = st.text_input(
            "የ'ቃላችን' ርዕስ", value=home["promise_title"], key="home_promise_title"
        )
        edit_promise_body = st.text_area(
            "የ'ቃላችን' ጽሁፍ",
            value=home["promise_body"],
            key="home_promise_body",
            height=90,
        )
        new_banner_photo = st.file_uploader(
            "አዲስ የመነሻ ገጽ ፎቶ (ከፈለጉ ብቻ)",
            type=["png", "jpg", "jpeg", "webp"],
            help="አዲስ ፎቶ ካልመረጡ የአሁኑ ፎቶ (ካለ) ይቀጥላል።",
            key="home_banner_photo",
        )
        save_home = st.form_submit_button("የመነሻ ገጽ ለውጦችን አስቀምጥ", use_container_width=True)

    if save_home:
        old_banner = home.get("banner_photo_filename", "")
        new_banner_filename = None
        if new_banner_photo:
            new_banner_filename = _save_product_photo(
                new_banner_photo.getvalue(), new_banner_photo.name
            )
        try:
            update_home_content(
                edit_ribbon.strip(),
                edit_title.strip(),
                edit_body.strip(),
                edit_promise_title.strip(),
                edit_promise_body.strip(),
                new_banner_filename,
            )
        except Exception:
            if new_banner_filename:
                _remove_product_photo(new_banner_filename)
            raise
        if new_banner_filename and new_banner_filename != old_banner and old_banner:
            _remove_product_photo(old_banner)
        st.session_state.admin_notice = "የመነሻ ገጽ ተዘምኗል።"
        st.rerun()

    st.markdown('<div class="eyebrow">About Us · ስለ እኛ</div>', unsafe_allow_html=True)
    st.markdown("<h2>የ'ስለ እኛ' ገጽ ማስተካከያ</h2>", unsafe_allow_html=True)

    about = read_store().get("about", dict(ABOUT_DEFAULTS))
    current_about_photo = _product_photo_path(about.get("photo_filename", ""))
    if current_about_photo:
        st.image(str(current_about_photo), caption="የአሁኑ ፎቶ", use_container_width=True)

    with st.form("admin_edit_about"):
        about_title = st.text_input("ርዕስ", value=about["title"], key="about_title")
        about_body = st.text_area(
            "ሙሉ መግለጫ", value=about["body"], key="about_body", height=160
        )
        about_photo = st.file_uploader(
            "አዲስ ፎቶ (ከፈለጉ ብቻ)",
            type=["png", "jpg", "jpeg", "webp"],
            key="about_photo_uploader",
        )
        save_about = st.form_submit_button("ስለ እኛ ለውጦችን አስቀምጥ", use_container_width=True)

    if save_about:
        old_about_photo = about.get("photo_filename", "")
        new_about_filename = None
        if about_photo:
            new_about_filename = _save_product_photo(about_photo.getvalue(), about_photo.name)
        try:
            update_about_content(about_title.strip(), about_body.strip(), new_about_filename)
        except Exception:
            if new_about_filename:
                _remove_product_photo(new_about_filename)
            raise
        if new_about_filename and new_about_filename != old_about_photo and old_about_photo:
            _remove_product_photo(old_about_photo)
        st.session_state.admin_notice = "የ'ስለ እኛ' ገጽ ተዘምኗል።"
        st.rerun()

    st.markdown('<div class="eyebrow">Chatbot Knowledge Base · የቻትቦት እውቀት</div>', unsafe_allow_html=True)
    st.markdown("<h2>ጥያቄ እና መልስ (FAQ) ማስተዳደር</h2>", unsafe_allow_html=True)
    st.caption("እዚህ የሚጨመሩ ጥያቄና መልሶች AI ረዳቱ ደንበኞችን ሲመልስ ይጠቀምባቸዋል።")

    faqs = read_store().get("faqs", [])
    with st.form("admin_add_faq"):
        st.markdown("**አዲስ ጥያቄ እና መልስ ጨምር**")
        new_question = st.text_input("ጥያቄ", key="new_faq_question")
        new_answer = st.text_area("መልስ", key="new_faq_answer", height=90)
        add_faq_submit = st.form_submit_button("ጨምር", use_container_width=True)
    if add_faq_submit:
        clean_question = new_question.strip()
        clean_answer = new_answer.strip()
        if not clean_question or not clean_answer:
            st.error("ጥያቄ እና መልስ ሁለቱንም ያስገቡ።")
        else:
            add_faq(clean_question, clean_answer)
            st.session_state.admin_notice = "ጥያቄ እና መልስ ተጨምሯል።"
            st.rerun()

    if faqs:
        for faq in faqs:
            with st.expander(faq["question"]):
                with st.form(f"edit_faq_{faq['id']}"):
                    edit_question = st.text_input(
                        "ጥያቄ", value=faq["question"], key=f"faq_q_{faq['id']}"
                    )
                    edit_answer = st.text_area(
                        "መልስ", value=faq["answer"], key=f"faq_a_{faq['id']}", height=90
                    )
                    save_faq_col, delete_faq_col = st.columns(2)
                    with save_faq_col:
                        save_faq_submit = st.form_submit_button("አስቀምጥ", use_container_width=True)
                    with delete_faq_col:
                        delete_faq_submit = st.form_submit_button("ሰርዝ", use_container_width=True)
                if save_faq_submit:
                    edit_faq(faq["id"], edit_question.strip(), edit_answer.strip())
                    st.session_state.admin_notice = "ጥያቄና መልስ ተዘምኗል።"
                    st.rerun()
                if delete_faq_submit:
                    delete_faq(faq["id"])
                    st.session_state.admin_notice = "ጥያቄና መልስ ተሰርዟል።"
                    st.rerun()
    else:
        st.caption("እስካሁን የተጨመረ ጥያቄና መልስ የለም።")


def render_admin() -> None:
    st.markdown('<div class="eyebrow">Admin · አስተዳደር</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-intro"><h2>የሱቅ አስተዳደር</h2>'
        "<p>ትዕዛዞችን ይመልከቱ፣ ሁኔታቸውን ያዘምኑ እና የምርት ዋጋዎችን ያስተካክሉ።</p></div>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("admin_authenticated"):
        logout_col, _ = st.columns([1, 4])
        with logout_col:
            if st.button("ውጣ · Log out", key="admin_logout"):
                st.session_state.admin_authenticated = False
                st.rerun()
        render_admin_dashboard()
        return

    with st.form("admin_login"):
        password = st.text_input("የአስተዳዳሪ ይለፍ ቃል", type="password")
        login = st.form_submit_button("ግባ · Log in", use_container_width=True)
    if login:
        configured_password = os.getenv("ADMIN_PASSWORD", "")
        if not configured_password:
            st.error("ADMIN_PASSWORD ሚስጥሩ አልተዘጋጀም።")
        elif hmac.compare_digest(password, configured_password):
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("የአስተዳዳሪ ይለፍ ቃሉ ትክክል አይደለም።")


def _groq_error_detail(response: requests.Response, api_key: str) -> str:
    """Return a short, safe diagnostic without exposing the API key."""
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = error.get("message") or error.get("type") or str(error)
        elif error:
            message = str(error)
        else:
            message = response.text.strip()
    except ValueError:
        message = response.text.strip()

    message = " ".join(str(message).split())
    if not message:
        message = response.reason or "No error message returned by Groq."
    message = message.replace(api_key, "[redacted]")
    return f"HTTP {response.status_code}: {message[:320]}"


def groq_reply(messages: list[dict[str, str]]) -> tuple[str, str | None]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return (
            "ይቅርታ፣ የAI አገልግሎት ቁልፍ አልተዘጋጀም። እባክዎ በኋላ ይሞክሩ።",
            "GROQ_API_KEY is missing or empty in the running app environment.",
        )

    store = read_store()
    catalog_items = store["items"]
    catalog_context = "\n".join(
        f"- {item['name']}: {item['price']:,} ብር" for item in catalog_items
    )
    faqs = store.get("faqs", [])
    faq_context = "\n".join(f"ጥ: {faq['question']}\nመ: {faq['answer']}" for faq in faqs)
    faq_section = f"\n\nየተለመዱ ጥያቄና መልሶች:\n{faq_context}\n" if faq_context else ""
    system_message = {
        "role": "system",
        "content": (
            "እርስዎ ኖካ የደንበኛ ረዳት ነዎት። ሁልጊዜ በአማርኛ ብቻ "
            "በትህትና፣ በግልጽነት እና በአጭር ይመልሱ። ዋጋ የሌለውን ነገር "
            "አትገምቱ፤ ከዚህ የንግድ መረጃ ውጭ ከሆነ ደንበኛው በቀጥታ እንዲጠይቅ "
            "ይጋብዙት። ትዕዛዝ ለመስጠት የሚፈለገውን ዕቃ፣ መጠን/ብዛት፣ አድራሻ "
            "እና ስልክ እንዲያዘጋጅ ያስታውሱ።\n\n"
            f"የአሁኑ ምናሌ እና ዋጋዎች:\n{catalog_context}\n"
            "የማድረሻ ጊዜ እና የመጨረሻ ዋጋ እንደ አካባቢ ሊለያይ ይችላል።"
            f"{faq_section}"
        ),
    }
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [system_message, *messages],
                "temperature": 0.4,
                "max_tokens": 500,
            },
            timeout=45,
        )
        if not response.ok:
            detail = _groq_error_detail(response, api_key)
            if response.status_code in {401, 403}:
                customer_message = (
                    "ይቅርታ፣ የAI አገልግሎት ቁልፍ ችግር አለበት። "
                    "እባክዎ በኋላ ይሞክሩ።"
                )
            elif response.status_code == 429:
                customer_message = (
                    "ይቅርታ፣ የAI አገልግሎቱ ለጊዜው ተጨናንቋል። "
                    "እባክዎ ጥቂት ቆይተው ይሞክሩ።"
                )
            else:
                customer_message = (
                    "ይቅርታ፣ ከAI ረዳቱ ጋር ግንኙነት ላይ ችግር ተፈጥሯል። "
                    "እባክዎ ጥቂት ቆይተው ይሞክሩ።"
                )
            return customer_message, detail

        payload: dict[str, Any] = response.json()
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Groq returned an empty assistant message.")
        return content.strip(), None
    except requests.Timeout:
        return (
            "ይቅርታ፣ የAI ረዳቱ ምላሽ ለመስጠት በጣም ዘግይቷል። እባክዎ እንደገና ይሞክሩ።",
            "The Groq request timed out after 45 seconds.",
        )
    except requests.ConnectionError as error:
        return (
            "ይቅርታ፣ ከAI ረዳቱ ጋር መገናኘት አልተቻለም። እባክዎ ቆይተው ይሞክሩ።",
            f"Could not connect to Groq: {type(error).__name__}.",
        )
    except requests.RequestException as error:
        return (
            "ይቅርታ፣ ከAI ረዳቱ ጋር ግንኙነት ላይ ችግር ተፈጥሯል። እባክዎ ጥቂት ቆይተው ይሞክሩ።",
            f"Groq request failed: {type(error).__name__}.",
        )
    except (KeyError, IndexError, TypeError, ValueError) as error:
        return (
            "ይቅርታ፣ የAI ምላሹን ማንበብ አልተቻለም። እባክዎ ጥያቄዎን እንደገና ይላኩ።",
            f"Groq returned an unexpected response: {type(error).__name__}: {error}",
        )


def render_chat() -> None:
    st.markdown('<div class="eyebrow">AI assistant · የAI ረዳት</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-intro"><h2>ጥያቄ አለዎት? በአማርኛ ይጠይቁ</h2>'
        "<p>ስለ ልብስ ዋጋ፣ ስለ ምግብ ምናሌ ወይም ትዕዛዝ አሰጣጥ ይጠይቁ።</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="chat-note">ምሳሌ፦ <b>የሴቶች ባህላዊ ቀሚስ ስንት ነው?</b> ወይም '
        "<b>የበዓል ምግብ ጥቅል እንዴት እዘዛለሁ?</b></div>",
        unsafe_allow_html=True,
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "ሰላም! እንኳን ወደ ቅርስ ቤት በደህና መጡ። ስለ ልብስ፣ ምግብ ዋጋ ወይም ትዕዛዝ ምን ልርዳዎት?",
            }
        ]

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("ጥያቄዎን በአማርኛ ይጻፉ...")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("መልስ እያዘጋጀሁ ነው..."):
                answer, error_detail = groq_reply(st.session_state.chat_messages)
            st.markdown(answer)
            if error_detail:
                st.error("የቴክኒክ ስህተት ተፈጥሯል።")
                with st.expander("የስህተት ዝርዝር / Error details"):
                    st.code(error_detail)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})

    if len(st.session_state.chat_messages) > 1 and st.button("ውይይቱን አጽዳ", key="clear-chat"):
        st.session_state.chat_messages = []
        st.rerun()


def main() -> None:
    inject_styles()
    render_brand_header()

    configured_admin_key = os.getenv("ADMIN_URL_KEY", "")
    provided_admin_key = st.query_params.get(ADMIN_URL_PARAM, "")
    show_admin_tab = bool(configured_admin_key) and hmac.compare_digest(
        provided_admin_key, configured_admin_key
    )

    tab_labels = [
        "መነሻ · Home",
        "ማዕከለ-ስዕል · Gallery",
        "ስለ እኛ · About",
        "ትዕዛዝ · Order",
        "AI ረዳት · Chat",
    ]
    if show_admin_tab:
        tab_labels.append("Admin · አስተዳደር")

    tabs = st.tabs(tab_labels)
    home_tab, gallery_tab, about_tab, order_tab, chat_tab = tabs[:5]

    with home_tab:
        render_home()
    with gallery_tab:
        render_gallery()
    with about_tab:
        render_about()
    with order_tab:
        render_order()
    with chat_tab:
        render_chat()
    if show_admin_tab:
        with tabs[5]:
            render_admin()

    st.markdown(
        '<div class="footer">ኖካ · የኢትዮጵያ ባህልን ከልብ ጋር እናካፍላለን</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
