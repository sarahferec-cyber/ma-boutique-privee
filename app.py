import streamlit as st

import pandas as pd

import requests

import re

import unicodedata

import json

import base64

 

# ============================================================

# CONFIGURATION ET CONSTANTES

# ============================================================

NOM_BOUTIQUE = "Mes Bons Plans de Sarah 🌸"

 

GOOGLE_SHEET_URL = (

    "https://docs.google.com/spreadsheets/d/"

    "1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit?usp=sharing"

)

 

STOCK_API_URL = (

    "https://script.google.com/macros/s/"

    "AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/exec"

)

 

# IMPORTANT :

# Dans Streamlit > Settings > Secrets, ajouter :

# DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1549946850885238865/OItwwHS0spEUH0vzmBSJjAaCXwx2Yicaz2l30EolaALbmEufafnZI36M5OsuT3FlNqt_"

DISCORD_WEBHOOK = st.secrets.get("DISCORD_WEBHOOK", "")

 

PRIX_CARBURANT = 1.80

 

# ============================================================

# CONFIGURATION INTERFACE STREAMLIT

# ============================================================

st.set_page_config(

    page_title=NOM_BOUTIQUE,

    page_icon="🌸",

    layout="wide"

)

 

# ============================================================

# FONCTIONS DE PERSISTANCE DU PANIER

# Le panier est encodé dans le paramètre ?panier= de l'URL.

# Il reste donc présent après un rechargement de la page.

# ============================================================

def encoder_panier(panier):

    try:

        brut = json.dumps(

            panier,

            ensure_ascii=False,

            separators=(",", ":")

        ).encode("utf-8")

        return base64.urlsafe_b64encode(brut).decode("ascii")

    except Exception:

        return ""

 

 

def decoder_panier(valeur):

    try:

        if not valeur:

            return []

        brut = base64.urlsafe_b64decode(valeur.encode("ascii"))

        panier = json.loads(brut.decode("utf-8"))

        if not isinstance(panier, list):

            return []

 

        panier_propre = []

        for produit in panier:

            if not isinstance(produit, dict):

                continue

 

            nom = str(produit.get("produit", "")).strip()

            quantite = int(produit.get("quantite", 0))

            prix = float(produit.get("prix", 0))

 

            if nom and quantite > 0 and prix >= 0:

                panier_propre.append({

                    "produit": nom,

                    "quantite": quantite,

                    "prix": prix

                })

 

        return panier_propre

    except Exception:

        return []

 

 

def sauvegarder_panier():

    if st.session_state.panier:

        st.query_params["panier"] = encoder_panier(st.session_state.panier)

    else:

        if "panier" in st.query_params:

            del st.query_params["panier"]

 

 

def vider_panier():

    st.session_state.panier = []

    sauvegarder_panier()

 

 

# ============================================================

# INITIALISATION ET PERSISTANCE DE LA SESSION

# ============================================================

if "panier" not in st.session_state:

    panier_url = st.query_params.get("panier", "")

    st.session_state.panier = decoder_panier(panier_url)

 

if "commande_envoyee" not in st.session_state:

    st.session_state.commande_envoyee = False

 

if "distance_ar" not in st.session_state:

    st.session_state.distance_ar = 50.0

 

if "prix_litre" not in st.session_state:

    st.session_state.prix_litre = PRIX_CARBURANT

 

 

# ============================================================

# FONCTIONS OUTILS ET NORMALISATION

# ============================================================

def normaliser_texte(texte):

    texte = str(texte)

    texte = unicodedata.normalize("NFD", texte)

    texte = "".join(

        caractere

        for caractere in texte

        if unicodedata.category(caractere) != "Mn"

    )

    texte = texte.lower()

    re_space = re.compile(r"\s+")

    texte = re_space.sub(" ", texte).strip()

    return texte

 

 

def trouver_colonne(article, noms_possibles):

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

    if valeur is None or pd.isna(valeur):

        return valeur_defaut

 

    if isinstance(valeur, (int, float)):

        return float(valeur)

 

    texte = str(valeur).strip()

 

    if not texte:

        return valeur_defaut

 

    texte = texte.replace("€", "").replace(" ", "")

 

    if "," in texte and "." in texte:

        if texte.rfind(",") > texte.rfind("."):

            texte = texte.replace(".", "").replace(",", ".")

        else:

            texte = texte.replace(",", "")

    else:

        texte = texte.replace(",", ".")

 

    try:

        return float(texte)

    except Exception:

        return valeur_defaut

 

 

# ============================================================

# LECTURE ET EXTRACTION DU GOOGLE SHEET

# ============================================================

def nom_produit(article):

    colonne = trouver_colonne(

        article,

        ["Denomination", "Dénomination", "Produit", "Nom", "Article"]

    )

    return (

        str(article.get(colonne, "Produit sans nom")).strip()

        if colonne

        else "Produit sans nom"

    )

 

 

