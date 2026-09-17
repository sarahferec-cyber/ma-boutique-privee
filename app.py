import streamlit as st
import pandas as pd
import requests
import io
import time
import html
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
    min-height: 250px;
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
    """
    Transforme proprement une valeur en nombre.
    Accepte par exemple :
    12
    12.50
    12,50
    12,50 €
    """
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
    """
    Transforme proprement une valeur en entier.
    """
    try:
        nombre = convertir_float(valeur, valeur_defaut)
        return int(nombre)
    except (ValueError, TypeError):
        return valeur_defaut
def envoyer_discord(message):
    """
    Envoie un message sur Discord si le webhook
    est configuré dans st.secrets.
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
    Charge le Google Sheets au format CSV
    et nettoie les noms de colonnes.
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
        # --------------------------------------------------------
        # Nettoyage des noms de colonnes
        # --------------------------------------------------------
        data.columns = [
            str(c).strip().lower()
            for c in data.columns
        ]
        # Normalisation des accents
        remplacements_accents = {
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
        for ancien, nouveau in remplacements_accents.items():
            data.columns = data.columns.str.replace(
                ancien,
                nouveau,
                regex=False
            )
        # Nettoyage supplémentaire
        data.columns = (
            data.columns
            .str.replace("\n", " ", regex=False)
            .str.replace("  ", " ", regex=False)
            .str.strip()
        )
        # --------------------------------------------------------
        # Nettoyage du contenu
        # --------------------------------------------------------
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
    Retourne la première colonne trouvée
    parmi plusieurs noms possibles.
    """
    for nom in noms_possibles:
        if nom in dataframe.columns:
            return nom
    return None
def echapper_html(valeur):
    """
    Sécurise les textes affichés dans du HTML.
    """
    return html.escape(str(valeur))
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
    st.write(
        "Bienvenue dans votre espace privé 🛍️"
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
    ])
# ============================================================
# 12. VÉRIFICATION DES COLONNES OBLIGATOIRES
# ============================================================
colonnes_manquantes = []
if col_nom is None:
    colonnes_manquantes.append("Denomination / Produit")
if col_stock is None:
    colonnes_manquantes.append("Quantité / Stock")
if col_pinit is None:
    colonnes_manquantes.append("Prix initial")
if col_ppromo is None:
    colonnes_manquantes.append("Prix promo")
if colonnes_manquantes:
    st.error(
        "❌ Certaines colonnes obligatoires sont absentes "
        "du Google Sheets."
    )
    st.write(
        "Colonnes manquantes :"
    )
    for colonne in colonnes_manquantes:
        st.write(f"- **{colonne}**")
    st.write(
        "Colonnes actuellement détectées :"
    )
    st.code(
        ", ".join(df.columns.tolist())
    )
    st.stop()
# ============================================================
# 13. BARRE LATÉRALE : FILTRES
# ============================================================
st.sidebar.header(
    "🎯 Filtres de recherche"
)
if col_cat is not None:
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
# 14. FILTRAGE DU CATALOGUE
# ============================================================
if (
    categorie_choisie == "Toutes"
    or col_cat is None
):
    df_filtre = df.copy()
else:
    df_filtre = df[
        df[col_cat].astype(str).str.strip()
        == categorie_choisie
    ].copy()
# ============================================================
# 15. PANIER
# ============================================================
st.sidebar.markdown("---")
st.sidebar.header(
    "🛒 Votre Panier"
)
if not st.session_state.panier:
    st.sidebar.info(
        "Votre panier est vide pour le moment. ✨"
    )
