"""
Field mappings and value transformations for inspection reports.

Ported from PHP field_mappings.php
"""

from datetime import datetime
from typing import Any, Optional

# =============================================================================
# Field Labels - Map field codes to human-readable labels
# =============================================================================

FIELD_LABELS = {
    # CAMPI LAYER MOSC_Verbale_di_sopralluogo
    'uniquerowid': 'ID Univoco',
    'objectid': 'ID oggetto',
    'globalid': 'ID globale',
    'id_report': 'ID report',
    'nome_operatore': 'Operatore',
    'tratta': 'Tratta',
    'tipologia_appalto': 'Tipologia Appalto',
    'data_rilevamento': 'Data Rilevamento',
    'ora_rilevamento': 'Ora rilevamento',
    'presenza_dl': 'Presenza DL',
    'nome_dl': 'Nominativo DL',
    'presenza_cse': 'Presenza CSE',
    'nome_cse': 'Nome CSE',
    'area_intervento': 'Area di intervento',
    'corsie_svincolo': 'Corsie (svincolo)',
    'carreggiata': 'Carreggiata',
    'km_iniz': 'KM iniziale',
    'km_iniz_text': 'KM iniziale (A,B)',
    'm_iniz': 'm iniziale',
    'km_fin': 'KM finale',
    'km_fin_text': 'KM finale (A,B)',
    'm_fin': 'm finale',
    'pk_iniz': 'PK iniziale',
    'pk_fin': 'PK finale',
    'nome_svincolo': 'Nome svincolo',
    'nome_casello': 'Nome casello',
    'nome_area_servizio': 'Nome area di servizio',
    'num_imprese': 'Numero di imprese',
    'note': 'Note',
    'posizione': 'Posizione',
    'firma_op': 'Firma',
    'created_user': 'Profilo utente (creator)',
    'created_date': 'Data di creazione survey',
    'last_edited_user': 'Profilo utente ultima modifica (creator)',
    'last_edited_date': 'Data ultima modifica',
    # CAMPI LAYER MOSC_Verbale_di_sopralluogo - Repeat PK Pavimentazioni
    'corsia': 'Corsia',
    'tipo_intervento_pav': 'Tipologia di intervento',
    'km_iniz_pav': 'KM iniziale',
    'km_iniz_text_pav': 'KM iniziale (A,B)',
    'm_iniz_pav': 'm iniziale',
    'km_fin_pav': 'KM finale',
    'km_fin_text_pav': 'KM finale (A,B)',
    'm_fin_pav': 'm finale',
    'pk_iniz_pav': 'PK iniziale',
    'pk_fin_pav': 'PK finale',
    'parentrowid': 'ID padre',
    # CAMPI LAYER MOSC_Verbale_di_sopralluogo - Repeat Imprese
    'nome_impresa': 'Nome impresa',
    'rapp_contrattuale': 'Rapporto contrattuale',
    'n_squadra_pronto_int': 'Squadre pronto intervento',
    'cantierizzazione': 'Cantierizzaz.',
    'attivita': 'Attività realizzata',
    'n_uomini': 'N° uomini impiegati',
    'n_mezzi': 'N° mezzi impiegati',
}

# =============================================================================
# Field Values - Map coded values to human-readable labels
# =============================================================================

