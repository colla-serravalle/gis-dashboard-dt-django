"""
UI string definitions for the GIS Dashboard.

All user-visible text in templates, JavaScript, and Python views is defined here.
To update a label, change the value — do not change the key (templates and JS depend on it).
To find all usages of a key: grep -r "ui_strings\\." templates/ static/js/ apps/
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

    # --- Filtri (filter-manager.js) ---
    "filter_apply_btn": "Applica Filtri",
    "filter_clear_btn": "Pulisci",
    "filter_no_active": "Nessun filtro attivo",
    "filter_active_suffix": "filtri attivi",
    "filter_select_placeholder": "Seleziona opzioni",
    "filter_select_all": "Seleziona tutto",
    "filter_deselect_all": "Deseleziona tutto",
    "filter_dropdown_help": "Clicca per aprire il menu e seleziona le opzioni desiderate",
    "filter_date_from_title": "Data inizio periodo",
    "filter_date_to_title": "Data fine periodo",
    "filter_date_range_help": "Lascia vuoto per non limitare l'inizio o la fine",
    "filter_options_selected_suffix": "opzioni selezionate",
    "filter_period_label": "Periodo",
    "filter_search_placeholder": "Cerca...",
    "filter_loading": "Caricamento...",

    # --- Tabella / Paginazione (report-list.js, segnalazioni-list.js) ---
    "table_no_data": "Nessun dato trovato",
    "table_load_error": "Errore nel caricamento dei dati",
    "pagination_page": "Pagina",
    "pagination_of": "di",

    # --- Segnalazioni JS ---
    "segnalazioni_open_title": "Apri Segnalazione",

    # --- PDF (pdf-download.js, report-list.js) ---
    "pdf_error_user_msg": "Si è verificato un errore durante la generazione del PDF. Riprova.",

    # --- Errori view accounts ---
    "error_csrf_token": "Token di sicurezza non valido. Riprova.",
    "error_login_locked": "Troppi tentativi di login. Account temporaneamente bloccato.",
    "error_credentials": "Username e/o password errati!",
    "error_session_invalid": "Sessione non valida. Effettua nuovamente il login.",
    "error_session_expired": "Sessione scaduta per inattività. Effettua nuovamente il login.",
    "error_form_invalid": "Dati non validi. Riprova.",

    # --- Errori view reports ---
    "error_invalid_report_id": "ID report non valido.",
    "error_record_not_found": "Record non trovato",
    "error_record_not_found_period": "Record non trovato.",
    "error_pagination_params": "Parametri di paginazione non validi.",
    "error_filter_param": "Parametro di filtro non valido.",
    "error_internal": "Si è verificato un errore interno.",
    "error_invalid_params": "Parametri non validi.",
    "error_rowid_missing": "Parametro 'rowid' mancante.",
    "error_pdf_generation": "Errore nella generazione del PDF.",
    "error_attachment_fetch": "Errore nel recupero dell'allegato.",
    "error_content_type": "Tipo di contenuto non consentito.",
}
