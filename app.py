# 1. Configuration de la page style Amazon Mobile
st.set_page_config(page_title="Mes Bons Plans 🌸", page_icon="🛍️", layout="wide")

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
    "copine": "viprose",
    "client1": "bonplan75"
}

if "connecte" not in st.session_state:
    st.session_state.connecte = False
if "utilisateur" not in st.session_state:
    st.session_state.utilisateur = ""

if not st.session_state.connecte:
    st.title("🎀 Espace Privé : Le Dressing des Bons Plans 🌸")
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

st.title("🌸 Le Dressing des Bons Plans 🛍️")
st.write(f"Coucou **{st.session_state.utilisateur.capitalize()}** !")

if st.sidebar.button("🚪 Se déconnecter"):
    st.session_state.connecte = False
    st.session_state.utilisateur = ""
    st.rerun()

URL_SHEETS = "https://docs.google.com/spreadsheets/d/1S9bjzHGdS-zTc_uQIqdgJqd5OMOMSrD5telEoPX6jhA/edit?usp=sharing"
URL_DISCORD = "https://discord.com"

def load_clean_data():
    try:
        csv_url = URL_SHEETS.replace("/edit?usp=sharing", "/export?format=csv").replace("/edit", "/export?format=csv")
        reponse = requests.get(csv_url)
        reponse.encoding = 'utf-8'
        data = pd.read_csv(io.StringIO(reponse.text), encoding="utf-8", engine="python", on_bad_lines='skip')
        
        # Nettoyage et harmonisation automatique des colonnes
        data.columns = [str(c).strip() for c in data.columns]
        data.rename(columns={
            'Photo produit': 'Photo', 
            'Denomination': 'Denomination', 
            'Categorie': 'Categorie', 
            'Litre / Gramme': 'Format', 
            'Quantité': 'Quantite', 
            'Prix initial': 'Prix initial', 
            'Prix promo': 'Prix promo'
        }, inplace=True)
        
        for col in data.select_dtypes(include=['object']).columns:
            data[col] = data[col].astype(str).str.replace('"', '').str.strip()
            
        data = data[data['Denomination'].notna() & (data['Denomination'] != 'nan') & (data['Denomination'] != '')]
        data['Categorie'] = data['Categorie'].astype(str).str.strip().str.capitalize()
        return data
    except:
        return pd.DataFrame()

df = load_clean_data()
if df.empty:
    st.warning("Erreur de chargement des données Sheets...")
    st.stop()

if "panier" not in st.session_state:
    st.session_state.panier = {}

st.sidebar.markdown("## 🎀 Navigation")
les_categories = list(df["Categorie"].unique())
categories_menu = ["✨ Tous les rayons"] + [f"🌸 {cat}" for cat in sorted(les_categories) if cat != 'Nan']
choix_cat_brut = st.sidebar.selectbox("Faites votre shopping par rayon :", categories_menu)
choix_cat = choix_cat_brut.replace("🌸 ", "")

df_filtre = df if choix_cat_brut == "✨ Tous les rayons" else df[df["Categorie"] == choix_cat]

st.subheader(f"💫 Sélection : {choix_cat_brut} ({len(df_filtre)} pépites)")
cols = st.columns(3)

for index, row in df_filtre.reset_index().iterrows():
    with cols[index % 3]:
        st.markdown('<div class="product-card">', unsafe_allow_html=True)
        cat_nom = str(row['Categorie']).lower()
        if "lessive" in cat_nom: icon = "🧺"
        elif "hygiene" in cat_nom or "hygiène" in cat_nom: icon = "✨"
        elif "entretien" in cat_nom: icon = "🧼"
        elif "alimentaire" in cat_nom: icon = "🍬"
        elif "animalerie" in cat_nom: icon = "🐱"
        else: icon = "🛍️"
            
        lien_photo = str(row['Photo']).strip() if 'Photo' in row else ""
        if lien_photo and lien_photo.startswith('http') and lien_photo != 'nan':
            st.image(lien_photo, use_container_width=True)
        else:
            st.markdown(f"<h1 style='text-align: center; font-size: 50px;'>{icon}</h1>", unsafe_allow_html=True)
            
        st.markdown(f"### {row['Denomination']}")
        fmt = row['Format'] if 'Format' in row else "N/A"
        
        try: max_stock = int(float(str(row['Quantite']).replace(' ', '')))
        except: max_stock = 0
            
        if max_stock <= 0:
            st.markdown("<p style='color: red; font-size: 14px;'>❌ <b>Rupture de stock !</b></p>", unsafe_allow_html=True)
            quantite = 0
        else:
            st.markdown(f"<p style='color: #8B5A6F; font-size: 14px;'>Format : {fmt} | Stock : <b>{max_stock}</b></p>", unsafe_allow_html=True)
            try:
                p_init = float(str(row['Prix initial']).replace('€', '').replace(',', '.').replace(' ', '').strip())
                p_promo = float(str(row['Prix promo']).replace('€', '').replace(',', '.').replace(' ', '').strip())
                remise = int((1 - (p_promo / p_init)) * 100) if p_init > 0 else 0
                st.markdown(f"<span class='promo-badge'>-{remise}%</span> <b style='font-size: 22px; color: #D2143A;'>{p_promo:.2f} €</b> <span style='text-decoration: line-through; color: #C0A9B0;'>{p_init:.2f} €</span>", unsafe_allow_html=True)
            except:
                p_pr = str(row['Prix promo']).replace(' ', '')
                st.markdown(f"<h3 style='color: #D2143A;'>{p_pr}</h3>", unsafe_allow_html=True)
                p_promo, p_init = 0, 0
                
            st.markdown("<p style='font-size: 12px; color: gray;'>Quantité :</p>", unsafe_allow_html=True)
            quantite = st.number_input(f"Qté {row['Denomination']}", min_value=0, max_value=max_stock, value=st.session_state.panier.get(row['Denomination'], {}).get('quantite', 0), key=f"prod_{index}", label_visibility="collapsed")
        
        if quantite > 0:
            st.session_state.panier[row['Denomination']] = {"quantite": quantite, "prix": p_promo, "economie": (p_init - p_promo) * quantite if p_init > 0 else 0}
        elif row['Denomination'] in st.session_state.panier:
            del st.session_state.panier[row['Denomination']]
        st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.panier:
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🛒 Votre Panier Rose")
    total_facture = 0.0
    texte_message = ""
    
    for article, info in st.session_state.panier.items():
        sous_total = info['quantite'] * info['prix']
        total_facture += sous_total
        st.sidebar.write(f"💗 **{info['quantite']}x** {article} ({sous_total:.2f}€)")
        texte_message += f"- {info['quantite']}x {article}\n"
        
    st.sidebar.markdown(f"### Total : {total_facture:.2f} €")
    
    if st.sidebar.button("🛍️ Envoyer ma commande"):
        st.balloons()
        t_fin = f"Client : {st.session_state.utilisateur.capitalize()}\n\n" + texte_message + f"Total : {total_facture:.2f}€"
        requests.post(URL_DISCORD, json={"content": t_fin})
        st.session_state.panier = {}
        st.rerun()
else:
    st.sidebar.markdown("---")
    st.sidebar.info("Votre panier est vide. Bon shopping ! ✨")
