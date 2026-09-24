2. Code Source Python
import streamlit as st
import pandas as pd
import requests
import re
import unicodedata

# ============================================================
# CONFIGURATION ET CONSTANTES
# ============================================================
NOM_BOUTIQUE = "Mes Bons Plans de Sarah 🌸"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit?usp=sharing"
STOCK_API_URL = "https://script.google.com/macros/s/AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/exec"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1549946850885238865/OItwwHS0spEUH0vzmBSJjAaCXwx2Yicaz2l30EolaALbmEufafnZI36M5OsuT3FlNqt_"

PRIX_CARBURANT = 1.80
CONSOMMATION_L_100KM = 6.5
FRAIS_LIVRAISON_BASE = 4.90

# ============================================================
# CONFIGURATION INTERFACE STREAMLIT
# ============================================================
st.set_page_config(
    page_title=NOM_BOUTIQUE,
    page_icon="🌸",
    layout="wide"
)

# ============================================================
# INITIALISATION ET PERSISTANCE DE LA SESSION
# ============================================================
if "panier" not in st.session_state:
    st.session_state.panier = []
if "commande_envoyee" not in st.session_state:
    st.session_state.commande_envoyee = False
if "distance_ar" not in st.session_state:
    st.session_state.distance_ar = 50.0  # Trajet Aller-Retour Aigues-Vives ➡️ Carcassonne
if "consommation_100" not in st.session_state:
    st.session_state.consommation_100 = CONSOMMATION_L_100KM
if "prix_litre" not in st.session_state:
    st.session_state.prix_litre = PRIX_CARBURANT

# ============================================================
# FONCTIONS OUTILS ET NORMALISATION
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
    re_sub = re.sub(r"\s+", " ", texte).strip()
    return re_sub

def trouver_colonne(article, noms_possibles):
    """Cherche une colonne dans une ligne de données ou un dictionnaire."""
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
    """Convertit proprement une valeur texte ou monétaire en nombre flottant."""
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
    colonne = trouver_colonne(article, ["Denomination", "Dénomination", "Produit", "Nom", "Article"])
    return str(article.get(colonne, "Produit sans nom")).strip() if colonne else "Produit sans nom"

def categorie_produit(article):
    colonne = trouver_colonne(article, ["Categorie", "Catégorie", "Catégorie produit", "Famille"])
    valeur = article.get(colonne, "Autre") if colonne else "Autre"
    return "Autre" if pd.isna(valeur) or str(valeur).strip() == "" else str(valeur).strip()

def photo_produit(article):
    colonne = trouver_colonne(article, ["Photo produit", "Photo", "Image", "Photo produit URL"])
    return str(article.get(colonne, "")).strip() if colonne and not pd.isna(article.get(colonne)) else ""

def obtenir_stock(article):
    colonne = trouver_colonne(article, ["Quantité", "Quantite", "Stock", "Stocks"])
    return int(convertir_nombre(article.get(colonne, 0), 0)) if colonne else 0

def obtenir_prix(article):
    colonne = trouver_colonne(article, ["Prix initial", "Prix", "Prix normal", "Tarif"])
    return convertir_nombre(article.get(colonne, 0.0), 0.0) if colonne else 0.0

def obtenir_prix_promo(article):
    colonne = trouver_colonne(article, ["Prix promo", "Promo", "Prix promotion", "Prix promotionnel"])
    if colonne is None:
        return None
    valeur = article.get(colonne, "")
    if pd.isna(valeur) or str(valeur).strip() == "":
        return None
    prix = convertir_nombre(valeur, 0.0)
    return prix if prix > 0 else None

def format_produit(article):
    colonne = trouver_colonne(article, ["Litre / Gramme", "Litre/Gramme", "Format", "Poids", "Volume"])
    return str(article.get(colonne, "")).strip() if colonne and not pd.isna(article.get(colonne)) else ""

def prix_kg_litre(article):
    colonne = trouver_colonne(article, ["Prix au Kg / Litre", "Prix au Kg/Litre", "Prix Kg", "Prix Litre", "Prix au kilo", "Prix au litre"])
    return str(article.get(colonne, "")).strip() if colonne and not pd.isna(article.get(colonne)) else ""

@st.cache_data(ttl=60)
def charger_produits():
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", GOOGLE_SHEET_URL)
    if not match:
        raise ValueError("Impossible de trouver l'identifiant du Google Sheet.")
    spreadsheet_id = match.group(1)
    url_csv = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
    try:
        dataframe = pd.read_csv(url_csv)
    except Exception as erreur:
        raise RuntimeError(f"Impossible de charger le Google Sheet : {erreur}")
    if dataframe.empty:
        return dataframe
    dataframe.columns = [str(colonne).strip() for colonne in dataframe.columns]
    dataframe = dataframe.dropna(how="all").reset_index(drop=True)
    return dataframe

# ============================================================
# LOGIQUE ET INTERACTIONS DU PANIER
# ============================================================
def ajouter_au_panier(article):
    nom = nom_produit(article)
    prix_normal = obtenir_prix(article)
    prix_promo = obtenir_prix_promo(article)
    prix_final = prix_promo if prix_promo is not None else prix_normal
    
    for produit in st.session_state.panier:
        if produit["produit"] == nom:
            stock = obtenir_stock(article)
            if produit["quantite"] < stock:
                produit["quantite"] += 1
            return
    st.session_state.panier.append({
        "produit": nom,
        "quantite": 1,
        "prix": prix_final
    })

