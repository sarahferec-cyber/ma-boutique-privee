from pathlib import Path
import zipfile
import hashlib

base = Path("/mnt/data/la_boutique_des_bons_plans_v2")
base.mkdir(parents=True, exist_ok=True)
(base / ".streamlit").mkdir(exist_ok=True)

app = r'''import hashlib
import hmac
import re
import time
import unicodedata
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


# ============================================================
# IDENTITÉ
# ============================================================

NOM_BOUTIQUE = "LA boutique des bons plans"
NOM_AFFICHE = "Mes Bons Plans de Sarah 🌸"
EXPLOITANTE = "Sarah Ferec"
VILLE_AFFICHAGE = "Aigues-Vives, France"
EMAIL_CONTACT = "sarah.ferec@laposte.net"

SIREN = "À compléter"
SIRET = "À compléter"

PRIX_CARBURANT = 1.80
CONSOMMATION_L_100KM = 6.5

# Protection locale complémentaire : empêche un double clic / double
# envoi depuis la même session. La vraie protection contre deux clients
# simultanés DOIT être faite côté API/Apps Script.
DELAI_MINIMUM_ENTRE_COMMANDES_SECONDES = 30


# ============================================================
# SECRETS STREAMLIT
# ============================================================

def secret_str(cle, defaut=""):
    try:
        return str(st.secrets[cle]).strip()
    except Exception:
        return defaut


GOOGLE_SHEET_URL = secret_str("GOOGLE_SHEET_URL")
STOCK_API_URL = secret_str("STOCK_API_URL")
DISCORD_WEBHOOK = secret_str("DISCORD_WEBHOOK")

# Compte administration uniquement.
# [admin]
# identifiant = "hash_sha256"
try:
    COMPTES_ADMIN = dict(st.secrets["admin"])
except Exception:
    COMPTES_ADMIN = {}


st.set_page_config(
    page_title=NOM_AFFICHE,
    page_icon="🌸",
    layout="wide",
)


# ============================================================
# SESSION
# ============================================================

if "admin_connecte" not in st.session_state:
    st.session_state.admin_connecte = False

if "admin_utilisateur" not in st.session_state:
    st.session_state.admin_utilisateur = ""

if "panier" not in st.session_state:
    st.session_state.panier = []

if "commande_en_cours" not in st.session_state:
    st.session_state.commande_en_cours = False

if "derniere_commande_timestamp" not in st.session_state:
    st.session_state.derniere_commande_timestamp = 0.0

if "page" not in st.session_state:
    st.session_state.page = "boutique"


# ============================================================
# OUTILS
# ============================================================

def normaliser_texte(texte):
    texte = str(texte)
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(
        c for c in texte
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", texte.lower()).strip()


def trouver_colonne(article, noms_possibles):
    colonnes = list(article.index) if hasattr(article, "index") else []
    normalisees = {
        normaliser_texte(col): col
        for col in colonnes
    }

    for nom in noms_possibles:
        cle = normaliser_texte(nom)
        if cle in normalisees:
            return normalisees[cle]

    return None


def convertir_nombre(valeur, defaut=0.0):
    if valeur is None:
        return defaut

    try:
        if pd.isna(valeur):
            return defaut
    except Exception:
        pass

    if isinstance(valeur, (int, float)):
        return float(valeur)

    texte = str(valeur).strip()
    if not texte:
        return defaut

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
        return defaut


def hash_password(mot_de_passe):
    return hashlib.sha256(
        mot_de_passe.encode("utf-8")
    ).hexdigest()


def verifier_admin(identifiant, mot_de_passe):
    attendu = str(
        COMPTES_ADMIN.get(
            identifiant.strip().lower(),
            "",
        )
    )

    if not attendu:
        return False

    fourni = hash_password(mot_de_passe)
    return hmac.compare_digest(fourni, attendu)


# ============================================================
# PRODUITS
# ============================================================

def nom_produit(article):
    colonne = trouver_colonne(
        article,
        ["Denomination", "Dénomination", "Produit", "Nom", "Article"],
    )
    if colonne is None:
        return "Produit sans nom"

    valeur = article.get(colonne, "")
    try:
        if pd.isna(valeur):
            return "Produit sans nom"
    except Exception:
        pass

    return str(valeur).strip()


def categorie_produit(article):
    colonne = trouver_colonne(
        article,
        ["Categorie", "Catégorie", "Catégorie produit", "Famille"],
    )
    if colonne is None:
        return "Autre"

    valeur = article.get(colonne, "")
    try:
        if pd.isna(valeur) or str(valeur).strip() == "":
            return "Autre"
    except Exception:
        pass

    return str(valeur).strip()


def photo_produit(article):
    colonne = trouver_colonne(
        article,
        ["Photo produit", "Photo", "Image", "Photo produit URL"],
    )
    if colonne is None:
        return ""

    valeur = article.get(colonne, "")
    try:
        if pd.isna(valeur):
            return ""
    except Exception:
        pass

    return str(valeur).strip()


def obtenir_stock(article):
    colonne = trouver_colonne(
        article,
        ["Quantité", "Quantite", "Stock", "Stocks"],
    )
    if colonne is None:
        return 0

    return int(max(0, convertir_nombre(article.get(colonne, 0), 0)))


def obtenir_prix(article):
    colonne = trouver_colonne(
        article,
        ["Prix initial", "Prix", "Prix normal", "Tarif"],
    )
    if colonne is None:
        return 0.0

    return convertir_nombre(article.get(colonne, 0), 0.0)


def obtenir_prix_promo(article):
    colonne = trouver_colonne(
        article,
        ["Prix promo", "Promo", "Prix promotion", "Prix promotionnel"],
    )
    if colonne is None:
        return None

    valeur = article.get(colonne, "")
    try:
        if pd.isna(valeur) or str(valeur).strip() == "":
            return None
    except Exception:
        pass

    prix = convertir_nombre(valeur, 0.0)
    return prix if prix > 0 else None


def format_produit(article):
    colonne = trouver_colonne(
        article,
        ["Litre / Gramme", "Litre/Gramme", "Format", "Poids", "Volume"],
    )
    if colonne is None:
        return ""

    valeur = article.get(colonne, "")
    try:
        if pd.isna(valeur):
            return ""
    except Exception:
        pass

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
            "Prix au litre",
        ],
    )
    if colonne is None:
        return ""

    valeur = article.get(colonne, "")
    try:
        if pd.isna(valeur):
            return ""
    except Exception:
        pass

    return str(valeur).strip()


def prix_actuel(article):
    promo = obtenir_prix_promo(article)
    return promo if promo is not None else obtenir_prix(article)


@st.cache_data(ttl=60)
def charger_produits():
    if not GOOGLE_SHEET_URL:
        raise RuntimeError(
            "GOOGLE_SHEET_URL n'est pas configurée."
        )

    match = re.search(
        r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
        GOOGLE_SHEET_URL,
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

    dataframe = pd.read_csv(url_csv)

    if dataframe.empty:
        return dataframe

    dataframe.columns = [
        str(col).strip()
        for col in dataframe.columns
    ]

    return dataframe.dropna(
        how="all"
    ).reset_index(drop=True)


# ============================================================
# PANIER CLIENT
# ============================================================

def ajouter_au_panier(article):
    nom = nom_produit(article)
    stock = obtenir_stock(article)

    if stock <= 0:
        return False, "Produit en rupture de stock."

    for ligne in st.session_state.panier:
        if ligne["produit"] == nom:
            if ligne["quantite"] >= stock:
                return False, "Stock maximum déjà atteint dans ton panier."

            ligne["quantite"] += 1
            ligne["prix"] = prix_actuel(article)
            return True, "Quantité ajoutée."

    st.session_state.panier.append(
        {
            "produit": nom,
            "quantite": 1,
            "prix": prix_actuel(article),
        }
    )

    return True, "Produit ajouté."


def retirer_du_panier(nom):
    for ligne in st.session_state.panier:
        if ligne["produit"] == nom:
            ligne["quantite"] -= 1

            if ligne["quantite"] <= 0:
                st.session_state.panier.remove(ligne)

            return


def augmenter_panier(nom):
    produits = charger_produits()

    for _, article in produits.iterrows():
        if nom_produit(article) == nom:
            stock = obtenir_stock(article)

            for ligne in st.session_state.panier:
                if ligne["produit"] == nom:
                    if ligne["quantite"] >= stock:
                        return False, "Stock maximum atteint."

                    ligne["quantite"] += 1
                    ligne["prix"] = prix_actuel(article)

                    return True, "Quantité augmentée."

    return False, "Produit introuvable."


def vider_panier():
    st.session_state.panier = []


def calculer_total():
    return round(
        sum(
            ligne["prix"] * ligne["quantite"]
            for ligne in st.session_state.panier
        ),
        2,
    )


# ============================================================
# VÉRIFICATION AVANT COMMANDE
# ============================================================

def revalider_panier():
    if not st.session_state.panier:
        return False, "Le panier est vide.", []

    produits = charger_produits()

    index = {
        normaliser_texte(nom_produit(article)): article
        for _, article in produits.iterrows()
    }

    commande = []

    for ligne in st.session_state.panier:
        cle = normaliser_texte(ligne["produit"])
        article = index.get(cle)

        if article is None:
            return (
                False,
                f"« {ligne['produit']} » n'est plus disponible.",
                [],
            )

        stock = obtenir_stock(article)
        quantite = int(ligne["quantite"])

        if quantite > stock:
            return (
                False,
                f"Stock insuffisant pour « {ligne['produit']} » : "
                f"{stock} disponible(s).",
                [],
            )

        prix = round(prix_actuel(article), 2)

        commande.append(
            {
                "produit": nom_produit(article),
                "quantite": quantite,
                "prix_unitaire": prix,
                "total_ligne": round(prix * quantite, 2),
            }
        )

    return True, "OK", commande


# ============================================================
# COMMANDE / ANTI DOUBLE ENVOI
# ============================================================

def empreinte_commande(coordonnees, commande):
    """
    Empreinte locale permettant d'éviter le double clic et les renvois
    identiques dans la même session.
    """
    contenu = {
        "nom": coordonnees["nom"],
        "email": coordonnees["email"].lower(),
        "telephone": coordonnees["telephone"],
        "adresse": coordonnees["adresse_livraison"],
        "produits": commande,
    }

    brut = repr(contenu).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def envoyer_commande(coordonnees, commande, idempotency_key):
    if not STOCK_API_URL:
        return False, "STOCK_API_URL n'est pas configurée."

    donnees = {
        "action": "retirer_commande",
        "utilisateur": "client_public",
        "idempotency_key": idempotency_key,
        "client": coordonnees,
        "produits": commande,
        "total": round(
            sum(
                ligne["total_ligne"]
                for ligne in commande
            ),
            2,
        ),
        "date_commande": datetime.now().isoformat(
            timespec="seconds"
        ),
    }

    try:
        reponse = requests.post(
            STOCK_API_URL,
            json=donnees,
            timeout=20,
        )

        if reponse.status_code not in (200, 201):
            return False, f"Erreur serveur : {reponse.status_code}"

        resultat = reponse.json()

        if not resultat.get("success", False):
            return False, resultat.get(
                "message",
                "Commande refusée par le serveur.",
            )

        return True, "Commande validée."

    except requests.exceptions.Timeout:
        return False, "Le serveur met trop de temps à répondre."

    except requests.exceptions.RequestException:
        return False, "Erreur de connexion au serveur."

    except Exception:
        return False, "Réponse serveur invalide."


def envoyer_discord(commande, total):
    if not DISCORD_WEBHOOK:
        return

    lignes = [
        f"• {ligne['produit']} x{ligne['quantite']} "
        f"= {ligne['total_ligne']:.2f} €"
        for ligne in commande
    ]

    message = (
        "🌸 **Nouvelle commande**\n\n"
        + "\n".join(lignes)
        + f"\n\n💰 Total : {total:.2f} €"
    )

    try:
        requests.post(
            DISCORD_WEBHOOK,
            json={"content": message},
            timeout=10,
        )
    except Exception:
        pass


# ============================================================
# PAGES LÉGALES
# ============================================================

def page_mentions_legales():
    st.header("📄 Mentions légales")

    st.markdown(
        f"""
**Nom commercial :** {NOM_BOUTIQUE}  
**Exploitante :** {EXPLOITANTE}  
**Statut :** Micro-entreprise / entrepreneur individuel  
**Localisation affichée :** {VILLE_AFFICHAGE}  
**E-mail :** {EMAIL_CONTACT}  
**SIREN :** {SIREN}  
**SIRET :** {SIRET}

**Téléphone professionnel :** À compléter  
**Hébergeur :** À compléter
"""
    )

    st.info(
        "La localisation affichée ne remplace pas automatiquement l'adresse "
        "juridique de l'entreprise. Les modalités de non-diffusion de l'adresse "
        "personnelle doivent être vérifiées avant publication."
    )


def page_cgv():
    st.header("📜 Conditions générales de vente")

    st.markdown(
        f"""
### Vendeur

**{NOM_BOUTIQUE}**, micro-entreprise de **{EXPLOITANTE}**.  
Localisation publique : **{VILLE_AFFICHAGE}**.  
Contact : **{EMAIL_CONTACT}**.

### Commandes

Le client peut consulter le catalogue et préparer une commande sans créer
de compte.

La commande est soumise à une vérification de disponibilité par le serveur.
Une confirmation est affichée lorsque la commande a été acceptée.

### Livraison

La boutique effectue des livraisons.

**Zone, délais, créneaux et frais de livraison : à compléter avant publication.**

### Paiement

La version actuelle ne réalise pas de paiement bancaire en ligne.

**Moyen de paiement accepté : à compléter avant publication.**

### Rétractation

Le droit légal de rétractation s'applique lorsqu'il est prévu par la
réglementation, sous réserve notamment des exceptions concernant certains
produits périssables.

### Garanties

Les garanties légales applicables aux consommateurs sont respectées.

### Données personnelles

Voir la politique de confidentialité.

### Médiation

**Médiateur de la consommation : à compléter avant publication.**
"""
    )


def page_confidentialite():
    st.header("🔐 Politique de confidentialité")

    st.markdown(
        f"""
Le responsable du traitement est **{EXPLOITANTE}**, exploitante de
**{NOM_BOUTIQUE}**.

Contact : **{EMAIL_CONTACT}**

Les données éventuellement demandées lors d'une commande peuvent comprendre :

- nom et prénom ;
- adresse de livraison ;
- e-mail ;
- téléphone ;
- contenu de la commande.

Elles servent au traitement et à la livraison de la commande et aux obligations
légales applicables.

Les coordonnées personnelles du client ne sont pas transmises au webhook
Discord de notification interne.

**Durées précises de conservation : à compléter avant publication.**

Pour exercer vos droits : **{EMAIL_CONTACT}**.
"""
    )


# ============================================================
# ADMINISTRATION
# ============================================================

def interface_admin():
    st.header("🔒 Administration")

    if not st.session_state.admin_connecte:
        st.info(
            "Cette zone est réservée à la gestion de la boutique."
        )

        with st.form("admin_login"):
            identifiant = st.text_input("Identifiant administrateur")
            mot_de_passe = st.text_input(
                "Mot de passe administrateur",
                type="password",
            )

            connexion = st.form_submit_button(
                "🔐 Connexion",
                type="primary",
            )

            if connexion:
                if verifier_admin(identifiant, mot_de_passe):
                    st.session_state.admin_connecte = True
                    st.session_state.admin_utilisateur = (
                        identifiant.strip().lower()
                    )
                    st.rerun()
                else:
                    st.error("Identifiants incorrects.")

        return

    st.success(
        f"Administration connectée : {st.session_state.admin_utilisateur}"
    )

    if st.button("🚪 Déconnexion administration"):
        st.session_state.admin_connecte = False
        st.session_state.admin_utilisateur = ""
        st.rerun()

    st.subheader("📦 État du catalogue")

    try:
        produits = charger_produits()

        if produits.empty:
            st.warning("Aucun produit.")

        else:
            tableau = []

            for _, article in produits.iterrows():
                tableau.append(
                    {
                        "Produit": nom_produit(article),
                        "Catégorie": categorie_produit(article),
                        "Stock": obtenir_stock(article),
                        "Prix": f"{prix_actuel(article):.2f} €",
                    }
                )

            st.dataframe(
                pd.DataFrame(tableau),
                use_container_width=True,
                hide_index=True,
            )

    except Exception as erreur:
        st.error(str(erreur))

    st.info(
        "La modification du stock reste effectuée dans ton système de stock "
        "actuel. L'API doit effectuer une réservation atomique pour protéger "
        "les commandes simultanées."
    )


# ============================================================
# CONFIGURATION
# ============================================================

def configuration_incomplete():
    manquants = []

    if not GOOGLE_SHEET_URL:
        manquants.append("GOOGLE_SHEET_URL")

    if not STOCK_API_URL:
        manquants.append("STOCK_API_URL")

    if not COMPTES_ADMIN:
        manquants.append("[admin]")

    return manquants


# ============================================================
# EN-TÊTE / NAVIGATION
# ============================================================

st.title(NOM_AFFICHE)
st.caption(f"{NOM_BOUTIQUE} — {VILLE_AFFICHAGE}")

nav1, nav2, nav3 = st.columns([2, 2, 1])

with nav1:
    if st.button("🌸 Boutique"):
        st.session_state.page = "boutique"
        st.rerun()

with nav2:
    if st.button("🔒 Administration"):
        st.session_state.page = "admin"
        st.rerun()

with nav3:
    st.metric("Panier", len(st.session_state.panier))


# ============================================================
# ADMIN
# ============================================================

if st.session_state.page == "admin":
    interface_admin()
    st.stop()


# ============================================================
# BOUTIQUE PUBLIQUE
# ============================================================

manquants = configuration_incomplete()

if manquants:
    st.error("⚠️ Configuration incomplète.")
    for element in manquants:
        st.write(f"- `{element}`")
    st.info(
        "Configure les secrets Streamlit avant de publier."
    )
    st.stop()

try:
    produits = charger_produits()
except Exception as erreur:
    st.error("Impossible de charger les produits.")
    st.code(str(erreur))
    st.stop()

if produits.empty:
    st.warning("Aucun produit disponible.")
    st.stop()


# ============================================================
# RECHERCHE / FILTRES
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
        placeholder="Ex : chocolat, huile, café...",
    )

with col2:
    categorie_selectionnee = st.selectbox(
        "🌸 Catégorie",
        ["Toutes"] + categories,
    )


produits_affiches = produits.copy()

if recherche:
    recherche_normalisee = normaliser_texte(recherche)

    indices = []

    for index, article in produits_affiches.iterrows():
        texte = " ".join(
            [
                nom_produit(article),
                categorie_produit(article),
                format_produit(article),
                prix_kg_litre(article),
            ]
        )

        if recherche_normalisee in normaliser_texte(texte):
            indices.append(index)

    produits_affiches = produits_affiches.loc[indices]

if categorie_selectionnee != "Toutes":
    produits_affiches = produits_affiches[
        produits_affiches.apply(
            lambda article:
            categorie_produit(article) == categorie_selectionnee,
            axis=1,
        )
    ]

st.write(
    f"**{len(produits_affiches)} produit(s)** trouvé(s)"
)


# ============================================================
# PRODUITS
# ============================================================

for index, article in produits_affiches.iterrows():

    nom = nom_produit(article)
    categorie = categorie_produit(article)
    stock = obtenir_stock(article)
    prix_normal = obtenir_prix(article)
    prix_promo = obtenir_prix_promo(article)
    photo = photo_produit(article)
    format_article = format_produit(article)
    prix_unitaire = prix_kg_litre(article)

    prix_final = (
        prix_promo
        if prix_promo is not None
        else prix_normal
    )

    with st.container(border=True):

        col_photo, col_info, col_action = st.columns(
            [1.2, 3.8, 1.5]
        )

        with col_photo:
            if photo:
                try:
                    st.image(
                        photo,
                        use_container_width=True,
                    )
                except Exception:
                    st.write("🌸")
            else:
                st.write("🌸")

        with col_info:
            st.subheader(nom)
            st.caption(f"🌸 {categorie}")

            if format_article:
                st.write(
                    f"📦 Format : {format_article}"
                )

            if prix_unitaire:
                st.write(
                    f"⚖️ Prix : {prix_unitaire}"
                )

            if prix_promo is not None:
                st.markdown(
                    f"### 🔥 {prix_final:.2f} €"
                )
                st.caption(
                    f"Prix initial : {prix_normal:.2f} €"
                )
            else:
                st.markdown(
                    f"### {prix_final:.2f} €"
                )

            if stock > 0:
                st.success(
                    f"En stock : {stock}"
                )
            else:
                st.error("Rupture de stock")

        with col_action:
            if stock > 0:

                if st.button(
                    "🛒 Ajouter",
                    key=f"ajouter_{index}",
                ):
                    ok, message = ajouter_au_panier(
                        article
                    )

                    if ok:
                        st.success(message)
                    else:
                        st.warning(message)

                    st.rerun()

            else:
                st.button(
                    "Rupture",
                    disabled=True,
                    key=f"rupture_{index}",
                )


# ============================================================
# PANIER
# ============================================================

st.divider()
st.header("🛒 Mon panier")

if not st.session_state.panier:
    st.info("Ton panier est vide 🌸")

else:

    for i, ligne in enumerate(
        st.session_state.panier
    ):

        col1, col2, col3, col4 = st.columns(
            [4, 1, 1, 2]
        )

        with col1:
            st.write(
                f"**{ligne['produit']}**"
            )

        with col2:
            st.write(
                f"{ligne['prix']:.2f} €"
            )

        with col3:
            st.write(
                f"x{ligne['quantite']}"
            )

        with col4:

            moins = st.button(
                "➖",
                key=f"moins_{i}",
            )

            plus = st.button(
                "➕",
                key=f"plus_{i}",
            )

            if moins:
                retirer_du_panier(
                    ligne["produit"]
                )
                st.rerun()

            if plus:
                ok, message = augmenter_panier(
                    ligne["produit"]
                )

                if not ok:
                    st.warning(message)

                st.rerun()

    st.divider()

    st.subheader(
        f"💰 Total produits : "
        f"{calculer_total():.2f} €"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Vider le panier"):
            vider_panier()
            st.rerun()

    with col2:
        if st.button(
            "✅ Passer la commande",
            type="primary",
        ):
            st.session_state.commande_en_cours = True
            st.rerun()


# ============================================================
# FORMULAIRE DE COMMANDE
# ============================================================

if (
    st.session_state.commande_en_cours
    and st.session_state.panier
):

    st.divider()
    st.header("📦 Finaliser la commande")

    # Protection contre le double clic / double soumission.
    maintenant = time.time()

    if (
        maintenant
        - st.session_state.derniere_commande_timestamp
        < DELAI_MINIMUM_ENTRE_COMMANDES_SECONDES
    ):
        st.warning(
            "Une commande vient d'être envoyée depuis cette session. "
            "Attends quelques secondes avant d'en envoyer une autre."
        )

    with st.form("commande_client"):

        nom_client = st.text_input(
            "Nom et prénom *"
        )

        email_client = st.text_input(
            "E-mail *"
        )

        telephone_client = st.text_input(
            "Téléphone *"
        )

        adresse_client = st.text_area(
            "Adresse de livraison *"
        )

        acceptation = st.checkbox(
            "J'ai lu les CGV et la politique de "
            "confidentialité et j'accepte les conditions "
            "applicables à ma commande. *"
        )

        confirmer = st.form_submit_button(
            "📦 Confirmer ma commande",
            type="primary",
        )

        if confirmer:

            maintenant = time.time()

            if (
                maintenant
                - st.session_state.derniere_commande_timestamp
                < DELAI_MINIMUM_ENTRE_COMMANDES_SECONDES
            ):
                st.error(
                    "Une commande vient déjà d'être envoyée. "
                    "Merci d'attendre avant une nouvelle validation."
                )
                st.stop()

            if not all(
                [
                    nom_client.strip(),
                    email_client.strip(),
                    telephone_client.strip(),
                    adresse_client.strip(),
                    acceptation,
                ]
            ):
                st.error(
                    "Merci de compléter tous les champs obligatoires."
                )
                st.stop()

            email_normalise = email_client.strip()

            if not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                email_normalise,
            ):
                st.error(
                    "L'adresse e-mail semble invalide."
                )
                st.stop()

            # Relecture complète du stock/prix avant envoi.
            ok, message, commande = revalider_panier()

            if not ok:
                st.error(message)
                charger_produits.clear()
                st.rerun()

            coordonnees = {
                "nom": nom_client.strip(),
                "email": email_normalise,
                "telephone": telephone_client.strip(),
                "adresse_livraison": adresse_client.strip(),
            }

            # Une clé stable permet à l'API de reconnaître un éventuel
            # renvoi identique de la même commande.
            idempotency_key = empreinte_commande(
                coordonnees,
                commande,
            )

            succes, message = envoyer_commande(
                coordonnees,
                commande,
                idempotency_key,
            )

            if succes:

                total = round(
                    sum(
                        ligne["total_ligne"]
                        for ligne in commande
                    ),
                    2,
                )

                envoyer_discord(
                    commande,
                    total,
                )

                st.session_state.derniere_commande_timestamp = (
                    time.time()
                )

                st.session_state.commande_en_cours = False
                st.session_state.panier = []

                charger_produits.clear()

                st.success(
                    "🎉 Commande enregistrée avec succès !"
                )

                st.balloons()

                st.rerun()

            else:
                st.error(message)


# ============================================================
# INFOS LÉGALES
# ============================================================

st.divider()

with st.expander("📄 Mentions légales"):
    page_mentions_legales()

with st.expander("📜 Conditions générales de vente"):
    page_cgv()

with st.expander("🔐 Confidentialité"):
    page_confidentialite()


# ============================================================
# CALCULATEUR CARBURANT
# ============================================================

st.divider()
st.header("⛽ Estimation carburant")

col1, col2 = st.columns(2)

with col1:
    distance = st.number_input(
        "Distance aller-retour (km)",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )

with col2:
    consommation = st.number_input(
        "Consommation (L/100 km)",
        min_value=0.1,
        value=CONSOMMATION_L_100KM,
        step=0.1,
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
            f"{distance:.0f} km",
        )

    with col2:
        st.metric(
            "Carburant",
            f"{litres:.2f} L",
        )

    with col3:
        st.metric(
            "Coût estimé",
            f"{cout:.2f} €",
        )


st.divider()

st.caption(
    f"🌸 {NOM_AFFICHE} — {NOM_BOUTIQUE} — {VILLE_AFFICHAGE}"
)
'''

