Mes Bons Plans de Sarah
Code Python de la nouvelle version — copie intégrale du fichier .py. Pour la mise en ligne, privilégier le fichier Python afin de conserver les indentations.
 
import streamlit as st
 
import pandas as pd
 
import requests
 
import re
 
import unicodedata
 
import json
 
import base64
import sqlite3
import hashlib
import hmac
import secrets
import smtplib
from email.message import EmailMessage
from datetime import datetime, date, timedelta
 
 
 
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
 
# DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1549946850885238865/OItwwHS0spEUH0vzmBSJjAaCXwx2Yicaz2l30EolaALbmEufafnZI36M"
 
DISCORD_WEBHOOK = st.secrets.get("DISCORD_WEBHOOK", "")
 
 
 
# ATTENTION : pour Streamlit Community Cloud, un fichier SQLite local peut être perdu
# lors d'un redémarrage. Utiliser un stockage persistant avant ouverture publique.
DB_PATH = st.secrets.get("DB_PATH", "sarah_boutique.sqlite3")
ADMIN_PASSWORD_HASH = st.secrets.get("ADMIN_PASSWORD_SHA256", "").strip().lower()
 
 
 
 
# ============================================================
 
# CONFIGURATION INTERFACE STREAMLIT
 
# ============================================================
 
st.set_page_config(
 
    page_title=NOM_BOUTIQUE,
 
    page_icon="🌸",
 
    layout="wide"
 
)
 
 
 
# ============================================================
 
st.markdown("""
<style>
:root {--rose:#A56880;--prune:#66374D;--fond:#F7F0F1;--card:#FFFCFB;}
.stApp,[data-testid="stAppViewContainer"] {background:#F7F0F1;color:#453840;}
[data-testid="stSidebar"] {background:#F0E2E7;border-right:1px solid #E4CDD6;}
[data-testid="stHeader"] {background:rgba(247,240,241,.96);}
[data-testid="stMainBlockContainer"] {max-width:1350px;padding-top:2rem;}
h1,h2,h3 {color:#66374D!important;}
[data-testid="stMarkdownContainer"] p {line-height:1.5;}
div[data-testid="stVerticalBlockBorderWrapper"] > div[style*="border"] {background:#FFFCFB;border:1px solid #EAD9DF!important;border-radius:17px!important;box-shadow:0 5px 18px rgba(102,55,77,.07);padding:10px;}
div.stButton > button {border-radius:12px!important;border:1px solid #D8B9C5!important;background:#FFF9FB;color:#713C50;font-weight:600;min-height:40px;}
div.stButton > button:hover {background:#EEDBE3;color:#66374D;border-color:#A56880!important;}
div.stButton > button[kind="primary"] {background:#A56880!important;color:white!important;border-color:#A56880!important;}
[data-testid="stTextInput"] input {background:#FFFCFB;border-radius:11px;}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {background:#FFFCFB;border-radius:11px;}
[data-testid="stImage"] img {object-fit:contain;max-height:230px;}
@media(max-width:700px){[data-testid="stMainBlockContainer"]{padding:1rem .7rem;}h1{font-size:1.7rem!important;}}
</style>
""", unsafe_allow_html=True)# FONCTIONS DE PERSISTANCE DU PANIER
 
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
if "confirmation_commande" not in st.session_state:
    st.session_state.confirmation_commande = None
if "animation_confirmation" not in st.session_state:
    st.session_state.animation_confirmation = False
if "commande_stock_en_erreur" not in st.session_state:
    st.session_state.commande_stock_en_erreur = False
 
 
 
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
 
 
 
 
 