def categorie_produit(article):

    colonne = trouver_colonne(

        article,

        ["Categorie", "Catégorie", "Catégorie produit", "Famille"]

    )

    valeur = article.get(colonne, "Autre") if colonne else "Autre"

    return (

        "Autre"

        if pd.isna(valeur) or str(valeur).strip() == ""

        else str(valeur).strip()

    )

 

 

def photo_produit(article):

    colonne = trouver_colonne(

        article,

        ["Photo produit", "Photo", "Image", "Photo produit URL"]

    )

    return (

        str(article.get(colonne, "")).strip()

        if colonne and not pd.isna(article.get(colonne))

        else ""

    )

 

 

def obtenir_stock(article):

    colonne = trouver_colonne(

        article,

        ["Quantité", "Quantite", "Stock", "Stocks"]

    )

    return (

        int(convertir_nombre(article.get(colonne, 0), 0))

        if colonne

        else 0

    )

 

 

def obtenir_prix(article):

    colonne = trouver_colonne(

        article,

        ["Prix initial", "Prix", "Prix normal", "Tarif"]

    )

    return (

        convertir_nombre(article.get(colonne, 0.0), 0.0)

        if colonne

        else 0.0

    )

 

 

def obtenir_prix_promo(article):

    colonne = trouver_colonne(

        article,

        ["Prix promo", "Promo", "Prix promotion", "Prix promotionnel"]

    )

 

    if colonne is None:

        return None

 

    valeur = article.get(colonne, "")

 

    if pd.isna(valeur) or str(valeur).strip() == "":

        return None

 

    prix = convertir_nombre(valeur, 0.0)

    return prix if prix > 0 else None

 

 

def format_produit(article):

    colonne = trouver_colonne(

        article,

        ["Litre / Gramme", "Litre/Gramme", "Format", "Poids", "Volume"]

    )

    return (

        str(article.get(colonne, "")).strip()

        if colonne and not pd.isna(article.get(colonne))

        else ""

    )

 

 

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

    return (

        str(article.get(colonne, "")).strip()

        if colonne and not pd.isna(article.get(colonne))

        else ""

    )

 

 

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

 

    dataframe = dataframe.dropna(how="all").reset_index(drop=True)

    return dataframe

 

 

# ============================================================

# LOGIQUE ET INTERACTIONS DU PANIER

# ============================================================

def ajouter_au_panier(article):

    nom = nom_produit(article)

    prix_normal = obtenir_prix(article)

    prix_promo = obtenir_prix_promo(article)

    prix_final = (

        prix_promo

        if prix_promo is not None

        else prix_normal

    )

 

    stock = obtenir_stock(article)

 

    for produit in st.session_state.panier:

        if produit["produit"] == nom:

            if produit["quantite"] < stock:

                produit["quantite"] += 1

                sauvegarder_panier()

            return

 

    if stock > 0:

        st.session_state.panier.append({

            "produit": nom,

            "quantite": 1,

            "prix": prix_final

        })

        sauvegarder_panier()

 

 

def supprimer_du_panier(index):

    if 0 <= index < len(st.session_state.panier):

        st.session_state.panier.pop(index)

        sauvegarder_panier()

 

 

# ============================================================

# TRANSMISSION DISCORD

# ============================================================

def envoyer_commande_discord(

    nom_client,

    adresse_livraison,

    panier,

    total_articles,

    total_general

):

    if not DISCORD_WEBHOOK:

        return False, (

            "Le webhook Discord n'est pas configuré dans "

            "les Secrets Streamlit."

        )

 

    lignes = []

 

    for produit in panier:

        sous_total = produit["quantite"] * produit["prix"]

        lignes.append(

            f"• {produit['produit']} × {produit['quantite']} "

            f"— {sous_total:.2f} €"

        )

 

    message = (

        "🌸 **NOUVELLE COMMANDE — Mes Bons Plans de Sarah**\n\n"

        f"👤 **Client :** {nom_client}\n"

        f"📍 **Adresse :** {adresse_livraison}\n\n"

        "🛒 **Produits :**\n"

        + "\n".join(lignes)

        + "\n\n"

        f"💰 TOTAL : **{total_general:.2f} €**"

    )

 

    try:

        reponse = requests.post(

            DISCORD_WEBHOOK,

            json={"content": message},

            timeout=15

        )

 

        if reponse.status_code in (200, 204):

            return True, ""

 

        return False, (

            f"Discord a répondu avec le code "

            f"{reponse.status_code}."

        )

 

    except Exception as erreur:

        return False, f"Erreur Discord : {erreur}"

 

 

# ============================================================

# RETRAIT DES PRODUITS DU STOCK

# ============================================================

