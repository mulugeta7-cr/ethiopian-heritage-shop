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

    return {"items": items, "orders": normalized_orders, "home": normalized_home}


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
            border-radius: 1.2rem;
            background: rgba(255, 253, 248, .9);
            box-shadow: 0 10px 26px rgba(24, 50, 43, .06);
        }}

        .feature-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.4rem;
            height: 2.4rem;
            margin-bottom: .7rem;
            border-radius: .8rem;
            color: #fffdf8;
            background: var(--green);
            font-size: 1.1rem;
        }}

        .feature-card h3 {{
            margin: 0 0 .35rem;
            font-size: 1.05rem;
        }}

        .feature-card p {{
            margin: 0;
            color: rgba(24, 50, 43, .68);
            font-size: .92rem;
            line-height: 1.7;
        }}

        .chat-note {{
            padding: 1rem 1.2rem;
            border: 1px dashed rgba(22, 132, 74, .4);
            border-radius: 1rem;
            background: rgba(22, 132, 74, .06);
            color: rgba(24, 50, 43, .8);
        }}

        .footer {{
            margin-top: 3rem;
            padding-top: 1.4rem;
            border-top: 1px solid rgba(24, 50, 43, .1);
            color: rgba(24, 50, 43, .55);
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


def render_gallery() -> None:
    st.markdown('<div class="eyebrow">Gallery · ማዕከለ-ስዕል</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-intro"><h2>የልብስ እና ምግብ ማዕከለ-ስዕል</h2>'
        "<p>ያሉንን ምርቶች በዋጋቸው እና በፎቶቸው ይመልከቱ።</p></div>",
        unsafe_allow_html=True,
    )

    store = read_store()
    items = store["items"]

    category_filter = st.radio(
        "ማጣሪያ",
        ["ሁሉም", "ልብስ", "ምግብ"],
        horizontal=True,
        key="gallery_category_filter",
    )
    filtered_items = [
        item
        for item in items
        if category_filter == "ሁሉም" or item["category"] == category_filter
    ]

    if not filtered_items:
        st.info("በዚህ ዓይነት ምንም ምርት አልተገኘም።")
        return

    columns = st.columns(3)
    for index, item in enumerate(filtered_items):
        with columns[index % 3]:
            photo_path = _product_photo_path(item.get("photo_filename", ""))
            if photo_path:
                st.image(str(photo_path), use_container_width=True)
            else:
                st.markdown(
                    '<div style="height:180px;border-radius:1rem;background:rgba(24,50,43,.06);'
                    'display:flex;align-items:center;justify-content:center;color:rgba(24,50,43,.4);">'
                    "ምስል የለም</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(f"**{item['name']}**")
            st.caption(f"{item['category']} · {item['price']:,} ብር")


def render_order() -> None:
    st.markdown('<div class="eyebrow">Order · ትዕዛዝ</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-intro"><h2>ትዕዛዝ ያስገቡ</h2>'
        "<p>የሚፈልጉትን ምርት ይምረጡ እና መረጃዎን ያስገቡ።</p></div>",
        unsafe_allow_html=True,
    )

    category = st.radio(
        "ዓይነት",
        ["ሁሉም", "ልብስ", "ምግብ"],
        horizontal=True,
        key="order_category_filter",
    )

    catalog_items = read_store()["items"]
    available_items = [
        item for item in catalog_items if category == "ሁሉም" or item["category"] == category
    ]

    if not available_items:
        st.info("በዚህ ዓይነት ምንም ምርት የለም።")
        return

    with st.form("order_request_form", clear_on_submit=False):
        item = st.selectbox(
            "የሚፈልጉትን ይምረጡ",
            available_items,
            format_func=lambda product: f"{product['name']} · {product['price']:,} ብር",
        )
        quantity = st.number_input("ብዛት", min_value=1, max_value=50, value=1, step=1)
        name = st.text_input("ሙሉ ስም")
        phone = st.text_input("ስልክ ቁጥር")
        notes = st.text_area("ተጨማሪ መረጃ (አማራጭ)", height=80)
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
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message", "")
    except ValueError:
        message = response.text[:200]
    key_hint = f" (key starts with {api_key[:6]}...)" if api_key else " (no API key found)"
    return f"HTTP {response.status_code}{key_hint}: {message}"


def groq_reply(messages: list[dict[str, str]]) -> tuple[str, str | None]:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return "", "GROQ_API_KEY ሚስጥሩ አልተዘጋጀም። እባክዎ አስተዳዳሪውን ያነጋግሩ።"

    system_prompt = (
        "አንተ የቅርስ ቤት ደንበኛ አገልግሎት ረዳት ነህ። ንግዱ ባህላዊ የኢትዮጵያ ልብስ እና ምግብ ያቀርባል። "
        "ሁልጊዜ በአማርኛ፣ በትህትና እና በአጭሩ መልስ ስጥ። ስለ ዋጋ፣ ምርት እና ትዕዛዝ ጥያቄዎችን ይመልሱ።"
    )
    store = read_store()
    catalog_summary = "\n".join(
        f"- {item['name']} ({item['category']}): {item['price']:,} ብር"
        for item in store["items"]
    )
    full_system_prompt = f"{system_prompt}\n\nየአሁኑ ምርቶች:\n{catalog_summary}"

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "system", "content": full_system_prompt}] + messages,
            },
            timeout=30,
        )
        if response.status_code != 200:
            return "", _groq_error_detail(response, api_key)
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        return answer, None
    except requests.RequestException as exc:
        return "", f"የግንኙነት ስህተት፦ {exc}"


def render_chat() -> None:
    st.markdown('<div class="eyebrow">AI Assistant · AI ረዳት</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-intro"><h2>ጥያቄ ይጠይቁ</h2>'
        "<p>ስለ ዋጋ፣ ምርት ወይም ትዕዛዝ ማንኛውንም ጥያቄ ይጠይቁ።</p></div>",
        unsafe_allow_html=True,
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "ሰላም! እንኳን ደህና መጡ። ስለ ልብስ ወይም ምግብ ማንኛውንም ጥያቄ ሊጠይቁኝ ይችላሉ።"}
        ]

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("መልእክትዎን ይጻፉ...")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("እያሰብኩ ነው..."):
                answer, error = groq_reply(st.session_state.chat_messages)
            if error:
                st.error(error)
                answer = "ይቅርታ፣ አሁን መመለስ አልቻልኩም። እባክዎ ቆይተው ይሞክሩ።"
            st.markdown(answer)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})

    if len(st.session_state.chat_messages) > 1 and st.button("ውይይቱን አጽዳ", key="clear-chat"):
        st.session_state.chat_messages = []
        st.rerun()


def main() -> None:
    inject_styles()
    render_brand_header()
    home_tab, gallery_tab, order_tab, chat_tab, admin_tab = st.tabs(
        [
            "መነሻ · Home",
            "ማዕከለ-ስዕል · Gallery",
            "ትዕዛዝ · Order",
            "AI ረዳት · Chat",
            "Admin · አስተዳደር",
        ]
    )

    with home_tab:
        render_home()
    with gallery_tab:
        render_gallery()
    with order_tab:
        render_order()
    with chat_tab:
        render_chat()
    with admin_tab:
        render_admin()

    st.markdown(
        '<div class="footer">ቅርስ ቤት · የኢትዮጵያ ባህልን ከልብ ጋር እናካፍላለን</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
