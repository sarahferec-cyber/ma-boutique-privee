import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime
# ============================================================
# CONFIGURATION
# ============================================================
# URL de ton Google Sheet
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit?usp=sharing"
# URL /exec de ton Apps Script
STOCK_API_URL = "https://script.google.com/macros/s/AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/exec"
# Webhook Discord
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1549946850885238865/OItwwHS0spEUH0vzmBSJjAaCXwx2Yicaz2l30EolaALbmEufafnZI36M5OsuT3FlNqt_"
# ============================================================
# COMPTES AUTORISÉS
# ============================================================
COMPTES_AUTORISES = {
    "sarah": "shopping2026",
    "maman": "parfaite",
    "carole": "unique",
    "ben": "groot",
    "helene": "mae",
    "laurie": "mojito",
    "tiffany": "babysitter",
    "lesfilles": "economies",
    "invite": "bonplan11",
}
# ============================================================
# PARAMÈTRES
# ============================================================
NOM_BOUTIQUE = "Mes Bons Plans de Sarah 🌸"
PRIX_CARBURANT = 1.80
CONSOMMATION_L_100KM = 6.5
# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(
    page_title=NOM_BOUTIQUE,
    page_icon="🌸",
    layout="wide",
)
# ============================================================
# STYLE
# ============================================================
st.markdown(
    """
    <style>
    .main {
        padding-top: 1rem;
    }
    .produit-card {
        border: 1px solid #eeeeee;
        border-radius: 14px;
        padding: 15px;
        margin-bottom: 12px;
        background-color: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .stock-ok {
        color: #16803c;
        font-weight: bold;
    }
    .stock-ko {
        color: #d32f2f;
        font-weight: bold;
    }
    .ancien-prix {
        text-decoration: line-through;
        color: #888888;
        font-size: 0.95rem;
    }
    .prix-promo {
        font-size: 1.35rem;
        font-weight: bold;
    }
    .prix-normal {
        font-size: 1.25rem;
        font-weight: bold;
    }
    .badge-promo {
        display: inline-block;
        padding: 4px 9px;
        border-radius: 20px;
        background-color: #ffe1e8;
        color: #c2185b;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .panier-resume {
        border: 1px solid #eeeeee;
        border-radius: 12px;
        padding: 12px;
        background-color: #fafafa;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# ============================================================
# SESSION STATE
# ============================================================
if "connecte" not in st.session_state:
    st.session_state.connecte = False
if "utilisateur" not in st.session_state:
    st.session_state.utilisateur = ""
if "panier" not in st.session_state:
    st.session_state.panier = {}
if "commande_envoyee" not in st.session_state:
    st.session_state.commande_envoyee = False
# ============================================================
# OUTILS
# ============================================================
def normaliser_texte(texte):
    """
    Normalise un texte pour faciliter les comparaisons.
    """
    if texte is None:
        return ""
    texte = str(texte).strip().lower()
    remplacements = {
        "à": "a",
        "â": "a",
        "ä": "a",
        "á": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "î": "i",
        "ï": "i",
        "í": "i",
        "ô": "o",
        "ö": "o",
        "ó": "o",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ú": "u",
        "ç": "c",
    }
    for ancien, nouveau in remplacements.items():
        texte = texte.replace(ancien, nouveau)
    texte = re.sub(r"\s+", " ", texte)
    return texte
def trouver_colonne(objet, noms_possibles):
    """
    Recherche une colonne en ignorant :
    - majuscules/minuscules
    - accents
    - espaces superflus
    """
    if hasattr(objet, "columns"):
        colonnes = list(objet.columns)
    elif hasattr(objet, "index"):
        colonnes = list(objet.index)
    else:
        colonnes = list(objet)
    for colonne in colonnes:
        colonne_normalisee = normaliser_texte(
            colonne
        )
        for nom in noms_possibles:
            if colonne_normalisee == normaliser_texte(nom):
                return colonne
    return None
def convertir_nombre(valeur, valeur_defaut=0.0):
    """
    Convertit proprement une valeur venant du Google Sheet.
    """
    if valeur is None:
        return valeur_defaut
    try:
        if pd.isna(valeur):
            return valeur_defaut
    except (ValueError, TypeError):
        pass
    valeur = str(valeur).strip()
    if not valeur:
        return valeur_defaut
    # Gestion des nombres français :
    # 12,50 € -> 12.50
    valeur = valeur.replace(",", ".")
    valeur = re.sub(
        r"[^0-9.\-]",
        "",
        valeur
    )
    try:
        return float(valeur)
    except (ValueError, TypeError):
        return valeur_defaut
# ============================================================
# CHARGEMENT DU GOOGLE SHEET
# ============================================================
@st.cache_data(ttl=30)
def charger_produits():
    match = re.search(
        r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
        GOOGLE_SHEET_URL
    )
    if not match:
        raise ValueError(
            "Impossible de trouver l'identifiant du Google Sheet."
        )
    spreadsheet_id = match.group(1)
    url_csv = (
        "https://docs.google.com/spreadsheets/d/"
        + spreadsheet_id
        + "/export?format=csv"
    )
    df = pd.read_csv(url_csv)
    # Nettoyage des noms de colonnes
    df.columns = [
        str(colonne).strip()
        for colonne in df.columns
    ]
    return df
# ============================================================
# PHOTO
# ============================================================
def photo_produit(article):
    colonne = trouver_colonne(
        article.index,
        [
            "Photo produit",
            "Photo",
            "Image",
            "Photo produit URL",
        ]
    )
    if colonne is None:
        return ""
    valeur = article[colonne]
    if pd.isna(valeur):
        return ""
    return str(valeur).strip()
# ============================================================
# STOCK
# ============================================================
def obtenir_stock(article):
    colonne_stock = trouver_colonne(
        article.index,
        [
            "Quantité",
            "Quantite",
            "Stock",
            "Stocks",
        ]
    )
    if colonne_stock is None:
        return 0
    return max(
        0,
        int(
            convertir_nombre(
                article[colonne_stock],
                0
            )
        )
    )
# ============================================================
# PRIX INITIAL
# ============================================================
def obtenir_prix(article):
    colonne_prix = trouver_colonne(
        article.index,
        [
            "Prix initial",
            "Prix",
            "Prix normal",
            "Tarif",
        ]
    )
    if colonne_prix is None:
        return 0.0
    return convertir_nombre(
        article[colonne_prix],
        0.0
    )
# ============================================================
# PRIX PROMO
# ============================================================
def obtenir_prix_promo(article):
    colonne = trouver_colonne(
        article.index,
        [
            "Prix promo",
            "Promo",
            "Prix promotion",
            "Prix promotionnel",
        ]
    )
    if colonne is None:
        return None
    prix = convertir_nombre(
        article[colonne],
        0.0
    )
    if prix <= 0:
        return None
    return prix
# ============================================================
# PRIX FINAL
# ============================================================
def prix_final(article):
    promo = obtenir_prix_promo(article)
    if promo is not None:
        return promo
    return obtenir_prix(article)
# ============================================================
# NOM PRODUIT
# ============================================================
def nom_produit(article):
    colonne = trouver_colonne(
        article.index,
        [
            "Denomination",
            "Dénomination",
            "Produit",
            "Nom",
            "Article",
        ]
    )
    if colonne is None:
        return "Produit sans nom"
    valeur = article[colonne]
    if pd.isna(valeur):
        return "Produit sans nom"
    valeur = str(valeur).strip()
    if not valeur:
        return "Produit sans nom"
    return valeur
# ============================================================
# CATÉGORIE
# ============================================================
def categorie_produit(article):
    colonne = trouver_colonne(
        article.index,
        [
            "Categorie",
            "Catégorie",
            "Catégorie produit",
            "Famille",
        ]
    )
    if colonne is None:
        return "Autres"
    valeur = article[colonne]
    if pd.isna(valeur):
        return "Autres"
    valeur = str(valeur).strip()
    if not valeur:
        return "Autres"
    return valeur
# ============================================================
# LITRE / GRAMME
# ============================================================
def format_produit(article):
    colonne = trouver_colonne(
        article.index,
        [
            "Litre / Gramme",
            "Litre/Gramme",
            "Litre / Grammes",
        ]
    )
    if colonne is None:
        return ""
    valeur = article[colonne]
    if pd.isna(valeur):
        return ""
    valeur = str(valeur).strip()
    if not valeur:
        return ""
    return valeur
# ============================================================
# PRIX AU KG / LITRE
# ============================================================
def prix_kg_litre(article):
    colonne = trouver_colonne(
        article.index,
        [
            "Prix au Kg / Litre",
            "Prix au Kg/Litre",
            "Prix au Kg",
            "Prix au Litre",
        ]
    )
    if colonne is None:
        return ""
    valeur = article[colonne]
    if pd.isna(valeur):
        return ""
    valeur = str(valeur).strip()
    if not valeur:
        return ""
    return valeur
# ============================================================
# DESCRIPTION
# ============================================================
def description_produit(article):
    # Ton fichier ne possède pas de colonne Description.
    # On utilise donc le format Litre / Gramme
    # comme information complémentaire.
    infos = []
    format_article = format_produit(article)
    if format_article:
        infos.append(format_article)
    prix_unitaire = prix_kg_litre(article)
    if prix_unitaire:
        infos.append(
            f"{prix_unitaire} / kg ou litre"
        )
    return " • ".join(infos)
# ============================================================
# PANIER
# ============================================================
def ajouter_panier(article):
    nom = nom_produit(article)
    stock = obtenir_stock(article)
    prix = prix_final(article)
    if stock <= 0:
        st.warning(
            f"❌ {nom} est actuellement en rupture de stock."
        )
        return
    if nom in st.session_state.panier:
        quantite_actuelle = (
            st.session_state.panier[nom]["quantite"]
        )
        if quantite_actuelle >= stock:
            st.warning(
                f"⚠️ Il ne reste que "
                f"{stock} unité(s) de {nom}."
            )
            return
        st.session_state.panier[nom]["quantite"] += 1
    else:
        st.session_state.panier[nom] = {
            "quantite": 1,
            "prix": prix,
        }
def augmenter_panier(nom, df):
    if nom not in st.session_state.panier:
        return
    lignes = df[
        df.apply(
            lambda ligne:
            nom_produit(ligne) == nom,
            axis=1
        )
    ]
    if lignes.empty:
        return
    article = lignes.iloc[0]
    stock = obtenir_stock(article)
    quantite_actuelle = (
        st.session_state.panier[nom]["quantite"]
    )
    if quantite_actuelle >= stock:
        st.warning(
            f"⚠️ Stock maximum atteint pour {nom}."
        )
        return
    st.session_state.panier[nom]["quantite"] += 1
def retirer_panier(nom):
    if nom not in st.session_state.panier:
        return
    st.session_state.panier[nom]["quantite"] -= 1
    if (
        st.session_state.panier[nom]["quantite"]
        <= 0
    ):
        del st.session_state.panier[nom]
def vider_panier():
    st.session_state.panier = {}
def calculer_total():
    total = 0.0
    for article in st.session_state.panier.values():
        total += (
            float(article["prix"])
            * int(article["quantite"])
        )
    return total
def calculer_nombre_articles():
    nombre = 0
    for article in st.session_state.panier.values():
        nombre += int(
            article["quantite"]
        )
    return nombre
def calculer_economie(df):
    economie = 0.0
    for nom, article_panier in (
        st.session_state.panier.items()
    ):
        lignes = df[
            df.apply(
                lambda ligne:
                nom_produit(ligne) == nom,
                axis=1
            )
        ]
        if lignes.empty:
            continue
        article = lignes.iloc[0]
        prix_normal = obtenir_prix(
            article
        )
        prix_actuel = float(
            article_panier["prix"]
        )
        if prix_actuel < prix_normal:
            economie += (
                prix_normal - prix_actuel
            ) * int(
                article_panier["quantite"]
            )
    return economie
# ============================================================
# STOCK : ENVOI DE LA COMMANDE
# ============================================================
def retirer_stock_commande():
    produits = []
    for nom, article in (
        st.session_state.panier.items()
    ):
        produits.append(
            {
                "produit": nom,
                "quantite": int(
                    article["quantite"]
                ),
            }
        )
    payload = {
        "action": "retirer_commande",
        "utilisateur": (
            st.session_state.utilisateur
        ),
        "produits": produits,
    }
    try:
        response = requests.post(
            STOCK_API_URL,
            json=payload,
            timeout=30,
        )
    except requests.RequestException as erreur:
        return (
            False,
            f"Erreur de connexion au stock : {erreur}"
        )
    if response.status_code not in (200, 201):
        return (
            False,
            f"Erreur Apps Script HTTP "
            f"{response.status_code}"
        )
    try:
        resultat = response.json()
    except ValueError:
        return (
            False,
            "Apps Script n'a pas renvoyé "
            "une réponse JSON valide."
        )
    if not resultat.get(
        "success",
        False
    ):
        return (
            False,
            resultat.get(
                "message",
                "La modification du stock a échoué."
            )
        )
    return (
        True,
        resultat.get(
            "message",
            "Stock mis à jour."
        )
    )
# ============================================================
# DISCORD
# ============================================================
def envoyer_discord(
    total,
    mode,
    adresse,
    informations
):
    if (
        not DISCORD_WEBHOOK
        or DISCORD_WEBHOOK.startswith("TON_")
    ):
        return
    contenu = (
        "🌸 **Nouvelle commande**\n\n"
        f"👤 Client : "
        f"{st.session_state.utilisateur}\n"
        f"💰 Total : {total:.2f} €\n"
        f"📦 Mode : {mode}\n"
        f"📍 Adresse : {adresse}\n"
        f"📝 Informations : {informations}\n\n"
        "🛒 **Produits :**\n"
    )
    for nom, article in (
        st.session_state.panier.items()
    ):
        sous_total = (
            float(article["prix"])
            * int(article["quantite"])
        )
        contenu += (
            f"- {nom} × "
            f"{article['quantite']} "
            f"= {sous_total:.2f} €\n"
        )
    try:
        requests.post(
            DISCORD_WEBHOOK,
            json={
                "content": contenu
            },
            timeout=10
        )
    except requests.RequestException:
        pass
# ============================================================
# CONNEXION
# ============================================================
if not st.session_state.connecte:
    st.title(NOM_BOUTIQUE)
    st.subheader("🔐 Connexion")
    utilisateur = st.text_input(
        "Identifiant"
    )
    mot_de_passe = st.text_input(
        "Mot de passe",
        type="password"
    )
    if st.button(
        "Se connecter",
        use_container_width=True
    ):
        if (
            utilisateur
            in COMPTES_AUTORISES
            and mot_de_passe
            == COMPTES_AUTORISES[
                utilisateur
            ]
        ):
            st.session_state.connecte = True
            st.session_state.utilisateur = (
                utilisateur
            )
            st.rerun()
        else:
            st.error(
                "❌ Identifiant ou mot de passe incorrect."
            )
    st.stop()
# ============================================================
# CHARGEMENT DES PRODUITS
# ============================================================
try:
    df = charger_produits()
except Exception as erreur:
    st.error(
        "❌ Impossible de charger "
        "les produits depuis Google Sheets."
    )
    st.code(
        str(erreur)
    )
    st.stop()
# ============================================================
# EN-TÊTE
# ============================================================
col1, col2 = st.columns(
    [5, 1]
)
with col1:
    st.title(
        NOM_BOUTIQUE
    )
with col2:
    if st.button(
        "🚪 Déconnexion"
    ):
        st.session_state.connecte = False
        st.session_state.utilisateur = ""
        st.session_state.panier = {}
        st.rerun()
nombre_articles = (
    calculer_nombre_articles()
)
message_bienvenue = (
    f"Bienvenue "
    f"{st.session_state.utilisateur} 🌸"
)
if nombre_articles > 0:
    message_bienvenue += (
        f" — 🛒 {nombre_articles} article(s)"
    )
st.caption(
    message_bienvenue
)
# ============================================================
# RECHERCHE
# ============================================================
recherche = st.text_input(
    "🔎 Rechercher un produit",
    placeholder=(
        "Exemple : chocolat, lessive, café..."
    )
)
# ============================================================
# CATÉGORIES
# ============================================================
categories = sorted(
    list(
        {
            categorie_produit(ligne)
            for _, ligne in df.iterrows()
        }
    ),
    key=normaliser_texte
)
categorie = st.selectbox(
    "📂 Catégorie",
    ["Toutes"] + categories
)
# ============================================================
# FILTRAGE
# ============================================================
df_affiche = df.copy()
if recherche.strip():
    texte_recherche = normaliser_texte(
        recherche
    )
    def correspond_recherche(ligne):
        texte = " ".join(
            [
                normaliser_texte(
                    nom_produit(ligne)
                ),
                normaliser_texte(
                    categorie_produit(ligne)
                ),
                normaliser_texte(
                    format_produit(ligne)
                ),
                normaliser_texte(
                    prix_kg_litre(ligne)
                ),
            ]
        )
        return texte_recherche in texte
    df_affiche = df_affiche[
        df_affiche.apply(
            correspond_recherche,
            axis=1
        )
    ]
if categorie != "Toutes":
    df_affiche = df_affiche[
        df_affiche.apply(
            lambda ligne:
            categorie_produit(ligne)
            == categorie,
            axis=1
        )
    ]
# ============================================================
# PRODUITS
# ============================================================
st.subheader(
    "🛍️ Produits"
)
st.caption(
    f"{len(df_affiche)} produit(s) affiché(s)"
)
if df_affiche.empty:
    st.info(
        "Aucun produit ne correspond "
        "à votre recherche."
    )
else:
    for index, article in (
        df_affiche.iterrows()
    ):
        nom = nom_produit(article)
        categorie_article = (
            categorie_produit(article)
        )
        description = (
            description_produit(article)
        )
        stock = obtenir_stock(article)
        prix_normal = obtenir_prix(
            article
        )
        prix_promo = (
            obtenir_prix_promo(article)
        )
        prix = prix_final(article)
        photo = photo_produit(
            article
        )
        promo_active = (
            prix_promo is not None
            and prix_promo < prix_normal
        )
        economie_unitaire = 0.0
        if promo_active:
            economie_unitaire = (
                prix_normal - prix_promo
            )
        st.markdown(
            "<div class='produit-card'>",
            unsafe_allow_html=True
        )
        # ----------------------------------------------------
        # PHOTO
        # ----------------------------------------------------
        col_photo, col_infos, col_prix, col_action = (
            st.columns([1.3, 4, 2, 1.5])
        )
        with col_photo:
            if photo:
                try:
                    st.image(
                        photo,
                        use_container_width=True
                    )
                except Exception:
                    st.write("🌸")
            else:
                st.markdown(
                    "### 🌸"
                )
        # ----------------------------------------------------
        # INFORMATIONS
        # ----------------------------------------------------
        with col_infos:
            titre = f"### {nom}"
            if promo_active:
                titre += (
                    " "
                    "<span class='badge-promo'>"
                    "PROMO"
                    "</span>"
                )
            st.markdown(
                titre,
                unsafe_allow_html=True
            )
            if categorie_article:
                st.caption(
                    f"📂 {categorie_article}"
                )
            if description:
                st.write(
                    description
                )
            if stock > 0:
                st.markdown(
                    f"<span class='stock-ok'>"
                    f"🟢 {stock} disponible(s)"
                    f"</span>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<span class='stock-ko'>"
                    "🔴 Rupture de stock"
                    "</span>",
                    unsafe_allow_html=True
                )
        # ----------------------------------------------------
        # PRIX
        # ----------------------------------------------------
        with col_prix:
            if promo_active:
                st.markdown(
                    f"<span class='ancien-prix'>"
                    f"{prix_normal:.2f} €"
                    f"</span>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<span class='prix-promo'>"
                    f"{prix_promo:.2f} €"
                    f"</span>",
                    unsafe_allow_html=True
                )
                st.caption(
                    f"💚 Économie "
                    f"{economie_unitaire:.2f} €"
                )
            else:
                st.markdown(
                    f"<span class='prix-normal'>"
                    f"{prix:.2f} €"
                    f"</span>",
                    unsafe_allow_html=True
                )
        # ----------------------------------------------------
        # BOUTON
        # ----------------------------------------------------
        with col_action:
            if stock > 0:
                if st.button(
                    "➕ Ajouter",
                    key=f"ajouter_{index}",
                    use_container_width=True
                ):
                    ajouter_panier(
                        article
                    )
                    st.rerun()
            else:
                st.button(
                    "Rupture",
                    disabled=True,
                    key=f"rupture_{index}",
                    use_container_width=True
                )
        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )
# ============================================================
# PANIER
# ============================================================
st.divider()
st.subheader(
    "🛒 Mon panier"
)
if not st.session_state.panier:
    st.info(
        "Votre panier est vide."
    )
else:
    total = calculer_total()
    economie = calculer_economie(
        df
    )
    nombre_articles = (
        calculer_nombre_articles()
    )
    st.markdown(
        f"""
        <div class="panier-resume">
        🛒 <strong>{nombre_articles}</strong> article(s)
        &nbsp;&nbsp;•&nbsp;&nbsp;
        💰 <strong>{total:.2f} €</strong>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")
    for nom, article in list(
        st.session_state.panier.items()
    ):
        quantite = int(
            article["quantite"]
        )
        prix = float(
            article["prix"]
        )
        sous_total = (
            quantite * prix
        )
        col1, col2, col3, col4 = st.columns(
            [4, 2, 1.5, 1.5]
        )
        with col1:
            st.write(
                f"**{nom}**"
            )
        with col2:
            st.write(
                f"{quantite} × "
                f"{prix:.2f} €"
            )
        with col3:
            st.write(
                f"**{sous_total:.2f} €**"
            )
        with col4:
            col_moins, col_plus = st.columns(2)
            with col_moins:
                if st.button(
                    "➖",
                    key=f"retirer_{nom}"
                ):
                    retirer_panier(
                        nom
                    )
                    st.rerun()
            with col_plus:
                if st.button(
                    "➕",
                    key=f"ajouter_panier_{nom}"
                ):
                    augmenter_panier(
                        nom,
                        df
                    )
                    st.rerun()
    st.divider()
    if economie > 0:
        st.success(
            f"💚 Économie réalisée : "
            f"{economie:.2f} €"
        )
    st.markdown(
        f"## Total : {total:.2f} €"
    )
    if st.button(
        "🗑️ Vider le panier"
    ):
        vider_panier()
        st.rerun()
# ============================================================
# FINALISATION COMMANDE
# ============================================================
if st.session_state.panier:
    st.divider()
    st.subheader(
        "📦 Finaliser la commande"
    )
    mode = st.radio(
        "Mode de récupération",
        [
            "🚗 Livraison",
            "📍 Retrait",
        ],
        horizontal=True
    )
    adresse = ""
    if mode == "🚗 Livraison":
        adresse = st.text_area(
            "📍 Adresse de livraison",
            placeholder=(
                "Votre adresse..."
            )
        )
    informations = st.text_area(
        "📝 Informations complémentaires",
        placeholder=(
            "Exemple : heure souhaitée..."
        )
    )
    st.info(
        "Le stock sera retiré de "
        "Google Sheets uniquement après "
        "validation réussie."
    )
    if st.button(
        "✅ Valider ma commande",
        type="primary",
        use_container_width=True
    ):
        if (
            mode == "🚗 Livraison"
            and not adresse.strip()
        ):
            st.error(
                "❌ Merci d'indiquer "
                "votre adresse de livraison."
            )
        else:
            with st.spinner(
                "Vérification du stock..."
            ):
                succes, message = (
                    retirer_stock_commande()
                )
            if not succes:
                st.error(
                    f"❌ Commande non validée : "
                    f"{message}"
                )
                st.warning(
                    "Aucun stock n'a été retiré."
                )
            else:
                total = calculer_total()
                envoyer_discord(
                    total,
                    mode,
                    adresse,
                    informations
                )
                vider_panier()
                charger_produits.clear()
                st.success(
                    "🎉 Commande validée !"
                )
                st.success(
                    "📦 Le stock a été mis à jour "
                    "dans Google Sheets."
                )
                st.balloons()
                st.rerun()
# ============================================================
# ESTIMATION CARBURANT
# ============================================================
with st.expander(
    "⛽ Estimation carburant"
):
    st.write(
        f"Calcul basé sur "
        f"{CONSOMMATION_L_100KM:.1f} L/100 km "
        f"et {PRIX_CARBURANT:.2f} €/L."
    )
    distance = st.number_input(
        "Distance aller (km)",
        min_value=0.0,
        value=10.0,
        step=1.0
    )
    if distance > 0:
        distance_totale = (
            distance * 2
        )
        litres = (
            distance_totale
            * CONSOMMATION_L_100KM
            / 100
        )
        cout = (
            litres
            * PRIX_CARBURANT
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Distance A/R",
                f"{distance_totale:.1f} km"
            )
        with col2:
            st.metric(
                "Carburant",
                f"{litres:.2f} L"
            )
        with col3:
            st.metric(
                "Coût estimé",
                f"{cout:.2f} €"
            )
# ============================================================
# PIED DE PAGE
# ============================================================
st.divider()
st.caption(
    "🌸 Mes Bons Plans de Sarah — boutique privée"
)