def retirer_stock_commande(panier):
    payload = {
        "action": "retirer_commande",
        "produits": [
            {
                "produit": produit["produit"],
                "quantite": produit["quantite"]
            }
            for produit in panier
        ]
    }

    try:
        reponse = requests.post(
            STOCK_API_URL,
            json=payload,
            timeout=15
        )

        resultat = reponse.json()

        if resultat.get("success") is True:
            return True, []

        return False, [
            resultat.get(
                "message",
                "Erreur inconnue lors du retrait du stock."
            )
        ]

    except Exception as erreur:
        return False, [str(erreur)]
# ============================================================

# RENDU DU MENU LATÉRAL GAUCHE

# ============================================================

def afficher_sidebar_complete():

    st.sidebar.header(f"🌸 {NOM_BOUTIQUE}")

    st.sidebar.markdown("---")

 

    st.sidebar.subheader("🛒 Mon Espace Achat")

 

    nombre_articles = sum(

        produit["quantite"]

        for produit in st.session_state.panier

    )

 

    with st.sidebar.expander(

        f"💼 Votre Panier ({nombre_articles} articles)",

        expanded=True

    ):

        if not st.session_state.panier:

            st.info("Votre panier est vide 🌸")

 

        else:

            total_articles = 0.0

 

            for index, produit in enumerate(

                st.session_state.panier

            ):

                sous_total = (

                    produit["quantite"] * produit["prix"]

                )

                total_articles += sous_total

 

                st.markdown(f"**{produit['produit']}**")

 

                col_qte, col_prix, col_suppr = st.columns(3)

 

                with col_qte:

                    st.caption(

                        f"Qté : {produit['quantite']}"

                    )

 

                with col_prix:

                    st.caption(f"{sous_total:.2f} €")

 

                with col_suppr:

                    if st.button(

                        "❌",

                        key=f"suppr_{index}"

                    ):

                        supprimer_du_panier(index)

                        st.rerun()

 

                st.markdown("---")

 

            st.markdown(

                f"Sous-total articles : "

                f"**{total_articles:.2f} €**"

            )

 

            total_general = total_articles

            st.markdown(

                f"### Total : "

                f"**{total_general:.2f} €**"

            )

 

            st.markdown(

                "#### 📝 Informations de commande"

            )

 

            nom_client = st.text_input(

                "Votre Nom et Prénom",

                key="client_nom"

            )

 

            adresse_livraison = st.text_area(

                "Adresse (Aigues-Vives ou environs)",

                key="client_adresse"

            )

 

            if st.button(

                "🚀 Valider ma commande",

                use_container_width=True

            ):

                if (

                    nom_client.strip() == ""

                    or adresse_livraison.strip() == ""

                ):

                    st.error(

                        "Veuillez remplir votre nom et "

                        "votre adresse pour valider."

                    )

 

                else:

                    # Copie du panier avant toute opération.

                    panier_commande = [

                        produit.copy()

                        for produit

                        in st.session_state.panier

                    ]

 

                    # 1. On transmet d'abord la commande à Discord.

                    discord_ok, discord_erreur = (

                        envoyer_commande_discord(

                            nom_client.strip(),

                            adresse_livraison.strip(),

                            panier_commande,

                            total_articles,

                            total_general

                        )

                    )

 

                    if not discord_ok:

                        st.error(

                            "La commande n'a pas été validée : "

                            f"{discord_erreur}"

                        )

                        st.info(

                            "Le stock n'a pas été modifié et "

                            "le panier est conservé."

                        )

 

                    else:

                        # 2. Discord a reçu la commande :

                        # on retire alors les produits du stock.

                        stock_ok, erreurs_stock = (

                            retirer_stock_commande(

                                panier_commande

                            )

                        )

 

                        if stock_ok:

                            # 3. Tout est bon : on vide le panier.

                            st.session_state.commande_envoyee = True

                            vider_panier()

                            st.cache_data.clear()

 

                            st.success(

                                "Commande enregistrée et "

                                "transmise ! ✨"

                            )

                            st.balloons()

                            st.rerun()

 

                        else:

                            st.warning(

                                "La commande a bien été reçue "

                                "sur Discord, mais certains retraits "

                                "de stock ont échoué."

                            )

 

                            for erreur in erreurs_stock:

                                st.caption(f"• {erreur}")

 

                            st.info(

                                "Le panier est conservé pour éviter "

                                "de perdre les informations."

                            )

 

    st.sidebar.markdown("---")

 

    # ========================================================

    # INFORMATIONS CARBURANT

    # ========================================================

    st.sidebar.subheader("⛽ Carburant")

    with st.sidebar.expander(

        "📊 Kilomètres et prix de l'essence",

        expanded=False

    ):

        st.markdown(

            "*Ces valeurs restent mémorisées "

            "d'une page à l'autre.*"

        )

        st.session_state.distance_ar = st.number_input(

            "Distance Aller-Retour (km)",

            value=st.session_state.distance_ar,

            step=1.0

        )

        st.session_state.prix_litre = st.number_input(

            "Prix du litre de carburant (€)",

            value=st.session_state.prix_litre,

            step=0.01

        )


