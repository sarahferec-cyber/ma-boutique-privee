import streamlit as st
import pandas as pd
import requests
import re
import unicodedata
# ============================================================
# CONFIGURATION
# ============================================================
NOM_BOUTIQUE = "Mes Bons Plans de Sarah 🌸"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit?usp=sharing"
STOCK_API_URL = "https://script.google.com/macros/s/AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/exec"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1549946850885238865/OItwwHS0spEUH0vzmBSJjAaCXwx2Yicaz2l30EolaALbmEufafnZI36M5OsuT3FlNqt_"
PRIX_CARBURANT = 1.80
CONSOMMATION_L_100KM = 6.5
# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(
    page_title=NOM_BOUTIQUE,
    page_icon="🌸",
    layout="wide"
)
# ============================================================
# SESSION
# ============================================================
if "panier" not in st.session_state:
    st.session_state.panier = []
if "commande_envoyee" not in st.session_state:
    st.session_state.commande_envoyee = False
# ============================================================
# OUTILS
# ============================================================
def normaliser_texte(texte):
    """Normalise un texte pour faciliter la recherche de colonnes."""
    texte = str(texte)
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(
        caractere
        for caractere in texte
        if unicodedata.category(caractere) != "Mn"
    )
    texte = texte.lower()
    texte = re.sub(r"\s+", " ", texte).strip()
    return texte
def trouver_colonne(article, noms_possibles):
    """
    Cherche une colonne dans une ligne Pandas.
    Accepte les différences d'accents, majuscules et espaces.
    """
    if hasattr(article, "index"):
        colonnes = list(article.index)
    elif isinstance(article, dict):
        colonnes = list(article.keys())
    else:
        return None
    colonnes_normalisees = {
        normaliser_texte(colonne): colonne
        for colonne in colonnes
    }
    for nom in noms_possibles:
        cle = normaliser_texte(nom)
        if cle in colonnes_normalisees:
            return colonnes_normalisees[cle]
    return None
def convertir_nombre(valeur, valeur_defaut=0.0):
    """Convertit proprement une valeur texte en nombre."""
    if valeur is None:
        return valeur_defaut
    if pd.isna(valeur):
        return valeur_defaut
    if isinstance(valeur, (int, float)):
        return float(valeur)
    texte = str(valeur).strip()
    if not texte:
        return valeur_defaut
    texte = texte.replace("€", "")
    texte = texte.replace(" ", "")
    if "," in texte and "." in texte:
        if texte.rfind(",") > texte.rfind("."):
            texte = texte.replace(".", "")
            texte = texte.replace(",", ".")
        else:
            texte = texte.replace(",", "")
    else:
        texte = texte.replace(",", ".")
    try:
        return float(texte)
    except Exception:
        return valeur_defaut
# ============================================================
# COLONNES DU GOOGLE SHEET
# ============================================================
def nom_produit(article):
    colonne = trouver_colonne(
        article,
        [
            "Denomination",
            "Dénomination",
            "Produit",
            "Nom",
            "Article"
        ]
    )
    if colonne is None:
        return "Produit sans nom"
    valeur = article.get(colonne, "")
    if pd.isna(valeur):
        return "Produit sans nom"
    return str(valeur).strip()
def categorie_produit(article):
    colonne = trouver_colonne(
        article,
        [
            "Categorie",
            "Catégorie",
            "Catégorie produit",
            "Famille"
        ]
    )
    if colonne is None:
        return "Autre"
    valeur = article.get(colonne, "")
    if pd.isna(valeur) or str(valeur).strip() == "":
        return "Autre"
    return str(valeur).strip()
def photo_produit(article):
    colonne = trouver_colonne(
        article,
        [
            "Photo produit",
            "Photo",
            "Image",
            "Photo produit URL"
        ]
    )
    if colonne is None:
        return ""
    valeur = article.get(colonne, "")
    if pd.isna(valeur):
        return ""
    return str(valeur).strip()
def obtenir_stock(article):
    colonne = trouver_colonne(
        article,
        [
            "Quantité",
            "Quantite",
            "Stock",
            "Stocks"
        ]
    )
    if colonne is None:
        return 0
    return convertir_nombre(
        article.get(colonne, 0),
        0
    )
def obtenir_prix(article):
    colonne = trouver_colonne(
        article,
        [
            "Prix initial",
            "Prix",
            "Prix normal",
            "Tarif"
        ]
    )
    if colonne is None:
        return 0.0
    return convertir_nombre(
        article.get(colonne, 0),
        0.0
    )
def obtenir_prix_promo(article):
    colonne = trouver_colonne(
        article,
        [
            "Prix promo",
            "Promo",
            "Prix promotion",
            "Prix promotionnel"
        ]
    )
    if colonne is None:
        return None
    valeur = article.get(colonne, "")
    if pd.isna(valeur) or str(valeur).strip() == "":
        return None
    prix = convertir_nombre(valeur, 0.0)
    if prix <= 0:
        return None
    return prix
