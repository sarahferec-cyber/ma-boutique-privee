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
# DISCORD
# ============================================================

DISCORD_WEBHOOK = "COLLE_TON_WEBHOOK_ICI"


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

APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/"
    "exec"
)


# ============================================================
# PARAMÈTRES LIVRAISON
# ============================================================

PRIX_LIVRAISON_KM = 0.10
SEUIL_LIVRAISON_GRATUITE = 30.00


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #fffafc;
    }

    h1, h2, h3 {
        color: #c2185b;
    }

    div.stButton > button {
        border-radius: 10px;
        font-weight: bold;
    }

    </style>
    """,
    unsafe_allow_html=True
)


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
# FONCTION NORMALISATION
# ============================================================

def normaliser_texte(texte):

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

    return texte


# ============================================================
# CONVERSION DES PRIX / QUANTITÉS
# ============================================================

def convertir_nombre(
    valeur,
    valeur_defaut=0.0
):

    try:

        if pd.isna(valeur):
            return valeur_defaut

        texte = str(valeur).strip()

        if not texte:
            return valeur_defaut

        texte = texte.replace("€", "")
        texte = texte.replace(" ", "")
        texte = texte.replace(",", ".")

        return float(texte)

    except Exception:

        return valeur_defaut


# ============================================================
# RECHERCHE D'UNE COLONNE
# ============================================================

def trouver_colonne(
    colonnes,
    alias
):

    colonnes_normalisees = {
        normaliser_texte(colonne): colonne
        for colonne in colonnes
    }

    for nom in alias:

        nom_normalise = normaliser_texte(nom)

        if nom_normalise in colonnes_normalisees:

            return colonnes_normalisees[
                nom_normalise
            ]

    return None


# ============================================================
# CHARGEMENT GOOGLE SHEETS
# ============================================================

@st.cache_data(ttl=60)
def charger_produits():

    url_csv = GOOGLE_SHEET_URL.replace(
        "/edit?usp=sharing",
        "/export?format=csv"
    )

    dataframe = pd.read_csv(
        url_csv
    )

    dataframe.columns = [
        str(colonne).strip()
        for colonne in dataframe.columns
    ]


    # --------------------------------------------------------
    # COLONNES
    # --------------------------------------------------------

    colonne_photo = trouver_colonne(
        dataframe.columns,
        [
            "photo produit",
            "photo",
            "image",
            "url photo",
            "url image"
        ]
    )


    colonne_nom = trouver_colonne(
        dataframe.columns,
        [
            "denomination",
            "denom",
            "produit",
            "nom",
            "nom produit"
        ]
    )


    colonne_categorie = trouver_colonne(
        dataframe.columns,
        [
            "categorie",
            "catégorie",
            "cat",
            "rayon"
        ]
    )


    colonne_format = trouver_colonne(
        dataframe.columns,
        [
            "litre / gramme",
            "litre/gramme",
            "format",
            "contenance",
            "poids"
        ]
    )


    colonne_stock = trouver_colonne(
        dataframe.columns,
        [
            "quantite",
            "quantité",
            "stock",
            "stock disponible"
        ]
    )


    colonne_prix_base = trouver_colonne(
        dataframe.columns,
        [
            "prix initial",
            "prix de base",
            "prix base",
            "initial",
            "prix"
        ]
    )


    colonne_prix_promo = trouver_colonne(
        dataframe.columns,
        [
            "prix promo",
            "prix promotion",
            "promo",
            "prix promotionnel"
        ]
    )


    if not colonne_nom:

        st.error(
            "❌ Impossible de trouver la colonne du nom du produit."
        )

        st.stop()


    # --------------------------------------------------------
    # NOUVEAU TABLEAU
    # --------------------------------------------------------

    produits = pd.DataFrame()


    produits["nom"] = (
        dataframe[colonne_nom]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    # --------------------------------------------------------
    # PHOTO
    # --------------------------------------------------------

    if colonne_photo:

        produits["photo"] = (
            dataframe[colonne_photo]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    else:

        produits["photo"] = ""


    # --------------------------------------------------------
    # CATÉGORIE
    # --------------------------------------------------------

    if colonne_categorie:

        produits["categorie"] = (
            dataframe[colonne_categorie]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    else:

        produits["categorie"] = ""


    # --------------------------------------------------------
    # FORMAT
    # --------------------------------------------------------

    if colonne_format:

        produits["format"] = (
            dataframe[colonne_format]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    else:

        produits["format"] = ""


    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    if colonne_stock:

        produits["stock"] = (
            dataframe[colonne_stock]
            .apply(convertir_nombre)
            .astype(int)
        )

    else:

        produits["stock"] = 0


    # --------------------------------------------------------
    # PRIX NORMAL
    # --------------------------------------------------------

    if colonne_prix_base:

        produits["prix_base"] = (
            dataframe[colonne_prix_base]
            .apply(convertir_nombre)
        )

    else:

        produits["prix_base"] = 0.0


    # --------------------------------------------------------
    # PRIX PROMO
    # --------------------------------------------------------

    if colonne_prix_promo:

        produits["prix_promo"] = (
            dataframe[colonne_prix_promo]
            .apply(
                lambda valeur:
                    convertir_nombre(
                        valeur,
                        0.0
                    )
            )
        )

    else:

        produits["prix_promo"] = 0.0


    # --------------------------------------------------------
    # PRIX FINAL
    # --------------------------------------------------------

    produits["prix"] = produits.apply(
        lambda ligne:
            ligne["prix_promo"]
            if ligne["prix_promo"] > 0
            else ligne["prix_base"],
        axis=1
    )


    # --------------------------------------------------------
    # SUPPRESSION DES LIGNES VIDES
    # --------------------------------------------------------

    produits = produits[
        produits["nom"].str.strip() != ""
    ]


    return produits.reset_index(
        drop=True
    )


# ============================================================
# ENVOYER NOTIFICATION DISCORD
# ============================================================

def envoyer_discord(message):

    try:

        if not DISCORD_WEBHOOK:

            st.error(
                "❌ Le webhook Discord n'est pas renseigné."
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


# ============================================================
# RETIRER DU STOCK
# ============================================================

def retirer_stock(
    produit,
    quantite
):

    try:

        donnees = {
            "action": "retirer",
            "produit": produit,
            "quantite": quantite,
            "utilisateur": st.session_state.utilisateur
        }


        reponse = requests.post(
            APPS_SCRIPT_URL,
            json=donnees,
            timeout=20
        )


        if reponse.status_code != 200:

            st.error(
                "❌ Le serveur de stock a refusé la commande."
            )

            st.code(
                f"Code HTTP : {reponse.status_code}"
            )

            return False


        try:

            resultat = reponse.json()


            if isinstance(
                resultat,
                dict
            ):

                if resultat.get(
                    "success"
                ) is False:

                    st.error(
                        resultat.get(
                            "message",
                            "Le stock n'a pas pu être modifié."
                        )
                    )

                    return False

        except Exception:

            pass


        return True


    except Exception as erreur:

        st.error(
            "❌ Impossible de contacter le serveur de stock."
        )

        st.code(
            str(erreur)
        )

        return False


# ============================================================
# PAGE DE CONNEXION
# ============================================================

def afficher_connexion():

    st.title(
        "🛍️ Mes Bons Plans de Sarah 🌸"
    )

    st.subheader(
        "🔐 Connexion"
    )


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

        utilisateur_propre = (
            utilisateur
            .strip()
            .lower()
        )


        mot_de_passe_attendu = (
            COMPTES_AUTORISES.get(
                utilisateur_propre
            )
        )


        if (
            mot_de_passe_attendu
            and mot_de_passe == mot_de_passe_attendu
        ):

            st.session_state.connecte = True

            st.session_state.utilisateur = (
                utilisateur_propre
            )

            st.success(
                "✅ Connexion réussie !"
            )

            st.rerun()


        else:

            st.error(
                "❌ Identifiant ou mot de passe incorrect."
            )


# ============================================================
# AFFICHER CONNEXION SI PAS CONNECTÉ
# ============================================================

if not st.session_state.connecte:

    afficher_connexion()

    st.stop()


# ============================================================
# EN-TÊTE APPLICATION
# ============================================================

colonne_titre, colonne_deconnexion = st.columns(
    [4, 1]
)


with colonne_titre:

    st.title(
        "🛍️ Mes Bons Plans de Sarah 🌸"
    )

    st.caption(
        "Connecté en tant que : "
        f"**{st.session_state.utilisateur}**"
    )


with colonne_deconnexion:

    if st.button(
        "🚪 Déconnexion",
        use_container_width=True
    ):

        st.session_state.connecte = False

        st.session_state.utilisateur = ""

        st.session_state.panier = {}

        st.rerun()


# ============================================================
# CHARGEMENT PRODUITS
# ============================================================

produits = charger_produits()


if produits.empty:

    st.warning(
        "Aucun produit disponible actuellement."
    )

    st.stop()


# ============================================================
# RECHERCHE
# ============================================================

st.subheader(
    "🔎 Rechercher un produit"
)


recherche = st.text_input(
    "Recherche",
    placeholder="Ex : lait, chocolat, lessive..."
)


# ============================================================
# CATÉGORIES
# ============================================================

categories = sorted(
    [
        categorie
        for categorie
        in produits["categorie"].dropna().unique()
        if str(categorie).strip()
    ]
)


categorie_selectionnee = st.selectbox(
    "Catégorie",
    ["Toutes"] + categories
)


# ============================================================
# FILTRAGE
# ============================================================

produits_affiches = produits.copy()


if recherche.strip():

    recherche_normalisee = normaliser_texte(
        recherche
    )


    produits_affiches = produits_affiches[
        produits_affiches["nom"].apply(
            lambda nom:
                recherche_normalisee
                in normaliser_texte(
                    nom
                )
        )
    ]


if categorie_selectionnee != "Toutes":

    produits_affiches = produits_affiches[
        produits_affiches["categorie"]
        == categorie_selectionnee
    ]


# ============================================================
# AFFICHAGE PRODUITS
# ============================================================

st.subheader(
    f"🛒 Produits disponibles : "
    f"{len(produits_affiches)}"
)


for _, produit in produits_affiches.iterrows():

    nom = produit["nom"]

    prix = float(
        produit["prix"]
    )

    stock = int(
        produit["stock"]
    )


    colonne_photo, colonne_infos = st.columns(
        [1, 2]
    )


    # --------------------------------------------------------
    # PHOTO
    # --------------------------------------------------------

    with colonne_photo:

        if produit["photo"]:

            try:

                st.image(
                    produit["photo"],
                    use_container_width=True
                )

            except Exception:

                st.info(
                    "📷 Photo indisponible"
                )

        else:

            st.info(
                "📷 Pas de photo"
            )


    # --------------------------------------------------------
    # INFORMATIONS PRODUIT
    # --------------------------------------------------------

    with colonne_infos:

        st.subheader(
            nom
        )


        if produit["categorie"]:

            st.caption(
                f"Catégorie : "
                f"{produit['categorie']}"
            )


        if produit["format"]:

            st.caption(
                f"Format : "
                f"{produit['format']}"
            )


        # ----------------------------------------------------
        # PRIX PROMO
        # ----------------------------------------------------

        if (
            produit["prix_promo"] > 0
            and
            produit["prix_base"]
            >
            produit["prix_promo"]
        ):

            st.markdown(
                f"~~{produit['prix_base']:.2f} €~~ "
                f"**{produit['prix_promo']:.2f} €**"
            )

        else:

            st.markdown(
                f"**{prix:.2f} €**"
            )


        # ----------------------------------------------------
        # STOCK
        # ----------------------------------------------------

        if stock <= 0:

            st.error(
                "❌ Rupture de stock"
            )

        else:

            st.success(
                f"Disponible : {stock}"
            )


            quantite = st.number_input(
                "Quantité",
                min_value=1,
                max_value=stock,
                value=1,
                step=1,
                key=f"quantite_{nom}"
            )


            if st.button(
                "🛒 Ajouter au panier",
                key=f"ajouter_{nom}",
                use_container_width=True
            ):

                quantite_deja = (
                    st.session_state.panier
                    .get(
                        nom,
                        {}
                    )
                    .get(
                        "quantite",
                        0
                    )
                )


                nouvelle_quantite = (
                    quantite_deja
                    + quantite
                )


                if nouvelle_quantite > stock:

                    st.error(
                        "❌ Quantité supérieure "
                        "au stock disponible."
                    )

                else:

                    st.session_state.panier[nom] = {
                        "quantite": nouvelle_quantite,
                        "prix": prix
                    }


                    st.success(
                        f"✅ {quantite} × "
                        f"{nom} ajouté au panier."
                    )


    st.divider()


# ============================================================
# PANIER
# ============================================================

st.subheader(
    "🛒 Mon panier"
)


if not st.session_state.panier:

    st.info(
        "Ton panier est vide."
    )


else:

    sous_total = 0.0


    # --------------------------------------------------------
    # ARTICLES
    # --------------------------------------------------------

    for nom, article in list(
        st.session_state.panier.items()
    ):

        quantite = int(
            article["quantite"]
        )

        prix = float(
            article["prix"]
        )

        total_article = (
            quantite * prix
        )


        sous_total += total_article


        colonne_nom, colonne_quantite, colonne_total, colonne_supprimer = st.columns(
            [4, 1, 2, 1]
        )


        with colonne_nom:

            st.write(
                nom
            )


        with colonne_quantite:

            st.write(
                f"x{quantite}"
            )


        with colonne_total:

            st.write(
                f"{total_article:.2f} €"
            )


        with colonne_supprimer:

            if st.button(
                "🗑️",
                key=f"supprimer_{nom}"
            ):

                del st.session_state.panier[
                    nom
                ]

                st.rerun()


    st.markdown(
        f"### Sous-total produits : "
        f"{sous_total:.2f} €"
    )


    # ========================================================
    # MODE DE RÉCEPTION
    # ========================================================

    mode_reception = st.radio(
        "Mode de réception",
        [
            "Retrait / remise en main propre",
            "Livraison"
        ]
    )


    frais_livraison = 0.0

    distance_km = 0.0


    # ========================================================
    # LIVRAISON
    # ========================================================

    if mode_reception == "Livraison":

        distance_km = st.number_input(
            "Distance de livraison (km)",
            min_value=0.0,
            value=0.0,
            step=1.0
        )


        if sous_total >= SEUIL_LIVRAISON_GRATUITE:

            frais_livraison = 0.0


            st.success(
                "🎉 Livraison gratuite ! "
                "Commande de 30 € ou plus."
            )


        else:

            frais_livraison = (
                distance_km
                * PRIX_LIVRAISON_KM
            )


            st.info(
                f"🚚 {distance_km:.1f} km × "
                f"{PRIX_LIVRAISON_KM:.2f} €/km = "
                f"{frais_livraison:.2f} €"
            )


    # ========================================================
    # TOTAL
    # ========================================================

    total_commande = (
        sous_total
        + frais_livraison
    )


    st.markdown(
        f"## 💰 Total : "
        f"{total_commande:.2f} €"
    )


    # ========================================================
    # VALIDATION
    # ========================================================

    if st.button(
        "✅ Valider ma commande",
        use_container_width=True
    ):

        # ----------------------------------------------------
        # DISTANCE OBLIGATOIRE POUR LIVRAISON
        # ----------------------------------------------------

        if (
            mode_reception == "Livraison"
            and
            sous_total < SEUIL_LIVRAISON_GRATUITE
            and
            distance_km <= 0
        ):

            st.error(
                "❌ Indique la distance de livraison."
            )

        else:

            # ------------------------------------------------
            # RECHARGEMENT DU STOCK
            # ------------------------------------------------

            produits_actuels = charger_produits()


            stock_ok = True


            for nom, article in (
                st.session_state.panier.items()
            ):

                ligne = produits_actuels[
                    produits_actuels["nom"]
                    == nom
                ]


                if ligne.empty:

                    st.error(
                        f"❌ Produit introuvable : "
                        f"{nom}"
                    )

                    stock_ok = False

                    break


                stock_disponible = int(
                    ligne.iloc[0]["stock"]
                )


                if (
                    article["quantite"]
                    >
                    stock_disponible
                ):

                    st.error(
                        f"❌ Stock insuffisant pour "
                        f"{nom}. "
                        f"Stock disponible : "
                        f"{stock_disponible}"
                    )

                    stock_ok = False

                    break


            # ------------------------------------------------
            # TRAITEMENT COMMANDE
            # ------------------------------------------------

            if stock_ok:

                commande_ok = True


                # ------------------------------------------------
                # RETIRER LES PRODUITS DU STOCK
                # ------------------------------------------------

                for nom, article in (
                    st.session_state.panier.items()
                ):

                    succes_stock = retirer_stock(
                        nom,
                        article["quantite"]
                    )


                    if not succes_stock:

                        commande_ok = False

                        break


                # ------------------------------------------------
                # NOTIFICATION DISCORD
                # ------------------------------------------------

                if commande_ok:

                    maintenant = datetime.now(
                        ZoneInfo(
                            "Europe/Paris"
                        )
                    )


                    lignes_produits = []


                    for nom, article in (
                        st.session_state.panier.items()
                    ):

                        quantite = int(
                            article["quantite"]
                        )

                        prix = float(
                            article["prix"]
                        )

                        total_article = (
                            quantite * prix
                        )


                        lignes_produits.append(
                            f"• {quantite} × "
                            f"{nom} — "
                            f"{prix:.2f} € / unité "
                            f"= {total_article:.2f} €"
                        )


                    produits_discord = "\n".join(
                        lignes_produits
                    )


                    if (
                        mode_reception
                        == "Livraison"
                    ):

                        livraison_discord = (
                            "🚚 Livraison\n"
                            f"Distance : "
                            f"{distance_km:.1f} km\n"
                            f"Frais : "
                            f"{frais_livraison:.2f} €"
                        )

                    else:

                        livraison_discord = (
                            "🤝 Retrait / remise "
                            "en main propre\n"
                            "Frais : 0.00 €"
                        )


                    message_discord = (
                        "🛒 **NOUVELLE COMMANDE !**\n\n"

                        f"👤 Client : "
                        f"{st.session_state.utilisateur}\n"

                        f"🕐 Date : "
                        f"{maintenant.strftime('%d/%m/%Y à %H:%M')}\n\n"

                        "📦 **Produits :**\n"

                        f"{produits_discord}\n\n"

                        f"💰 Sous-total : "
                        f"{sous_total:.2f} €\n"

                        f"{livraison_discord}\n\n"

                        f"💳 **TOTAL : "
                        f"{total_commande:.2f} €**"
                    )


                    discord_ok = envoyer_discord(
                        message_discord
                    )


                    # ------------------------------------------------
                    # VIDER LE PANIER
                    # ------------------------------------------------

                    st.session_state.panier = {}


                    # ------------------------------------------------
                    # ACTUALISER GOOGLE SHEETS
                    # ------------------------------------------------

                    charger_produits.clear()


                    # ------------------------------------------------
                    # MESSAGE
                    # ------------------------------------------------

                    if discord_ok:

                        st.success(
                            "✅ Commande enregistrée "
                            "et notification Discord envoyée !"
                        )

                    else:

                        st.warning(
                            "⚠️ La commande est enregistrée, "
                            "mais la notification Discord "
                            "n'a pas pu être envoyée."
                        )


                    # ------------------------------------------------
                    # BALLOONS
                    # ------------------------------------------------

                    st.balloons()


                    st.rerun()


# ============================================================
# CONDITIONS GÉNÉRALES
# ============================================================

st.divider()

st.subheader(
    "📜 Conditions générales"
)


st.markdown(
    """
    **Prix :** les prix affichés correspondent à des relevés de prix
    effectués pendant des promotions, à la date du relevé.

    Les prix pratiqués en magasin peuvent évoluer et les promotions
    peuvent prendre fin à tout moment. Le prix affiché dans cette
    application peut donc ne plus correspondre au prix actuellement
    pratiqué en magasin.

    L'utilisateur de cette application ne peut pas être tenu
    responsable d'une modification ultérieure des prix par le magasin.

    **Stocks :** les disponibilités peuvent également évoluer et un
    produit peut devenir indisponible entre le relevé et la commande.

    **Livraison :** lorsque le montant des produits est inférieur à
    30 €, la livraison est facturée 0,10 € par kilomètre.

    À partir de 30 € de produits, la livraison est gratuite.

    **Commande :** une commande est enregistrée lorsque le traitement
    du stock a été effectué par l'application.
    """
)