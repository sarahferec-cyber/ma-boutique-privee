import streamlit as st
import pandas as pd
import requests
import io
import time
import json

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
    """Transforme proprement une valeur en nombre."""
    try:
        if pd.isna(valeur):
            return valeur_defaut
        texte = str(valeur).strip()
        if texte.lower() in ["", "nan", "none", "n/a"]:
            return valeur_defaut
        texte = texte.replace("€", "")
        texte = texte.replace(" ", "")
        texte = texte.replace(",", ".")
        return float(texte)
    except (ValueError, TypeError):
        return valeur_defaut

def envoyer_discord(message):
    """Envoie un message sur Discord si le webhook est configuré."""
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
    """Charge le Google Sheets en CSV et nettoie les colonnes."""
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
        # Nettoyage des noms de colonnes
        data.columns = [
            str(c).strip().lower()
            for c in data.columns
        ]
        # Normalisation des accents
        data.columns = (
            data.columns
            .str.replace("é", "e", regex=False)
            .str.replace("è", "e", regex=False)
            .str.replace("ê", "e", regex=False)
            .str.replace("ë", "e", regex=False)
            .str.replace("à", "a", regex=False)
            .str.replace("â", "a", regex=False)
            .str.replace("ä", "a", regex=False)
            .str.replace("ù", "u", regex=False)
            .str.replace("û", "u", regex=False)
            .str.replace("ü", "u", regex=False)
            .str.replace("ô", "o", regex=False)
            .str.replace("î", "i", regex=False)
            .str.replace("ï", "i", regex=False)
            .str.replace("ç", "c", regex=False)
        )
        # Nettoyage du contenu
        for col in data.select_dtypes(include=["object"]).columns:
            data[col] = (
                data[col]
                .astype(str)
                .str.replace('"', '', regex=False)
                .str.strip()
            )
        return data
    except Exception as erreur:
        st.error("❌ Impossible de charger les données Google Sheets.")
        st.caption(f"Détail technique : {erreur}")
        return pd.DataFrame()

def trouver_colonne(dataframe, noms_possibles):
    """Retourne la première colonne trouvée dans la liste."""
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

# ============================================================
# 7. CONNEXION
# ============================================================
if not st.session_state.connecte:
    st.title("🎀 Espace Privé : La Boutique des Bons Plans 🌸")
    with st.form("formulaire_connexion"):
        identifiant = st.text_input("👤 Votre Identifiant :").strip().lower()
        mot_de_passe = st.text_input("🔑 Votre Mot de passe :", type="password")
        connexion = st.form_submit_button("✨ Entrer dans la boutique")
        if connexion:
            if identifiant in COMPTES_AUTORISES and COMPTES_AUTORISES[identifiant] == mot_de_passe:
                st.session_state.connecte = True
                st.session_state.utilisateur = identifiant
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect. ❌")
    st.stop()

# ============================================================
# 8. EN-TÊTE
# ============================================================
st.title("🌸 La Boutique des Bons Plans 🛍️")
st.write(f"Coucou **{st.session_state.utilisateur.capitalize()}** !")

# ============================================================
# 9. DÉCONNEXION
# ============================================================
if st.sidebar.button("🚪 Se déconnecter"):
    st.session_state.connecte = False
    st.session_state.utilisateur = ""
    st.session_state.panier = {}
    st.rerun()
    
# ============================================================
# 10. CHARGEMENT GOOGLE SHEETS
# ============================================================
df = load_clean_data()
if df.empty:
    st.warning("⚠️ Aucune donnée produit disponible.")
    st.stop()

# ============================================================
# 11. RECHERCHE ET RECOMPOSITION DES COLONNES IMPORTÉES
# ============================================================
col_nom = trouver_colonne(df, ["produit", "nom", "articles", "article"])
col_cat = trouver_colonne(df, ["categorie", "type", "rayon"])
col_format = trouver_colonne(df, ["format", "taille", "volume", "poids"])
col_lavages = trouver_colonne(df, ["lavages", "lavage", "quantite_lavages"])
col_stock = trouver_colonne(df, ["quantite", "stock", "en_stock", "nbre", "nombre"])
col_prix_base = trouver_colonne(df, ["prix_base", "prix_initial", "prix", "ancien_prix"])
col_prix_promo = trouver_colonne(df, ["prix_promo", "promo", "prix_reduit", "nouveau_prix"])

if not col_nom or not col_stock:
    st.error("❌ Les colonnes essentielles ('Produit' et 'Quantité') n'ont pas pu être détectées.")
    st.stop()

# ============================================================
# 12. BARRE LATÉRALE : FILTRES & PANIER
# ============================================================
st.sidebar.header("🎯 Filtres de recherche")

if col_cat:
    categories_disponibles = ["Toutes"] + sorted(list(df[col_cat].dropna().unique()))
else:
    categories_disponibles = ["Toutes"]