def format_produit(article):
    colonne = trouver_colonne(
        article,
        [
            "Litre / Gramme",
            "Litre/Gramme",
            "Format",
            "Poids",
            "Volume"
        ]
    )
    if colonne is None:
        return ""
    valeur = article.get(colonne, "")
    if pd.isna(valeur):
        return ""
    return str(valeur).strip()
def prix_kg_litre(article):
    colonne = trouver_colonne(
        article,
        [
            "Prix au Kg / Litre",
            "Prix au Kg/Litre",
            "Prix Kg",
            "Prix Litre",
            "Prix au kilo",
            "Prix au litre"
        ]
    )
    if colonne is None:
        return ""
    valeur = article.get(colonne, "")
    if pd.isna(valeur):
        return ""
    return str(valeur).strip()
# ============================================================
# CHARGEMENT GOOGLE SHEET
# ============================================================
@st.cache_data(ttl=60)
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
        f"https://docs.google.com/spreadsheets/d/"
        f"{spreadsheet_id}/export?format=csv"
    )
    try:
        dataframe = pd.read_csv(url_csv)
    except Exception as erreur:
        raise RuntimeError(
            f"Impossible de charger le Google Sheet : {erreur}"
        )
    if dataframe.empty:
        return dataframe
    dataframe.columns = [
        str(colonne).strip()
        for colonne in dataframe.columns
    ]
    dataframe = dataframe.dropna(
        how="all"
    ).reset_index(drop=True)
    return dataframe
# ============================================================
# PANIER
# ============================================================
def ajouter_au_panier(article):
    nom = nom_produit(article)
    prix_normal = obtenir_prix(article)
    prix_promo = obtenir_prix_promo(article)
    prix = prix_promo if prix_promo is not None else prix_normal
    for produit in st.session_state.panier:
        if produit["produit"] == nom:
            stock = obtenir_stock(article)
            if produit["quantite"] < stock:
                produit["quantite"] += 1
            return
    st.session_state.panier.append(
        {
            "produit": nom,
            "quantite": 1,
            "prix": prix
        }
    )
def retirer_du_panier(nom):
    for produit in st.session_state.panier:
        if produit["produit"] == nom:
            produit["quantite"] -= 1
            if produit["quantite"] <= 0:
                st.session_state.panier.remove(produit)
            return
def vider_panier():
    st.session_state.panier = []
def calculer_total():
    total = 0.0
    for produit in st.session_state.panier:
        total += (
            produit["prix"]
            * produit["quantite"]
        )
    return total
# ============================================================
# ENVOI COMMANDE APPS SCRIPT
# ============================================================
def envoyer_commande(nom_utilisateur):
    if not st.session_state.panier:
        return False, "Le panier est vide."
    produits = []
    for produit in st.session_state.panier:
        produits.append(
            {
                "produit": produit["produit"],
                "quantite": produit["quantite"]
            }
        )
    donnees = {
        "action": "retirer_commande",
        "utilisateur": nom_utilisateur,
        "produits": produits
    }
    try:
        reponse = requests.post(
            STOCK_API_URL,
            json=donnees,
            timeout=20
        )
        if reponse.status_code not in [200, 201]:
            return (
                False,
                f"Erreur serveur : {reponse.status_code}"
            )
        try:
            resultat = reponse.json()
        except Exception:
            return (
                False,
                "Réponse du serveur invalide."
            )
        if not resultat.get("success", False):
            return (
                False,
                resultat.get(
                    "message",
                    "La commande n'a pas pu être validée."
                )
            )
        return True, "Commande validée."
    except requests.exceptions.Timeout:
        return False, "Le serveur met trop de temps à répondre."
    except requests.exceptions.RequestException as erreur:
        return False, f"Erreur de connexion : {erreur}"
    except Exception as erreur:
        return False, f"Erreur : {erreur}"
# ============================================================
# DISCORD
# ============================================================
def envoyer_discord(nom_utilisateur):
    if not st.session_state.panier:
        return
    lignes = []
    for produit in st.session_state.panier:
        total_produit = (
            produit["prix"]
            * produit["quantite"]
        )
        lignes.append(
            f"• {produit['produit']} "
            f"x{produit['quantite']} "
            f"= {total_produit:.2f} €"
        )
    total = calculer_total()
    message = (
        f"🌸 **Nouvelle commande**\n\n"
        f"👤 Client : {nom_utilisateur}\n\n"
        + "\n".join(lignes)
        + f"\n\n💰 **Total : {total:.2f} €**"
    )
    try:
        requests.post(
            DISCORD_WEBHOOK,
            json={"content": message},
            timeout=10
        )
    except Exception:
        pass
