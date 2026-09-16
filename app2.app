new_category = st.selectbox("ዓይነት", ["ልብስ", "ምግብ"], key="new_item_cat")
            new_name = st.text_input("የምርት ስም", key="new_item_name")
            new_price = st.number_input("ዋጋ (ብር)", min_value=1, value=500, step=50, key="new_item_price")
            new_photo = st.file_uploader("የምርት ምስል", type=["png", "jpg", "jpeg", "webp"], key="new_item_photo")
            submit_add = st.form_submit_button("ምርት ጨምር", use_container_width=True)

        if submit_add:
            clean_name = new_name.strip()
            if not clean_name:
                st.error("እባክዎ የምርት ስም ያስገቡ።")
            else:
                filename = ""
                if new_photo:
                    try:
                        filename = _save_product_photo(new_photo.getvalue(), new_photo.name)
                    except ValueError as err:
                        st.error(str(err))
                        st.stop()
                add_catalog_item(new_category, clean_name, int(new_price), filename)
                st.session_state.admin_notice = f"'{clean_name}' በተካካይ ተጨምሯል።"
                st.rerun()

    with edit_col:
        st.markdown("**ነባር ምርቶችን አስተካክል / ሰርዝ**")
        if not items:
            st.info("ምንም ምርቶች የሉም።")
        else:
            selected_item = st.selectbox(
                "ምርት ይምረጡ",
                items,
                format_func=lambda product: f"{product['name']} ({product['category']}) - {product['price']:,} ብር",
                key="admin_select_edit_item",
            )
            with st.form(f"admin_edit_item_{selected_item['id']}"):
                edit_category = st.selectbox(
                    "ዓይነት",
                    ["ልብስ", "ምግብ"],
                    index=0 if selected_item["category"] == "ልብስ" else 1,
                    key=f"edit_cat_{selected_item['id']}",
                )
                edit_name = st.text_input("የምርት ስም", value=selected_item["name"], key=f"edit_name_{selected_item['id']}")
                edit_price = st.number_input(
                    "ዋጋ (ብር)",
                    min_value=1,
                    value=int(selected_item["price"]),
                    step=50,
                    key=f"edit_price_{selected_item['id']}",
                )
                edit_photo = st.file_uploader(
                    "አዲስ ምስል ይምረጡ (አማራጭ)",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"edit_photo_{selected_item['id']}",
                )
                
                col_update, col_delete = st.columns(2)
                submit_edit = col_update.form_submit_button("ለውጦችን አስቀምጥ", use_container_width=True)
                submit_delete = col_delete.form_submit_button("ምርቱን ሰርዝ", use_container_width=True)

            if submit_edit:
                clean_name = edit_name.strip()
                if not clean_name:
                    st.error("እባክዎ የምርት ስም ያስገቡ።")
                else:
                    new_filename = None
                    if edit_photo:
                        try:
                            new_filename = _save_product_photo(edit_photo.getvalue(), edit_photo.name)
                            old_filename = selected_item.get("photo_filename", "")
                            _remove_product_photo(old_filename)
                        except ValueError as err:
                            st.error(str(err))
                            st.stop()
                    edit_catalog_item(selected_item["id"], edit_category, clean_name, int(edit_price), new_filename)
                    st.session_state.admin_notice = f"'{clean_name}' ተዘምኗል።"
                    st.rerun()

            if submit_delete:
                delete_catalog_item(selected_item["id"])
                st.session_state.admin_notice = f"'{selected_item['name']}' ተሰርዟል።"
                st.rerun()

    st.divider()

    st.markdown('<div class="eyebrow">Content Management · የይዘት ማስተካከያ</div>', unsafe_allow_html=True)
    home_tab, about_tab, faq_tab = st.tabs(["መነሻ ገጽ (Home)", "ስለ እኛ (About)", "ተደጋጋሚ ጥያቄዎች (FAQs)"])

    with home_tab:
        home_data = store.get("home", dict(HOME_DEFAULTS))
        with st.form("admin_home_form"):
            hero_ribbon = st.text_input("Hero Ribbon", value=home_data.get("hero_ribbon", ""))
            hero_title = st.text_input("Hero Title", value=home_data.get("hero_title", ""))
            hero_body = st.text_area("Hero Body", value=home_data.get("hero_body", ""), height=100)
            promise_title = st.text_input("Promise Title", value=home_data.get("promise_title", ""))
            promise_body = st.text_area("Promise Body", value=home_data.get("promise_body", ""), height=80)
            banner_photo = st.file_uploader("የባነር ምስል", type=["png", "jpg", "jpeg", "webp"], key="admin_banner_photo")
            submit_home = st.form_submit_button("የመነሻ ገጽ ይዘት አዘምን")

        if submit_home:
            banner_filename = None
            if banner_photo:
                try:
                    banner_filename = _save_product_photo(banner_photo.getvalue(), banner_photo.name)
                    _remove_product_photo(home_data.get("banner_photo_filename", ""))
                except ValueError as err:
                    st.error(str(err))
                    st.stop()
            update_home_content(hero_ribbon, hero_title, hero_body, promise_title, promise_body, banner_filename)
            st.session_state.admin_notice = "የመነሻ ገጽ መረጃ ተዘምኗል።"
            st.rerun()

    with about_tab:
        about_data = store.get("about", dict(ABOUT_DEFAULTS))
        with st.form("admin_about_form"):
            about_title = st.text_input("ርዕስ", value=about_data.get("title", ""))
            about_body = st.text_area("ዝርዝር መረጃ", value=about_data.get("body", ""), height=150)
            about_photo = st.file_uploader("የስለ እኛ ምስል", type=["png", "jpg", "jpeg", "webp"], key="admin_about_photo")
            submit_about = st.form_submit_button("የስለ እኛ ገጽ አዘምን")

        if submit_about:
            about_filename = None
            if about_photo:
                try:
                    about_filename = _save_product_photo(about_photo.getvalue(), about_photo.name)
                    _remove_product_photo(about_data.get("photo_filename", ""))
                except ValueError as err:
                    st.error(str(err))
                    st.stop()
            update_about_content(about_title, about_body, about_filename)
            st.session_state.admin_notice = "የስለ እኛ ገጽ መረጃ ተዘምኗል።"
            st.rerun()

    with faq_tab:
        faqs = store.get("faqs", [])
        st.markdown("**አዲስ ተደጋጋሚ ጥያቄ ጨምር**")
        with st.form("admin_add_faq"):
            faq_q = st.text_input("ጥያቄ")
            faq_a = st.text_area("መልስ", height=80)
            submit_faq = st.form_submit_button("ጥያቄ ጨምር")

        if submit_faq:
            if faq_q.strip() and faq_a.strip():
                add_faq(faq_q.strip(), faq_a.strip())
                st.session_state.admin_notice = "አዲስ ጥያቄ ተጨምሯል።"
                st.rerun()
            else:
                st.error("እባክዎ ጥያቄውን እና መልሱን ሙሉ በሙሉ ያስገቡ።")

        if faqs:
            st.markdown("**ነባር ተደጋጋሚ ጥያቄዎች**")
            for faq in faqs:
                with st.expander(f"Q: {faq['question']}"):
                    with st.form(f"edit_faq_{faq['id']}"):
                        eq = st.text_input("ጥያቄ", value=faq['question'], key=f"q_{faq['id']}")
                        ea = st.text_area("መልስ", value=faq['answer'], key=f"a_{faq['id']}")
                        c1, c2 = st.columns(2)
                        save_f = c1.form_submit_button("አስቀምጥ")
                        del_f = c2.form_submit_button("ሰርዝ")

                    if save_f:
                        edit_faq(faq['id'], eq.strip(), ea.strip())
                        st.session_state.admin_notice = "ጥያቄው ተዘምኗል።"
                        st.rerun()
                    if del_f:
                        delete_faq(faq['id'])
                        st.session_state.admin_notice = "ጥያቄው ተሰርዟል።"
                        st.rerun()