# ============================================================

# AFFICHAGE DE LA BOUTIQUE ET DU CATALOGUE PRINCIPAL

# ============================================================

afficher_sidebar_complete()

 

st.title(f"🏪 Bienvenue chez {NOM_BOUTIQUE}")

 

try:

    df_produits = charger_produits()

 

    if df_produits.empty:

        st.warning(

            "Aucun produit trouvé dans la base "

            "de données Google Sheets."

        )

 

    else:

        categories_disponibles = (

            ["Tous"]

            + sorted(

                list(

                    df_produits.apply(

                        categorie_produit,

                        axis=1

                    ).unique()

                )

            )

        )

 

        # ========================================================
        # RECHERCHE PRODUITS
        # ========================================================
        recherche = st.text_input(
            "🔎 Rechercher un produit :",
            placeholder="Ex. lessive, Xtra, shampoing..."
        )

        categorie_selectionnee = st.selectbox(

            "📁 Filtrer par rayon / catégorie :",

            categories_disponibles

        )

 

        if categorie_selectionnee != "Tous":

            df_filtre = df_produits[

                df_produits.apply(

                    categorie_produit,

                    axis=1

                )

                == categorie_selectionnee

            ]

        else:

            df_filtre = df_produits

 

        # Applique la recherche au catalogue déjà filtré par catégorie.
        # Recherche dans le nom, la catégorie et le format.
        if recherche.strip():
            recherche_normalisee = normaliser_texte(recherche)

            df_filtre = df_filtre[
                df_filtre.apply(
                    lambda article: (
                        recherche_normalisee in normaliser_texte(nom_produit(article))
                        or recherche_normalisee in normaliser_texte(categorie_produit(article))
                        or recherche_normalisee in normaliser_texte(format_produit(article))
                    ),
                    axis=1
                )
            ]

        if recherche.strip() and df_filtre.empty:
            st.info("🔎 Aucun produit ne correspond à votre recherche.")

        st.write(

            f"Catalogue synchronisé en direct : "

            f"{len(df_filtre)} articles disponibles."

        )

 

        st.markdown("---")

 

        colonnes_grille = st.columns(4)

 

        for index, row in (

            df_filtre.reset_index(drop=True).iterrows()

        ):

            colonne_cible = (

                colonnes_grille[index % 4]

            )

 

            with colonne_cible:

                lien_photo = photo_produit(row)

 

                if lien_photo:

                    st.image(

                        lien_photo,

                        use_container_width=True

                    )

                else:

                    st.image(

                        "https://via.placeholder.com/"

                        "150?text=Pas+de+photo",

                        use_container_width=True

                    )

 

                st.markdown(

                    f"**{nom_produit(row)}**"

                )

 

                st.caption(

                    f"Format : {format_produit(row)} "

                    f"| {prix_kg_litre(row)}"

                )

 

                prix_init = obtenir_prix(row)

 

                # Correction de l'erreur

                # "prix_pr = Petersen = ..."

                prix_pr = obtenir_prix_promo(row)

 

                stock_dispo = obtenir_stock(row)

 

                if prix_pr is not None:

                    st.markdown(

                        f"~~{prix_init:.2f} €~~ "

                        f"🔴 **PROMO : {prix_pr:.2f} €**"

                    )

                else:

                    st.markdown(

                        f"Prix : **{prix_init:.2f} €**"

                    )

 

                if stock_dispo <= 0:

                    st.error("🚫 Rupture de stock")

 

                else:

                    quantite_panier = 0

 

                    for produit_panier in (

                        st.session_state.panier

                    ):

                        if (

                            produit_panier["produit"]

                            == nom_produit(row)

                        ):

                            quantite_panier = (

                                produit_panier["quantite"]

                            )

                            break

 

                    stock_restant_affichable = max(

                        0,

                        stock_dispo - quantite_panier

                    )

 

                    st.caption(

                        f"Stock disponible : "

                        f"{stock_restant_affichable}"

                    )

 

                    bouton_desactive = (

                        quantite_panier >= stock_dispo

                    )

 

                    if st.button(

                        "➕ Ajouter",

                        key=f"add_{index}",

                        use_container_width=True,

                        disabled=bouton_desactive

                    ):

                        ajouter_au_panier(row)

 

                        st.toast(

                            f"Ajouté : "

                            f"{nom_produit(row)}"

                        )

 

                        st.rerun()

 

                st.markdown(

                    "<br>",

                    unsafe_allow_html=True

                )

 

except Exception as e:

    st.error(

        f"Erreur d'initialisation de la base produit : {e}"

    )
