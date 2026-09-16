import streamlit as st
import pandas as pd
import requests
import io
import time

# 1. Configuration de la page style Amazon Mobile
st.set_page_config(page_title="Mes Bons Plans de Sarah 🌸", page_icon="🛍️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFF5F5; }
    .product-card { padding: 20px; border-radius: 15px; border: 2px solid #FFD1D1; background-color: white; margin-bottom: 20px; text-align: center; }
    .promo-badge { background-color: #FF69B4; color: white; padding: 3px 8px; font-weight: bold; border-radius: 20px; font-size: 13px; }
    [data-testid="stSidebar"] { background-color: #FFEAEF; border-right: 2px solid #FFD1D1; }
    h1, h2, h3 { color: #C71585 !important; font-family: 'Poppins', sans-serif; }
    .stButton>button { background-color: #FF69B4 !important; color: white !important; border-radius: 20px !important; font-weight: bold !important; width: 100%; }
    </style>
""", unsafe_allow_html=True)

     
# 🔐 LISTE DES COMPTES AUTORISÉS
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

if "connecte" not in st.session_state:
    st.session_state.connecte = False
if "utilisateur" not in st.session_state:
    st.session_state.utilisateur = ""
if "achat_reussi" not in st.session_state:
    st.session_state.achat_reussi = False

if not st.session_state.connecte:
    st.title("🎀 Espace Privé : La Boutique des Bons Plans 🌸")
    with st.form("formulaire_connexion"):
        identifiant = st.text_input("👤 Votre Identifiant :").strip().lower()
        mot_de_passe = st.text_input("🔑 Votre Mot de passe :", type="password")
        if st.form_submit_button("✨ Entrer dans la boutique"):
            if identifiant in COMPTES_AUTORISES and COMPTES_AUTORISES[identifiant] == mot_de_passe:
                st.session_state.connecte = True
                st.session_state.utilisateur = identifiant
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect. ❌")
    st.stop()

st.title("🌸 Le Boutique des Bons Plans 🛍️")
st.write(f"Coucou **{st.session_state.utilisateur.capitalize()}** !")

if st.sidebar.button("🚪 Se déconnecter"):
    st.session_state.connecte = False
    st.session_state.utilisateur = ""
    st.rerun()

URL_SHEETS = "https://docs.google.com/spreadsheets/d/1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit?usp=sharing"
URL_DISCORD = "https://discord.com/api/webhooks/1549589858765512704/gPHFkop5lN7wO7ITDsRsvfr_rymSGqsobjaz3lAkZ1LfSVXfSdLsX2NCaDWvhH2-pu1M"
URL_MACRO_STOCK = "https://script.google.com/macros/s/AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/exec"

def load_clean_data():
    try:
        csv_url = URL_SHEETS.replace("/edit?usp=sharing", "/export?format=csv").replace("/edit", "/export?format=csv")
        reponse = requests.get(csv_url)
        reponse.encoding = 'utf-8'
        data = pd.read_csv(io.StringIO(reponse.text), encoding="utf-8", engine="python", on_bad_lines='skip')
        
        # NETTOYAGE INTELLIGENT DES COLONNES
        data.columns = [str(c).strip().lower() for c in data.columns]
        data.columns = data.columns.str.replace('é', 'e').str.replace('è', 'e').str.replace('à', 'a')
        
        for col in data.select_dtypes(include=['object']).columns:
            data[col] = data[col].astype(str).str.replace('"', '').str.strip()
            
        return data
    except:
        return pd.DataFrame()

df = load_clean_data()

if df.empty:
    st.warning("Erreur de chargement des données Sheets...")
    st.stop()

if "panier" not in st.session_state:
    st.session_state.panier = {}

# Recherche adaptative des colonnes
col_photo = 'photo produit' if 'photo produit' in df.columns else 'photo'
col_nom = 'denomination' if 'denomination' in df.columns else 'denom'
col_cat = 'categorie' if 'categorie' in df.columns else 'cat'
col_fmt = 'litre / gramme' if 'litre / gramme' in df.columns else 'format'
col_stock = 'quantite' if 'quantite' in df.columns else 'stock'
col_pinit = 'prix initial' if 'prix initial' in df.columns else 'initial'
col_ppromo = 'prix promo' if 'prix promo' in df.columns else 'promo'

st.sidebar.markdown("## 🎀 Navigation")

# 1. DECOUPAGE INTELLIGENT : On sépare les catégories par la virgule pour éviter les rayons doublons
categories_uniques = set()
if col_cat in df.columns:
    for cellule in df[col_cat].dropna().astype(str):
        for morceau in cellule.split(','):
            nom_nettoye = morceau.strip().capitalize()
            if nom_nettoye != '' and nom_nettoye.lower() != 'nan':
                categories_uniques.add(nom_nettoye)

categories_triees = sorted(list(categories_uniques))

# Dictionnaire de correspondance pour attribuer le bon émoji à chaque univers
DICTIONNAIRE_EMOJIS = {
    "nouveaute": "🔥",
    "nouveauté": "🔥",
    "lessive": "🧺",
    "hygiene": "✨",
    "hygiène": "✨",
    "entretien": "🧼",
    "menage": "🧹",
    "ménage": "🧹",
    "alimentaire": "🍭",
    "animalerie": "🐱",
    "beaute": "💄",
    "beauté": "💄",
    "boisson": "🥤",
    "cuisine": "🍳"
}

# 2. Création du menu avec émojis adaptés
categories_menu = []
for cat in categories_triees:
    cat_lower = cat.lower()
    # On cherche si un émoji existe pour ce mot, sinon on met un émoji shopping par défaut 🌸
    emoji = DICTIONNAIRE_EMOJIS.get(cat_lower, "🌸")
    categories_menu.append(f"{emoji} {cat}")

# On s'assure que "Tous les rayons" et "Nouveauté" soient placés au tout début dans le bon ordre
# On nettoie la liste pour éviter les doublons textuels de Nouveauté
categories_menu = [c for c in categories_menu if "nouveaut" not in c.lower()]

if "Nouveauté" in categories_triees or "Nouveaute" in categories_triees:
    categories_menu = ["🔥 Nouveauté", "✨ Tous les rayons"] + categories_menu
else:
    categories_menu = ["✨ Tous les rayons"] + categories_menu

# 3. UNIQUE boîte de sélection (L'index=0 affiche Nouveauté en premier d'office)
choix_cat_brut = st.sidebar.selectbox("Faites votre shopping par rayon :", categories_menu, index=0)

# On nettoie la sélection pour retrouver le nom brut de la catégorie pour le filtrage
choix_cat = choix_cat_brut
for emj in DICTIONNAIRE_EMOJIS.values():
    choix_cat = choix_cat.replace(emj, "")
choix_cat = choix_cat.replace("✨", "").strip().lower()

# 4. FILTRAGE MULTI-RAYONS COMPATIBLE VIRGULES
if "tous les rayons" in choix_cat_brut.lower():
    df_filtre = df
else:
    df_filtre = df[df[col_cat].astype(str).str.lower().str.contains(choix_cat, na=False, regex=False)]

st.subheader(f"💫 Sélection : {choix_cat_brut} ({len(df_filtre)} pépites)")
cols = st.columns(3)

for index, row in df_filtre.reset_index().iterrows():
    nom_produit = str(row[col_nom]).strip() if col_nom in row else "Produit sans nom"
    if nom_produit.lower() in ["nan", "", "denomination"]:
        continue
        
    with cols[index % 3]:
        st.markdown('<div class="product-card">', unsafe_allow_html=True)
        cat_nom = str(row[col_cat]).lower() if col_cat in row else ""
        
        # 1. Sélection de l'icône de la carte produit
        icon = "🛍️"
        for mot_cle, emj in DICTIONNAIRE_EMOJIS.items():
            if mot_cle in cat_nom:
                icon = emj
                break
            
        lien_photo = str(row[col_photo]).strip() if col_photo in row else ""
        if lien_photo and lien_photo.startswith('http') and lien_photo != 'nan':
            st.image(lien_photo, use_container_width=True)
        else:
            st.markdown(f"<h1 style='text-align: center; font-size: 50px;'>{icon}</h1>", unsafe_allow_html=True)
            
        # 2. Affichage UNIQUE du nom du produit
        st.markdown(f"### {nom_produit}")
        
        # 3. Affichage du prix au kilo / litre automatique
        prix_unitaire = row['prix au kg / litre'] if 'prix au kg / litre' in row else "N/A"
        st.markdown(f"<p style='color: #C71585; font-size: 13px; font-weight: 500; margin-top: -10px;'>⚖️ {prix_unitaire}</p>", unsafe_allow_html=True)
        
        # 4. Affichage du format (Litre / Gramme)
        fmt = row[col_fmt] if col_fmt in row else "N/A"
        st.markdown(f"<p style='color: #555555; font-size: 14px; margin-bottom: 5px;'>📦 Format : {fmt}</p>", unsafe_allow_html=True)
        
        # 5. Affichage des prix (Initial barré et Promo en gros)
        p_init = row[col_pinit] if col_pinit in row else "0.00"
        p_promo = row[col_ppromo] if col_ppromo in row else "0.00"
        
        st.markdown(f"""
            <p style='font-size: 14px; margin-bottom: 2px;'>Avant : <span style='text-decoration: line-through; color: #888888;'>{p_init} €</span></p>
            <p style='font-size: 20px; font-weight: bold; color: #FF69B4; margin-top: 0px;'>🔥 {p_promo} €</p>
        """, unsafe_allow_html=True)
        
        # 6. Gestion des stocks et bouton d'achat
        try: max_stock = int(float(str(row[col_stock]).replace(' ', '')))
        except: max_stock = 0
            
        if max_stock <= 0:
            st.markdown("<p style='color: red; font-size: 14px; font-weight: bold;'>❌ Rupture de stock !</p>", unsafe_allow_html=True)
        else:
            st.markdown(f"<p style='color: green; font-size: 13px;'>✅ En stock ({max_stock} dispos)</p>", unsafe_allow_html=True)
            
            # Bouton d'achat pour ce produit précis
            if st.button(f"🛒 Prendre ce produit", key=f"btn_{index}"):
                # Code pour ajouter au panier (session_state)
                if nom_produit in st.session_state.panier:
                    if st.session_state.panier[nom_produit]['quantite'] < max_stock:
                        st.session_state.panier[nom_produit]['quantite'] += 1
                        st.success(f"Ajouté ! ✨")
                    else:
                        st.error("Désolé, pas assez de stock disponible !")
                else:
                    st.session_state.panier[nom_produit] = {'quantite': 1, 'prix': p_promo}
                    st.success(f"Ajouté au panier ! ✨")
                    time.sleep(0.5)
                    st.rerun()
                    
        st.markdown('</div>', unsafe_allow_html=True)

# --- FIN DU FICHIER : LE PANIER ROSE ET LA VALIDATION SÉCURISÉE ---
if st.session_state.achat_reussi:
    st.sidebar.success("Commande réalisée ! 🎉 Votre stock est à jour.")
    st.session_state.achat_reussi = False

if st.session_state.panier:
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🛒 Votre Panier Rose")
    
    total_facture = 0.0
    total_economies = 0.0
    texte_message = f"🌸 **Nouvelle commande de {st.session_state.utilisateur.capitalize()}** :\n"
    
    for article, infos in st.session_state.panier.items():
        qte = infos["quantite"]
        prix = infos["prix"]
        eco = infos["economie"]
        
        total_facture += prix * qte
        total_economies += eco
        
        st.sidebar.write(f"• {article} (x{qte}) — {prix*qte:.2f} €")
        texte_message += f"- {article} x{qte} ({prix:.2f}€/u)\n"
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📦 Mode de retrait")
    
    option_livraison = st.sidebar.checkbox("Demander la livraison à domicile 🏠")
    frais_livraison = 0.0
    km_distance = 0
    
    if option_livraison:
        km_distance = st.sidebar.slider("Distance de chez Sarah (en Km) :", min_value=1, max_value=50, value=5, help="Le tarif est de 0,10 € par kilomètre.")
        frais_livraison = km_distance * 0.10  
        st.sidebar.caption(f"🚗 Frais de livraison : +{frais_livraison:.2f} € ({km_distance} km)")
    else:
        st.sidebar.caption("🛒 Retrait gratuit en main propre chez Sarah")

    total_final_avec_livraison = total_facture + frais_livraison

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### Total : **{total_final_avec_livraison:.2f} €**")
    if total_economies > 0:
        st.sidebar.markdown(f"💖 *Vous économisez **{total_economies:.2f} €** sur cet achat !*")
        
    if st.sidebar.button("✨ Valider mon achat"):
        panier_a_traiter = st.session_state.panier.copy()
        st.session_state.panier = {}
        st.session_state.achat_reussi = True
        st.balloons()
        
        msg_discord = f"{texte_message}\n"
        if option_livraison:
            msg_discord += f"🚚 **Option Livraison activée :** {km_distance} Km (+{frais_livraison:.2f}€)\n"
        else:
            msg_discord += "🛒 **Retrait :** En main propre chez Sarah\n"
            
        msg_discord += f"💰 **Total Articles : {total_facture:.2f}€**\n"
        msg_discord += f"⭐ **TOTAL À PAYER : {total_final_avec_livraison:.2f}€**\n"
        msg_discord += f"🌸 **Économie réalisée : {total_economies:.2f}€**"
        
        try:
            requests.post(URL_DISCORD, json={"content": msg_discord}, timeout=3)
        except:
            pass
        
        for article, infos in panier_a_traiter.items():
            payload_stock = {
                "ligne": infos["ligne_sheets"],
                "quantite": infos["quantite"]
            }
            try:
                import json
                requests.post(URL_MACRO_STOCK, data=json.dumps(payload_stock), headers={"Content-Type": "application/json"}, timeout=3)
            except:
                pass
        
        time.sleep(1.0)
        st.rerun()
# --- SECTION : CONDITIONS GÉNÉRALES DE VENTE (CGV) (LIGNE 290) ---
st.sidebar.markdown("---")
with st.sidebar.popover("📄 Conditions Générales de Vente (CGV)"):
    st.markdown("""
    ### ⚖️ Conditions Générales de Vente
    En utilisant la boutique **"Mes Bons Plans de Sarah 🌸"**, vous acceptez les conditions suivantes :
    
    #### 1. 🛍️ Commandes & Réservations
    * Ce site est un espace privé de réservation de produits.
    * Toute validation de panier entraîne l'envoi d'une notification ferme via notre système de messagerie (Discord).
    
    #### 2. 📦 Stocks & Disponibilités
    * Les stocks affichés sont synchronisés en temps réel avec notre inventaire.
    * En cas de rupture de stock simultanée, la priorité est accordée à la première commande validée chronologiquement.
    
    #### 3. 💳 Modalités de Paiement & Retrait
    * Aucun paiement direct n'est effectué sur cette application.
    * Le règlement et la remise des articles s'effectuent selon les modalités convenues directement avec Sarah.
    
    #### 4. 🔒 Protection des Données (RGPD)
    * Les identifiants de connexion servent uniquement à personnaliser votre expérience et sécuriser l'accès à la boutique.
    * Aucune donnée personnelle n'est vendue ou partagée avec des tiers.
    """)
    st.caption("Mise à jour : Mars 2026")

# --- SECTION : ESPACE AVIS, NOTES & AMÉLIORATIONS ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🌸 Votre Avis compte !")

with st.sidebar.form("formulaire_avis_complet", clear_on_submit=True):
    # Système de notation de 1 à 5 étoiles
    note_etoiles = st.slider("Notez votre expérience sur la boutique :", min_value=1, max_value=5, value=5, help="1 = À améliorer, 5 = Parfait !")
    
    # Zone de texte pour les retours (compliments ou critiques constructives)
    avis_texte = st.text_area(
        "Laissez-moi un commentaire ou une idée de produit : 📝", 
        placeholder="Dites-moi ce que vous aimez ou ce que je devrais améliorer (points négatifs, produits manquants...)"
    )
    
    bouton_avis = st.form_submit_button("🚀 Envoyer mon avis")
    
    if bouton_avis:
        # Génération d'une ligne d'étoiles visuelle pour Discord (ex: ⭐⭐⭐⭐⭐)
        etoiles_visuelles = "⭐" * note_etoiles
        
        # Détermination de l'émoji et de l'alerte selon la note (Alerte si note <= 2)
        if note_etoiles <= 2:
            statut_avis = "⚠️ **AVIS REÇU (À AMÉLIORER / POINT NÉGATIF)**"
        else:
            statut_avis = "✨ **Nouvel avis client reçu**"
            
        # Préparation du message complet pour votre Discord
        msg_discord_avis = (
            f"{statut_avis}\n"
            f"👤 **Par :** {st.session_state.utilisateur.capitalize()}\n"
            f"📊 **Note :** {etoiles_visuelles} ({note_etoiles}/5)\n"
            f"💬 **Commentaire :** {avis_texte.strip() if avis_texte.strip() != '' else 'Aucun commentaire écrit.'}"
        )
        
        try:
            requests.post(URL_DISCORD, json={"content": msg_discord_avis}, timeout=3)
            if note_etoiles <= 2:
                st.sidebar.success("Merci pour ce retour honnête ! Sarah va faire le nécessaire pour s'améliorer. 💖")
            else:
                st.sidebar.success("Merci beaucoup pour votre superbe note ! 🌸")
        except:
            st.sidebar.error("Petit problème réseau lors de l'envoi. Réessayez.")