def diminuer_du_panier(index):
    """Diminue d'une unité, puis supprime si la quantité atteint zéro."""
    if 0 <= index < len(st.session_state.panier):
        article = st.session_state.panier[index]
        if article["quantite"] > 1:
            article["quantite"] -= 1
        else:
            st.session_state.panier.pop(index)
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
 
    total_general,
    premiere_commande=False, telephone="", email="", creneau="", reference=""
 
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
 
        f"📍 **Adresse :** {adresse_livraison}\n"
         f"📞 **Téléphone :** {telephone}\n📧 **E-mail :** {email}\n"
         f"📅 **Livraison :** {creneau}\n🔖 **Référence :** {reference}\n\n"
 
        "🛒 **Produits :**\n"
 
        + "\n".join(lignes)
 
        + "\n\n"
 
        f"💰 TOTAL ARTICLES : **{total_general:.2f} €**\n"
        + ("🎁 **Livraison offerte demandée (première commande déclarée) — à vérifier manuellement**\n" if premiere_commande else "🚚 Livraison : modalités et frais à confirmer\n")
 
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
 
def envoyer_liste_courses(nom, contact, liste):
    if not DISCORD_WEBHOOK:
        return False, "Discord n'est pas configuré."
    message = (
        "📝 **NOUVELLE LISTE DE COURSES / RECHERCHE**\n"
        f"👤 Nom : {nom}\n📞 Contact : {contact}\n"
        f"🔎 Produits recherchés :\n{liste}\n\n"
        "ℹ️ Recherche uniquement : aucun achat ni retrait de stock."
    )
    try:
        reponse = requests.post(DISCORD_WEBHOOK, json={"content": message}, timeout=15)
        return reponse.status_code in (200, 204), ("" if reponse.status_code in (200, 204) else f"Discord : {reponse.status_code}")
    except requests.RequestException as erreur:
        return False, str(erreur)
 
 
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
 
# ============================================================
# LIVRAISONS, COMMANDES ET ADMINISTRATION
# ============================================================
def db_conn():
    connexion = sqlite3.connect(DB_PATH, timeout=20)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA busy_timeout=20000")
    return connexion
 
 
def initialiser_db():
    with db_conn() as db:
        db.execute("CREATE TABLE IF NOT EXISTS creneaux (id INTEGER PRIMARY KEY AUTOINCREMENT, jour TEXT NOT NULL, debut TEXT NOT NULL, fin TEXT NOT NULL, capacite INTEGER NOT NULL DEFAULT 3, actif INTEGER NOT NULL DEFAULT 1, UNIQUE(jour,debut,fin))")
        db.execute("CREATE TABLE IF NOT EXISTS commandes (id TEXT PRIMARY KEY, cree_le TEXT NOT NULL, nom TEXT NOT NULL, telephone TEXT NOT NULL, email TEXT, adresse TEXT NOT NULL, creneau_id INTEGER NOT NULL, panier_json TEXT NOT NULL, total_prevu REAL NOT NULL, montant_encaisse REAL, statut TEXT NOT NULL DEFAULT 'réservée', premiere_commande INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(creneau_id) REFERENCES creneaux(id))")
        db.execute("CREATE TABLE IF NOT EXISTS lignes_livrees (commande_id TEXT, produit TEXT, quantite_gardee INTEGER, PRIMARY KEY(commande_id,produit))")
        colonnes = {r[1] for r in db.execute("PRAGMA table_info(commandes)").fetchall()}
        if "mode_remise" not in colonnes:
            db.execute("ALTER TABLE commandes ADD COLUMN mode_remise TEXT DEFAULT 'Livraison à domicile'")
        if "precision_lieu" not in colonnes:
            db.execute("ALTER TABLE commandes ADD COLUMN precision_lieu TEXT DEFAULT ''")
 
 
def places_disponibles():
    with db_conn() as db:
        return db.execute("""SELECT c.id,c.jour,c.debut,c.fin,c.capacite, c.actif,
        (SELECT COUNT(*) FROM commandes o WHERE o.creneau_id=c.id AND o.statut NOT IN ('annulée','livrée')) AS reservees
        FROM creneaux c WHERE c.jour>=? AND c.actif=1 ORDER BY c.jour,c.debut""", (date.today().isoformat(),)).fetchall()
 
 
def libelle_creneau(c):
    return f"{c['jour']} · {c['debut']}–{c['fin']} ({c['capacite']-c['reservees']} place(s))"
 
 