else:
    total_panier = 0.0
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
        total_panier += sous_total
        st.sidebar.markdown(
            f"**{echapper_html(nom_art)}**",
            unsafe_allow_html=True
        )
        st.sidebar.caption(
            f"Qté : {quantite} × "
            f"{prix:.2f} € = "
            f"**{sous_total:.2f} €**"
        )
        if st.sidebar.button(
            "🗑️ Retirer",
            key=f"del_{nom_art}"
        ):
            articles_a_supprimer.append(
                nom_art
            )
    # --------------------------------------------------------
    # Suppression des articles
    # --------------------------------------------------------
    if articles_a_supprimer:
        for article in articles_a_supprimer:
            if article in st.session_state.panier:
                del st.session_state.panier[article]
        st.rerun()
    # --------------------------------------------------------
    # Total
    # --------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader(
        f"Total : {total_panier:.2f} €"
    )
    # --------------------------------------------------------
    # Validation de commande
    # --------------------------------------------------------
    if st.sidebar.button(
        "✅ Valider ma commande",
        key="bouton_validation_panier"
    ):
        with st.spinner(
            "Prise en compte de votre commande en cours..."
        ):
            succes_total = True
            details_commande_discord = []
            # --------------------------------------------
            # Vérification du panier
            # --------------------------------------------
            panier_a_traiter = dict(
                st.session_state.panier
            )
            for nom_art, details_art in panier_a_traiter.items():
                quantite = convertir_int(
                    details_art.get("quantite", 0)
                )
                prix = convertir_float(
                    details_art.get("prix", 0)
                )
                if quantite <= 0:
                    succes_total = False
                    break
                payload = {
                    "action": "retirer",
                    "produit": nom_art,
                    "quantite": quantite,
                    "utilisateur": st.session_state.utilisateur
                }
                try:
                    res = requests.post(
                        URL_MACRO_STOCK,
                        json=payload,
                        timeout=10
                    )
                    if res.status_code != 200:
                        succes_total = False
                        break
                    details_commande_discord.append(
                        f"- {quantite}x "
                        f"{nom_art} "
                        f"({prix:.2f}€/u)"
                    )
                except Exception:
                    succes_total = False
                    break
            # --------------------------------------------
            # Résultat de la commande
            # --------------------------------------------
            if succes_total:
                msg_discord = (
                    f"🎉 **Nouvelle commande de "
                    f"{st.session_state.utilisateur.capitalize()} !**\n\n"
                    + "\n".join(
                        details_commande_discord
                    )
                    + f"\n\n💰 **Total : "
                    f"{total_panier:.2f} €**"
                )
                envoyer_discord(
                    msg_discord
                )
                st.session_state.panier = {}
                st.session_state.achat_reussi = True
                st.rerun()
            else:
                st.error(
                    "❌ Une erreur est survenue lors "
                    "de la mise à jour des stocks. "
                    "Votre panier n'a pas été vidé."
                )
# ============================================================
# 16. MESSAGE DE COMMANDE RÉUSSIE
# ============================================================
if st.session_state.achat_reussi:
    st.success(
        "🎉 Félicitations ! "
        "Votre commande a bien été enregistrée."
    )
    st.session_state.achat_reussi = False
