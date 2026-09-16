import streamlit as st
import pandas as pd
import requests
import io
import time
import json
# ============================================================
# 1. CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Mes Bons Plans de Sarah 🌸",
    page_icon="🛍️",
    layout="wide"
)
# ============================================================
# 2. STYLE
# ============================================================
st.markdown("""
<style>
.stApp {
    background-color: #FFF5F5;
}
.product-card {
    padding: 20px;
    border-radius: 15px;
    border: 2px solid #FFD1D1;
    background-color: white;
    margin-bottom: 20px;
    text-align: center;
}
.promo-badge {
    background-color: #FF69B4;
    color: white;
    padding: 3px 8px;
    font-weight: bold;
    border-radius: 20px;
    font-size: 13px;
}
[data-testid="stSidebar"] {
    background-color: #FFEAEF;
    border-right: 2px solid #FFD1D1;
}
h1, h2, h3 {
    color: #C71585 !important;
    font-family: 'Poppins', sans-serif;
}
.stButton > button {
    background-color: #FF69B4 !important;
    color: white !important;
    border-radius: 20px !important;
    font-weight: bold !important;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)
# ============================================================
# 3. COMPTES AUTORISÉS
# ============================================================
COMPTES_AUTORISES = {
    "sarah": "shopping2026",
    "maman": "parfaite",
    "carole": "unique",
    "ben": "groot",
    "helene": "mae",
    "laurie": "mojito",
    "tiffany": "babysitter",
    "lesfilles": "promos",
    "invite": "bonplan11"
}
# ============================================================
# 4. URLS
# ============================================================
URL_SHEETS = (
    "https://docs.google.com/spreadsheets/d/"
    "1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/"
    "edit?usp=sharing"
)
# IMPORTANT :
# Ne mets pas le webhook Discord directement dans le code.
# Ajoute-le dans les Secrets Streamlit :
#
# DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
#
# Puis le code récupérera st.secrets["DISCORD_WEBHOOK"]
URL_MACRO_STOCK = (
    "https://script.google.com/macros/s/"
    "AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/"
    "exec"
)
# ============================================================
# 5. FONCTIONS UTILITAIRES
# ============================================================
def convertir_float(valeur, valeur_defaut=0.0):
    """
    Transforme proprement une valeur en nombre.
    Accepte :
    2.50
    2,50
    "2,50 €"
    """
    try:
        if pd.isna(valeur):
            return valeur_defaut
        texte = str(valeur).strip()
        if texte.lower() in ["", "nan", "none", "n/a"]:
            return valeur_defaut
        texte = texte.replace("€", "")
        texte = texte.replace(" ", "")
        texte = texte.replace(",", ".")
        return float(texte)
    except (ValueError, TypeError):
        return valeur_defaut
def envoyer_discord(message):
    """
    Envoie un message sur Discord si le webhook est configuré.
    """
    try:
        webhook = st.secrets.get("DISCORD_WEBHOOK", "")
        if not webhook:
            return False
        response = requests.post(
            webhook,
            json={"content": message},
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception:
        return False
def load_clean_data():
    """
    Charge le Google Sheets en CSV et nettoie les colonnes.
    """
    try:
        csv_url = (
            URL_SHEETS
            .replace("/edit?usp=sharing", "/export?format=csv")
            .replace("/edit", "/export?format=csv")
        )
        response = requests.get(
            csv_url,
            timeout=15
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        data = pd.read_csv(
            io.StringIO(response.text),
            encoding="utf-8",
            engine="python",
            on_bad_lines="skip"
        )
        # Nettoyage des noms de colonnes
        data.columns = [
            str(c).strip().lower()
            for c in data.columns
        ]
        # Normalisation des accents
        data.columns = (
            data.columns
            .str.replace("é", "e", regex=False)
            .str.replace("è", "e", regex=False)
            .str.replace("ê", "e", regex=False)
            .str.replace("ë", "e", regex=False)
            .str.replace("à", "a", regex=False)
            .str.replace("â", "a", regex=False)
            .str.replace("ä", "a", regex=False)
            .str.replace("ù", "u", regex=False)
            .str.replace("û", "u", regex=False)
            .str.replace("ü", "u", regex=False)
            .str.replace("ô", "o", regex=False)
            .str.replace("î", "i", regex=False)
            .str.replace("ï", "i", regex=False)
            .str.replace("ç", "c", regex=False)
        )
        # Nettoyage du contenu
        for col in data.select_dtypes(
            include=["object"]
        ).columns:
            data[col] = (
                data[col]
                .astype(str)
                .str.replace('"', '', regex=False)
                .str.strip()
            )
        return data
    except Exception as erreur:
        st.error(
            "❌ Impossible de charger les données Google Sheets."
        )
        st.caption(
            f"Détail technique : {erreur}"
        )
        return pd.DataFrame()
def trouver_colonne(dataframe, noms_possibles):
    """
    Retourne la première colonne trouvée dans la liste.
    """
    for nom in noms_possibles:
        if nom in dataframe.columns:
            return nom
    return None
# ============================================================
# 6. SESSION STATE
# ============================================================
if "connecte" not in st.session_state:
    st.session_state.connecte = False
if "utilisateur" not in st.session_state:
    st.session_state.utilisateur = ""
if "achat_reussi" not in st.session_state:
    st.session_state.achat_reussi = False
if "panier" not in st.session_state:
    st.session_state.panier = {}
# ============================================================
# 7. CONNEXION
# ============================================================
if not st.session_state.connecte:
    st.title(
        "🎀 Espace Privé : La Boutique des Bons Plans 🌸"
    )
    with st.form("formulaire_connexion"):
        identifiant = st.text_input(
            "👤 Votre Identifiant :"
        ).strip().lower()
        mot_de_passe = st.text_input(
            "🔑 Votre Mot de passe :",
            type="password"
        )
        connexion = st.form_submit_button(
            "✨ Entrer dans la boutique"
        )
        if connexion:
            if (
                identifiant in COMPTES_AUTORISES
                and COMPTES_AUTORISES[identifiant]
                == mot_de_passe
            ):
                st.session_state.connecte = True
                st.session_state.utilisateur = identifiant
                st.rerun()
            else:
                st.error(
                    "Identifiant ou mot de passe incorrect. ❌"
                )
    st.stop()
# ============================================================
# 8. EN-TÊTE
# ============================================================
st.title(
    "🌸 La Boutique des Bons Plans 🛍️"
)
st.write(
    f"Coucou **{st.session_state.utilisateur.capitalize()}** !"
)
# ============================================================
# 9. DÉCONNEXION
# ============================================================
if st.sidebar.button("🚪 Se déconnecter"):
    st.session_state.connecte = False
    st.session_state.utilisateur = ""
    st.session_state.panier = {}
    st.rerun()
# ============================================================
# 10. CHARGEMENT GOOGLE SHEETS
# ============================================================
df = load_clean_data()
if df.empty:
    st.warning(
        "⚠️ Aucune donnée produit disponible."
    )
    st.stop()
# ============================================================
# 11. DÉTECTION DES COLONNES
# ============================================================
col_photo = trouver_colonne(
    df,
    [
        "photo produit",
        "photo",
        "image"
    ]
)
col_nom = trouver_colonne(
    df,
    [
        "denomination",
        "denom",
        "nom",
        "produit"
    ]
)
col_cat = trouver_colonne(
    df,
    [
        "categorie",
        "cat",
        "category"
    ]
)
col_fmt = trouver_colonne(
    df,
    [
        "litre / gramme",
        "litre/gramme",
        "format",
        "contenance"
    ]
)
col_stock = trouver_colonne(
    df,
    [
        "quantite",
        "stock",
        "quantité"
    ]
)
col_pinit = trouver_colonne(
    df,
    [
        "prix initial",
        "initial",
        "prix avant"
    ]
)
col_ppromo = trouver_colonne(
    df,
    [
        "prix promo",
        "promo",
        "prix"
    ]
)
col_prix_unitaire = trouver_colonne(
    df,
    [
        "prix au kg / litre",
        "prix au kg/litre",
        "prix au kg",
        "prix au litre"
    ]
)
# ============================================================
# 12. VÉRIFICATION DES COLONNES ESSENTIELLES
# ============================================================
colonnes_manquantes = []
if col_nom is None:
    colonnes_manquantes.append("denomination")
if col_cat is None:
    colonnes_manquantes.append("categorie")
if col_stock is None:
    colonnes_manquantes.append("quantite")
if col_pinit is None:
    colonnes_manquantes.append("prix initial")
if col_ppromo is None:
    colonnes_manquantes.append("prix promo")
if colonnes_manquantes:
    st.error(
        "❌ Certaines colonnes indispensables sont absentes "
        "du Google Sheets :"
    )
    for colonne in colonnes_manquantes:
        st.write(f"• `{colonne}`")
    st.info(
        "Vérifie les noms des colonnes dans ton Google Sheets."
    )
    st.stop()
# ============================================================
# 13. NAVIGATION
# ============================================================
st.sidebar.markdown(
    "## 🎀 Navigation"
)
# ============================================================
# 14. CATÉGORIES
# ============================================================
categories_uniques = set()
for cellule in (
    df[col_cat]
    .dropna()
    .astype(str)
):
    for morceau in cellule.split(","):
        nom_nettoye = morceau.strip().capitalize()
        if (
            nom_nettoye
            and nom_nettoye.lower() != "nan"
        ):
            categories_uniques.add(
                nom_nettoye
            )
categories_triees = sorted(
    list(categories_uniques)
)
# ============================================================
# 15. ÉMOJIS
# ============================================================
DICTIONNAIRE_EMOJIS = {
    "nouveaute": "🔥",
    "nouveauté": "🔥",
    "lessive": "🧺",
    "hygiene": "✨",
    "hygiène": "✨",
    "entretien": "🧼",
    "menage": "🧹",
    "ménage": "🧹",
    "alimentaire": "🍭",
    "animalerie": "🐱",
    "beaute": "💄",
    "beauté": "💄",
    "boisson": "🥤",
    "cuisine": "🍳"
}
# ============================================================
# 16. MENU CATÉGORIES
# ============================================================
categories_menu = []
for cat in categories_triees:
    cat_lower = cat.lower()
    emoji = DICTIONNAIRE_EMOJIS.get(
        cat_lower,
        "🌸"
    )
    categories_menu.append(
        f"{emoji} {cat}"
    )
# Retirer les doublons de nouveauté
categories_menu = [
    c
    for c in categories_menu
    if "nouveaut" not in c.lower()
]
presence_nouveaute = any(
    cat.lower() in ["nouveauté", "nouveaute"]
    for cat in categories_triees
)
if presence_nouveaute:
    categories_menu = [
        "🔥 Nouveauté",
        "✨ Tous les rayons"
    ] + categories_menu
else:
    categories_menu = [
        "✨ Tous les rayons"
    ] + categories_menu
# ============================================================
# 17. CHOIX CATÉGORIE
# ============================================================
choix_cat_brut = st.sidebar.selectbox(
    "Faites votre shopping par rayon :",
    categories_menu,
    index=0
)
# Nettoyage du choix
choix_cat = choix_cat_brut
for emoji in DICTIONNAIRE_EMOJIS.values():
    choix_cat = choix_cat.replace(
        emoji,
        ""
    )
choix_cat = (
    choix_cat
    .replace("✨", "")
    .strip()
    .lower()
)
# ============================================================
# 18. FILTRAGE
# ============================================================
if "tous les rayons" in choix_cat_brut.lower():
    df_filtre = df.copy()
elif "nouveauté" in choix_cat_brut.lower() or "nouveaute" in choix_cat_brut.lower():
    df_filtre = df[
        df[col_cat]
        .astype(str)
        .str.lower()
        .str.contains(
            "nouveaut",
            na=False,
            regex=False
        )
    ]
else:
    df_filtre = df[
        df[col_cat]
        .astype(str)
        .str.lower()
        .str.contains(
            choix_cat,
            na=False,
            regex=False
        )
    ]
# ============================================================
# 19. TITRE DE LA SÉLECTION
# ============================================================
st.subheader(
    f"💫 Sélection : {choix_cat_brut} "
    f"({len(df_filtre)} pépites)"
)
# ============================================================
# 20. AFFICHAGE DES PRODUITS
# ============================================================
cols = st.columns(3)
for index, row in df_filtre.reset_index().iterrows():
    # Index original Google Sheets
    index_original = row["index"]
    # --------------------------------------------------------
    # Nom
    # --------------------------------------------------------
    nom_produit = str(
        row[col_nom]
    ).strip()
    if nom_produit.lower() in [
        "nan",
        "",
        "denomination"
    ]:
        continue
    # --------------------------------------------------------
    # Prix
    # --------------------------------------------------------
    p_init = convertir_float(
        row[col_pinit]
    )
    p_promo = convertir_float(
        row[col_ppromo]
    )
    economie_unitaire = max(
        0,
        p_init - p_promo
    )
    # --------------------------------------------------------
    # Stock
    # --------------------------------------------------------
    max_stock = int(
        convertir_float(
            row[col_stock]
        )
    )
    # --------------------------------------------------------
    # Format
    # --------------------------------------------------------
    if col_fmt:
        fmt = str(
            row[col_fmt]
        ).strip()
    else:
        fmt = "N/A"
    # --------------------------------------------------------
    # Catégorie
    # --------------------------------------------------------
    cat_nom = str(
        row[col_cat]
    ).lower()
    # --------------------------------------------------------
    # Icône
    # --------------------------------------------------------
    icon = "🛍️"
    for mot_cle, emoji in DICTIONNAIRE_EMOJIS.items():
        if mot_cle in cat_nom:
            icon = emoji
            break
    # --------------------------------------------------------
    # CARTE PRODUIT
    # --------------------------------------------------------
    with cols[index % 3]:
        st.markdown(
            '<div class="product-card">',
            unsafe_allow_html=True
        )
        # ----------------------------------------------------
        # Photo
        # ----------------------------------------------------
        lien_photo = ""
        if col_photo:
            lien_photo = str(
                row[col_photo]
            ).strip()
        if (
            lien_photo
            and lien_photo.startswith("http")
            and lien_photo.lower() != "nan"
        ):
            try:
                st.image(
                    lien_photo,
                    use_container_width=True
                )
            except Exception:
                st.markdown(
                    f"""
                    <h1 style="
                        text-align:center;
                        font-size:50px;
                    ">
                        {icon}
                    </h1>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                f"""
                <h1 style="
                    text-align:center;
                    font-size:50px;
                ">
                    {icon}
                </h1>
                """,
                unsafe_allow_html=True
            )
        # ----------------------------------------------------
        # Nom
        # ----------------------------------------------------
        st.markdown(
            f"### {nom_produit}"
        )
        # ----------------------------------------------------
        # Prix au kg / litre
        # ----------------------------------------------------
        if col_prix_unitaire:
            prix_unitaire_brut = str(
                row[col_prix_unitaire]
            ).strip()
            if "€/kg" in prix_unitaire_brut.lower():
                prix_unitaire_propre = (
                    prix_unitaire_brut
                    .replace("€/kg", "€ au Kg")
                    .replace("€/KG", "€ au Kg")
                )
            elif "€/l" in prix_unitaire_brut.lower():
                prix_unitaire_propre = (
                    prix_unitaire_brut
                    .replace("€/L", "€ au Litre")
                    .replace("€/l", "€ au Litre")
                )
            else:
                prix_unitaire_propre = (
                    prix_unitaire_brut
                )
            if (
                prix_unitaire_propre.lower()
                not in ["nan", "n/a", ""]
            ):
                st.markdown(
                    f"""
                    <p style="
                        color:#C71585;
                        font-size:13px;
                        font-weight:500;
                        margin-top:-10px;
                    ">
                        ⚖️ {prix_unitaire_propre}
                    </p>
                    """,
                    unsafe_allow_html=True
                )
        # ----------------------------------------------------
        # Format
        # ----------------------------------------------------
        st.markdown(
            f"""
            <p style="
                color:#555555;
                font-size:14px;
                margin-bottom:5px;
            ">
                📦 Format : {fmt}
            </p>
            """,
            unsafe_allow_html=True
        )
        # ----------------------------------------------------
        # Prix
        # ----------------------------------------------------
        st.markdown(
            f"""
            <p style="
                font-size:14px;
                margin-bottom:2px;
            ">
                Avant :
                <span style="
                    text-decoration:line-through;
                    color:#888888;
                ">
                    {p_init:.2f} €
                </span>
            </p>
            <p style="
                font-size:20px;
                font-weight:bold;
                color:#FF69B4;
                margin-top:0;
            ">
                🔥 {p_promo:.2f} €
            </p>
            """,
            unsafe_allow_html=True
        )
        # ----------------------------------------------------
        # Stock
        # ----------------------------------------------------
        if max_stock <= 0:
            st.markdown(
                """
                <p style="
                    color:red;
                    font-size:14px;
                    font-weight:bold;
                ">
                    ❌ Rupture de stock !
                </p>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <p style="
                    color:green;
                    font-size:13px;
                ">
                    ✅ En stock ({max_stock} dispos)
                </p>
                """,
                unsafe_allow_html=True
            )
            # ------------------------------------------------
            # Bouton achat
            # ------------------------------------------------
            if st.button(
                "🛒 Prendre ce produit",
                key=f"btn_{index_original}"
            ):
                # Quantité déjà dans le panier
                if nom_produit in st.session_state.panier:
                    quantite_actuelle = st.session_state.panier[
                        nom_produit
                    ].get("quantite", 0)
                    if quantite_actuelle < max_stock:
                        st.session_state.panier[
                            nom_produit
                        ]["quantite"] += 1
                        st.success(
                            "Ajouté au panier ! ✨"
                        )
                    else:
                        st.error(
                            "Désolé, pas assez de stock disponible !"
                        )
                else:
                    # Ligne réelle dans le DataFrame
                    ligne_sheets = (
                        int(index_original) + 2
                    )
                    st.session_state.panier[
                        nom_produit
                    ] = {
                        "quantite": 1,
                        "prix": p_promo,
                        "prix_initial": p_init,
                        "economie_unitaire":
                            economie_unitaire,
                        "ligne_sheets":
                            ligne_sheets
                    }
                    st.success(
                        "Ajouté au panier ! ✨"
                    )
                    time.sleep(0.3)
                    st.rerun()
        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )
