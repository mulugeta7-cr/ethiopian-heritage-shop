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
        "ኖካ / NOOKA የተመሰረተው የኢትዮጵያን ባህላዊ ልብስ እና ምግብ ከቤተሰብ ወደ ቤተሰብ "
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


def _product_photo_path(filename: str) -> Path | None:
    if not filename:
        return None
    safe_filename = Path(filename).name
    photo_path = PHOTO_DIR / safe_filename
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

        .hero {{
            position: relative;
            overflow: hidden;
            margin: 1.2rem 0 2.2rem;
            padding: 3rem;
            border-radius: 2rem;
            background: linear-gradient(120deg, rgba(22, 132, 74, .96), rgba(24, 50, 43, .94));
            color: #fffdf8;
        }}

        .price-pill {{
            display: inline-block;
            padding: .25rem .6rem;
            border-radius: 999px;
            background: rgba(22, 132, 74, .1);
            color: var(--green);
            font-size: .8rem;
            font-weight: 800;
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


def _render_order_now(item: dict[str, Any], key_prefix: str) -> None:
    with st.expander("ይዘዙ · Order Now"):
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
            <div class="hero-content">
                <div style="color:var(--yellow); text-transform:uppercase; font-weight:bold;">{home['hero_ribbon']}</div>
                <h1 style="color:#fff;">{home['hero_title']}</h1>
                <p>{home['hero_body']}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    catalog_items = read_store()["items"]
    if catalog_items:
        st.subheader("ተወዳጅ ምርቶች")
        featured = catalog_items[:3]
        featured_columns = st.columns(len(featured))
        for column, item in zip(featured_columns, featured):
            with column:
                st.markdown(f"### {item['name']}")
                st.markdown(f'<span class="price-pill">{item["price"]:,} ብር</span>', unsafe_allow_html=True)
                _render_order_now(item, key_prefix="home")


def render_gallery() -> None:
    st.subheader("ምርቶቻችንን ይመልከቱ")
    catalog_items = read_store()["items"]
    catalog_filter = st.selectbox("የምርት ዓይነት", ["ሁሉም", "ልብስ", "ምግብ"], key="shop_category")
    visible_catalog = [
        item for item in catalog_items if catalog_filter == "ሁሉም" or item["category"] == catalog_filter
    ]
    if not visible_catalog:
        st.info("በዚህ ዓይነት የተመዘገበ ምርት የለም።")
    else:
        product_columns = st.columns(min(3, len(visible_catalog)))
        for index, item in enumerate(visible_catalog):
            with product_columns[index % len(product_columns)]:
                st.markdown(f"### {item['name']}")
                st.caption(item["category"])
                st.markdown(f'<span class="price-pill">{item["price"]:,} ብር</span>', unsafe_allow_html=True)
                _render_order_now(item, key_prefix="gallery")


def render_about() -> None:
    about = read_store().get("about", dict(ABOUT_DEFAULTS))
    st.title(about['title'])
    st.write(about['body'])


def main() -> None:
    inject_styles()
    render_brand_header()

    tabs = st.tabs(["መነሻ (Home)", "ሱቅ (Gallery)", "ስለ እኛ (About)"])
    with tabs[0]:
        render_home()
    with tabs[1]:
        render_gallery()
    with tabs[2]:
        render_about()


if __name__ == "__main__":
    main()