# ============================================================
# 17. TITRE DU CATALOGUE
# ============================================================
st.markdown("---")
st.subheader(
    "🛍️ Nos produits disponibles"
)
st.caption(
    f"{len(df_filtre)} produit(s) trouvé(s)"
)
# ============================================================
# 18. AFFICHAGE DES PRODUITS
# ============================================================
colonnes_produits = st.columns(3)
produits_affiches = 0
for index, row in df_filtre.iterrows():
    # --------------------------------------------------------
    # Nom du produit
    # --------------------------------------------------------
    nom_produit = str(
        row[col_nom]
    ).strip()
    if (
        not nom_produit
        or nom_produit.lower()
        in ["nan", "none"]
    ):
        continue
    # --------------------------------------------------------
    # Stock
    # --------------------------------------------------------
    stock_actuel = convertir_int(
        row[col_stock]
    )
    if stock_actuel <= 0:
        continue
    # --------------------------------------------------------
    # Prix
    # --------------------------------------------------------
    px_base = convertir_float(
        row[col_pinit]
    )
    px_promo = convertir_float(
        row[col_ppromo]
    )
    # Si aucun prix promo valide n'est fourni,
    # on utilise le prix initial.
    if px_promo <= 0:
        px_promo = px_base
    # --------------------------------------------------------
    # Pourcentage de remise
    # --------------------------------------------------------
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
    # Colonne d'affichage
    # --------------------------------------------------------
    col_courante = colonnes_produits[
        produits_affiches % 3
    ]
    produits_affiches += 1
    # --------------------------------------------------------
    # Informations produit
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
    # Photo
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
    # HTML sécurisé
    # --------------------------------------------------------
    nom_html = echapper_html(
        nom_produit
    )
    format_html = echapper_html(
        format_produit
    )
    # --------------------------------------------------------
    # Carte produit
    # --------------------------------------------------------
    with col_courante:
        # Photo si disponible
        if photo_url:
            try:
                st.image(
                    photo_url,
                    use_container_width=True
                )
            except Exception:
                pass
        # Badge promo
        if pourcentage_remise > 0:
            texte_promo_html = f"""
            <div style="
                background-color: #FF69B4;
                color: white;
                padding: 5px;
                border-radius: 10px;
                font-weight: bold;
                margin: 10px auto;
                width: fit-content;
                font-size: 14px;
            ">
                🔥 ÉCONOMIE : -{pourcentage_remise}%
            </div>
            """
        else:
            texte_promo_html = """
            <div style="
                margin: 10px 0;
                color: #757575;
                font-size: 13px;
                font-style: italic;
            ">
                Prix bas garanti ✨
            </div>
            """
        # Carte
        st.markdown(
            f"""
            <div class="product-card">
                <h3>{nom_html}</h3>
                <p style="
                    color: gray;
                    font-size: 14px;
                ">
                    📦 Format : {format_html}
                </p>
                <p style="
                    margin-top: 10px;
                    font-size: 18px;
                ">
                    <del style="
                        color: #FF4D4D;
                        font-size: 15px;
                    ">
                        {
                            f"{px_base:.2f} €"
                            if px_base > px_promo
                            else ""
                        }
                    </del>
                    <strong style="
                        color: #2E8B57;
                        font-size: 24px;
                        margin-left: 8px;
                    ">
                        {px_promo:.2f} €
                    </strong>
                </p>
                {texte_promo_html}
                <p style="
                    color: #C71585;
                    font-weight: bold;
                    margin-top: 10px;
                ">
                    📦 Disponibles :
                    {stock_actuel} restant(s)
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        # ----------------------------------------------------
        # Quantité
        # ----------------------------------------------------
        quantite_selectionnee = st.number_input(
            f"Quantité pour {nom_produit}",
            min_value=1,
            max_value=stock_actuel,
            value=1,
            step=1,
            key=f"input_{index}"
        )
        # ----------------------------------------------------
        # Quantité déjà présente dans le panier
        # ----------------------------------------------------
        quantite_deja_panier = 0
        if nom_produit in st.session_state.panier:
            quantite_deja_panier = convertir_int(
                st.session_state.panier[
                    nom_produit
                ].get("quantite", 0)
            )
        # ----------------------------------------------------
        # Bouton ajouter
        # ----------------------------------------------------
        if st.button(
            "🛒 Ajouter au panier",
            key=f"btn_{index}"
        ):
            nouvelle_quantite = (
                quantite_deja_panier
                + quantite_selectionnee
            )
            # --------------------------------------------
            # Vérification du stock
            # --------------------------------------------
            if nouvelle_quantite > stock_actuel:
                st.error(
                    "❌ Impossible d'ajouter cette "
                    "quantité : le stock disponible "
                    f"est de {stock_actuel}."
                )
            else:
                # ----------------------------------------
                # Ajout / mise à jour
                # ----------------------------------------
                st.session_state.panier[
                    nom_produit
                ] = {
                    "quantite": nouvelle_quantite,
                    "prix": px_promo
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
# 19. MESSAGE SI AUCUN PRODUIT DISPONIBLE
# ============================================================
if produits_affiches == 0:
    st.info(
        "😢 Aucun produit disponible "
        "dans cette catégorie pour le moment."
    )
# ============================================================
# 20. PIED DE PAGE
# ============================================================
st.markdown("---")
st.caption(
    "Application développée avec 🌸 pour "
    "Mes Bons Plans de Sarah. "
    "Tous droits réservés 2026."
)