secrets = r'''# À utiliser comme .streamlit/secrets.toml
# NE PAS publier ce fichier sur GitHub.

GOOGLE_SHEET_URL = "COLLE_ICI_TON_URL_GOOGLE_SHEET"
STOCK_API_URL = "COLLE_ICI_TON_URL_APPS_SCRIPT"

# IMPORTANT : créer un nouveau webhook Discord.
# L'ancien présent dans le code original doit être considéré comme compromis.
DISCORD_WEBHOOK = "COLLE_ICI_LE_NOUVEAU_WEBHOOK_DISCORD"

# SEUL le compte administrateur a un mot de passe.
# Exemple :
# [admin]
# sarah = "HASH_SHA256"

[admin]
sarah = "A_COMPLETER"
'''

hash_script = r'''import hashlib
import getpass

mot_de_passe = getpass.getpass(
    "Nouveau mot de passe administrateur : "
)

print(
    "\nHash SHA-256 à placer dans secrets.toml :\n"
)

print(
    hashlib.sha256(
        mot_de_passe.encode("utf-8")
    ).hexdigest()
)
'''

requirements = """streamlit
pandas
requests
"""

apps_script = r'''/**
 * Exemple de logique côté serveur pour la réservation atomique du stock.
 *
 * IMPORTANT :
 * - adapte les noms de colonnes à ton Google Sheet ;
 * - protège ton endpoint Apps Script par un secret serveur ;
 * - ne considère JAMAIS le stock affiché dans Streamlit comme une
 *   garantie de disponibilité.
 *
 * Le point essentiel est de vérifier puis décrémenter le stock
 * dans UNE opération protégée par LockService.
 *
 * Cette fonction est un modèle à adapter à ton fichier actuel.
 */

function doPost(e) {
  var lock = LockService.getScriptLock();

  try {
    lock.waitLock(15000);

    var data = JSON.parse(e.postData.contents);

    if (!data.idempotency_key) {
      return jsonResponse({
        success: false,
        message: "Clé de commande manquante."
      });
    }

    var props = PropertiesService.getScriptProperties();

    // Anti-double-commande serveur.
    var dejaTraitee = props.getProperty(
      "commande_" + data.idempotency_key
    );

    if (dejaTraitee) {
      return jsonResponse({
        success: true,
        message: "Commande déjà enregistrée.",
        duplicate: true
      });
    }

    // ========================================================
    // ICI : charger le Google Sheet et vérifier chaque stock.
    //
    // Pour chaque ligne :
    //   1. trouver le produit ;
    //   2. lire le stock ACTUEL ;
    //   3. vérifier stock >= quantité ;
    //   4. décrémenter le stock.
    //
    // Le LockService empêche deux commandes simultanées de
    // lire puis modifier le même stock en même temps.
    // ========================================================

    // Exemple :
    // var sheet = SpreadsheetApp.openById("ID").getSheetByName("Stock");
    // ...
    // sheet.getRange(ligne, colonneStock).setValue(nouveauStock);

    // Une fois toutes les vérifications réussies :
    props.setProperty(
      "commande_" + data.idempotency_key,
      new Date().toISOString()
    );

    return jsonResponse({
      success: true,
      message: "Commande enregistrée."
    });

  } catch (err) {

    return jsonResponse({
      success: false,
      message: "Erreur serveur."
    });

  } finally {

    try {
      lock.releaseLock();
    } catch (e) {}
  }
}


function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
'''

