import streamlit as st
import pandas as pd

# 1. Configuration de la page style Amazon Mobile
st.set_page_config(page_title="Mes Bons Plans 🌸", page_icon="🛍️", layout="wide")

# Relooking complet en mode "Girly / Pastel Rose & Gold"
st.markdown("""
    <style>
    /* Changer la couleur de fond générale de la page */
    .stApp {
        background-color: #FFF5F5;
    }
    
    /* Relooking des cartes produits */
    .product-card {
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #FFD1D1;
        background-color: white;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 3px 3px 10px rgba(255, 182, 193, 0.2);
        transition: transform 0.2s;
    }
    .product-card:hover {
        transform: scale(1.02);
        border-color: #FFB6C1;
    }
    
    /* Le badge promo en rose poudré/fuchsia girly */
    .promo-badge {
        background-color: #FF69B4;
        color: white;
        padding: 3px 8px;
        font-weight: bold;
        border-radius: 20px;
        font-size: 13px;
    }
    
    /* Personnalisation de la barre latérale (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #FFEAEF;
        border-right: 2px solid #FFD1D1;
    }
    
    /* Titres et textes importants en couleur rose foncé élégant */
    h1, h2, h3 {
        color: #C71585 !important;
        font-family: 'Poppins', sans-serif;
    }
    
    /* Boutons personnalisés */
    .stButton>button {
        background-color: #FF69B4 !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        font-weight: bold !important;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #FF1493 !important;
        box-shadow: 0px 4px 8px rgba(255, 20, 147, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌸 Le Dressing des Bons Plans 🛍️")
st.write("Trouvez vos pépites du quotidien à prix tout doux. Ajustez vos quantités et validez votre panier !")

# 2. Connexion dynamique à votre unique feuille Google Sheets
URL_SHEETS = "https://docs.google.com/spreadsheets/d/1S0doyE2GRiePlPybNiIfCGXXk9NoQS_7lQSmE1r5Iro/edit?usp=sharing"

@st.cache_data(ttl=5)
def load_clean_data(url):
    try:
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv").replace("/edit", "/export?format=csv")
        data = pd.read_csv(csv_url)
        data.columns = [c.strip() for c in data.columns]
        data = data[data['Denomination'].notna()]
        if 'Categorie' in data.columns:
            data['Categorie'] = data['Categorie'].astype(str).str.strip().str.capitalize()
        return data
    except Exception as e:
        st.error(f"Erreur de lecture du Google Sheets : {e}")
        return pd.DataFrame()

df = load_clean_data(URL_SHEETS)

if df.empty:
    st.warning("En attente des données du Google Sheets...")
    st.stop()

# Initialisation du panier
if "panier" not in st.session_state:
    st.session_state.panier = {}

# 3. Barre latérale girly
st.sidebar.markdown("## 🎀 Navigation")
les_categories = list(df["Categorie"].unique())
categories_menu = ["✨ Tous les rayons"] + [f"🌸 {cat}" for cat in sorted(les_categories)]
choix_cat_brut = st.sidebar.selectbox("Faites votre shopping par rayon :", categories_menu)

# Nettoyage du choix pour correspondre au Sheets
choix_cat = choix_cat_brut.replace("🌸 ", "")

df_filtre = df if choix_cat_brut == "✨ Tous les rayons" else df[df["Categorie"] == choix_cat]

# 4. Affichage des produits sous forme de Grille
st.subheader(f"💫 Sélection : {choix_cat_brut} ({len(df_filtre)} pépites)")
cols = st.columns(3)

col_produit = 'Denomination'
col_format = 'Litre / Gramme'
col_stock = 'Quantité'
col_prix_init = 'Prix initial' if 'Prix initial' in df.columns else 'Prix initial '
col_prix_promo = 'Prix promo'

for index, row in df_filtre.reset_index().iterrows():
    with cols[index % 3]:
        st.markdown('<div class="product-card">', unsafe_allow_html=True)
        
        # Icônes mignonnes selon la catégorie
        cat_nom = str(row['Categorie']).lower()
        if "lessive" in cat_nom or "entretien" in cat_nom:
            icon = "🧺"
        elif "hygiene" in cat_nom:
            icon = "✨"
        else:
            icon = "🍬"
            
        # Affichage de l'image ou de l'icône girly
        if 'Photo produit' in row and pd.notna(row['Photo produit']) and str(row['Photo produit']).startswith('http'):
            st.image(row['Photo produit'], use_container_width=True)
        else:
            st.markdown(f"<h1 style='text-align: center; font-size: 50px;'>{icon}</h1>", unsafe_allow_html=True)
            
        st.markdown(f"### {row[col_produit]}")
        st.markdown(f"<p style='color: #8B5A6F; font-size: 14px;'>Format : {row[col_format]} | Disponible : <b>{row[col_stock]}</b></p>", unsafe_allow_html=True)
        
        # Prix en mode rose/fuchsia
        try:
            p_init = float(str(row[col_prix_init]).replace('€', '').replace(',', '.').strip())
            p_promo = float(str(row[col_prix_promo]).replace('€', '').replace(',', '.').strip())
            remise = int((1 - (p_promo / p_init)) * 100) if p_init > 0 else 0
            st.markdown(f"<span class='promo-badge'>-{remise}%</span> <b style='font-size: 22px; color: #D2143A;'>{p_promo:.2f} €</b> <span style='text-decoration: line-through; color: #C0A9B0;'>{p_init:.2f} €</span>", unsafe_allow_html=True)
        except:
            st.markdown(f"<b style='font-size: 22px; color: #D2143A;'>{row[col_prix_promo]}</b>", unsafe_allow_html=True)
            p_promo = 0
            p_init = 0
            
        try:
            max_stock = int(float(str(row[col_stock]).strip()))
        except:
            max_stock = 1
            
        st.markdown("<p style='font-size: 12px; color: gray; margin-bottom: 2px;'>Choisir la quantité :</p>", unsafe_allow_html=True)
        quantite = st.number_input(
            f"Quantité pour {row[col_produit]}",
            min_value=0,
            max_value=max_stock if max_stock > 0 else 1,
            value=st.session_state.panier.get(row[col_produit], {}).get('quantite', 0),
            key=f"prod_{index}",
            label_visibility="collapsed"
        )
        
        if quantite > 0:
            st.session_state.panier[row[col_produit]] = {
                "quantite": quantite,
                "prix": p_promo,
                "economie": (p_init - p_promo) * quantite if p_init > 0 else 0
            }
        elif row[col_produit] in st.session_state.panier:
            del st.session_state.panier[row[col_produit]]
            
        st.markdown('</div>', unsafe_allow_html=True)

# 5. Le Panier de Shopping (Barre latérale)
if st.session_state.panier:
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🛒 Votre Panier Rose")
    
    total_facture = 0.0
    total_economies = 0.0
    texte_message = "Coucou ! Voici ma commande 🌸 :\\n\\n"
    
    for article, info in st.session_state.panier.items():
        sous_total = info['quantite'] * info['prix']
        total_facture += sous_total
        total_economies += info['economie']
        
        st.sidebar.write(f"💗 **{info['quantite']}x** {article} ({sous_total:.2f}€)")
        texte_message += f"- {info['quantite']}x {article}\\n"
        
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### Total : <span style='color: #D2143A;'>{total_facture:.2f} €</span>", unsafe_allow_html=True)
    st.sidebar.success(f"💝 Économie shopping : {total_economies:.2f} € !")
    
    texte_message += f"\\n🛍️ *Montant total : {total_facture:.2f}€*"
    
    if st.sidebar.button("🛍️ Envoyer ma commande"):
        st.balloons()
        st.sidebar.info("Génial ! Copie ce texte pour me l'envoyer :")
        st.sidebar.text_area("Texte de la commande :", value=texte_message.replace('\\n', '\n'), height=150)
else:
    st.sidebar.markdown("---")
    st.sidebar.info("Votre panier est vide. Bon shopping ! ✨")