FIELD_VALUES = {
    'nome_operatore': {
        'g_vitale': 'Giovanni Vitale',
        'g_ferrari': 'Giuseppe Ferrari',
        'm_micelli': 'Massimiliano Micelli',
        'a_bordonali': 'Angelo Bordonali',
        'g_fanara': 'Giuseppe Fanara',
        'i_serafino': 'Ivan Serafino',
        'f_palatucci': 'Ferdinando Palatucci',
        'd_maffeo': 'Domenico Maffeo',
        'p_perego': 'Paolo Perego',
        'r_pelizzola': 'Roberto Pellizzola',
        'f_miceli': 'Ferdinando Miceli',
        'a_palma': 'Andrea Palma',
        'd_ortolano': 'Domenico Ortolano',
        'g_carrella': 'Giovanni Carrella',
        'c_genovese': 'Claudio Genovese',
    },
    'nome_dl': {
        'g_amenta': 'Gerardo Amenta',
        'r_luca': 'Rocco Lucà',
        'r_giardina': 'Roberto Giardina',
        'l_guastalegname': 'Luca Guastalegname',
        'f_campiotti': 'Filippo Campiotti',
        'd_maggio': 'Demetrio Maggio',
        'g_romano': 'Giacomo Romano',
        'm_caserini': 'Michele Caserini',
        'd_sorbara': 'Domenico Sorbara',
        'r_pedulla': 'Rocco Pedullà',
    },
    'nome_cse': {
        'c_bonnet': 'Carlo Bonnet',
        'm_gigliotta': 'Michele Gigliotta',
        'l_guastalegname': 'Luca Guastalegname',
        'l_mollica': 'Leo Mollica',
        'i_viafora': 'Ida Viafora',
        'm_conte': 'Monica Conte',
        'r_luca': 'Rocco Lucà',
    },
    'tratta': {
        'A7_neg': 'A7 (km A,B)',
        'A7_pos': 'A7',
        'A50': 'A50 (Tangenziale Ovest)',
        'A51': 'A51 (Tangenziale Est)',
        'A52': 'A52 (Tangenziale Nord)',
        'A53': 'A53 (Raccordo Bereguardo-Pavia)',
        'A54': 'A54 (Tangenziale Ovest di Pavia)',
        'SP11': 'SP11',
        'RF': 'Raccordo Fiera',
    },
    'tipologia_appalto': {
        'pavimentazioni': 'Pavimentazioni',
        'man_fabbricati_piste_esazione': 'Manutenzione fabbricati e piste di esazione',
        'verniciature_manufatti': 'Verniciature manufatti',
        'segnaletica': 'Segnaletica',
        'giunti': 'Giunti',
        'man_strutture_metalliche': 'Manutenzione strutture metalliche',
        'sicurvia': 'Ripristino sicurvia',
        'recinzioni': 'Ripristino recinzioni',
        'pronto_intervento': 'Pronto intervento',
    },
    'nome_impresa': {
        'cogefa_giuggia': 'CO.GE.FA. S.p.A. - GIUGGIA Costruzioni S.r.l.',
        'ronzoni_favini': 'RONZONI S.r.l. - FAVINI Costruzioni S.r.l.',
        'gsm': 'GSM Continental Lavori e Servizi S.r.l.',
        'valori_mavi': 'Consorzio stabile VALORI S.c.a.r.l. - MAVI S.r.l.',
        'odos_celegato': 'Consorzio Stabile ODOS S.c.a.r.l. - CELEGATO S.r.l. - SAFITAL S.p.A.',
        'sea_infravie': 'SEA Segnaletica Stradale S.p.A. - INFRAVIE S.r.l.',
        'sias': 'SIAS S.p.A.',
        'avr_sioss': 'A.V.R. S.p.A. - GUBELA S.p.A. - S.I.O.S.S. S.r.l.',
        'avr_viagest': 'A.V.R. S.p.A. - Consorzio Stabile VIAGEST S.c.a.r.l.',
        'baldi_sodano': 'BALDI SODANO',
        'avr': 'A.V.R. S.p.A.',
        'nuove_iniziative': 'NUOVE INIZIATIVE S.p.A.',
        'mpm': 'M.P.M. S.r.l.',
        'cogepi': 'CO.GE.PI. S.r.l.',
        'mpm_semp': 'M.P.M. S.r.l. - SEMP S.r.l.',
        'ronzoni': 'RONZONI S.r.l.',
        'ets_istra_movibit': 'ETS ECOTECNOLOGIE STRADALI S.r.l. - ISTRA S.r.l. - MOVIBIT S.r.l.',
        'segnalcoop': 'SEGNALCOOP Soc. Coop.',
        'fes': 'FES S.p.A.',
    },
    'cantierizzazione': {
        'yes': 'Sì',
        'no': 'No',
    },
    'presenza_dl': {
        'yes': 'Sì',
        'no': 'No',
    },
    'presenza_cse': {
        'yes': 'Sì',
        'no': 'No',
    },
    'rapp_contrattuale': {
        'appalto': 'Appalto',
        'subappalto': 'Subappalto',
    },
    'tipo_intervento_pav': {
        'base': 'Base',
        'binder': 'Binder',
        'usura_chiuso': 'Usura (tappeto chiuso)',
        'usura_drenante': 'Usura (tappeto drenante)',
        'sma': 'SMA',
    },
    'carreggiata': {
        'north': 'Nord',
        'south': 'Sud',
        'both': 'Entrambe',
    },
    'corsie_svincolo': {
        'nord_e': 'Entrata carr. nord',
        'sud_e': 'Entrata carr. sud',
        'nord_u': 'Uscita carr. nord',
        'sud_u': 'Uscita carr. sud',
        'svincolo_completo': 'Intero svincolo',
    },
    'area_intervento': {
        'carreggiata': 'Carreggiata/complanare',
        'svincolo': 'Svincolo',
        'area_servizio': 'Area di servizio',
        'casello': 'Casello',
        'fuori_tratta': 'Fuori tratta',
    },
    'nome_svincolo': {
        'a7_svincolo_1': 'A7 Milano Piazza Maggi (km A+000)',
        'a7_svincolo_2': 'A7 Svincolo Milano Parcheggio Famagosta MM2 (km A+800)',
        'a7_svincolo_3': 'A7 Svincolo Milano via Boffalora (km B+500)',
        'a7_svincolo_4': 'A7 Svincolo Assago Milanofiori (km 1+900)',
        'a7_svincolo_5': 'A7 Svincolo A50 (km 3+350)',
        'a7_svincolo_6': 'A7 Uscita di servizio SP184 (km 4+880)',
        'a7_svincolo_7': 'A7 Svincolo Binasco (km 10+450)',
        'a7_svincolo_8': 'A7 Svincolo A53 Bereguardo - Pavia Nord (km 21+390)',
        'a7_svincolo_9': 'A7 Svincolo Gropello Cairoli - Pavia Sud (km 30+680)',
        'a7_svincolo_10': 'A7 Svincolo Casei Gerola',
        'a7_svincolo_11': 'A7 Svincolo Castelnuovo Scrivia',
        'a7_svincolo_12': 'A7 Svincolo A21 Piacenza-Torino',
        'a7_svincolo_13': 'A7 Svincolo Tortona',
        'a7_svincolo_14': 'A7 Svincolo A26 Genova - Gravellona Toce',
        'a7_svincolo_15': 'A7 Svincolo Serravalle Scrivia',
        'a50_svincolo_1': 'A50 Svincolo Milano Fiera - Rho - Pero - Milano Sempione (km 2+500)',
        'a50_svincolo_2': 'A50 Svincolo A4 Torino - Venezia (km 4+100)',
        'a50_svincolo_3': 'A50 Svincolo SS11 Novara - Milano Gallaratese MM1 (km 5+750)',
        'a50_svincolo_4': 'A50 Svincolo Settimo Milanese - Milano San Siro (km 6+700)',
        'a50_svincolo_5': 'A50 Svincolo Cusago - Milano Baggio (km 10+550)',
        'a50_svincolo_6': 'A50 Svincolo Vigevano - Milano Lorenteggio (km 13+975)',
        'a50_svincolo_7': 'A50 Svincolo Corsico - Gaggiano (km 14+810)',
        'a50_svincolo_8': 'A50 Svincolo SS35 dei Giovi Pavia - Milano Ticinese (km 21+335)',
        'a50_svincolo_9': 'A50 Svincolo Rozzano Quinto de Stampi - Milano via dei Missaglia (km 23+710)',
        'a50_svincolo_10': 'A50 Svincolo SS412 Val Tidone - Milano Vigentina (km 26+200)',
        'a50_svincolo_11': 'A50 Svincolo A1 (km 30+600)',
        'a51_svincolo_1': 'A51 Svincolo Milano Rogoredo - Milano via Emilia (km 0+300)',
        'a51_svincolo_2': 'A51 Svincolo Paullo - Milano q.re Santa Giulia (km 1+600)',
        'a51_svincolo_3': 'A51 Svincolo Milano via Mecenate (km 2+580)',
        'a51_svincolo_4': 'A51 Svincolo Milano via Fantoli (km 3+265)',
        'a51_svincolo_5': 'A51 Svincolo Milano viale Forlanini - Linate (km 4+520)',
        'a51_svincolo_6': 'A51 Svincolo Milano viale Rubattino (km 5+800)',
        'a51_svincolo_7': 'A51 Svincolo Milano Lambrate - Segrate (km 7+300)',
        'a51_svincolo_8': 'A51 Svincolo Milano via Padova (km 10+180)',
        'a51_svincolo_9': 'A51 Svincolo Milano via Palmanova (km 10+585)',
        'a51_svincolo_10': 'A51 Svincolo Sesto S. Giovanni - via Di Vittorio (km 11+750)',
        'a51_svincolo_11': 'A51 Svincolo A52 (km 11+800)',
        'a51_svincolo_12': 'A51 Svincolo Cologno Monzese Sud (km 12+490)',
        'a51_svincolo_13': 'A51 Entrata Cologno Monzese via per Imbersago (km 14+120)',
        'a51_svincolo_14': 'A51 Svincolo Cologno Monzese Nord (km 14+580)',
        'a51_svincolo_15': 'A51 Svincolo Cernusco sul Naviglio - Brugherio (km 15+650)',
        'a51_svincolo_16': 'A51 Svincolo Carugate (km 17+800)',
        'a51_svincolo_17': 'A51 Svincolo A4 Torino - Venezia (km 19+500)',
        'a51_svincolo_18': 'A51 Svincolo Agrate Brianza (km 20+900)',
        'a51_svincolo_19': 'A51 Svincolo Monza Est (km 21+175)',
        'a51_svincolo_20': 'A51 Svincolo Concorezzo (km 21+800)',
        'a51_svincolo_21': 'A51 Svincolo Burago (km 23+700)',
        'a51_svincolo_22': 'A51 Svincolo q.re Torri Bianche - Vimercate Sud - SP 2 (km 24+600)',
        'a51_svincolo_23': 'A51 Svincolo Vimercate Centro - Sud (km 25+140)',
        'a51_svincolo_24': 'A51 Svincolo Vimercate Centro - Nord (km 26+830)',
        'a51_svincolo_25': 'A51 Svincolo Vimercate Nord (km 28+353)',
        'a51_svincolo_26': 'A51 Svincolo Carnate - Usmate Velate Sud (km 29+181)',
        'a52_svincolo_1': 'A52 Svincolo Sesto S. Giovanni Sud - Cologno Monzese (km 1+090)',
        'a52_svincolo_2': 'A52 Svincolo Sesto S. Giovanni (km 3+171)',
        'a52_svincolo_3': 'A52 Svincolo A4 - Monza S. Alessandro (km 4+167)',
        'a52_svincolo_4': 'A52 Svincolo Monza Centro - Sesto S. Giovanni (km 5+400)',
        'a52_svincolo_5': 'A52 Svincolo Cinisello Balsamo - Robecco (km 6+000)',
        'a52_svincolo_6': 'A52 Svincolo Lecco - Monza Villa Reale - Cinisello Balsamo Sud - Milano Viale Zara (km 6+400)',
        'a52_svincolo_7': 'A52 Svincolo Cinisello Balsamo Nord - Muggiò (km 8+000)',
        'a52_svincolo_8': 'A52 Svincolo Nova Milanese (km 9+761)',
        'a52_svincolo_9': 'A52 Svincolo Erba - Vecchia Valassina (km 11+600)',
        'a52_svincolo_10': 'A52 Svincolo SP EX SS35 - Como - Meda (km 12+650)',
        'a52_svincolo_11': 'A52 Entrata Paderno Dugnano via SS 35 dei Giovi (km 15+100)',
        'a52_svincolo_12': 'A52 Svincolo Cormano - Bollate (km 17+000)',
        'a53_svincolo_1': 'A53 Svincolo SS526 Bereguardo - SS526 Magenta',
        'a53_svincolo_2': 'A53 Svincolo Cascina Barchette - Carpana - SS526 Abbiategrasso (km 2+016)',
        'a53_svincolo_3': 'A53 Svincolo Casottole - SS526 Abbiategrasso (km 2+717)',
        'a53_svincolo_4': "A53 Svincolo Torre d'Isola - SS526 Abbiategrasso (km 4+027)",
        'a53_svincolo_5': 'A53 Svincolo Cascina Campagna - Villaggio dei Pioppi - SS526 Abbiategrasso (km 4+839)',
        'a53_svincolo_6': 'A53 Svincolo Massaua - SS526 Abbiategrasso (km 6+576)',
        'a53_svincolo_7': 'A53 Svincolo Pavia via Riviera - Ospedali (km 8+473)',
        'a54_svincolo_1': 'A54 Svincolo Pavia Sud (km 0+535)',
        'a54_svincolo_2': 'A54 Svincolo San Martino Siccomario - Pavia Borgo Ticino (km 1+817)',
        'a54_svincolo_3': 'A54 Svincolo Pavia Centro - SS526 Abbiategrasso - Ospedali - Stazione (km 5+779)',
        'a54_svincolo_4': 'A54 Svincolo Istituti Universitari - Ospedali (km 6+152)',
        'a54_svincolo_5': 'A54 Svincolo Tangenziale Nord di Pavia - Pavia Centro via Brambilla (km 7+064)',
        'sp11_svincolo_1': 'SP11 Svincolo Milano Figino - via Silla (km 1+282)',
        'sp11_svincolo_2': 'SP11 Svincolo Pero Sud (km 2+585)',
    },
    'nome_casello': {
        'a7_casello_milanoovest': 'A7 Barriera di Milano Ovest',
        'a7_binasco': 'A7 Casello di Binasco',
        'a7_bereguardo': 'A7 Casello di Bereguardo',
        'a7_gropello': 'A7 Casello di Gropello Cairoli',
        'a7_casei': 'A7 Casello di Casei',
        'a7_castelnuovo': 'A7 Casello di Castelnuovo Scrivia',
        'a7_tortona': 'A7 Casello di Tortona',
        'a50_terrazzano': 'A50 Barriera di Terrazzano',
        'a51_agrate': 'A51 Barriera di Agrate',
        'a52_sesto': 'A52 Barriera di Sesto San Giovanni',
    },
    'nome_area_servizio': {
        'a7_ads_cantalupa_e': 'A7 AdS Cantalupa Est',
        'a7_ads_cantalupa_o': 'A7 AdS Cantalupa Ovest',
        'a7_ads_dorno_e': 'A7 AdS Dorno Est',
        'a7_ads_dorno_o': 'A7 AdS Dorno Ovest',
        'a7_ads_castelnuovo_e': 'A7 AdS Castelnuovo Scrivia Est',
        'a7_ads_castelnuovo_o': 'A7 AdS Castelnuovo Scrivia Ovest',
        'a7_ads_bettole_e': 'A7 AdS bettole di Novi Ligure Est',
        'a7_ads_bettole_o': 'A7 AdS bettole di Novi Ligure Ovest',
        'a50_ads_rho_o': 'A50 AdS Rho Ovest',
        'a50_ads_muggiano_e': 'A50 AdS Muggiano Est',
        'a50_ads_muggiano_o': 'A50 AdS Muggiano Ovest',
        'a50_ads_assago_o': 'A50 AdS Assago Ovest',
        'a50_ads_rozzano_e': 'A50 AdS Rozzano Est',
        'a50_ads_sangiuliano_e': 'A50 AdS San Giuliano Est',
        'a50_ads_sangiuliano_o': 'A50 AdS San Giuliano Ovest',
        'a51_ads_cascinagobba_e': 'A51 AdS Cascina Gobba Est',
        'a51_ads_cascinagobba_o': 'A51 AdS Cascina Gobba Ovest',
        'a51_ads_cologno_e': 'A51 AdS Cologno Monzese Est',
        'a51_ads_carugate_e': 'A51 AdS Carugate Est',
        'a51_ads_carugate_o': 'A51 AdS Carugate Ovest',
        'a51_ads_vimercate_o': 'A51 AdS Vimercate Ovest',
        'a52_ads_cinisello_n': 'A52 AdS Cinisello Nord',
    },
    'n_squadra_pronto_int': {
        'm1': 'M1',
        'm2': 'M2',
        'm3': 'M3',
        'm4': 'M4',
        'm5': 'M5',
        'm6': 'M6',
        'm7': 'M7',
        'm8': 'M8',
        'm9': 'M9',
        'm10': 'M10',
        'm11': 'M11',
        'm12': 'M12',
        'm14': 'M14',
    },
}