readme = r'''# LA boutique des bons plans — V2 publique

## Ce qui change

### CLIENT
Le catalogue est désormais public :

- pas de mot de passe ;
- pas de compte client obligatoire ;
- panier libre ;
- formulaire de commande ;
- vérification du stock avant validation.

### ADMINISTRATION
Une page séparée `/Administration` est disponible dans l'application.

Elle est protégée par un compte administrateur stocké dans Streamlit Secrets.

Les anciens comptes :
- maman
- carole
- ben
- helene
- laurie
- tiffany
- lesfilles
- invite

ne sont plus utilisés.

## Protection contre les doubles commandes

La V2 utilise trois niveaux :

1. Vérification du stock à l'ajout au panier.
2. Vérification du stock et du prix juste avant la commande.
3. Clé `idempotency_key` envoyée à l'API.

### TRÈS IMPORTANT

La troisième protection ne devient réellement efficace que si ton
Google Apps Script la traite.

Le fichier `google_apps_script_anti_double_commande.js` donne la structure
à intégrer dans ton Apps Script actuel.

`LockService` doit être utilisé pour que deux commandes simultanées ne puissent
pas toutes les deux réserver le dernier produit.

## Anti double clic

Le navigateur/session bloque aussi une nouvelle validation pendant 30 secondes.

Cette protection est seulement complémentaire. Elle ne remplace PAS
la protection serveur.

## Sécurité

L'ancien webhook Discord doit être révoqué/remplacé.

Les anciens mots de passe doivent également être changés.

Ne publie jamais `.streamlit/secrets.toml`.

## Avant mise en ligne

Compléter :

- SIREN/SIRET ;
- téléphone ;
- hébergeur ;
- médiateur ;
- zone de livraison ;
- délais ;
- frais de livraison ;
- moyens de paiement ;
- durées de conservation des données.

Puis tester au minimum :

- deux commandes simultanées pour le dernier article ;
- double clic sur confirmation ;
- quantité supérieure au stock ;
- produit supprimé du catalogue pendant qu'il est dans un panier ;
- changement de prix entre l'ajout au panier et la validation.
'''

(base / "app_boutique_bons_plans_v2.py").write_text(app, encoding="utf-8")
(base / ".streamlit" / "secrets.toml.example").write_text(secrets, encoding="utf-8")
(base / "generer_hash_admin.py").write_text(hash_script, encoding="utf-8")
(base / "google_apps_script_anti_double_commande.js").write_text(apps_script, encoding="utf-8")
(base / "requirements.txt").write_text(requirements, encoding="utf-8")
(base / "README_AVANT_PUBLICATION.md").write_text(readme, encoding="utf-8")

zip_path = Path("/mnt/data/LA_boutique_des_bons_plans_V2_client_admin.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for path in base.rglob("*"):
        if path.is_file():
            z.write(path, path.relative_to(base.parent))

print(f"Archive créée : {zip_path}")
print(f"Fichiers : {len(list(base.rglob('*')))}")