# ============================================================
# CHARGEMENT DES PRODUITS (ACCES DIRECT)
# ============================================================
try:
    produits = charger_produits()
except Exception as erreur:
    st.error(
        "❌ Impossible de charger les produits."
    )
    st.code(str(erreur))
    st.stop()
if produits.empty:
    st.warning(
        "⚠️ Aucun produit trouvé dans le Google Sheet."
    )
    st.stop()
# ============================================================
# HEADER
# ============================================================
col1, col2, col3 = st.columns([4, 2, 2])
with col1:
    st.title(NOM_BOUTIQUE)
    st.markdown(
        "_Votre catalogue de déstockage en accès libre._"
    )
with col2:
    st.metric(
        "Produits disponibles",
        len(produits)
    )
with col3:
    st.metric(
        "Articles dans le panier",
        len(st.session_state.panier)
    )
st.divider()
# ============================================================
# RECHERCHE ET FILTRES
# ============================================================
categories = sorted(
    set(
        categorie_produit(article)
        for _, article in produits.iterrows()
    )
)
col1, col2 = st.columns([2, 1])
with col1:
    recherche = st.text_input(
        "🔎 Rechercher un produit",
        placeholder="Ex : chocolat, huile, café..."
    )
with col2:
    categorie_selectionnee = st.selectbox(
        "🌸 Catégorie",
        ["Toutes"] + categories
    )
# ============================================================
# FILTRAGE
# ============================================================
produits_affiches = produits.copy()
if recherche:
    recherche_normalisee = normaliser_texte(
        recherche
    )
    indices = []
    for index, article in produits_affiches.iterrows():
        texte_recherche = " ".join(
            [
                nom_produit(article),
                categorie_produit(article),
                format_produit(article),
                prix_kg_litre(article)
            ]
        )
        texte_recherche = normaliser_texte(
            texte_recherche
        )
        if recherche_normalisee in texte_recherche:
            indices.append(index)
    produits_affiches = produits_affiches.loc[
        indices
    ]
if categorie_selectionnee != "Toutes":
    indices = []
    for index, article in produits_affiches.iterrows():
        if (
            categorie_produit(article)
            == categorie_selectionnee
        ):
            indices.append(index)
    produits_affiches = produits_affiches.loc[
        indices
    ]