def _call_groq_api(prompt: str) -> str:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "GROQ_API_KEY አልተዋቀረም። እባክዎ የአካባቢ ተለዋዋጭ ያዋቅሩ።"

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as err:
        return f"ረዳቱን ማነጋገር አልተቻለም፦ {err}"


def render_ai_assistant() -> None:
    st.markdown('<div class="eyebrow">AI Support · AI ረዳት</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-intro"><h2>የቅርስ ቤት ረዳት</h2>'
        "<p>ስለ ምርቶቻችን፣ ዋጋዎች ወይም ባህላዊ መረጃ ማንኛውንም ጥያቄ ይጠይቁ።</p></div>",
        unsafe_allow_html=True,
    )

    store = read_store()
    catalog_context = json.dumps(store["items"], ensure_ascii=False)
    faqs_context = json.dumps(store.get("faqs", []), ensure_ascii=False)
    system_prompt_context = (
        f"You are an AI customer support bot for 'ቅርስ ቤት (Qirss Bet)', an Ethiopian traditional clothing and food store.\n"
        f"Current catalog items: {catalog_context}\n"
        f"FAQs: {faqs_context}\n"
        f"Respond politely and accurately in Amharic (or English if prompted in English). Answer questions about prices, items, and heritage."
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("ጥያቄዎን እዚህ ጻፉ..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        full_prompt = f"{system_prompt_context}\n\nUser Question: {user_input}"
        with st.chat_message("assistant"):
            with st.spinner("እየተሰላ ነው..."):
                bot_reply = _call_groq_api(full_prompt)
                st.markdown(bot_reply)

        st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})