def reserver_commande(commande):
    with db_conn() as db:
        db.execute("BEGIN IMMEDIATE")
        c = db.execute("""SELECT c.id,c.capacite,c.actif,c.jour,
          (SELECT COUNT(*) FROM commandes o WHERE o.creneau_id=c.id AND o.statut NOT IN ('annulée','livrée')) AS reservees
          FROM creneaux c WHERE c.id=?""", (commande['creneau_id'],)).fetchone()
        if not c or not c['actif'] or c['jour'] < date.today().isoformat() or c['reservees'] >= c['capacite']:
            return False, 'Ce créneau vient de devenir indisponible.'
        db.execute("""INSERT INTO commandes (id,cree_le,nom,telephone,email,adresse,creneau_id,panier_json,total_prevu,premiere_commande,mode_remise,precision_lieu)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (commande['id'],datetime.now().isoformat(timespec='seconds'),commande['nom'],commande['telephone'],commande['email'],commande['adresse'],commande['creneau_id'],json.dumps(commande['panier'],ensure_ascii=False),commande['total'],int(commande['premiere_commande']),commande['mode_remise'],commande['precision_lieu']))
    return True, ''
 
 
def annuler_reservation(identifiant):
    with db_conn() as db:
        db.execute("UPDATE commandes SET statut='annulée' WHERE id=? AND statut='réservée'", (identifiant,))
 
 
def envoyer_email_confirmation(commande, texte_creneau):
    # Optionnel : secrets SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    if not commande['email'] or not st.secrets.get('SMTP_HOST',''):
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Votre commande Mes Bons Plans de Sarah — ' + commande['id']
        msg['From'] = st.secrets['SMTP_FROM']
        msg['To'] = commande['email']
        lignes = '\n'.join(f"{p['produit']} x{p['quantite']} : {p['prix']*p['quantite']:.2f} €" for p in commande['panier'])
        msg.set_content(f"Bonjour {commande['nom']},\n\nCommande {commande['id']}\nCréneau demandé : {texte_creneau}\nLieu : {commande['mode_remise']} — {commande['adresse']} ({commande['precision_lieu']})\nLieu et horaire à confirmer par Sarah.\n\n{lignes}\n\nTotal prévisionnel : {commande['total']:.2f} €\nAucun paiement à l'avance. Vous pouvez vérifier et refuser des articles à la remise ; vous ne payez que ceux gardés.\nLa livraison et les éventuels frais restent à confirmer par Sarah.\nMerci !")
        with smtplib.SMTP(st.secrets['SMTP_HOST'],int(st.secrets.get('SMTP_PORT',587)),timeout=15) as smtp:
            smtp.starttls()
            smtp.login(st.secrets['SMTP_USER'],st.secrets['SMTP_PASSWORD'])
            smtp.send_message(msg)
        return True
    except Exception:
        return False
 
 
def prix_comparaison(article):
    col = trouver_colonne(article, ['Prix comparé','Prix compare','Prix de comparaison','Prix constaté','Prix magasin'])
    return convertir_nombre(article.get(col),0) if col else 0
 
 
def afficher_planning_public():
    st.markdown('### 🚚 Planning de livraison')
    st.caption('Consultez les disponibilités avant de faire vos achats. Choisissez votre créneau lors de la validation du panier.')
    creneaux = [c for c in places_disponibles() if c['reservees'] < c['capacite']]
    if not creneaux:
        st.info('Les prochains créneaux seront publiés ici prochainement. 🌸')
    else:
        for c in creneaux[:12]:
            st.write('🌸 ' + libelle_creneau(c))
 
 
def afficher_admin():
    with st.expander('🔐 Administration de la boutique', expanded=False):
        if not ADMIN_PASSWORD_HASH:
            st.warning('Administration désactivée : configurez ADMIN_PASSWORD_SHA256 dans les Secrets Streamlit.')
            return
        if not st.session_state.get('admin_auth',False):
            with st.form('connexion_admin'):
                pwd = st.text_input('Mot de passe administrateur',type='password')
                ok = st.form_submit_button('Se connecter')
            if ok:
                digest = hashlib.sha256(pwd.encode()).hexdigest()
                if hmac.compare_digest(digest,ADMIN_PASSWORD_HASH):
                    st.session_state.admin_auth=True
                    st.rerun()
                else:
                    st.error('Mot de passe incorrect.')
            return
        if st.button('Se déconnecter',key='admin_logout'):
            st.session_state.admin_auth=False
            st.rerun()
        tab1,tab2=st.tabs(['📅 Créneaux','📦 Commandes et clientes'])
        with tab1:
            with st.form('ajout_creneau'):
                jour=st.date_input('Jour de livraison',min_value=date.today())
                debut=st.time_input('Début',value=datetime.strptime('14:00','%H:%M').time())
                fin=st.time_input('Fin',value=datetime.strptime('16:00','%H:%M').time())
                capacite=st.number_input('Commandes maximum',min_value=1,max_value=100,value=3)
                ajouter=st.form_submit_button('Ajouter ce créneau')
            if ajouter:
                if debut>=fin:
                    st.error('La fin doit être après le début.')
                else:
                    try:
                        with db_conn() as db:
                            db.execute('INSERT INTO creneaux (jour,debut,fin,capacite) VALUES (?,?,?,?)',(jour.isoformat(),debut.strftime('%H:%M'),fin.strftime('%H:%M'),int(capacite)))
                        st.success('Créneau créé.')
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.warning('Ce créneau existe déjà.')
            with db_conn() as db:
                rows=db.execute('SELECT * FROM creneaux WHERE jour>=? ORDER BY jour,debut',(date.today().isoformat(),)).fetchall()
            for c in rows:
                a,b,d=st.columns([4,2,2])
                a.write(f"{c['jour']} {c['debut']}–{c['fin']} · max {c['capacite']} · {'ouvert' if c['actif'] else 'fermé'}")
                if b.button('Fermer' if c['actif'] else 'Ouvrir',key=f"toggle_{c['id']}"):
                    with db_conn() as db:
                        db.execute('UPDATE creneaux SET actif=? WHERE id=?',(0 if c['actif'] else 1,c['id']))
                    st.rerun()
                nouvelle_cap=d.number_input('Places',min_value=1,max_value=100,value=c['capacite'],key=f"cap_{c['id']}")
                if nouvelle_cap != c['capacite']:
                    with db_conn() as db:
                        db.execute('UPDATE creneaux SET capacite=? WHERE id=?',(int(nouvelle_cap),c['id']))
                    st.rerun()
        with tab2:
            with db_conn() as db:
                commandes=db.execute("SELECT o.*,c.jour,c.debut,c.fin FROM commandes o LEFT JOIN creneaux c ON c.id=o.creneau_id ORDER BY o.cree_le DESC LIMIT 200").fetchall()
            for c in commandes:
                with st.expander(f"{c['id']} · {c['nom']} · {c['jour']} {c['debut']} · {c['statut']}"):
                    st.write(f"Téléphone : {c['telephone']} | E-mail : {c['email'] or 'non fourni'}")
                    st.write(f"Mode de remise : {c['mode_remise']} · Lieu : {c['adresse']}")
                    if c['precision_lieu']:
                        st.write(f"Précisions : {c['precision_lieu']}")
                    st.write(f"Total prévu : {c['total_prevu']:.2f} €")
                    lignes=json.loads(c['panier_json'])
                    if c['statut']=='réservée':
                        with st.form('fin_'+c['id']):
                            gardees={}
                            for i,p in enumerate(lignes):
                                gardees[i]=st.number_input(p['produit']+' — quantité gardée',min_value=0,max_value=int(p['quantite']),value=int(p['quantite']),key=f"garde_{c['id']}_{i}")
                            montant=sum(gardees[i]*p['prix'] for i,p in enumerate(lignes))
                            st.write(f"Montant à encaisser pour les articles gardés : **{montant:.2f} €**")
                            confirmer=st.form_submit_button('✅ Livraison terminée et montant encaissé')
                        if confirmer:
                            with db_conn() as db:
                                db.execute("UPDATE commandes SET statut='livrée',montant_encaisse=? WHERE id=? AND statut='réservée'",(montant,c['id']))
                                for i,p in enumerate(lignes):
                                    db.execute('INSERT OR REPLACE INTO lignes_livrees VALUES (?,?,?)',(c['id'],p['produit'],gardees[i]))
                            st.success('Livraison enregistrée. Les articles refusés doivent être réintégrés manuellement au stock Google Sheets.')
                            st.rerun()
                        if st.button('Annuler la réservation',key='cancel_'+c['id']):
                            annuler_reservation(c['id'])
                            st.warning('Réservation annulée. Vérifiez manuellement le stock.')
                            st.rerun()
                    else:
                        st.write(f"Montant encaissé : {c['montant_encaisse'] if c['montant_encaisse'] is not None else '—'}")
 
initialiser_db()
 
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
 
 
 
            for index, produit in enumerate(st.session_state.panier):
                sous_total = produit["quantite"] * produit["prix"]
                total_articles += sous_total
                st.markdown(f"**{produit['produit']}**")
                st.caption(f"{produit['prix']:.2f} € / unité · Sous-total : {sous_total:.2f} €")
                col_moins, col_qte, col_plus, col_suppr = st.columns(4)
                with col_moins:
                    if st.button("−", key=f"moins_{index}", help="Retirer une unité"):
                        diminuer_du_panier(index)
                        st.rerun()
                with col_qte:
                    st.markdown(f"**{produit['quantite']}**")
                with col_plus:
                    if st.button("+", key=f"plus_{index}", help="Ajouter une unité"):
                        try:
                            df_actuel = charger_produits()
                            correspondances = df_actuel[
                                df_actuel.apply(nom_produit, axis=1) == produit["produit"]
                            ]
                            if not correspondances.empty:
                                ajouter_au_panier(correspondances.iloc[0])
                                st.rerun()
                            else:
                                st.warning("Produit introuvable dans le catalogue.")
                        except Exception:
                            st.warning("Impossible de vérifier le stock actuellement.")
                with col_suppr:
                    if st.button("🗑️", key=f"suppr_{index}", help="Supprimer la ligne"):
                        supprimer_du_panier(index)
                        st.rerun()
                st.divider()
 
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
 
 
 
            mode_remise = st.radio(
                "📍 Comment souhaitez-vous récupérer votre commande ?",
                ["Point de rendez-vous", "Livraison à domicile"],
                key="mode_remise_client"
            )
            adresse_livraison = st.text_area(
 
                "Lieu de rendez-vous proposé (commune et endroit précis)" if mode_remise == "Point de rendez-vous" else "Adresse complète de livraison",
 
                key="client_adresse"
 
            )
 
 
 
            precision_lieu = st.text_input('Précisions pour se retrouver (facultatif)', key='precision_lieu_client')
            st.caption('Le lieu et le créneau seront confirmés par Sarah avant le rendez-vous.')
            telephone_client = st.text_input('Téléphone pour organiser la livraison *', key='client_tel')
            email_client = st.text_input('E-mail (pour recevoir votre confirmation)', key='client_email')
            disponibles = [c for c in places_disponibles() if c['reservees'] < c['capacite']]
            choix = {libelle_creneau(c): c for c in disponibles}
            creneau_choisi = st.selectbox('📅 Choisissez votre créneau de livraison *', list(choix), index=None, placeholder='Sélectionnez un créneau') if choix else None
            if not choix:
                st.warning('Aucun créneau ouvert pour le moment. Revenez bientôt !')
            st.caption('Aucun paiement à l’avance. À la remise, vérifiez les articles et ne payez que ceux que vous gardez.')
            premiere_commande = st.checkbox(
                "🎁 C'est ma première commande : je souhaite bénéficier de la livraison offerte",
                key="premiere_commande",
                help="Offre réservée à la première commande, sous réserve de vérification et de zone desservie."
            )
            st.caption("Les frais de livraison ne sont pas inclus dans le total des articles. Sarah confirmera l'éligibilité et les modalités avant la livraison.")
 
            if st.session_state.commande_stock_en_erreur:
                st.error("Commande déjà transmise à la boutique, mais problème de stock. Contactez la boutique avant toute nouvelle tentative pour éviter un doublon.")
            if st.button(
                "🚀 Valider ma commande",
                width="stretch",
                disabled=st.session_state.commande_stock_en_erreur
            ):
 
                if (
 
                    nom_client.strip() == ""
 
                    or adresse_livraison.strip() == ""
                    or not telephone_client.strip()
                    or not creneau_choisi
 
                ):
 
                    st.error(
 
                        "Veuillez remplir votre nom et "
 
                        "votre adresse, votre téléphone et un créneau pour valider."
 
                    )
 
 
 
                else:
 
                    # Copie du panier avant toute opération.
 
                    panier_commande = [
 
                        produit.copy()
 
                        for produit
 
                        in st.session_state.panier
 
                    ]
 
 
 
                    # Revalider les prix depuis la feuille, pas depuis l'URL du panier.
                    try:
                        catalogue=charger_produits()
                        index_catalogue={nom_produit(r):r for _,r in catalogue.iterrows()}
                        for p in panier_commande:
                            if p['produit'] not in index_catalogue:
                                raise ValueError('Article introuvable : '+p['produit'])
                            article=index_catalogue[p['produit']]
                            if obtenir_stock(article)<p['quantite']:
                                raise ValueError('Stock insuffisant : '+p['produit'])
                            promo=obtenir_prix_promo(article)
                            p['prix']=promo if promo is not None else obtenir_prix(article)
                        total_general=sum(p['prix']*p['quantite'] for p in panier_commande)
                        ref=secrets.token_hex(6).upper()
                        commande={'id':ref,'nom':nom_client.strip(),'telephone':telephone_client.strip(),
                          'email':email_client.strip(),'adresse':adresse_livraison.strip(),
                          'mode_remise':mode_remise,'precision_lieu':precision_lieu.strip(),
                          'creneau_id':choix[creneau_choisi]['id'],'panier':panier_commande,
                          'total':total_general,'premiere_commande':premiere_commande}
                        reserve,erreur=reserver_commande(commande)
                        if not reserve:
                            st.error(erreur)
                        else:
                            discord_ok,discord_erreur=envoyer_commande_discord(
                              commande['nom'],f"{commande['mode_remise']} — {commande['adresse']} — {commande['precision_lieu']}",panier_commande,total_general,
                              total_general,premiere_commande,telephone_client,email_client,
                              creneau_choisi,ref)
                            if not discord_ok:
                                annuler_reservation(ref)
                                st.error('Réservation annulée : notification boutique impossible. '+discord_erreur)
                            else:
                                stock_ok,erreurs_stock=retirer_stock_commande(panier_commande)
                                if not stock_ok:
                                    st.session_state.commande_stock_en_erreur=True
                                    st.error('Commande '+ref+' transmise à Sarah, mais stock non mis à jour. Ne recommencez pas ; contactez la boutique.')
                                    for erreur_stock in erreurs_stock:
                                        st.caption(str(erreur_stock))
                                else:
                                    email_ok=envoyer_email_confirmation(commande,creneau_choisi)
                                    st.session_state.confirmation_commande={
                                      'nombre':sum(p['quantite'] for p in panier_commande),
                                      'total':total_general,'livraison_demandee':premiere_commande,
                                      'reference':ref,'creneau':creneau_choisi,'email_ok':email_ok,
                                      'email_demande':bool(email_client.strip()),
                                      'lieu':commande['adresse'],'mode_remise':mode_remise}
                                    st.session_state.animation_confirmation=True
                                    vider_panier()
                                    st.cache_data.clear()
                                    st.rerun()
                    except Exception as erreur:
                        st.error('Impossible de valider la commande : '+str(erreur))
    st.sidebar.markdown("---")
 
 
 
# AFFICHAGE DE LA BOUTIQUE ET DU CATALOGUE PRINCIPAL
 
# ============================================================
 
afficher_sidebar_complete()
 
# Confirmation visible après le rechargement de la page.
if st.session_state.confirmation_commande:
    recap = st.session_state.confirmation_commande
    st.markdown("""
    <div style="background:#F2E3E9;border:2px solid #C68CA3;border-radius:22px;
    padding:26px;text-align:center;margin:14px 0 24px 0;">
      <div style="font-size:42px">🎉 🌸 🎉</div>
      <div style="font-size:26px;color:#713C50;font-weight:750">Merci pour votre commande !</div>
      <div style="font-size:16px;color:#775365;margin-top:8px">
        Votre commande a bien été enregistrée et transmise à la boutique ♡
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.success(f"✅ Confirmation : {recap['nombre']} article(s) — Total : {recap['total']:.2f} €")
    st.info(f"📅 Créneau demandé : {recap.get('creneau','—')} · 📍 {recap.get('mode_remise','')} : {recap.get('lieu','')} · Référence : {recap.get('reference','—')}")
    if recap.get('email_demande'):
        st.info('💌 E-mail de confirmation envoyé.' if recap.get('email_ok') else '💌 Envoi de l’e-mail indisponible. Conservez cette référence de commande.')
    if recap.get("livraison_demandee"):
        st.info("🎁 Votre demande de livraison offerte a été transmise. Sarah vérifiera votre éligibilité et vous confirmera les modalités.")
    st.info("La boutique a reçu votre demande. Sarah confirmera le lieu et le créneau avant le rendez-vous.")
    if st.session_state.animation_confirmation:
        st.balloons()
        st.session_state.animation_confirmation = False
    if st.button("🌸 Fermer la confirmation", key="fermer_confirmation"):
        st.session_state.confirmation_commande = None
        st.rerun()
 
 
 
 
 
# Navigation principale — la liste de souhaits n'encombre plus l'accueil.
page = st.radio(
    "Navigation",
    ["🏠 Accueil", "🛍️ Boutique", "💝 Liste de souhaits", "🚚 Livraisons", "🔐 Administration"],
    horizontal=True,
    label_visibility="collapsed",
    key="navigation_boutique",
)
 
if page == '🏠 Accueil':
    st.markdown("""
    <div style="background:linear-gradient(115deg,#EFD9E1 0%,#FAF0F2 65%,#FFF9F7 100%);border:1px solid #E7CBD6;border-radius:25px;padding:35px 30px;margin-bottom:22px;box-shadow:0 8px 26px rgba(102,55,77,.06)">
      <div style="font-size:12px;letter-spacing:2.2px;color:#935D73;font-weight:700">✿ LA BOUTIQUE DES PETITS PRIX ✿</div>
      <div style="font-family:Georgia,serif;font-size:clamp(29px,3.5vw,49px);line-height:1.15;color:#66374D;margin:12px 0">Mes Bons Plans de Sarah 🌸</div>
      <div style="color:#805468;font-size:17px;margin-bottom:12px">Vos marques préférées à prix doux ♡</div>
      <div style="color:#6B5260;font-size:14px">Lessive · Entretien · Hygiène · Promotions</div>
    </div>
    """, unsafe_allow_html=True)
 
    st.markdown("""
    <div style="background:#EEDBE3;border:1px solid #DFC2CE;border-radius:22px;padding:24px;margin:16px 0;color:#713C50;text-align:center">
    <div style="font-size:28px">🎁 🌸</div>
    <div style="font-size:24px;font-weight:750">Livraison offerte pour votre première commande !</div>
    <div style="font-size:14px;margin-top:8px">Cochez « Première commande » dans votre panier pour demander votre avantage ♡</div>
    <div style="font-size:12px;margin-top:8px">Sous réserve de vérification et de zone de livraison desservie. Frais éventuels confirmés avant livraison.</div>
    </div>
    """, unsafe_allow_html=True)
 
    st.markdown("### 🛍️ Vos produits à petits prix")
    st.caption("Parcourez la boutique, ajoutez vos articles au panier, puis choisissez votre créneau et votre lieu de rendez-vous.")
    if st.button("Découvrir les produits 🌸", width="stretch"):
        st.session_state.navigation_boutique = "🛍️ Boutique"
        st.rerun()
elif page == "💝 Liste de souhaits":
    st.title("💝 Votre liste de souhaits")
    with st.expander("📝 Ma liste de courses ♡ — demander la recherche de produits", expanded=False):
        st.write("Vous cherchez un article absent du catalogue ? Envoyez votre liste. Sarah recherchera les produits et vous répondra avec les prix et disponibilités, sans obligation d'achat.")
        with st.form("form_liste_courses", clear_on_submit=True):
            nom_recherche = st.text_input("Votre prénom et nom", max_chars=100)
            contact_recherche = st.text_input("Votre téléphone ou e-mail pour recevoir une réponse", max_chars=150)
            liste_recherche = st.text_area("Produits recherchés (marque, format, quantité si possible)", placeholder="Ex. Ariel 40 lavages, shampoing Garnier...", max_chars=1100)
            accord_contact = st.checkbox("J'accepte que mes coordonnées soient utilisées pour répondre à ma demande.")
            soumettre_recherche = st.form_submit_button("💌 Envoyer ma liste à Sarah", width="stretch")
        if soumettre_recherche:
            if not (nom_recherche.strip() and contact_recherche.strip() and liste_recherche.strip() and accord_contact):
                st.warning("Complétez votre nom, un moyen de contact, votre liste et l'autorisation de réponse.")
            else:
                ok, erreur = envoyer_liste_courses(nom_recherche.strip(), contact_recherche.strip(), liste_recherche.strip())
                if ok:
                    st.success("🌸 Votre liste a bien été envoyée à Sarah ! Ce n'est pas une commande.")
                else:
                    st.error("Votre demande n'a pas pu être envoyée : " + erreur)
elif page == "🚚 Livraisons":
    afficher_planning_public()
    st.info("Au moment de valider le panier, choisissez un créneau d'une heure et proposez un lieu de rendez-vous. Sarah confirmera le lieu et l'horaire.")
elif page == "🔐 Administration":
    afficher_admin()
elif page == "🛍️ Boutique":
    st.title("🛍️ La boutique")
 
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
 
 
 
            st.markdown("### ✨ Explorez nos rayons")
            categories_visibles = [c for c in categories_disponibles if c != "Tous"][:5]
            if "rayon_actif" not in st.session_state:
                st.session_state.rayon_actif = "Tous"
            if categories_visibles:
                colonnes_rayons = st.columns(len(categories_visibles))
                for col, categorie in zip(colonnes_rayons, categories_visibles):
                    with col:
                        if st.button("♡ " + str(categorie), key="rayon_" + str(categorie), width="stretch"):
                            st.session_state.rayon_actif = categorie
                            st.rerun()
            st.markdown("### 🛍️ Notre sélection")
            # ========================================================
            # RECHERCHE PRODUITS
            # ========================================================
            recherche = st.text_input(
                "🔎 Rechercher un produit :",
                placeholder="Ex. lessive, Xtra, shampoing..."
            )
 
            categorie_selectionnee = st.selectbox(
 
                "📁 Filtrer par rayon / catégorie :",
 
                categories_disponibles,
                index=categories_disponibles.index(st.session_state.rayon_actif) if st.session_state.rayon_actif in categories_disponibles else 0
 
            )
            st.session_state.rayon_actif = categorie_selectionnee
 
 
 
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
 
 
 
            colonnes_grille = st.columns(3)
 
 
 
            for index, row in (
 
                df_filtre.reset_index(drop=True).iterrows()
 
            ):
 
                colonne_cible = (
 
                    colonnes_grille[index % 3]
 
                )
 
 
 
                with colonne_cible:
                    lien_photo = photo_produit(row)
 
 
 
                    if lien_photo:
 
                        st.image(
 
                            lien_photo,
 
                            width="stretch"
 
                        )
 
                    else:
 
                        st.image(
 
                            "https://via.placeholder.com/"
 
                            "150?text=Pas+de+photo",
 
                            width="stretch"
 
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
 
 
 
                    prix_comp=prix_comparaison(row)
                    prix_vente=prix_pr if prix_pr is not None else prix_init
                    if prix_comp > prix_vente > 0:
                        economie=prix_comp-prix_vente
                        pct=100*economie/prix_comp
                        st.caption(f"💚 Comparaison indicative : {economie:.2f} € de moins ({pct:.0f} %) qu'un prix constaté de {prix_comp:.2f} € — source et date à vérifier.")
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
 
                            key=f"add_{row.name}_{index}",
 
                            width="stretch",
 
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
