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
les_categories = list(df[col_cat].unique()) if col_cat in df.columns else []

# 1. On nettoie et on trie les catégories par ordre alphabétique
categories_propres = [str(cat).strip().capitalize() for cat in les_categories if str(cat).lower() != 'nan' and str(cat).strip() != '']
categories_triees = sorted(categories_propres)

# 2. Si "Nouveauté" existe (avec ou sans accent), on la force en TOUT PREMIER dans la liste
if "Nouveauté" in categories_triees:
    categories_triees.remove("Nouveauté")
    categories_menu = ["🌸 Nouveauté", "✨ Tous les rayons"] + [f"🌸 {cat}" for cat in categories_triees]
elif "Nouveaute" in categories_triees:
    categories_triees.remove("Nouveaute")
    categories_menu = ["🌸 Nouveauté", "✨ Tous les rayons"] + [f"🌸 {cat}" for cat in categories_triees]
else:
    categories_menu = ["✨ Tous les rayons"] + [f"🌸 {cat}" for cat in categories_triees]

# 3. On affiche la liste (index=0 signifie que le premier élément, donc Nouveauté, est sélectionné d'office)
choix_cat_brut = st.sidebar.selectbox("Faites votre shopping par rayon :", categories_menu, index=0)
choix_cat = choix_cat_brut.replace("🌸 ", "").replace("✨ ", "").strip().lower()

# 4. Filtrage des produits pour l'affichage
if choix_cat_brut == "✨ Tous les rayons":
    df_filtre = df
else:
    df_filtre = df[df[col_cat].str.lower().str.strip() == choix_cat]

if choix_cat_brut == "✨ Tous les rayons":
    df_filtre = df
else:
    df_filtre = df[df[col_cat].str.lower().str.strip() == choix_cat]

st.subheader(f"💫 Sélection : {choix_cat_brut} ({len(df_filtre)} pépites)")
cols = st.columns(3)

for index, row in df_filtre.reset_index().iterrows():
    nom_produit = str(row[col_nom]).strip() if col_nom in row else "Produit sans nom"
    if nom_produit.lower() in ["nan", "", "denomination"]:
        continue
        
    with cols[index % 3]:
        st.markdown('<div class="product-card">', unsafe_allow_html=True)
        cat_nom = str(row[col_cat]).lower() if col_cat in row else ""
        if "lessive" in cat_nom: icon = "🧺"
        elif "hygiene" in cat_nom or "hygiène" in cat_nom: icon = "✨"
        elif "entretien" in cat_nom: icon = "🧼"
        elif "alimentaire" in cat_nom: icon = "🍬"
        elif "animalerie" in cat_nom: icon = "🐱"
        else: icon = "🛍️"
            
        lien_photo = str(row[col_photo]).strip() if col_photo in row else ""
        if lien_photo and lien_photo.startswith('http') and lien_photo != 'nan':
            st.image(lien_photo, use_container_width=True)
        else:
            st.markdown(f"<h1 style='text-align: center; font-size: 50px;'>{icon}</h1>", unsafe_allow_html=True)
            
        st.markdown(f"### {nom_produit}")
        fmt = row[col_fmt] if col_fmt in row else "N/A"
        
        try: max_stock = int(float(str(row[col_stock]).replace(' ', '')))
        except: max_stock = 0
        
        # 🔑 CORRECTION : On initialise la quantité à 0 pour éviter le plantage
        quantite = 0
            
        if max_stock <= 0:
            st.markdown("<p style='color: red; font-size: 14px;'>❌ <b>Rupture de stock !</b></p>", unsafe_allow_html=True)
            quantite = 0
        else:
            st.markdown(f"<p style='color: #8B5A6F; font-size: 14px;'>Format : {fmt} | Stock : <b>{max_stock}</b></p>", unsafe_allow_html=True)
            try:
                p_init = float(str(row[col_pinit]).replace('€', '').replace(',', '.').replace(' ', '').strip())
                p_promo = float(str(row[col_ppromo]).replace('€', '').replace(',', '.').replace(' ', '').strip())
                remise = int((1 - (p_promo / p_init)) * 100) if p_init > 0 else 0
                st.markdown(f"<span class='promo-badge'>-{remise}%</span> <b style='font-size: 22px; color: #D2143A;'>{p_promo:.2f} €</b> <span style='text-decoration: line-through; color: #C0A9B0;'>{p_init:.2f} €</span>", unsafe_allow_html=True)
            except:
                p_pr = str(row[col_ppromo]).replace(' ', '') if col_ppromo in row else "0"
                st.markdown(f"<h3 style='color: #D2143A;'>{p_pr}</h3>", unsafe_allow_html=True)
                p_promo, p_init = 0, 0
                
            st.markdown("<p style='font-size: 12px; color: gray;'>Quantité :</p>", unsafe_allow_html=True)
            quantite = st.number_input(f"Qté {nom_produit}", min_value=0, max_value=max_stock, value=st.session_state.panier.get(nom_produit, {}).get('quantite', 0), key=f"prod_{index}", label_visibility="collapsed")
        
        # Enregistrement dans le panier (index + 2 correspond à la ligne réelle de Google Sheets)
        if quantite > 0:
            st.session_state.panier[nom_produit] = {
                "quantite": quantite, 
                "prix": p_promo, 
                "economie": (p_init - p_promo) * quantite if p_init > 0 else 0,
                "ligne_sheets": index + 2  
            }
        elif nom_produit in st.session_state.panier:
            del st.session_state.panier[nom_produit]
        st.markdown('</div>', unsafe_allow_html=True)
        # --- FIN DU FICHIER : LE PANIER ROSE, LIVRAISON ET VALIDATION ---
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
    
    # 🚚 OPTION DE LIVRAISON PAR KILOMÈTRE (Ajusté à 0.10 €)
    option_livraison = st.sidebar.checkbox("Demander la livraison à domicile 🏠")
    frais_livraison = 0.0
    km_distance = 0
    
    if option_livraison:
        km_distance = st.sidebar.slider(
            "Distance de chez Sarah (en Km) :", 
            min_value=1, 
            max_value=50, 
            value=5,
            help="Le tarif est de 0,05 € par kilomètre."
        )
        frais_livraison = km_distance * 0.05  # 🔑 Modification du prix ici
        st.sidebar.caption(f"🚗 Frais de livraison : +{frais_livraison:.2f} € ({km_distance} km)")
    else:
        st.sidebar.caption("🛒 Retrait gratuit en main propre chez Sarah")

    # Calcul du montant final incluant la livraison
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
        
        # Préparation du message Discord avec les infos de livraison ajustées
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
                requests.post(
                    URL_MACRO_STOCK, 
                    data=json.dumps(payload_stock), 
                    headers={"Content-Type": "application/json"},
                    timeout=3
                )
            except:
                pass
        
        time.sleep(1.0)
        st.rerun()
# --- SECTION : ESPACE AVIS, NOTES & AMÉLIORATIONS (LIGNE 290) ---
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