# ============================================================
# RENDU DU MENU LATÉRAL GAUCHE (SIDEBAR COMPLETE)
# ============================================================
def afficher_sidebar_complete():
    st.sidebar.header(f"🌸 {NOM_BOUTIQUE}")
    st.sidebar.markdown("---")
    
    # --------------------------------------------------------
    # VOLET 1 : GESTION DU PANIER DÉROULANT
    # --------------------------------------------------------
    st.sidebar.subheader("🛒 Mon Espace Achat")
    nombre_articles = sum(produit["quantite"] for produit in st.session_state.panier)
    
    with st.sidebar.expander(f"💼 Votre Panier ({nombre_articles} articles)", expanded=True):
        if not st.session_state.panier:
            st.info("Votre panier est vide 🌸")
        else:
            total_articles = 0.0
            for index, produit in enumerate(st.session_state.panier):
                sous_total = produit["quantite"] * produit["prix"]
                total_articles += sous_total
                
                st.markdown(f"**{produit['produit']}**")
                col_qte, col_prix, col_suppr = st.columns(3)
                
                with col_qte:
                    st.caption(f"Qté : {produit['quantite']}")
                with col_prix:
                    st.caption(f"{sous_total:.2f} €")
                with col_suppr:
                    if st.button("❌", key=f"suppr_{index}"):
                        st.session_state.panier.pop(index)
                        st.rerun()
                st.markdown("---")
            
            # Application de la règle de livraison offerte dès 50€
            st.markdown(f"Sous-total articles : **{total_articles:.2f} €**")
            
            if total_articles >= 50.0:
                frais_livraison = 0.0
                st.success("🎉 Livraison offerte ! (Panier ≥ 50€)")
            else:
                frais_livraison = FRAIS_LIVRAISON_BASE
                manque_pour_gratuite = 50.0 - total_articles
                st.warning(f"💡 Ajoutez **{manque_pour_gratuite:.2f} €** pour débloquer la livraison gratuite.")
                st.markdown(f"Frais de livraison : {frais_livraison:.2f} €")
            
            total_general = total_articles + frais_livraison
            st.markdown(f"### Total Général : **{total_general:.2f} €**")
            
            # Coordonnées du client
            st.markdown("#### 📝 Informations de commande")
            nom_client = st.text_input("Votre Nom et Prénom", key="client_nom")
            adresse_livraison = st.text_area("Adresse (Aigues-Vives ou environs)", key="client_adresse")
            
            if st.button("🚀 Valider ma commande", use_container_width=True):
                if nom_client.strip() == "" or adresse_livraison.strip() == "":
                    st.error("Veuillez remplir votre nom et votre adresse pour valider.")
                else:
                    st.success("Commande enregistrée ! ✨")
                    st.session_state.panier = []
                    st.rerun()

    st.sidebar.markdown("---")

    # --------------------------------------------------------
    # VOLET 2 : CALCULATEUR CARBURANT PERSISTANT (EN MÉMOIRE)
    # --------------------------------------------------------
    st.sidebar.subheader("⛽ Calculateur Carburant")
    
    with st.sidebar.expander("📊 Estimation Économie Trajet A/R", expanded=False):
        st.markdown("*Ces valeurs restent mémorisées d'une page à l'autre.*")
        
        st.session_state.distance_ar = st.number_input(
            "Distance Aller-Retour (km)", 
            value=st.session_state.distance_ar, 
            step=1.0
        )
        st.session_state.consommation_100 = st.number_input(
            "Consommation moyenne (L/100km)", 
            value=st.session_state.consommation_100, 
            step=0.1
        )
        st.session_state.prix_litre = st.number_input(
            "Prix du litre de carburant (€)", 
            value=st.session_state.prix_litre, 
            step=0.01
        )
        
        # Calcul mathématique basé sur le trajet Aller-Retour direct
        litres_trajet = (st.session_state.distance_ar * st.session_state.consommation_100) / 100
        cout_carburant_trajet = litres_trajet * st.session_state.prix_litre
        cout_mensuel_22j = cout_carburant_trajet * 22
        
        st.markdown("---")
        st.markdown(f"Coût par trajet A/R : **{cout_carburant_trajet:.2f} €**")
        st.markdown(f"Économie mensuelle (22j) : **{cout_mensuel_22j:.2f} €**")
        st.caption("💡 Trésorerie préservée dès l'arrêt définitif des navettes vers Carcassonne.")

# ============================================================
# AFFICHAGE DE LA BOUTIQUE ET DU CATALOGUE PRINCIPAL
# ============================================================
# Rendu de la barre latérale gauche (panier + carburant)
afficher_sidebar_complete()

# Chargement et affichage des produits au centre
st.title(f"🏪 Bienvenue chez {NOM_BOUTIQUE}")
try:
    df_produits = charger_produits()
    if df_produits.empty:
        st.warning("Aucun produit trouvé dans la base de données Google Sheets.")
    else:
        st.write(f"Catalogue synchronisé en direct : {len(df_produits)} articles disponibles.")
except Exception as e:
    st.error(f"Erreur d'initialisation de la base produit : {e}")