def render_faqs() -> None:
    st.markdown('<div class="eyebrow">FAQ · ተደጋጋሚ ጥያቄዎች</div>', unsafe_allow_html=True)
    st.markdown("<h2>ተደጋጋሚ ጥያቄዎች እና መልሶች</h2>", unsafe_allow_html=True)

    faqs = read_store().get("faqs", [])
    if not faqs:
        st.info("ምንም ተደጋጋሚ ጥያቄዎች አልተመዘገቡም።")
        return

    for faq in faqs:
        with st.expander(faq["question"]):
            st.write(faq["answer"])


def main() -> None:
    inject_styles()
    render_brand_header()

    query_params = st.query_params
    is_admin = query_params.get(ADMIN_URL_PARAM) == "true" or st.session_state.get("is_admin", False)

    if is_admin:
        st.session_state.is_admin = True
        st.sidebar.markdown("### Admin Controls")
        if st.sidebar.button("የአስተዳዳሪ ገጽ ውጣ (Exit Admin)"):
            st.session_state.is_admin = False
            if ADMIN_URL_PARAM in st.query_params:
                del st.query_params[ADMIN_URL_PARAM]
            st.rerun()

        tabs = ["አስተዳዳሪ (Admin)", "መነሻ (Home)", "ማዕከለ-ስዕል (Gallery)", "ስለ እኛ (About)", "ትዕዛዝ (Order)", "AI ረዳት", "FAQs"]
        active_tab = st.tabs(tabs)
        
        with active_tab[0]:
            render_admin_dashboard()
        with active_tab[1]:
            render_home()
        with active_tab[2]:
            render_gallery()
        with active_tab[3]:
            render_about()
        with active_tab[4]:
            render_order()
        with active_tab[5]:
            render_ai_assistant()
        with active_tab[6]:
            render_faqs()

    else:
        tabs = ["መነሻ (Home)", "ማዕከለ-ስዕል (Gallery)", "ስለ እኛ (About)", "ትዕዛዝ (Order)", "AI ረዳት", "FAQs"]
        active_tab = st.tabs(tabs)

        with active_tab[0]:
            render_home()
        with active_tab[1]:
            render_gallery()
        with active_tab[2]:
            render_about()
        with active_tab[3]:
            render_order()
        with active_tab[4]:
            render_ai_assistant()
        with active_tab[5]:
            render_faqs()

    st.markdown(
        """
        <div class="footer">
            © ቅርስ ቤት (Qirss Bet) - Ethiopian Shinasha Traditional Clothes & Food. All rights reserved.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