st.write(
    f"**{len(produits_affiches)} produit(s)** trouvé(s)"
)
# ============================================================
# AFFICHAGE DES PRODUITS
# ============================================================
for index, article in produits_affiches.iterrows():
    nom = nom_produit(article)
    categorie = categorie_produit(article)
    stock = obtenir_stock(article)
    prix_normal = obtenir_prix(article)
    prix_promo = obtenir_prix_promo(article)
    format_article = format_produit(article)
    prix_unitaire = prix_kg_litre(article)
    photo = photo_produit(article)
    if prix_promo is not None:
        prix_final = prix_promo
        en_promo = True
    else:
        prix_final = prix_normal
        en_promo = False
    with st.container(border=True):
        col_photo, col_info, col_action = st.columns(
            [1.2, 3.8, 1.5]
        )
        # ----------------------------------------------------
        # PHOTO
        # ----------------------------------------------------
        with col_photo:
            if photo:
                try:
                    st.image(
                        photo,
                        use_container_width=True
                    )
                except Exception:
                    st.markdown(
                        "🌸"
                    )
            else:
                st.markdown(
                    """
                    <div style="
                        font-size:60px;
                        text-align:center;
                        padding:20px;
                    ">
                    🌸
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        # ----------------------------------------------------
        # INFORMATIONS
        # ----------------------------------------------------
        with col_info:
            st.subheader(nom)
            st.caption(
                f"🌸 {categorie}"
            )
            if format_article:
                st.write(
                    f"📦 Format : {format_article}"
                )
            if prix_unitaire:
                st.write(
                    f"⚖️ Prix : {prix_unitaire}"
                )
            if en_promo:
                st.markdown(
                    f"### 🔥 {prix_final:.2f} €"
                )
                st.caption(
                    f"Prix initial : "
                    f"{prix_normal:.2f} €"
                )
            else:
                st.markdown(
                    f"### {prix_final:.2f} €"
                )
            if stock > 0:
                st.success(
                    f"En stock : {int(stock)}"
                )
            else:
                st.error(
                    "Rupture de stock"
                )
        # ----------------------------------------------------
        # BOUTON
        # ----------------------------------------------------
        with col_action:
            st.write("")
            if stock > 0:
                if st.button(
                    "🛒 Ajouter",
                    key=f"ajouter_{index}"
                ):
                    ajouter_au_panier(article)
                    st.rerun()
            else:
                st.button(
                    "Rupture",
                    key=f"rupture_{index}",
                    disabled=True
                )
# ============================================================
# PANIER & CONFORMITE LEGALE
# ============================================================
st.divider()
st.header("🛒 Mon panier")
if not st.session_state.panier:
    st.info(
        "Ton panier est vide 🌸"
    )
else:
    for i, produit in enumerate(
        st.session_state.panier
    ):
        col1, col2, col3, col4 = st.columns([4, 1, 1, 2])
        with col1:
            st.write(
                f"**{produit['produit']}**"
            )
        with col2:
            st.write(
                f"{produit['prix']:.2f} €"
            )
        with col3:
            st.write(
                f"x{produit['quantite']}"
            )
        with col4:
            moins = st.button(
                "➖",
                key=f"moins_{i}"
            )
            plus = st.button(
                "➕",
                key=f"plus_{i}"
            )
            if moins:
                retirer_du_panier(
                    produit["produit"]
                )
                st.rerun()
            if plus:
                produit["quantite"] += 1
                st.rerun()
    st.divider()
    total = calculer_total()
    st.subheader(
        f"💰 Total : {total:.2f} €"
    )
    st.markdown(
        "### 📝 Validation de votre demande de réservation"
    )
    st.info(
        "Conformément à la réglementation, veuillez renseigner vos coordonnées pour finaliser votre demande. Aucune transaction bancaire n'est effectuée sur ce site."
    )
    col_nom, col_vide = st.columns()
    with col_nom:
        client_id = st.text_input(
            "Nom et Prénom *",
            key="client_identite",
            placeholder="Ex : Marie Durant"
        )
    accepte_conditions = st.checkbox(
        "En cochant cette case, j'accepte que mes données (Nom/Prénom) soient transmises pour le traitement exclusif de ma réservation et je déclare avoir pris connaissance des Mentions Légales.",
        key="legal_check"
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🗑️ Vider le panier"
        ):
            vider_panier()
            st.rerun()
    with col2:
        disabled_btn = not (
            accepte_conditions
            and client_id.strip() != ""
        )
        commander = st.button(
            "✅ Valider ma commande",
            type="primary",
            disabled=disabled_btn
        )
        if commander:
            nom_propre = client_id.strip()
            succes, message = envoyer_commande(
                nom_propre
            )
            if succes:
                envoyer_discord(nom_propre)
                st.session_state.panier = []
                st.session_state.commande_envoyee = True
                charger_produits.clear()
                st.success(
                    "🎉 Commande validée avec succès !"
                )
                st.balloons()
                st.rerun()
            else:
                st.error(message)
# ============================================================
# ESTIMATION CARBURANT
# ============================================================
st.divider()
st.header("⛽ Estimation carburant")
st.write(
    "Calcule le coût approximatif de ton trajet."
)
col1, col2 = st.columns(2)
with col1:
    distance = st.number_input(
        "Distance aller-retour (km)",
        min_value=0.0,
        value=0.0,
        step=1.0
    )
with col2:
    consommation = st.number_input(
        "Consommation (L/100 km)",
        min_value=0.1,
        value=CONSOMMATION_L_100KM,
        step=0.1
    )
if distance > 0:
    litres = (
        distance
        * consommation
        / 100
    )
    cout = (
        litres
        * PRIX_CARBURANT
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Distance",
            f"{distance:.0f} km"
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
# FOOTER / MENTIONS LEGALES
# ============================================================
st.divider()
st.markdown(
    """
    <div style="background-color:#f9f9f9; padding:15px; border-radius:5px; font-size:12px; color:#555555;">
        <p style="margin-bottom:5px;"><strong>🌸 Mentions Légales & Conformité</strong></p>
        <p style="margin-bottom:5px;"><strong>Éditeur du site :</strong> Site géré de manière privée par Sarah (Mes Bons Plans de Sarah). Ce site ne constitue pas une boutique marchande en ligne automatisée : il s'agit d'un outil de visualisation de catalogue et de réservation de stocks physiques.</p>
        <p style="margin-bottom:5px;"><strong>Hébergement :</strong> Ce service est hébergé de manière sécurisée par la plateforme Streamlit Cloud / GitHub.</p>
        <p style="margin-bottom:5px;"><strong>RGPD / Protection des données :</strong> Les seules données personnelles collectées de manière éphémère sont vos Nom et Prénom au moment de la validation finale du panier. Ces informations sont transmises de manière sécurisée à notre outil interne (Discord/Google Sheets) aux seules fins de préparation et de mise à disposition de votre commande. Vous disposez d'un droit d'accès et de suppression en contactant directement l'administratrice.</p>
    </div>
    """,
    unsafe_allow_html=True
)
