import streamlit as st
import pandas as pd
import requests
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo
# ============================================================
# CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Mes Bons Plans de Sarah 🌸",
    page_icon="🛍️",
    layout="wide"
)
# ============================================================
# PARAMÈTRES
# ============================================================
GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA"
    "/edit?usp=sharing"
)
STOCK_API_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbxTep4v3fevHxEU0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA"
    "/exec"
)
# Mets ici ton NOUVEAU webhook Discord
DISCORD_WEBHOOK = "COLLE_TON_NOUVEAU_WEBHOOK_ICI"
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
# STYLE
# ============================================================
st.markdown(
    """
    <style>
    .main-title {
        text-align: center;
        font-size: 2.3rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #777;
        margin-bottom: 1.5rem;
    }
    [data-testid="stSidebar"] {
        min-width: 280px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px;
    }
    .prix-initial {
        color: #888;
        text-decoration: line-through;
        font-size: 0.95rem;
    }
    .prix-promo {
        font-size: 1.25rem;
        font-weight: 700;
    }
    .economie {
        font-weight: 700;
        margin-top: 4px;
    }
    .economie-panier {
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
    """,
    unsafe_allow_html=True
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
# ============================================================
# FONCTIONS
# ============================================================
def normaliser_texte(texte):
    """Normalise les noms de colonnes."""
    texte = str(texte).strip().lower()
    texte = unicodedata.normalize(
        "NFD",
        texte
    )
    texte = "".join(
        caractere
        for caractere in texte
        if unicodedata.category(caractere) != "Mn"
    )
    texte = texte.replace(" ", "")
    texte = texte.replace("_", "")
    texte = texte.replace("-", "")
    return texte
def trouver_colonne(df, alias):
    """Trouve une colonne parmi plusieurs noms possibles."""
    colonnes_normalisees = {
        normaliser_texte(col): col
        for col in df.columns
    }
    for nom in alias:
        nom_normalise = normaliser_texte(nom)
        if nom_normalise in colonnes_normalisees:
            return colonnes_normalisees[nom_normalise]
    return None
@st.cache_data(ttl=60)
def charger_produits():
    url_csv = GOOGLE_SHEET_URL.replace(
        "/edit?usp=sharing",
        "/export?format=csv"
    )
    df = pd.read_csv(url_csv)
    # ========================================================
    # COLONNES
    # ========================================================
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
    col_categorie = trouver_colonne(
        df,
        [
            "categorie",
            "catégorie",
            "cat",
            "rayon"
        ]
    )
    col_format = trouver_colonne(
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
    col_prix_initial = trouver_colonne(
        df,
        [
            "prix initial",
            "prix de base",
            "prix base",
            "initial",
            "prix"
        ]
    )
    col_prix_promo = trouver_colonne(
        df,
        [
            "prix promo",
            "prix promotion",
            "promo",
            "prix promotionnel"
        ]
    )
    if col_nom is None:
        st.error(
            "❌ Impossible de trouver la colonne du nom du produit."
        )
        st.stop()
    # ========================================================
    # RENOMMAGE VERS NOMS INTERNES
    # ========================================================
    nouveau_df = pd.DataFrame()
    nouveau_df["nom"] = (
        df[col_nom]
        .fillna("")
        .astype(str)
    )
    if col_photo:
        nouveau_df["photo"] = (
            df[col_photo]
            .fillna("")
            .astype(str)
        )
    else:
        nouveau_df["photo"] = ""
    if col_categorie:
        nouveau_df["categorie"] = (
            df[col_categorie]
            .fillna("")
            .astype(str)
        )
    else:
        nouveau_df["categorie"] = "Autres"
    if col_format:
        nouveau_df["format"] = (
            df[col_format]
            .fillna("")
            .astype(str)
        )
    else:
        nouveau_df["format"] = ""
    if col_stock:
        nouveau_df["stock"] = pd.to_numeric(
            df[col_stock],
            errors="coerce"
        ).fillna(0).astype(int)
    else:
        nouveau_df["stock"] = 0
    # ========================================================
    # PRIX INITIAL
    # ========================================================
    if col_prix_initial:
        nouveau_df["prix_initial"] = pd.to_numeric(
            df[col_prix_initial]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace("€", "", regex=False)
            .str.strip(),
            errors="coerce"
        )
    else:
        nouveau_df["prix_initial"] = None
    # ========================================================
    # PRIX PROMO
    # ========================================================
    if col_prix_promo:
        nouveau_df["prix_promo"] = pd.to_numeric(
            df[col_prix_promo]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace("€", "", regex=False)
            .str.strip(),
            errors="coerce"
        )
    else:
        nouveau_df["prix_promo"] = None
    # ========================================================
    # PRIX UTILISÉ POUR LA COMMANDE
    # ========================================================
    nouveau_df["prix"] = nouveau_df["prix_promo"]
    nouveau_df["prix"] = nouveau_df["prix"].fillna(
        nouveau_df["prix_initial"]
    )
    # ========================================================
    # CALCUL DES ÉCONOMIES
    # ========================================================
    nouveau_df["economie"] = (
        nouveau_df["prix_initial"]
        - nouveau_df["prix"]
    )
    # Si l'économie est négative, on la force à 0
    nouveau_df["economie"] = (
        nouveau_df["economie"]
        .clip(lower=0)
        .fillna(0)
    )
    nouveau_df["pourcentage_economie"] = 0.0
    masque_prix_valide = (
        nouveau_df["prix_initial"].notna()
        & (nouveau_df["prix_initial"] > 0)
        & (nouveau_df["prix"] < nouveau_df["prix_initial"])
    )
    nouveau_df.loc[
        masque_prix_valide,
        "pourcentage_economie"
    ] = (
        (
            (
                nouveau_df.loc[
                    masque_prix_valide,
                    "prix_initial"
                ]
                -
                nouveau_df.loc[
                    masque_prix_valide,
                    "prix"
                ]
            )
            /
            nouveau_df.loc[
                masque_prix_valide,
                "prix_initial"
            ]
        )
        * 100
    )
    # ========================================================
    # NETTOYAGE
    # ========================================================
    nouveau_df = nouveau_df[
        nouveau_df["nom"].str.strip() != ""
    ].copy()
    nouveau_df["prix"] = pd.to_numeric(
        nouveau_df["prix"],
        errors="coerce"
    ).fillna(0)
    nouveau_df["prix_initial"] = pd.to_numeric(
        nouveau_df["prix_initial"],
        errors="coerce"
    )
    nouveau_df["economie"] = pd.to_numeric(
        nouveau_df["economie"],
        errors="coerce"
    ).fillna(0)
    nouveau_df["pourcentage_economie"] = pd.to_numeric(
        nouveau_df["pourcentage_economie"],
        errors="coerce"
    ).fillna(0)
    return nouveau_df.reset_index(drop=True)
def envoyer_discord(message):
    try:
        if (
            not DISCORD_WEBHOOK
            or DISCORD_WEBHOOK
            == "COLLE_TON_NOUVEAU_WEBHOOK_ICI"
        ):
            st.error(
                "❌ Le webhook Discord n'est pas renseigné."
            )
            return False
        reponse = requests.post(
            DISCORD_WEBHOOK,
            json={"content": message},
            timeout=15
        )
        if reponse.status_code in [200, 204]:
            return True
        st.error(
            "❌ Discord a refusé la notification."
        )
        st.code(
            f"Code HTTP : {reponse.status_code}"
        )
        if reponse.text:
            st.code(
                reponse.text
            )
        return False
    except Exception as erreur:
        st.error(
            "❌ Impossible de contacter Discord."
        )
        st.code(
            str(erreur)
        )
        return False
def retirer_stock(produit, quantite):
    try:
        payload = {
            "action": "retirer",
            "produit": produit,
            "quantite": quantite,
            "utilisateur": st.session_state.utilisateur
        }
        reponse = requests.post(
            STOCK_API_URL,
            json=payload,
            timeout=20
        )
        if reponse.status_code not in [200, 201]:
            return False
        return True
    except Exception:
        return False
def calculer_sous_total():
    total = 0
    for article in st.session_state.panier.values():
        total += (
            article["quantite"]
            * article["prix"]
        )
    return total
def calculer_economie_totale():
    total = 0
    for article in st.session_state.panier.values():
        total += (
            article["quantite"]
            * article.get("economie", 0)
        )
    return total
# ============================================================
# CONNEXION
# ============================================================
if not st.session_state.connecte:
    st.markdown(
        '<div class="main-title">🛍️ Mes Bons Plans de Sarah 🌸</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="subtitle">Connexion à votre espace</div>',
        unsafe_allow_html=True
    )
    espace_gauche, espace_centre, espace_droit = st.columns(
        [1, 2, 1]
    )
    with espace_centre:
        with st.container(border=True):
            st.subheader("🔐 Connexion")
            utilisateur = st.text_input(
                "Identifiant",
                placeholder="Votre identifiant"
            )
            mot_de_passe = st.text_input(
                "Mot de passe",
                type="password",
                placeholder="Votre mot de passe"
            )
            connexion = st.button(
                "🚀 Se connecter",
                use_container_width=True
            )
            if connexion:
                utilisateur = utilisateur.strip().lower()
                if (
                    utilisateur in COMPTES_AUTORISES
                    and COMPTES_AUTORISES[utilisateur]
                    == mot_de_passe
                ):
                    st.session_state.connecte = True
                    st.session_state.utilisateur = utilisateur
                    st.session_state.panier = {}
                    st.rerun()
                else:
                    st.error(
                        "❌ Identifiant ou mot de passe incorrect."
                    )
    st.stop()
# ============================================================
# CHARGEMENT DES PRODUITS
# ============================================================
df = charger_produits()
# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🌸 Mes Bons Plans")
    st.success(
        f"👤 Connecté : **{st.session_state.utilisateur}**"
    )
    st.divider()
    # ========================================================
    # RECHERCHE
    # ========================================================
    st.markdown("### 🔎 Recherche")
    recherche = st.text_input(
        "Rechercher un produit",
        placeholder="Ex : lait, lessive..."
    )
    # ========================================================
    # CATÉGORIE
    # ========================================================
    st.markdown("### 📂 Catégorie")
    categories = sorted(
        [
            str(c)
            for c in df["categorie"].dropna().unique()
            if str(c).strip()
        ]
    )
    categorie_selectionnee = st.selectbox(
        "Catégorie",
        ["Toutes"] + categories
    )
    st.divider()
    # ========================================================
    # CARBURANT
    # ========================================================
    st.markdown("### ⛽ Estimation carburant")
    prix_essence = st.slider(
        "Prix de l'essence",
        min_value=1.20,
        max_value=2.50,
        value=1.80,
        step=0.01,
        format="%.2f €/L"
    )
    consommation = st.slider(
        "Consommation",
        min_value=3.0,
        max_value=15.0,
        value=6.0,
        step=0.1,
        format="%.1f L/100 km"
    )
    distance_estimee = st.number_input(
        "Distance estimée",
        min_value=0.0,
        value=10.0,
        step=1.0,
        format="%.1f"
    )
    cout_essence_estime = (
        distance_estimee
        * consommation
        / 100
        * prix_essence
    )
    st.info(
        f"⛽ Coût carburant estimé : "
        f"**{cout_essence_estime:.2f} €**"
    )
    st.divider()
    if st.button(
        "🚪 Se déconnecter",
        use_container_width=True
    ):
        st.session_state.connecte = False
        st.session_state.utilisateur = ""
        st.session_state.panier = {}
        st.rerun()
# ============================================================
# FILTRAGE PRODUITS
# ============================================================
df_affiche = df.copy()
if recherche:
    recherche_normalisee = normaliser_texte(
        recherche
    )
    masque_recherche = (
        df_affiche["nom"]
        .apply(normaliser_texte)
        .str.contains(
            recherche_normalisee,
            na=False
        )
    )
    df_affiche = df_affiche[
        masque_recherche
    ]
if categorie_selectionnee != "Toutes":
    df_affiche = df_affiche[
        df_affiche["categorie"]
        == categorie_selectionnee
    ]
# ============================================================
# TITRE
# ============================================================
st.markdown(
    '<div class="main-title">🛍️ Mes Bons Plans de Sarah 🌸</div>',
    unsafe_allow_html=True
)
st.markdown(
    f"""
    <div class="subtitle">
        Bienvenue <strong>{st.session_state.utilisateur}</strong> !
    </div>
    """,
    unsafe_allow_html=True
)
# ============================================================
# LAYOUT PRINCIPAL
# ============================================================
col_panier, col_produits = st.columns(
    [1, 2.2],
    gap="large"
)
# ============================================================
# PANIER À GAUCHE
# ============================================================
with col_panier:
    st.subheader(
        f"🛒 Panier "
        f"({sum(item['quantite'] for item in st.session_state.panier.values())})"
    )
    with st.container(border=True):
        if not st.session_state.panier:
            st.info(
                "🛒 Votre panier est vide."
            )
            st.write(
                "Ajoutez des produits depuis la liste "
                "à droite."
            )
        else:
            # ====================================================
            # ARTICLES DU PANIER
            # ====================================================
            for panier_index, (
                nom,
                article
            ) in enumerate(
                list(st.session_state.panier.items())
            ):
                quantite = article["quantite"]
                prix = article["prix"]
                prix_initial = article.get(
                    "prix_initial",
                    prix
                )
                economie_unitaire = article.get(
                    "economie",
                    0
                )
                total_article = (
                    quantite * prix
                )
                economie_article = (
                    quantite * economie_unitaire
                )
                st.markdown(
                    f"**{nom}**"
                )
                # Prix initial / prix promo
                if (
                    prix_initial
                    and prix_initial > prix
                ):
                    st.markdown(
                        f"""
                        <span class="prix-initial">
                            {prix_initial:.2f} € / unité
                        </span>
                        &nbsp;
                        <span class="prix-promo">
                            {prix:.2f} €
                        </span>
                        """,
                        unsafe_allow_html=True
                    )
                    st.caption(
                        f"💸 Économie : "
                        f"{economie_article:.2f} €"
                    )
                else:
                    st.write(
                        f"{prix:.2f} € / unité"
                    )
                st.write(
                    f"{quantite} × "
                    f"{prix:.2f} € "
                    f"= **{total_article:.2f} €**"
                )
                if st.button(
                    "🗑️ Retirer",
                    key=f"supprimer_panier_{panier_index}",
                    use_container_width=True
                ):
                    del st.session_state.panier[nom]
                    st.rerun()
                if panier_index < (
                    len(st.session_state.panier) - 1
                ):
                    st.divider()
            st.divider()
            # ====================================================
            # SOUS-TOTAL
            # ====================================================
            sous_total = calculer_sous_total()
            economie_totale = calculer_economie_totale()
            st.metric(
                "💰 Sous-total",
                f"{sous_total:.2f} €"
            )
            # ====================================================
            # ÉCONOMIE TOTALE
            # ====================================================
            if economie_totale > 0:
                st.markdown(
                    f"""
                    <div class="economie-panier">
                        💸 <strong>Économie réalisée</strong><br>
                        <span style="font-size: 1.25rem;">
                            {economie_totale:.2f} €
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            # ====================================================
            # MODE DE REMISE
            # ====================================================
            st.markdown(
                "### 🚚 Livraison"
            )
            mode_livraison = st.radio(
                "Mode de remise",
                [
                    "Retrait / remise en main propre",
                    "Livraison"
                ],
                key="mode_livraison"
            )
            frais_livraison = 0.0
            distance_commande = 0.0
            cout_essence_commande = 0.0
            if mode_livraison == "Livraison":
                distance_commande = st.number_input(
                    "📍 Distance de livraison",
                    min_value=0.0,
                    value=float(
                        distance_estimee
                    ),
                    step=1.0,
                    format="%.1f",
                    key="distance_commande"
                )
                if sous_total < 30:
                    frais_livraison = (
                        distance_commande * 0.10
                    )
                    st.info(
                        f"🚚 Frais de livraison : "
                        f"**{frais_livraison:.2f} €**"
                    )
                else:
                    frais_livraison = 0.0
                    st.success(
                        "🎉 Livraison gratuite à partir de 30 € !"
                    )
                # -----------------------------------------------
                # ESSENCE
                # -----------------------------------------------
                cout_essence_commande = (
                    distance_commande
                    * consommation
                    / 100
                    * prix_essence
                )
                st.caption(
                    f"⛽ Essence estimée : "
                    f"{cout_essence_commande:.2f} €"
                )
                reste_apres_essence = (
                    frais_livraison
                    - cout_essence_commande
                )
                if frais_livraison > 0:
                    if reste_apres_essence >= 0:
                        st.caption(
                            f"⛽ Après estimation du carburant : "
                            f"{reste_apres_essence:.2f} €"
                        )
                    else:
                        st.caption(
                            f"⛽ L'estimation du carburant dépasse "
                            f"les frais de livraison de "
                            f"{abs(reste_apres_essence):.2f} €."
                        )
                    st.caption(
                        "Cette estimation ne tient pas compte de "
                        "l'usure, de l'assurance, des péages ou "
                        "des autres frais du véhicule."
                    )
            else:
                st.success(
                    "🤝 Retrait / remise en main propre"
                )
            # ====================================================
            # TOTAL
            # ====================================================
            total_commande = (
                sous_total
                + frais_livraison
            )
            st.divider()
            st.metric(
                "💳 TOTAL",
                f"{total_commande:.2f} €"
            )
            # ====================================================
            # VALIDATION
            # ====================================================
            st.markdown(
                "### ✅ Validation"
            )
            valider = st.button(
                "✅ Valider la commande",
                type="primary",
                use_container_width=True,
                key="valider_commande"
            )
            if valider:
                if not st.session_state.panier:
                    st.error(
                        "❌ Le panier est vide."
                    )
                else:
                    # ============================================
                    # VÉRIFICATION DES STOCKS
                    # ============================================
                    stocks_ok = True
                    for nom, article in (
                        st.session_state.panier.items()
                    ):
                        produit_ligne = df[
                            df["nom"] == nom
                        ]
                        if produit_ligne.empty:
                            stocks_ok = False
                            st.error(
                                f"❌ Produit introuvable : {nom}"
                            )
                            continue
                        stock_disponible = int(
                            produit_ligne.iloc[0]["stock"]
                        )
                        if article["quantite"] > stock_disponible:
                            stocks_ok = False
                            st.error(
                                f"❌ Stock insuffisant pour "
                                f"**{nom}**. "
                                f"Disponible : "
                                f"{stock_disponible}"
                            )
                    # ============================================
                    # COMMANDE
                    # ============================================
                    if stocks_ok:
                        date_commande = datetime.now(
                            ZoneInfo("Europe/Paris")
                        )
                        date_formatee = (
                            date_commande
                            .strftime("%d/%m/%Y à %H:%M")
                        )
                        # ----------------------------------------
                        # MESSAGE DISCORD
                        # ----------------------------------------
                        lignes_produits = []
                        for nom, article in (
                            st.session_state.panier.items()
                        ):
                            qte = article["quantite"]
                            prix = article["prix"]
                            economie = article.get(
                                "economie",
                                0
                            )
                            total_article = (
                                qte * prix
                            )
                            economie_article = (
                                qte * economie
                            )
                            ligne = (
                                f"• {qte} × {nom} — "
                                f"{prix:.2f} € / unité = "
                                f"{total_article:.2f} €"
                            )
                            if economie_article > 0:
                                ligne += (
                                    f" | Économie : "
                                    f"{economie_article:.2f} €"
                                )
                            lignes_produits.append(
                                ligne
                            )
                        produits_message = "\n".join(
                            lignes_produits
                        )
                        if (
                            mode_livraison
                            == "Livraison"
                        ):
                            livraison_message = (
                                "🚚 Livraison\n"
                                f"Distance : "
                                f"{distance_commande:.1f} km\n"
                                f"Frais : "
                                f"{frais_livraison:.2f} €\n"
                                f"⛽ Essence estimée : "
                                f"{cout_essence_commande:.2f} €\n"
                                f"⛽ Prix essence : "
                                f"{prix_essence:.2f} €/L\n"
                                f"🚗 Consommation : "
                                f"{consommation:.1f} L/100 km"
                            )
                        else:
                            livraison_message = (
                                "🤝 Retrait / remise en main propre\n"
                                "Frais : 0.00 €"
                            )
                        message_discord = (
                            "🛒 **NOUVELLE COMMANDE !**\n\n"
                            f"👤 Client : "
                            f"{st.session_state.utilisateur}\n"
                            f"🕐 Date : "
                            f"{date_formatee}\n\n"
                            "📦 **Produits :**\n"
                            f"{produits_message}\n\n"
                            f"💰 Sous-total : "
                            f"{sous_total:.2f} €\n"
                            f"💸 Économie réalisée : "
                            f"{economie_totale:.2f} €\n"
                            f"{livraison_message}\n\n"
                            f"💳 **TOTAL : "
                            f"{total_commande:.2f} €**"
                        )
                        # ========================================
                        # RETRAIT STOCK
                        # ========================================
                        stock_reussi = True
                        for nom, article in (
                            st.session_state.panier.items()
                        ):
                            resultat_stock = retirer_stock(
                                nom,
                                article["quantite"]
                            )
                            if not resultat_stock:
                                stock_reussi = False
                                st.error(
                                    f"❌ Impossible de mettre à jour "
                                    f"le stock pour : {nom}"
                                )
                                break
                        # ========================================
                        # SI STOCK OK
                        # ========================================
                        if stock_reussi:
                            discord_ok = envoyer_discord(
                                message_discord
                            )
                            # Vider le panier
                            st.session_state.panier = {}
                            # Rafraîchir les produits
                            charger_produits.clear()
                            if discord_ok:
                                st.balloons()
                                st.success(
                                    "🎉 Commande validée ! "
                                    "La notification Discord a été envoyée."
                                )
                            else:
                                st.warning(
                                    "⚠️ Commande validée, "
                                    "mais la notification Discord "
                                    "n'a pas pu être envoyée."
                                )
                            st.rerun()
# ============================================================
# PRODUITS À DROITE
# ============================================================
with col_produits:
    st.subheader(
        f"🛍️ Produits ({len(df_affiche)})"
    )
    if df_affiche.empty:
        st.info(
            "Aucun produit ne correspond à votre recherche."
        )
    else:
        for index, produit in df_affiche.iterrows():
            nom = str(produit["nom"])
            photo = str(produit["photo"]).strip()
            categorie = str(produit["categorie"])
            format_produit = str(produit["format"])
            stock = int(produit["stock"])
            prix = float(produit["prix"])
            prix_initial = produit["prix_initial"]
            if pd.isna(prix_initial):
                prix_initial = None
            else:
                prix_initial = float(prix_initial)
            economie = float(
                produit["economie"]
            )
            pourcentage_economie = float(
                produit["pourcentage_economie"]
            )
            with st.container(border=True):
                col_photo, col_infos = st.columns(
                    [1, 2]
                )
                # ------------------------------------------------
                # PHOTO
                # ------------------------------------------------
                with col_photo:
                    if (
                        photo.startswith("http://")
                        or photo.startswith("https://")
                    ):
                        st.image(
                            photo,
                            use_container_width=True
                        )
                    else:
                        st.write("🛍️")
                # ------------------------------------------------
                # INFORMATIONS
                # ------------------------------------------------
                with col_infos:
                    st.markdown(
                        f"### {nom}"
                    )
                    if categorie:
                        st.caption(
                            f"📂 {categorie}"
                        )
                    if format_produit:
                        st.write(
                            f"📦 Format : {format_produit}"
                        )
                    # ============================================
                    # PRIX
                    # ============================================
                    if (
                        prix_initial is not None
                        and prix_initial > prix
                    ):
                        st.markdown(
                            f"""
                            <span class="prix-initial">
                                {prix_initial:.2f} €
                            </span>
                            &nbsp;&nbsp;
                            <span class="prix-promo">
                                {prix:.2f} €
                            </span>
                            """,
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"""
                            <div class="economie">
                                🏷️ -{pourcentage_economie:.0f} %
                                &nbsp; | &nbsp;
                                💸 Économie :
                                {economie:.2f} €
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"""
                            <span class="prix-promo">
                                {prix:.2f} €
                            </span>
                            """,
                            unsafe_allow_html=True
                        )
                    # ============================================
                    # STOCK
                    # ============================================
                    if stock > 0:
                        st.success(
                            f"Disponible : {stock}"
                        )
                        # ========================================
                        # FORMULAIRE AJOUT PANIER
                        # ========================================
                        with st.form(
                            key=f"form_ajout_{index}"
                        ):
                            quantite = st.number_input(
                                "Quantité",
                                min_value=1,
                                max_value=stock,
                                value=1,
                                step=1,
                                key=f"nombre_{index}"
                            )
                            ajouter = st.form_submit_button(
                                "🛒 Ajouter au panier",
                                use_container_width=True
                            )
                            if ajouter:
                                if nom in st.session_state.panier:
                                    ancienne_quantite = (
                                        st.session_state
                                        .panier[nom]["quantite"]
                                    )
                                    nouvelle_quantite = (
                                        ancienne_quantite
                                        + int(quantite)
                                    )
                                    if nouvelle_quantite > stock:
                                        st.error(
                                            f"❌ Stock maximum disponible : "
                                            f"{stock}"
                                        )
                                    else:
                                        st.session_state.panier[
                                            nom
                                        ]["quantite"] = (
                                            nouvelle_quantite
                                        )
                                        st.session_state.panier[
                                            nom
                                        ]["prix"] = prix
                                        st.session_state.panier[
                                            nom
                                        ]["prix_initial"] = (
                                            prix_initial
                                            if prix_initial is not None
                                            else prix
                                        )
                                        st.session_state.panier[
                                            nom
                                        ]["economie"] = economie
                                        st.rerun()
                                else:
                                    st.session_state.panier[
                                        nom
                                    ] = {
                                        "quantite": int(quantite),
                                        "prix": prix,
                                        "prix_initial": (
                                            prix_initial
                                            if prix_initial is not None
                                            else prix
                                        ),
                                        "economie": economie
                                    }
                                    st.rerun()
                    else:
                        st.error(
                            "❌ Rupture de stock"
                        )