# =============================================================================
# Field Order - Define display order for each section
# =============================================================================

FIELD_ORDER = {
    'main': [
        'id_report',
        'nome_operatore',
        'data_rilevamento',
        'ora_rilevamento',
        'tratta',
        'area_intervento',
        'carreggiata',
        'km_iniz',
        'km_iniz_text',
        'm_iniz',
        'km_fin',
        'km_fin_text',
        'm_fin',
        'pk_iniz',
        'pk_fin',
        'nome_svincolo',
        'corsie_svincolo',
        'nome_casello',
        'nome_area_servizio',
        'tipologia_appalto',
        'presenza_dl',
        'nome_dl',
        'presenza_cse',
        'nome_cse',
        'num_imprese',
        'note',
        'posizione',
        'created_date',
        'last_edited_date',
    ],
    'pk_pav': [
        'corsia',
        'tipo_intervento_pav',
        'km_iniz_pav',
        'km_iniz_text_pav',
        'm_iniz_pav',
        'km_fin_pav',
        'km_fin_text_pav',
        'm_fin_pav',
        'pk_iniz_pav',
        'pk_fin_pav',
    ],
    'impresa': [
        'nome_impresa',
        'rapp_contrattuale',
        'n_squadra_pronto_int',
        'cantierizzazione',
        'attivita',
        'n_uomini',
        'n_mezzi',
    ],
}

