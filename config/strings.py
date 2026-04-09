"""
UI string definitions for the GIS Dashboard.

All user-visible text in templates is defined here.
To update a label, change the value — do not change the key (templates depend on it).
To find all usages of a key: grep -r "ui_strings\\." templates/
"""

UI_STRINGS = {
    # --- Comuni ---
    "loading": "Caricamento...",
    "actions_col": "Azioni",
    "error_title": "Errore",

    # --- Navigazione (sidebar) ---
    "nav_home": "Home",
    "nav_documents": "Documenti",
    "nav_services": "Servizi",
    "nav_contacts": "Contatti",
    "nav_support": "Assistenza",
    "nav_profile": "Profilo",
    "nav_logout": "Logout",
    "nav_toggle_title": "Toggle sidebar",

    # --- Home ---
    "home_greeting": "Buongiorno",
    "home_welcome": "Ti diamo il benvenuto nell'area di gestione della reportistica di Milano Serravalle - Milano Tangenziali S.p.A.",
    "home_services_title": "Servizi",
    "home_services_subtitle": "Elenco dei servizi disponibili.",
    "home_goto_btn": "Vai alla pagina",

    # --- Login ---
    "login_title": "Login DT Serravalle",
    "login_azure_btn": "Accedi con Azure",
    "login_divider": "oppure",
    "login_admin_only": "Accesso riservato agli amministratori",
    "login_username_label": "Username",
    "login_password_label": "Password",
    "login_submit_btn": "Login",

    # --- Reports ---
    "reports_page_title": "Report di sopralluogo",
    "reports_page_subtitle": "Archivio dei sopralluoghi effettuati.",
    "reports_back_link": "Torna all'elenco",
    "reports_detail_prefix": "Dettaglio report #",
    "reports_pdf_btn": "Scarica PDF",
    "reports_maps_btn": "Apri in Google Maps",
    "reports_pdf_loading": "Generazione PDF in corso...",

    # --- Segnalazioni ---
    "segnalazioni_page_title": "Segnalazioni",
    "segnalazioni_page_subtitle": "Archivio delle segnalazioni ricevute.",
    "segnalazioni_col_title": "Titolo",
    "segnalazioni_col_category": "Categoria",
    "segnalazioni_col_status": "Stato",
    "segnalazioni_col_date": "Data",

    # --- Profilo ---
    "profile_page_title": "Profilo Utente",
    "profile_field_username": "Nome Utente",
    "profile_field_email": "Email",
    "profile_field_fullname": "Nome Completo",
    "profile_field_joined": "Data Registrazione",
}
