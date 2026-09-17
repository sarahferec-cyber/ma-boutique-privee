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
    "lesfilles": "promos",
    "invite": "bonplan11"
}

# ============================================================
# GOOGLE SHEETS
# ============================================================

GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/"
    "edit?usp=sharing"
)

# ============================================================
# APPS SCRIPT POUR LE STOCK
# ============================================================

STOCK_ENDPOINT = (
    "https://script.google.com/macros/s/"
    "AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/"
    "exec"
)

# ============================================================
# DISCORD
# ============================================================

DISCORD_WEBHOOK = "COLLE_TON_NOUVEAU_WEBHOOK_ICI"


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
        .main {
            background-color: #fff9fc;
        }

        h1, h2, h3 {
            color: #c2185b;
        }

        [data-testid="stSidebar"] {
            background-color: #fff0f6;
        }

        .produit {
            border: 1px solid #f3c6d9;
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: white;
        }

        .prix-promo {
            font-size: 24px;
            font-weight: bold;
            color: #c2185b;
        }

        .ancien-prix {
            color: #888;
            text-decoration: line-through;
        }

        .total-panier {
            font-size: 26px;
            font-weight: bold;
            color: #c2185b;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def normaliser_texte(texte):
    """Normalise un nom de colonne."""
    texte = str(texte).strip().lower()

    texte = unicodedata.normalize(
        "NFD",
        texte
    )

    texte = "".join(
        c for c in texte
        if unicodedata.category(c) != "Mn"
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


def convertir_nombre(valeur, valeur_defaut=0):
    """Convertit proprement un nombre venant de Google Sheets."""

    if pd.isna(valeur):
        return valeur_defaut

    texte = str(valeur).strip()

    if not texte:
        return valeur_defaut

    texte = texte.replace("€", "")
    texte = texte.replace(" ", "")
    texte = texte.replace(",", ".")

    try:
        return float(texte)
    except:
        return valeur_defaut


# ============================================================
# CHARGEMENT DES PRODUITS
# ============================================================

@st.cache_data(ttl=60)
def charger_produits():

    try:
        url_csv = GOOGLE_SHEET_URL.replace(
            "/edit?usp=sharing",
            "/export?format=csv"
        )

        df = pd.read_csv(url_csv)

    except Exception as erreur:

        st.error("❌ Impossible de charger le catalogue.")

        st.code(str(erreur))

        return pd.DataFrame()

    # --------------------------------------------------------
    # Recherche des colonnes
    # --------------------------------------------------------

    colonne_photo = trouver_colonne(
        df,
        [
            "photo produit",
            "photo",
            "image",
            "url photo",
            "url image"
        ]
    )

    colonne_nom = trouver_colonne(
        df,
        [
            "denomination",
            "denom",
            "produit",
            "nom",
            "nom produit"
        ]
    )

    colonne_categorie = trouver_colonne(
        df,
        [
            "categorie",
            "catégorie",
            "cat",
            "rayon"
        ]
    )

    colonne_format = trouver_colonne(
        df,
        [
            "litre / gramme",
            "litre/gramme",
            "format",
            "contenance",
            "poids"
        ]
    )

    colonne_stock = trouver_colonne(
        df,
        [
            "quantite",
            "quantité",
            "stock",
            "stock disponible"
        ]
    )

    colonne_prix_base = trouver_colonne(
        df,
        [
            "prix initial",
            "prix de base",
            "prix base",
            "initial",
            "prix"
        ]
    )

    colonne_prix_promo = trouver_colonne(
        df,
        [
            "prix promo",
            "prix promotion",
            "promo",
            "prix promotionnel"
        ]
    )

    if colonne_nom is None:

        st.error(
            "❌ Impossible de trouver la colonne du nom du produit."
        )

        return pd.DataFrame()

    # --------------------------------------------------------
    # Création du tableau standardisé
    # --------------------------------------------------------

    produits = pd.DataFrame()

    produits["Produit"] = df[colonne_nom].fillna("").astype(str).str.strip()

    if colonne_photo:
        produits["Photo"] = df[colonne_photo].fillna("").astype(str).str.strip()
    else:
        produits["Photo"] = ""

    if colonne_categorie:
        produits["Catégorie"] = (
            df[colonne_categorie]
            .fillna("Autre")
            .astype(str)
            .str.strip()
        )
    else:
        produits["Catégorie"] = "Autre"

    if colonne_format:
        produits["Format"] = (
            df[colonne_format]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        produits["Format"] = ""

    if colonne_stock:
        produits["Stock"] = df[colonne_stock].apply(convertir_nombre)
    else:
        produits["Stock"] = 0

    if colonne_prix_base:
        produits["Prix_base"] = df[colonne_prix_base].apply(convertir_nombre)
    else:
        produits["Prix_base"] = 0

    if colonne_prix_promo:
        produits["Prix_promo"] = df[colonne_prix_promo].apply(convertir_nombre)
    else:
        produits["Prix_promo"] = produits["Prix_base"]

    # --------------------------------------------------------
    # Prix final
    # --------------------------------------------------------

    produits["Prix"] = produits["Prix_promo"]

    produits.loc[
        produits["Prix"] <= 0,
        "Prix"
    ] = produits["Prix_base"]

    # Supprimer les lignes sans nom
    produits = produits[
        produits["Produit"].str.strip() != ""
    ]

    return produits.reset_index(drop=True)


# ============================================================
# DISCORD
# ============================================================

def envoyer_discord(message):

    try:

        if (
            not DISCORD_WEBHOOK
            or DISCORD_WEBHOOK == "COLLE_TON_NOUVEAU_WEBHOOK_ICI"
        ):

            st.error(
                "❌ Le webhook Discord n'est pas renseigné dans app.py."
            )

            return False

        reponse = requests.post(
            DISCORD_WEBHOOK,
            json={
                "content": message
            },
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
            st.code(reponse.text)

        return False

    except Exception as erreur:

        st.error(
            "❌ Impossible de contacter Discord."
        )

        st.code(str(erreur))

        return False


# ============================================================
# RETRAIT STOCK
# ============================================================

def retirer_stock(produit, quantite):

    try:

        payload = {
            "action": "retirer",
            "produit": produit,
            "quantite": quantite,
            "utilisateur": st.session_state.utilisateur
        }

        reponse = requests.post(
            STOCK_ENDPOINT,
            json=payload,
            timeout=20
        )

        if reponse.status_code != 200:

            st.error(
                "❌ Le stock n'a pas pu être mis à jour."
            )

            st.code(
                f"Code HTTP : {reponse.status_code}"
            )

            return False

        return True

    except Exception as erreur:

        st.error(
            "❌ Erreur lors de la mise à jour du stock."
        )

        st.code(str(erreur))

        return False


# ============================================================
# INITIALISATION SESSION
# ============================================================

if "connecte" not in st.session_state:
    st.session_state.connecte = False

if "utilisateur" not in st.session_state:
    st.session_state.utilisateur = ""

if "panier" not in st.session_state:
    st.session_state.panier = {}


# ============================================================
# CONNEXION
# ============================================================

if not st.session_state.connecte:

    st.title("🛍️ Mes Bons Plans de Sarah 🌸")

    st.markdown(
        "### Bienvenue !"
    )

    st.write(
        "Connecte-toi pour accéder aux bons plans."
    )

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col2:

        utilisateur = st.text_input(
            "👤 Utilisateur"
        )

        mot_de_passe = st.text_input(
            "🔑 Mot de passe",
            type="password"
        )

        if st.button(
            "💗 Se connecter",
            use_container_width=True
        ):

            utilisateur = utilisateur.strip().lower()

            if (
                utilisateur in COMPTES_AUTORISES
                and COMPTES_AUTORISES[utilisateur] == mot_de_passe
            ):

                st.session_state.connecte = True
                st.session_state.utilisateur = utilisateur

                st.success(
                    "Connexion réussie 💕"
                )

                st.rerun()

            else:

                st.error(
                    "❌ Identifiant ou mot de passe incorrect."
                )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🌸 Mes Bons Plans")

    st.success(
        f"Connecté : {st.session_state.utilisateur}"
    )

    st.divider()

    st.subheader("🔎 Recherche")

    recherche = st.text_input(
        "Rechercher un produit",
        placeholder="Ex : lait, chocolat..."
    )

    st.divider()

    st.subheader("📂 Catégorie")

    produits = charger_produits()

    if not produits.empty:

        categories = [
            "Toutes"
        ] + sorted(
            produits["Catégorie"]
            .dropna()
            .unique()
            .tolist()
        )

        categorie_selectionnee = st.selectbox(
            "Choisir une catégorie",
            categories
        )

    else:

        categorie_selectionnee = "Toutes"

    st.divider()

    # ========================================================
    # ESSENCE
    # ========================================================

    st.subheader("⛽ Calcul du déplacement")

    prix_essence = st.slider(
        "Prix de l'essence (€ / L)",
        min_value=1.20,
        max_value=2.50,
        value=1.80,
        step=0.01
    )

    consommation = st.slider(
        "Consommation du véhicule (L / 100 km)",
        min_value=3.0,
        max_value=15.0,
        value=6.0,
        step=0.1
    )

    distance_sidebar = st.number_input(
        "Distance totale (aller + retour)",
        min_value=0.0,
        max_value=1000.0,
        value=0.0,
        step=1.0
    )

    cout_essence = (
        distance_sidebar
        * consommation
        / 100
        * prix_essence
    )

    st.info(
        f"""
        ⛽ Coût estimé de l'essence

        **{cout_essence:.2f} €**

        Pour {distance_sidebar:.1f} km
        avec une consommation de
        {consommation:.1f} L/100 km
        à {prix_essence:.2f} €/L.
        """
    )

    st.divider()

    # ========================================================
    # CONDITIONS GÉNÉRALES
    # ========================================================

    with st.expander("📜 Conditions générales"):

        st.markdown(
            """
            **Prix affichés**

            Les prix indiqués dans l'application correspondent
            à des relevés effectués lors de promotions, à la
            date du relevé.

            Les prix des magasins peuvent évoluer et les
            promotions peuvent prendre fin.

            Le prix affiché dans l'application peut donc être
            différent du prix réellement pratiqué en magasin
            au moment de l'achat.

            **Stock**

            Les stocks sont donnés à titre indicatif et peuvent
            évoluer rapidement.

            **Livraison**

            • Panier inférieur à **30 €** :
              livraison à **0,10 €/km**

            • Panier de **30 € ou plus** :
              livraison **gratuite**

            La distance indiquée doit correspondre à la distance
            totale du trajet.

            **Déplacement**

            Le calcul de l'essence est une estimation basée sur
            le prix du carburant, la consommation du véhicule et
            la distance renseignée.

            Il ne constitue pas un calcul comptable exact du
            coût total du déplacement.
            """
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
# TITRE
# ============================================================

st.title("🛍️ Mes Bons Plans de Sarah 🌸")

st.caption(
    f"Bonjour {st.session_state.utilisateur} 💕"
)


# ============================================================
# FILTRAGE PRODUITS
# ============================================================

if produits.empty:

    st.warning(
        "⚠️ Aucun produit disponible."
    )

    st.stop()


produits_affiches = produits.copy()


if recherche:

    recherche_normalisee = normaliser_texte(
        recherche
    )

    produits_affiches = produits_affiches[
        produits_affiches["Produit"]
        .apply(
            lambda x:
            recherche_normalisee
            in normaliser_texte(x)
        )
    ]


if categorie_selectionnee != "Toutes":

    produits_affiches = produits_affiches[
        produits_affiches["Catégorie"]
        == categorie_selectionnee
    ]


# ============================================================
# AFFICHAGE PRODUITS
# ============================================================

st.subheader(
    f"🛒 {len(produits_affiches)} produit(s)"
)

if produits_affiches.empty:

    st.info(
        "Aucun produit ne correspond à ta recherche."
    )

else:

    colonnes = st.columns(3)

    for index, produit in produits_affiches.iterrows():

        with colonnes[index % 3]:

            st.markdown(
                '<div class="produit">',
                unsafe_allow_html=True
            )

            # ------------------------------------------------
            # PHOTO
            # ------------------------------------------------

            photo = produit["Photo"]

            if (
                photo
                and photo.lower() not in ["nan", "none"]
                and (
                    photo.startswith("http://")
                    or photo.startswith("https://")
                )
            ):

                try:

                    st.image(
                        photo,
                        use_container_width=True
                    )

                except:

                    st.write("🛍️")

            else:

                st.markdown(
                    "### 🛍️"
                )

            # ------------------------------------------------
            # NOM
            # ------------------------------------------------

            st.subheader(
                produit["Produit"]
            )

            # ------------------------------------------------
            # CATÉGORIE / FORMAT
            # ------------------------------------------------

            if produit["Catégorie"]:

                st.caption(
                    f"📂 {produit['Catégorie']}"
                )

            if produit["Format"]:

                st.caption(
                    f"📦 {produit['Format']}"
                )

            # ------------------------------------------------
            # STOCK
            # ------------------------------------------------

            stock = int(
                produit["Stock"]
            )

            if stock <= 0:

                st.error(
                    "❌ Rupture de stock"
                )

            else:

                st.success(
                    f"Disponible : {stock}"
                )

            # ------------------------------------------------
            # PRIX
            # ------------------------------------------------

            prix_base = float(
                produit["Prix_base"]
            )

            prix = float(
                produit["Prix"]
            )

            if (
                prix_base > prix
                and prix_base > 0
            ):

                st.markdown(
                    f"""
                    <span class="ancien-prix">
                    {prix_base:.2f} €
                    </span>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div class="prix-promo">
                    {prix:.2f} €
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    f"""
                    <div class="prix-promo">
                    {prix:.2f} €
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # ------------------------------------------------
            # QUANTITÉ
            # ------------------------------------------------

            if stock > 0:

                quantite = st.number_input(
                    "Quantité",
                    min_value=1,
                    max_value=stock,
                    value=1,
                    step=1,
                    key=f"quantite_{index}"
                )

                if st.button(
                    "🛒 Ajouter au panier",
                    key=f"ajouter_{index}",
                    use_container_width=True
                ):

                    nom = produit["Produit"]

                    if nom in st.session_state.panier:

                        nouvelle_quantite = (
                            st.session_state.panier[nom]["quantite"]
                            + quantite
                        )

                        if nouvelle_quantite <= stock:

                            st.session_state.panier[nom][
                                "quantite"
                            ] = nouvelle_quantite

                        else:

                            st.error(
                                f"Il ne reste que {stock} unité(s)."
                            )

                    else:

                        st.session_state.panier[nom] = {
                            "quantite": int(quantite),
                            "prix": prix
                        }

                    st.success(
                        "Produit ajouté 💕"
                    )

                    st.rerun()

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# ============================================================
# PANIER
# ============================================================

st.divider()

st.header("🛒 Mon panier")

panier = st.session_state.panier


if not panier:

    st.info(
        "Ton panier est vide."
    )

else:

    sous_total = 0

    for nom, article in list(panier.items()):

        quantite = article["quantite"]
        prix_unitaire = article["prix"]

        total_article = (
            quantite
            * prix_unitaire
        )

        sous_total += total_article

        col1, col2, col3, col4 = st.columns(
            [4, 1, 2, 1]
        )

        with col1:

            st.write(
                f"**{nom}**"
            )

        with col2:

            st.write(
                f"x {quantite}"
            )

        with col3:

            st.write(
                f"{total_article:.2f} €"
            )

        with col4:

            if st.button(
                "🗑️",
                key=f"supprimer_{nom}"
            ):

                del st.session_state.panier[nom]

                st.rerun()


    # ========================================================
    # SOUS TOTAL
    # ========================================================

    st.markdown(
        f"### 💰 Sous-total : {sous_total:.2f} €"
    )

    # ========================================================
    # LIVRAISON
    # ========================================================

    st.subheader("🚚 Mode de remise")

    mode = st.radio(
        "Choisir une option",
        [
            "Retrait / remise en main propre",
            "Livraison"
        ],
        horizontal=True
    )

    frais_livraison = 0.0
    distance_livraison = 0.0

    if mode == "Livraison":

        distance_livraison = st.number_input(
            "📍 Distance totale du trajet (km)",
            min_value=0.0,
            max_value=1000.0,
            value=0.0,
            step=1.0
        )

        if sous_total < 30:

            frais_livraison = (
                distance_livraison
                * 0.10
            )

            st.info(
                "Panier inférieur à 30 € : "
                "0,10 €/km."
            )

        else:

            frais_livraison = 0.0

            st.success(
                "🎉 Panier de 30 € ou plus : "
                "livraison gratuite !"
            )

    # ========================================================
    # CALCUL ESSENCE
    # ========================================================

    cout_essence_commande = 0.0

    if mode == "Livraison":

        cout_essence_commande = (
            distance_livraison
            * consommation
            / 100
            * prix_essence
        )

        st.info(
            f"""
            ⛽ Coût d'essence estimé :
            **{cout_essence_commande:.2f} €**

            🚚 Frais de livraison facturés :
            **{frais_livraison:.2f} €**
            """
        )

        rentabilite_deplacement = (
            frais_livraison
            - cout_essence_commande
        )

        if rentabilite_deplacement > 0:

            st.success(
                f"📈 Après l'essence, il reste "
                f"environ **{rentabilite_deplacement:.2f} €** "
                f"sur les frais de livraison."
            )

        elif rentabilite_deplacement < 0:

            st.warning(
                f"📉 L'essence coûte environ "
                f"**{abs(rentabilite_deplacement):.2f} €** "
                f"de plus que les frais de livraison."
            )

        else:

            st.info(
                "⚖️ Les frais de livraison couvrent "
                "environ le coût d'essence."
            )

    # ========================================================
    # TOTAL
    # ========================================================

    total_commande = (
        sous_total
        + frais_livraison
    )

    st.markdown(
        f"""
        <div class="total-panier">
        💳 TOTAL : {total_commande:.2f} €
        </div>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # COMMANDER
    # ========================================================

    st.divider()

    if st.button(
        "✅ Valider ma commande",
        use_container_width=True,
        type="primary"
    ):

        # ----------------------------------------------------
        # Vérification stock avant validation
        # ----------------------------------------------------

        stock_ok = True

        for nom, article in panier.items():

            ligne = produits[
                produits["Produit"] == nom
            ]

            if ligne.empty:

                st.error(
                    f"❌ Produit introuvable : {nom}"
                )

                stock_ok = False

                continue

            stock_actuel = int(
                ligne.iloc[0]["Stock"]
            )

            if article["quantite"] > stock_actuel:

                st.error(
                    f"❌ Stock insuffisant pour {nom}. "
                    f"Disponible : {stock_actuel}"
                )

                stock_ok = False

        # ----------------------------------------------------
        # Si tout est OK
        # ----------------------------------------------------

        if stock_ok:

            stock_tout_ok = True

            for nom, article in panier.items():

                succes = retirer_stock(
                    nom,
                    article["quantite"]
                )

                if not succes:

                    stock_tout_ok = False

            if stock_tout_ok:

                # ============================================
                # DATE
                # ============================================

                maintenant = datetime.now(
                    ZoneInfo("Europe/Paris")
                )

                date_commande = maintenant.strftime(
                    "%d/%m/%Y à %H:%M"
                )

                # ============================================
                # MESSAGE DISCORD
                # ============================================

                message = (
                    "🛒 **NOUVELLE COMMANDE !**\n\n"
                )

                message += (
                    f"👤 **Client :** "
                    f"{st.session_state.utilisateur}\n"
                )

                message += (
                    f"🕐 **Date :** "
                    f"{date_commande}\n\n"
                )

                message += "📦 **Produits :**\n"

                for nom, article in panier.items():

                    quantite = article["quantite"]
                    prix_unitaire = article["prix"]

                    total_article = (
                        quantite
                        * prix_unitaire
                    )

                    message += (
                        f"• {quantite} × {nom} — "
                        f"{prix_unitaire:.2f} € / unité "
                        f"= {total_article:.2f} €\n"
                    )

                message += "\n"

                message += (
                    f"💰 **Sous-total :** "
                    f"{sous_total:.2f} €\n"
                )

                if mode == "Livraison":

                    message += (
                        "🚚 **Livraison**\n"
                    )

                    message += (
                        f"📍 Distance : "
                        f"{distance_livraison:.1f} km\n"
                    )

                    message += (
                        f"💶 Frais : "
                        f"{frais_livraison:.2f} €\n"
                    )

                    message += (
                        f"⛽ Essence estimée : "
                        f"{cout_essence_commande:.2f} €\n"
                    )

                    message += (
                        f"⛽ Prix essence : "
                        f"{prix_essence:.2f} €/L\n"
                    )

                    message += (
                        f"🚗 Consommation : "
                        f"{consommation:.1f} L/100 km\n"
                    )

                else:

                    message += (
                        "🤝 **Retrait / remise en main propre**\n"
                    )

                message += "\n"

                message += (
                    f"💳 **TOTAL : "
                    f"{total_commande:.2f} €**"
                )

                # ============================================
                # ENVOI DISCORD
                # ============================================

                discord_ok = envoyer_discord(
                    message
                )

                # ============================================
                # FIN COMMANDE
                # ============================================

                st.session_state.panier = {}

                charger_produits.clear()

                st.balloons()

                if discord_ok:

                    st.success(
                        "🎉 Commande enregistrée ! "
                        "La notification Discord a bien été envoyée."
                    )

                else:

                    st.warning(
                        "⚠️ La commande est enregistrée, "
                        "mais la notification Discord "
                        "n'a pas pu être envoyée."
                    )

                st.rerun()