# =============================================================================
# Date Fields Configuration
# =============================================================================

DATE_FIELDS = {
    'data_rilevamento': '%d/%m/%Y',  # Date only
    'ora_rilevamento': '%H:%M',  # Time only
    'created_date': '%d/%m/%Y %H:%M',  # Date and time
    'last_edited_date': '%d/%m/%Y %H:%M',  # Date and time
}


# =============================================================================
# Helper Functions
# =============================================================================

def is_empty(value: Any) -> bool:
    """Check if a value is considered empty."""
    if value is None:
        return True
    if isinstance(value, str):
        value = value.strip()
        if value == '' or value.lower() == 'null':
            return True
    return False


def is_date_field(field_name: str) -> bool:
    """Check if a field is a date field."""
    return field_name in DATE_FIELDS


def get_date_format(field_name: str) -> str:
    """Get the date format for a field."""
    return DATE_FIELDS.get(field_name, '%d/%m/%Y')


def format_date(timestamp: Any, format_str: str = '%d/%m/%Y') -> str:
    """
    Convert timestamp to formatted date string.

    Args:
        timestamp: Unix timestamp (seconds or milliseconds)
        format_str: strftime format string

    Returns:
        Formatted date string or original value if conversion fails
    """
    if is_empty(timestamp):
        return str(timestamp) if timestamp is not None else ''

    try:
        # Convert to float
        ts = float(timestamp)

        # If timestamp is in milliseconds (like ArcGIS), convert to seconds
        if ts > 9999999999:
            ts = ts / 1000

        # Convert to datetime and format
        dt = datetime.fromtimestamp(ts)
        return dt.strftime(format_str)

    except (ValueError, TypeError, OSError):
        return str(timestamp)