# ============================================================
# 21. MESSAGE APRÈS COMMANDE
# ============================================================
if st.session_state.achat_reussi:
    st.sidebar.success(
        "Commande réalisée ! 🎉 "
        "Votre stock est à jour."
    )
    st.session_state.achat_reussi = False
# ============================================================
# 22. PANIER
# ============================================================
if st.session_state.panier:
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "## 🛒 Votre Panier Rose"
    )
    total_facture = 0.0
    total_economies = 0.0
    texte_message = (
        f"🌸 **Nouvelle commande de "
        f"{st.session_state.utilisateur.capitalize()}** :\n"
    )
    # --------------------------------------------------------
    # ARTICLES
    # --------------------------------------------------------
    for article, infos in st.session_state.panier.items():
        qte = int(
            infos.get(
                "quantite",
                1
            )
        )
        prix = convertir_float(
            infos.get(
                "prix",
                0
            )
        )
        economie_unitaire = convertir_float(
            infos.get(
                "economie_unitaire",
                0
            )
        )
        # Économie totale pour cet article
        economie_article = (
            economie_unitaire * qte
        )
        # Total article
        total_article = (
            prix * qte
        )
        total_facture += (
            total_article
        )
        total_economies += (
            economie_article
        )
        st.sidebar.write(
            f"• {article} "
            f"(x{qte}) — "
            f"{total_article:.2f} €"
        )
        texte_message += (
            f"- {article} "
            f"x{qte} "
            f"({prix:.2f}€/u)\n"
        )
    # ========================================================
    # LIVRAISON
    # ========================================================
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "### 📦 Mode de retrait"
    )
    option_livraison = st.sidebar.checkbox(
        "Demander la livraison à domicile 🏠"
    )
    frais_livraison = 0.0
    km_distance = 0
    if option_livraison:
        km_distance = st.sidebar.slider(
            "Distance de chez Sarah (en Km) :",
            min_value=1,
            max_value=50,
            value=5,
            help=(
                "Le tarif est de "
                "0,10 € par kilomètre."
            )
        )
        frais_livraison = (
            km_distance * 0.10
        )
        st.sidebar.caption(
            f"🚗 Frais de livraison : "
            f"+{frais_livraison:.2f} € "
            f"({km_distance} km)"
        )
    else:
        st.sidebar.caption(
            "🛒 Retrait gratuit en main propre chez Sarah"
        )
    # ========================================================
    # TOTAL
    # ========================================================
    total_final_avec_livraison = (
        total_facture
        + frais_livraison
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
        ### Total :
        **{total_final_avec_livraison:.2f} €**
        """
    )
    if total_economies > 0:
        st.sidebar.markdown(
            f"""
            💖 Vous économisez
            **{total_economies:.2f} €**
            sur cet achat !
            """
        )
    # ========================================================
    # VALIDATION
    # ========================================================
    if st.sidebar.button(
        "✨ Valider mon achat"
    ):
        # Copie du panier avant suppression
        panier_a_traiter = {
            article: infos.copy()
            for article, infos
            in st.session_state.panier.items()
        }
        # ----------------------------------------------------
        # MESSAGE DISCORD
        # ----------------------------------------------------
        msg_discord = (
            f"{texte_message}\n"
        )
        if option_livraison:
            msg_discord += (
                f"🚚 **Option Livraison activée :** "
                f"{km_distance} Km "
                f"(+{frais_livraison:.2f}€)\n"
            )
        else:
            msg_discord += (
                "🛒 **Retrait :** "
                "En main propre chez Sarah\n"
            )
        msg_discord += (
            f"💰 **Total Articles : "
            f"{total_facture:.2f}€**\n"
        )
        msg_discord += (
            f"⭐ **TOTAL À PAYER : "
            f"{total_final_avec_livraison:.2f}€**\n"
        )
        msg_discord += (
            f"🌸 **Économie réalisée : "
            f"{total_economies:.2f}€**"
        )
        # ----------------------------------------------------
        # ENVOI DISCORD
        # ----------------------------------------------------
        discord_ok = envoyer_discord(
            msg_discord
        )
        # ----------------------------------------------------
        # MISE À JOUR STOCK GOOGLE SHEETS
        # ----------------------------------------------------
        stock_ok = True
        for article, infos in panier_a_traiter.items():
            ligne_sheets = infos.get(
                "ligne_sheets"
            )
            quantite = infos.get(
                "quantite",
                1
            )
            # Si l'information manque,
            # on ne fait pas planter toute la commande.
            if ligne_sheets is None:
                stock_ok = False
                continue
            payload_stock = {
                "ligne": int(
                    ligne_sheets
                ),
                "quantite": int(
                    quantite
                )
            }
            try:
                response_stock = requests.post(
                    URL_MACRO_STOCK,
                    data=json.dumps(
                        payload_stock
                    ),
                    headers={
                        "Content-Type":
                            "application/json"
                    },
                    timeout=5
                )
                if response_stock.status_code not in [
                    200,
                    201,
                    204
                ]:
                    stock_ok = False
            except Exception:
                stock_ok = False
        # ----------------------------------------------------
        # FIN DE COMMANDE
        # ----------------------------------------------------
        st.session_state.panier = {}
        st.session_state.achat_reussi = True
        st.balloons()
        # Messages d'information
        if not discord_ok:
            st.sidebar.warning(
                "⚠️ La commande est enregistrée, "
                "mais la notification Discord "
                "n'a pas pu être envoyée."
            )
        if not stock_ok:
            st.sidebar.warning(
                "⚠️ La commande est enregistrée, "
                "mais une mise à jour du stock "
                "n'a pas pu être effectuée."
            )
        time.sleep(1)
        st.rerun()
# ============================================================
# 23. CONDITIONS GÉNÉRALES DE VENTE
# ============================================================
st.sidebar.markdown("---")
with st.sidebar.popover(
    "📄 Conditions Générales de Vente (CGV)"
):
    st.markdown(
        """
        ### ⚖️ Conditions Générales de Vente
        En utilisant la boutique
        **"Mes Bons Plans de Sarah 🌸"**,
        vous acceptez les conditions suivantes :
        #### 1. 🛍️ Commandes & Réservations
        * Ce site est un espace privé de
          réservation de produits.
        * Toute validation de panier entraîne
          l'envoi d'une notification via notre
          système de messagerie Discord.
        #### 2. 📦 Stocks & Disponibilités
        * Les stocks affichés sont synchronisés
          avec l'inventaire.
        * En cas de rupture de stock simultanée,
          la priorité est accordée à la première
          commande validée chronologiquement.
        #### 3. 💳 Modalités de Paiement & Retrait
        * Aucun paiement direct n'est effectué
          sur cette application.
        * Le règlement et la remise des articles
          s'effectuent selon les modalités
          convenues directement avec Sarah.
        #### 4. 🔒 Protection des Données (RGPD)
        * Les identifiants de connexion servent
          uniquement à personnaliser votre
          expérience et sécuriser l'accès
          à la boutique.
        * Aucune donnée personnelle n'est vendue
          ou partagée avec des tiers.
        """
    )
    st.caption(
        "Mise à jour : Septembre 2026"
    )
# ============================================================
# 24. AVIS CLIENTS
# ============================================================
st.sidebar.markdown("---")
st.sidebar.markdown(
    "### 🌸 Votre Avis compte !"
)
with st.sidebar.form(
    "formulaire_avis_complet",
    clear_on_submit=True
):
    note_etoiles = st.slider(
        "Notez votre expérience sur la boutique :",
        min_value=1,
        max_value=5,
        value=5,
        help=(
            "1 = À améliorer, "
            "5 = Parfait !"
        )
    )
    avis_texte = st.text_area(
        "Laissez-moi un commentaire ou une idée de produit : 📝",
        placeholder=(
            "Dites-moi ce que vous aimez "
            "ou ce que je devrais améliorer "
            "(points négatifs, produits manquants...)"
        )
    )
    bouton_avis = st.form_submit_button(
        "🚀 Envoyer mon avis"
    )
    if bouton_avis:
        etoiles_visuelles = (
            "⭐" * note_etoiles
        )
        if note_etoiles <= 2:
            statut_avis = (
                "⚠️ **AVIS REÇU "
                "(À AMÉLIORER / POINT NÉGATIF)**"
            )
        else:
            statut_avis = (
                "✨ **Nouvel avis client reçu**"
            )
        commentaire = (
            avis_texte.strip()
            if avis_texte.strip()
            else "Aucun commentaire écrit."
        )
        msg_discord_avis = (
            f"{statut_avis}\n"
            f"👤 **Par :** "
            f"{st.session_state.utilisateur.capitalize()}\n"
            f"📊 **Note :** "
            f"{etoiles_visuelles} "
            f"({note_etoiles}/5)\n"
            f"💬 **Commentaire :** "
            f"{commentaire}"
        )
        if envoyer_discord(
            msg_discord_avis
        ):
            if note_etoiles <= 2:
                st.sidebar.success(
                    "Merci pour ce retour honnête ! "
                    "Sarah va faire le nécessaire "
                    "pour s'améliorer. 💖"
                )
            else:
                st.sidebar.success(
                    "Merci beaucoup pour votre "
                    "superbe note ! 🌸"
                )
        else:
            st.sidebar.error(
                "Petit problème lors de l'envoi. "
                "Vérifiez la configuration Discord."
            )