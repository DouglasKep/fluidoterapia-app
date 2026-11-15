        st.metric(
            "Aporte de K sugerido automáticamente",
            f"{k_rate_default:.3f} mEq/kg/h",
            f"Según K sérico {k_serum:.1f} mmol/L · {k_schedule}",
        )
        use_manual_k_rate = st.checkbox(
            "Introducir otro ritmo indicado en la prescripción",
            key="iv_k_manual_override",
        )
        if use_manual_k_rate:
            k_auto_signature = (k_schedule, round(float(k_serum), 3))
            if st.session_state.get("_iv_k_auto_signature") != k_auto_signature:
                st.session_state["iv_k_rate_manual"] = float(k_rate_default)
                st.session_state["_iv_k_auto_signature"] = k_auto_signature
            k_rate = st.number_input(
                "Aporte total de K prescrito (mEq/kg/h)",
                min_value=0.0,
                max_value=0.5,
                value=float(k_rate_default),
                step=0.01,
                format="%.3f",
                key="iv_k_rate_manual",
                help="Se actualiza con el potasio sérico mientras uses este modo. No superar 0,5 mEq/kg/h.",
            )
        else:
            k_rate = float(k_rate_default)