categorie_choisie = st.sidebar.selectbox("Filtrer par rayon :", categories_disponibles)

st.sidebar.markdown("---")
st.sidebar.header("🛒 Votre Panier")

if not st.session_state.panier:
    st.sidebar.info("Votre panier est vide pour le moment. ✨")
else:
    total_panier = 0.0
    articles_a_supprimer = []
    
    for nom_art, details_art in list(st.session_state.panier.items()):
        sous_total = details_art["quantite"] * details_art["prix"]
        total_panier += sous_total
        
        st.sidebar.markdown(f"**{nom_art}**")
        st.sidebar.caption(f"Qté : {details_art['quantite']} × {details_art['prix']:.2f} € = **{sous_total:.2f} €**")
        
        if st.sidebar.button(f"🗑️ Retirer", key=f"del_{nom_art}"):
            articles_a_supprimer.append(nom_art)
            
    for art in articles_a_supprimer:
        del st.session_state.panier[art]
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"Total : {total_panier:.2f} €")
    
    if st.sidebar.button("✅ Valider ma commande", key="bouton_validation_panier"):
        with st.spinner("Prise en compte de votre commande en cours..."):
Utilisez le code avec précaution.succes_total = Truedetails_commande_discord = []for nom_art, details_art in st.session_state.panier.items():payload = {"action": "retirer","produit": nom_art,"quantite": int(details_art["quantite"]),"utilisateur": st.session_state.utilisateur}try:res = requests.post(URL_MACRO_STOCK, json=payload, timeout=10)if res.status_code != 200:succes_total = Falseelse:details_commande_discord.append(f"- {details_art['quantite']}x {nom_art} ({details_art['prix']:.2f}€/u)")except Exception:succes_total = Falseif succes_total:msg_discord = f"🎉 Nouvelle commande de {st.session_state.utilisateur.capitalize()} !\n" + "\n".join(details_commande_discord) + f"\n\n💰 Total : {total_panier:.2f} €"envoyer_discord(msg_discord)st.session_state.panier = {}st.session_state.achat_reussi = Truest.rerun()else:st.error("❌ Une erreur est survenue lors de la mise à jour des stocks.")if st.session_state.achat_reussi:st.success("🎉 Félicitations ! Votre commande a bien été enregistrée.")st.session_state.achat_reussi = False============================================================13. FILTRAGE ET AFFICHAGE DU CATALOGUE PRODUITS============================================================df_filtre = df.copy()if col_cat and categorie_choisie != "Toutes":df_filtre = df_filtre[df_filtre[col_cat] == categorie_choisie]colonnes_produits = st.columns(3)for index, row in df_filtre.iterrows():nom_produit = row[col_nom]stock_actuel = int(convertir_float(row[col_stock]))if pd.isna(nom_produit) or str(nom_produit).strip() == "" or stock_actuel <= 0:continuepx_base = convertir_float(row[col_prix_base]) if col_prix_base else 0.0px_promo = convertir_float(row[col_prix_promo]) if col_prix_promo else px_basepourcentage_remise = int(((px_base - px_promo) / px_base) * 100) if px_base > px_promo else 0col_courante = colonnes_produits[index % 3]with col_courante:if pourcentage_remise > 0:texte_promo_html = f"""🔥 ÉCONOMIE : -{pourcentage_remise}%"""else:texte_promo_html = "Prix bas garanti ✨"st.markdown(f"""{nom_produit}📦 Format : {row[col_format] if col_format and not pd.isna(row[col_format]) else 'N/A'}{f"{px_base:.2f} €" if px_base > px_promo else ""}{px_promo:.2f} €{texte_promo_html}Disponibles : {stock_actuel} restant(s)""", unsafe_allow_html=True)quantite_selectionnee = st.number_input(f"Quantité pour {nom_produit}",min_value=1,max_value=stock_actuel,value=1,key=f"input_{index}")if st.button(f"🛒 Ajouter au panier", key=f"btn_{index}"):if nom_produit in st.session_state.panier:nvelle_qte = st.session_state.panier[nom_produit]["quantite"] + quantite_selectionneeif nvelle_qte <= stock_actuel:st.session_state.panier[nom_produit]["quantite"] = nvelle_qtest.toast(f"✅ Quantité mise à jour pour {nom_produit} !", icon="🛒")time.sleep(0.5)st.rerun()else:st.error(f"Impossible d'ajouter plus que le stock disponible ({stock_actuel}).")else:st.session_state.panier[nom_produit] = {"quantite": quantite_selectionnee,"prix": px_promo}st.toast(f"🛒 {nom_produit} ajouté au panier !", icon="✨")time.sleep(0.5)st.rerun()============================================================14. PIED DE PAGE============================================================st.markdown("---")st.caption("Application développée avec 🌸 pour Mes Bons Plans de Sarah. Tous droits réservés 2026.")
<FollowUp>