def get_field_label(field_name: str) -> str:
    """
    Get the human-readable label for a field.

    Args:
        field_name: The field code/name

    Returns:
        Human-readable label or formatted field name
    """
    if field_name in FIELD_LABELS:
        return FIELD_LABELS[field_name]

    # Convert snake_case to Title Case as fallback
    return field_name.replace('_', ' ').title()


def get_field_value(field_name: str, value: Any) -> str:
    """
    Get the display value for a field.

    Args:
        field_name: The field code/name
        value: The raw value

    Returns:
        Human-readable value or original value
    """
    # Handle date fields first
    if is_date_field(field_name):
        if value is not None and str(value).strip() != '':
            try:
                # Check if it's numeric (timestamp)
                float(value)
                fmt = get_date_format(field_name)
                return format_date(value, fmt)
            except (ValueError, TypeError):
                pass

    # Check for field value mapping
    if field_name in FIELD_VALUES:
        if value in FIELD_VALUES[field_name]:
            return FIELD_VALUES[field_name][value]

    # Return original value
    return str(value) if value is not None else ''


def process_attributes(attributes: dict, section: str = 'main') -> list:
    """
    Process raw attributes into display-ready format.

    Args:
        attributes: Dictionary of raw attribute values
        section: Section name for field ordering

    Returns:
        List of dicts with 'field', 'label', 'value', 'original_value' keys
    """
    processed = []
    field_order = FIELD_ORDER.get(section, [])

    if field_order:
        # Process fields in defined order
        for field_name in field_order:
            if field_name in attributes:
                original_value = attributes[field_name]

                if not is_empty(original_value):
                    processed.append({
                        'field': field_name,
                        'label': get_field_label(field_name),
                        'value': get_field_value(field_name, original_value),
                        'original_value': original_value,
                    })
    else:
        # Process all fields (excluding empty ones)
        for field_name, original_value in attributes.items():
            if not is_empty(original_value):
                processed.append({
                    'field': field_name,
                    'label': get_field_label(field_name),
                    'value': get_field_value(field_name, original_value),
                    'original_value': original_value,
                })

    return processed


def process_features(features: list, section: str = 'main') -> list:
    """
    Process a list of features.

    Args:
        features: List of feature dicts with 'attributes' and optionally 'geometry'
        section: Section name for field ordering

    Returns:
        List of processed feature dicts
    """
    processed = []

    for feature in features:
        processed.append({
            'attributes': process_attributes(feature.get('attributes', {}), section),
            'geometry': feature.get('geometry'),
        })

    return processed


def get_field_options(field_name: str) -> dict:
    """Get all possible values for a field (useful for dropdowns)."""
    return FIELD_VALUES.get(field_name, {})


def get_field_order(section: str) -> list:
    """Get the field order for a section."""
    return FIELD_ORDER.get(section, [])
