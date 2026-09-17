import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime
# ============================================================
# 1. CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Mes Bons Plans de Sarah 🌸",
    page_icon="🛍️",
    layout="wide"
)
# ============================================================
# 2. STYLE GÉNÉRAL
# ============================================================
# Aucun HTML pour les cartes produits.
# Le CSS ci-dessous sert uniquement à l'apparence générale.
st.markdown("""
<style>
.stApp {
    background-color: #FFF5F5;
}
[data-testid="stSidebar"] {
    background-color: #FFEAEF;
    border-right: 2px solid #FFD1D1;
}
h1, h2, h3 {
    color: #C71585 !important;
}
.stButton > button {
    background-color: #FF69B4 !important;
    color: white !important;
    border-radius: 20px !important;
    font-weight: bold !important;
    width: 100%;
}
.stNumberInput input {
    border-radius: 10px;
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
URL_MACRO_STOCK = (
    "https://script.google.com/macros/s/"
    "AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/"
    "exec"
)
# ============================================================
# 5. FONCTIONS UTILITAIRES
# ============================================================
def convertir_float(valeur, valeur_defaut=0.0):
    try:
        if pd.isna(valeur):
            return valeur_defaut
        texte = str(valeur).strip()
        if texte.lower() in ["", "nan", "none", "n/a", "na"]:
            return valeur_defaut
        texte = texte.replace("€", "")
        texte = texte.replace(" ", "")
        texte = texte.replace(",", ".")
        return float(texte)
    except (ValueError, TypeError):
        return valeur_defaut
def convertir_int(valeur, valeur_defaut=0):
    try:
        return int(convertir_float(valeur, valeur_defaut))
    except (ValueError, TypeError):
        return valeur_defaut
def envoyer_discord(message):
    """
    Envoie une notification Discord.
    Le webhook doit être placé dans les secrets Streamlit :
    
    DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
    """
    try:
        webhook = st.secrets.get("DISCORD_WEBHOOK", "")
        if not webhook:
            return False
        response = requests.post(
            webhook,
            json={"content": message},
            timeout=10
        )
        return response.status_code in [200, 204]
    except Exception:
        return False
@st.cache_data(ttl=60)
def load_clean_data():
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
    data.columns = [
        str(colonne).strip().lower()
        for colonne in data.columns
    ]
    remplacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ä": "a",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ô": "o",
        "ö": "o",
        "î": "i",
        "ï": "i",
        "ç": "c"
    }
    for ancien, nouveau in remplacements.items():
        data.columns = data.columns.str.replace(
            ancien,
            nouveau,
            regex=False
        )
    data.columns = (
        data.columns
        .str.replace("\n", " ", regex=False)
        .str.replace("  ", " ", regex=False)
        .str.strip()
    )
    for colonne in data.select_dtypes(
        include=["object"]
    ).columns:
        data[colonne] = (
            data[colonne]
            .astype(str)
            .str.replace('"', '', regex=False)
            .str.strip()
        )
    return data
def trouver_colonne(dataframe, noms_possibles):
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
if "mode_livraison" not in st.session_state:
    st.session_state.mode_livraison = "Retrait / remise en main propre"
if "distance_km" not in st.session_state:
    st.session_state.distance_km = 0.0
# ============================================================
# 7. PAGE DE CONNEXION
# ============================================================
if not st.session_state.connecte:
    st.title("🎀 Espace Privé")
    st.subheader(
        "La Boutique des Bons Plans 🌸"
    )
    st.write(
        "Bienvenue dans votre espace privé 🛍️"
    )
    with st.form("formulaire_connexion"):
        identifiant = st.text_input(
            "👤 Votre Identifiant"
        )
        mot_de_passe = st.text_input(
            "🔑 Votre Mot de passe",
            type="password"
        )
        connexion = st.form_submit_button(
            "✨ Entrer dans la boutique"
        )
        if connexion:
            identifiant = identifiant.strip().lower()
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
                    "❌ Identifiant ou mot de passe incorrect."
                )
    st.stop()
# ============================================================
# 8. EN-TÊTE
# ============================================================
st.title(
    "🌸 La Boutique des Bons Plans 🛍️"
)
st.write(
    f"Coucou **{st.session_state.utilisateur.capitalize()}** ! 👋"
)
# ============================================================
# 9. DÉCONNEXION
# ============================================================
if st.sidebar.button(
    "🚪 Se déconnecter",
    key="bouton_deconnexion"
):
    st.session_state.connecte = False
    st.session_state.utilisateur = ""
    st.session_state.panier = {}
    st.session_state.achat_reussi = False
    st.rerun()
# ============================================================
# 10. CHARGEMENT DES DONNÉES
# ============================================================
try:
    df = load_clean_data()
except Exception as erreur:
    st.error(
        "❌ Impossible de charger les données Google Sheets."
    )
    st.caption(
        f"Détail technique : {erreur}"
    )
    st.stop()
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
        "image",
        "url photo",
        "url image"
    ]
)
col_nom = trouver_colonne(
    df,
    [
        "denomination",
        "denom",
        "produit",
        "nom",
        "nom produit"
    ]
)
col_cat = trouver_colonne(
    df,
    [
        "categorie",
        "catégorie",
        "cat",
        "rayon"
    ]
)
col_fmt = trouver_colonne(
    df,
    [
        "litre / gramme",
        "litre/gramme",
        "format",
        "contenance",
        "poids"
    ]
)
col_stock = trouver_colonne(
    df,
    [
        "quantite",
        "quantité",
        "stock",
        "stock disponible"
    ]
)
col_pinit = trouver_colonne(
    df,
    [
        "prix initial",
        "prix de base",
        "prix base",
        "initial",
        "prix"
    ]
)
col_ppromo = trouver_colonne(
    df,
    [
        "prix promo",
        "prix promotion",
        "promo",
        "prix promotionnel"
    ]
)
# ============================================================
# 12. VÉRIFICATION DES COLONNES
# ============================================================
colonnes_obligatoires = {
    "Produit": col_nom,
    "Stock": col_stock,
    "Prix initial": col_pinit,
    "Prix promo": col_ppromo
}
colonnes_manquantes = [
    nom
    for nom, colonne in colonnes_obligatoires.items()
    if colonne is None
]
if colonnes_manquantes:
    st.error(
        "❌ Des colonnes obligatoires sont introuvables."
    )
    st.write("Colonnes manquantes :")
    for colonne in colonnes_manquantes:
        st.write(f"- {colonne}")
    st.write("Colonnes détectées :")
    st.code(
        ", ".join(df.columns.tolist())
    )
    st.stop()
# ============================================================
# 13. FILTRE PAR CATÉGORIE
# ============================================================
st.sidebar.header(
    "🎯 Filtres de recherche"
)
if col_cat:
    categories = (
        df[col_cat]
        .dropna()
        .astype(str)
        .str.strip()
    )
    categories = sorted(
        [
            categorie
            for categorie in categories.unique()
            if categorie
        ]
    )
    categories_disponibles = (
        ["Toutes"] + categories
    )
else:
    categories_disponibles = ["Toutes"]
categorie_choisie = st.sidebar.selectbox(
    "Filtrer par rayon :",
    categories_disponibles
)
# ============================================================
# 14. APPLICATION DU FILTRE
# ============================================================
if (
    categorie_choisie == "Toutes"
    or col_cat is None
):
    df_filtre = df.copy()
else:
    df_filtre = df[
        df[col_cat]
        .astype(str)
        .str.strip()
        == categorie_choisie
    ].copy()
# ============================================================
# 15. PANIER
# ============================================================
st.sidebar.markdown("---")
st.sidebar.header(
    "🛒 Votre Panier"
)
total_produits = 0.0
if not st.session_state.panier:
    st.sidebar.info(
        "Votre panier est vide pour le moment. ✨"
    )
else:
    articles_a_supprimer = []
    for nom_art, details_art in list(
        st.session_state.panier.items()
    ):
        quantite = convertir_int(
            details_art.get("quantite", 0)
        )
        prix = convertir_float(
            details_art.get("prix", 0)
        )
        sous_total = quantite * prix
        total_produits += sous_total
        st.sidebar.write(
            f"**{nom_art}**"
        )
        st.sidebar.caption(
            f"{quantite} × {prix:.2f} € = "
            f"{sous_total:.2f} €"
        )
        if st.sidebar.button(
            "🗑️ Retirer",
            key=f"del_{nom_art}"
        ):
            articles_a_supprimer.append(
                nom_art
            )
    if articles_a_supprimer:
        for article in articles_a_supprimer:
            if article in st.session_state.panier:
                del st.session_state.panier[
                    article
                ]
        st.rerun()
# ============================================================
# 16. LIVRAISON
# ============================================================
if st.session_state.panier:
    st.sidebar.markdown("---")
    st.sidebar.subheader(
        "🚗 Livraison"
    )
    mode_livraison = st.sidebar.radio(
        "Choisissez votre mode :",
        [
            "Retrait / remise en main propre",
            "Livraison"
        ],
        key="choix_livraison"
    )
    frais_livraison = 0.0
    distance_km = 0.0
    if mode_livraison == "Livraison":
        distance_km = st.sidebar.number_input(
            "📍 Distance du trajet (km)",
            min_value=0.0,
            step=0.5,
            value=0.0,
            key="distance_livraison"
        )
        if total_produits >= 30:
            frais_livraison = 0.0
            st.sidebar.success(
                "🎁 Livraison offerte ! "
                "Votre commande atteint 30 €."
            )
        else:
            frais_livraison = (
                distance_km * 0.10
            )
            st.sidebar.info(
                f"🚗 Livraison : "
                f"{distance_km:.1f} km × 0,10 € "
                f"= {frais_livraison:.2f} €"
            )
    else:
        st.sidebar.success(
            "✨ Aucun frais de déplacement."
        )
else:
    mode_livraison = (
        "Retrait / remise en main propre"
    )
    frais_livraison = 0.0
    distance_km = 0.0
# ============================================================
# 17. TOTAL
# ============================================================
if st.session_state.panier:
    total_commande = (
        total_produits
        + frais_livraison
    )
    st.sidebar.markdown("---")
    st.sidebar.write(
        f"🛍️ Produits : "
        f"**{total_produits:.2f} €**"
    )
    st.sidebar.write(
        f"🚗 Livraison : "
        f"**{frais_livraison:.2f} €**"
    )
    st.sidebar.subheader(
        f"💳 Total : {total_commande:.2f} €"
    )
# ============================================================
# 18. VALIDATION DE LA COMMANDE
# ============================================================
if (
    st.session_state.panier
    and st.sidebar.button(
        "✅ Valider ma commande",
        key="bouton_validation_panier"
    )
):
    with st.spinner(
        "Prise en compte de votre commande..."
    ):
        succes_total = True
        details_commande = []
        panier_a_traiter = dict(
            st.session_state.panier
        )
        # ----------------------------------------------------
        # VÉRIFICATION ET MISE À JOUR DU STOCK
        # ----------------------------------------------------
        for nom_art, details_art in panier_a_traiter.items():
            quantite = convertir_int(
                details_art.get(
                    "quantite",
                    0
                )
            )
            prix = convertir_float(
                details_art.get(
                    "prix",
                    0
                )
            )
            if quantite <= 0:
                succes_total = False
                break
            payload = {
                "action": "retirer",
                "produit": nom_art,
                "quantite": quantite,
                "utilisateur":
                    st.session_state.utilisateur
            }
            try:
                response = requests.post(
                    URL_MACRO_STOCK,
                    json=payload,
                    timeout=10
                )
                if response.status_code != 200:
                    succes_total = False
                    break
                details_commande.append(
                    f"• {quantite} × "
                    f"{nom_art} — "
                    f"{prix:.2f} €/u"
                )
            except Exception:
                succes_total = False
                break
        # ----------------------------------------------------
        # COMMANDE VALIDÉE
        # ----------------------------------------------------
        if succes_total:
            date_commande = datetime.now().strftime(
                "%d/%m/%Y à %H:%M"
            )
            message_discord = (
                "🎉 **NOUVELLE COMMANDE !** 🎉\n\n"
                f"👤 **Cliente :** "
                f"{st.session_state.utilisateur.capitalize()}\n\n"
                "🛍️ **Commande :**\n"
                + "\n".join(details_commande)
                + "\n\n"
                f"🛍️ **Total produits :** "
                f"{total_produits:.2f} €\n"
                f"🚗 **Mode :** "
                f"{mode_livraison}\n"
            )
            if mode_livraison == "Livraison":
                message_discord += (
                    f"📍 **Distance :** "
                    f"{distance_km:.1f} km\n"
                    f"🚗 **Frais de livraison :** "
                    f"{frais_livraison:.2f} €\n"
                )
            else:
                message_discord += (
                    "🚗 **Frais de livraison :** "
                    "0,00 €\n"
                )
            message_discord += (
                f"\n💳 **TOTAL COMMANDE :** "
                f"{total_commande:.2f} €\n"
                f"🕐 **Date :** "
                f"{date_commande}"
            )
            discord_envoye = envoyer_discord(
                message_discord
            )
            # ------------------------------------------------
            # NETTOYAGE DU PANIER
            # ------------------------------------------------
            st.session_state.panier = {}
            st.session_state.achat_reussi = True
            load_clean_data.clear()
            # ------------------------------------------------
            # MESSAGE LOCAL
            # ------------------------------------------------
            if discord_envoye:
                st.session_state.message_discord = (
                    "📨 La commande a également été "
                    "envoyée sur Discord."
                )
            else:
                st.session_state.message_discord = (
                    "ℹ️ La commande est enregistrée. "
                    "La notification Discord n'a pas pu "
                    "être envoyée."
                )
            st.rerun()
        else:
            st.error(
                "❌ Une erreur est survenue lors de "
                "la mise à jour des stocks. "
                "La commande n'a pas pu être finalisée."
            )
# ============================================================
# 19. CONFIRMATION + BALLONS
# ============================================================
if st.session_state.achat_reussi:
    st.balloons()
    st.success(
        "🎉 Félicitations ! "
        "Votre commande a bien été enregistrée !"
    )
    if "message_discord" in st.session_state:
        st.info(
            st.session_state.message_discord
        )
        del st.session_state.message_discord
    st.session_state.achat_reussi = False
# ============================================================
# 20. CATALOGUE
# ============================================================
st.markdown("---")
st.subheader(
    "🛍️ Nos produits disponibles"
)
st.caption(
    f"{len(df_filtre)} produit(s) "
    "dans cette sélection"
)
# ============================================================
# 21. AFFICHAGE DES PRODUITS
# ============================================================
colonnes_produits = st.columns(3)
produits_affiches = 0
for index, row in df_filtre.iterrows():
    nom_produit = str(
        row[col_nom]
    ).strip()
    if (
        not nom_produit
        or nom_produit.lower()
        in ["nan", "none"]
    ):
        continue
    stock_actuel = convertir_int(
        row[col_stock]
    )
    if stock_actuel <= 0:
        continue
    px_base = convertir_float(
        row[col_pinit]
    )
    px_promo = convertir_float(
        row[col_ppromo]
    )
    if px_promo <= 0:
        px_promo = px_base
    if (
        px_base > 0
        and px_base > px_promo
    ):
        pourcentage_remise = int(
            round(
                (
                    (px_base - px_promo)
                    / px_base
                ) * 100
            )
        )
    else:
        pourcentage_remise = 0
    # --------------------------------------------------------
    # FORMAT
    # --------------------------------------------------------
    format_produit = "N/A"
    if (
        col_fmt is not None
        and not pd.isna(row[col_fmt])
    ):
        format_produit = str(
            row[col_fmt]
        ).strip()
        if format_produit.lower() == "nan":
            format_produit = "N/A"
    # --------------------------------------------------------
    # PHOTO
    # --------------------------------------------------------
    photo_url = ""
    if (
        col_photo is not None
        and not pd.isna(row[col_photo])
    ):
        photo_url = str(
            row[col_photo]
        ).strip()
        if photo_url.lower() == "nan":
            photo_url = ""
    # --------------------------------------------------------
    # COLONNE DU PRODUIT
    # --------------------------------------------------------
    col_courante = colonnes_produits[
        produits_affiches % 3
    ]
    produits_affiches += 1
    # ========================================================
    # PRODUIT — SANS HTML
    # ========================================================
    with col_courante:
        # ----------------------------------------------------
        # PHOTO
        # ----------------------------------------------------
        if photo_url:
            try:
                st.image(
                    photo_url,
                    use_container_width=True
                )
            except Exception:
                st.warning(
                    "⚠️ Photo indisponible"
                )
        else:
            st.info(
                "📷 Pas de photo disponible"
            )
        # ----------------------------------------------------
        # NOM
        # ----------------------------------------------------
        st.subheader(
            nom_produit
        )
        # ----------------------------------------------------
        # FORMAT
        # ----------------------------------------------------
        st.caption(
            f"📦 Format : {format_produit}"
        )
        # ----------------------------------------------------
        # PRIX
        # ----------------------------------------------------
        if px_base > px_promo:
            st.markdown(
                f"~~{px_base:.2f} €~~ "
                f"**{px_promo:.2f} €**"
            )
        else:
            st.markdown(
                f"### {px_promo:.2f} €"
            )
        # ----------------------------------------------------
        # PROMOTION
        # ----------------------------------------------------
        if pourcentage_remise > 0:
            st.success(
                f"🔥 Économie : "
                f"-{pourcentage_remise}%"
            )
        else:
            st.caption(
                "✨ Prix bas garanti"
            )
        # ----------------------------------------------------
        # STOCK
        # ----------------------------------------------------
        st.info(
            f"📦 Disponibles : "
            f"{stock_actuel} restant(s)"
        )
        # ----------------------------------------------------
        # QUANTITÉ
        # ----------------------------------------------------
        quantite_selectionnee = st.number_input(
            "Quantité",
            min_value=1,
            max_value=stock_actuel,
            value=1,
            step=1,
            key=f"input_{index}"
        )
        # ----------------------------------------------------
        # QUANTITÉ DÉJÀ DANS LE PANIER
        # ----------------------------------------------------
        quantite_deja_panier = 0
        if nom_produit in st.session_state.panier:
            quantite_deja_panier = convertir_int(
                st.session_state.panier[
                    nom_produit
                ].get(
                    "quantite",
                    0
                )
            )
        # ----------------------------------------------------
        # BOUTON AJOUT PANIER
        # ----------------------------------------------------
        if st.button(
            "🛒 Ajouter au panier",
            key=f"btn_{index}"
        ):
            nouvelle_quantite = (
                quantite_deja_panier
                + quantite_selectionnee
            )
            if nouvelle_quantite > stock_actuel:
                st.error(
                    "❌ Stock insuffisant. "
                    f"Il reste seulement "
                    f"{stock_actuel} exemplaire(s)."
                )
            else:
                st.session_state.panier[
                    nom_produit
                ] = {
                    "quantite":
                        nouvelle_quantite,
                    "prix":
                        px_promo
                }
                if quantite_deja_panier > 0:
                    st.toast(
                        f"✅ Quantité mise à jour "
                        f"pour {nom_produit} !",
                        icon="🛒"
                    )
                else:
                    st.toast(
                        f"🛒 {nom_produit} "
                        "ajouté au panier !",
                        icon="✨"
                    )
                time.sleep(0.5)
                st.rerun()
# ============================================================
# 22. AUCUN PRODUIT
# ============================================================
if produits_affiches == 0:
    st.info(
        "😢 Aucun produit disponible "
        "dans cette catégorie pour le moment."
    )
# ============================================================
# 23. CONDITIONS GÉNÉRALES
# ============================================================
st.markdown("---")
st.subheader(
    "📋 Conditions générales"
)
st.markdown(
    """
### 💰 Prix et promotions
Les prix indiqués dans cette application correspondent à des
**relevés de prix effectués pendant les périodes de promotion**,
à la date du relevé.
Les prix pratiqués par les magasins et enseignes sont
susceptibles d'évoluer. Une promotion peut notamment prendre
fin ou le prix d'un produit peut être modifié après le relevé.
Par conséquent, **le prix affiché dans l'application peut ne
plus correspondre au prix actuellement pratiqué en magasin**.
Je ne peux pas être tenue responsable d'une modification,
d'une fin de promotion ou d'une évolution du prix décidée par
l'enseigne après la date du relevé.
### 🛍️ Disponibilité des produits
Les disponibilités et quantités indiquées correspondent aux
informations disponibles au moment de la mise à jour de
l'application.
Les stocks pouvant évoluer rapidement, la disponibilité d'un
produit peut changer entre son affichage et la validation d'une
commande.
### 🚗 Livraison
La livraison est proposée **à 0,10 € par kilomètre** lorsque
le montant des achats est inférieur à **30 €**.
Le montant des frais est calculé selon la distance indiquée
pour le déplacement.
**À partir de 30 € d'achat, la livraison est offerte. 🎁**
La livraison est effectuée dans la limite de la distance et
des possibilités de déplacement de la personne qui assure
la remise de la commande.
### ℹ️ Informations générales
Les informations présentes dans cette application sont
communiquées à titre informatif et sont basées sur les
relevés effectués au moment de la préparation des bons plans.
Les prix, promotions et disponibilités peuvent évoluer
indépendamment de ma volonté.
En utilisant cette application, vous reconnaissez avoir pris
connaissance de ces conditions.
*Dernière mise à jour : 2026*
"""
)
# ============================================================
# 24. PIED DE PAGE
# ============================================================
st.markdown("---")
st.caption(
    "🌸 Mes Bons Plans de Sarah — "
    "Tous droits réservés 2026."
)