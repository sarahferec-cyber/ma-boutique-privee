import streamlit as st
import pandas as pd

# Configuration globale de l'application
st.set_page_config(page_title="Les Bons Plans de Sarah", page_icon="🛍️", layout="centered")

# --- Initialisation du panier en session ---
if "panier" not in st.session_state:
    st.session_state.panier = {}

st.title("Les Bons Plans de Sarah 🛍️")

# --- 1. Importation et Nettoyage Automatique depuis ton Google Sheets ---
URL_SHEETS = "https://docs.google.com/spreadsheets/d/1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit?usp=sharing"

try:
    # Lecture en sautant les lignes anormales
    df = pd.read_csv(URL_SHEETS, on_bad_lines='skip')
    
    # Neutralisation des espaces cachés, minuscules forcées et suppression des accents
    df.columns = df.columns.str.strip().str.lower()
    df.columns = df.columns.str.replace('é', 'e').str.replace('è', 'e').str.replace('à', 'a')
except Exception as e:
    st.error(f"Erreur technique lors du chargement : {e}")
    df = pd.DataFrame()

# --- 2. Boucle d'affichage dynamique des produits ---
if not df.empty:
    for index, row in df.iterrows():
        # Lecture sécurisée des données nettoyées
        lien_photo = str(row['photo produit']).strip() if 'photo produit' in df.columns else ""
        nom_produit = str(row['denomination']).strip() if 'denomination' in df.columns else ""
        fmt = str(row['litre / gramme']).strip() if 'litre / gramme' in df.columns else "N/A"
        
        # Ignorer les lignes vides du Sheets
        if not nom_produit or nom_produit.lower() == "nan" or nom_produit == "produit sans nom":
            continue
            
        st.markdown('<div style="border:1px solid #ddd; padding:15px; border-radius:10px; margin-bottom:15px;">', unsafe_allow_html=True)
        
        # Affichage de l'image ou icône par défaut
        if lien_photo and lien_photo.startswith('http') and lien_photo != 'nan':
            st.image(lien_photo, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; font-size: 50px; margin:0;'>🛍️</h1>", unsafe_allow_html=True)
            
        st.markdown(f"### {nom_produit}")
        
        # Gestion dynamique du stock
        try:
            val_stock = str(row['quantite']) if 'quantite' in df.columns else "0"
            max_stock = int(float(val_stock.replace(' ', '')))
        except:
            max_stock = 0
            
        if max_stock <= 0:
            st.markdown("<p style='color: red; font-size: 14px; margin:0;'>❌ <b>Rupture de stock !</b></p>", unsafe_allow_html=True)
            quantite = 0
        else:
            st.markdown(f"<p style='color: #8B5A6F; font-size: 14px; margin:0;'>Format : {fmt} | Stock : <b>{max_stock}</b></p>", unsafe_allow_html=True)
            
            # Traitement des prix et affichage du badge de réduction
            try:
                val_init = str(row['prix initial']) if 'prix initial' in df.columns else "0"
                val_promo = str(row['prix promo']) if 'prix promo' in df.columns else "0"
                
                p_init = float(val_init.replace('€', '').replace(',', '.').replace(' ', '').strip())
                p_promo = float(val_promo.replace('€', '').replace(',', '.').replace(' ', '').strip())
                
                remise = int((1 - (p_promo / p_init)) * 100) if p_init > 0 else 0
                st.markdown(f"<span style='background-color:#D2143A; color:white; padding:2px 6px; border-radius:5px; font-size:14px; margin-right:5px;'>-{remise}%</span> <b style='font-size: 22px; color: #D2143A;'>{p_promo:.2f} €</b> <span style='text-decoration: line-through; color: #C0A9B0;'>{p_init:.2f} €</span>", unsafe_allow_html=True)
            except:
                p_promo_str = str(row['prix promo']) if 'prix promo' in df.columns else "0"
                st.markdown(f"<h3 style='color: #D2143A; margin:0;'>{p_promo_str}</h3>", unsafe_allow_html=True)
                p_promo, p_init = 0, 0
                
            st.markdown("<p style='font-size: 12px; color: gray; margin-bottom:5px; margin-top:10px;'>Quantité désirée :</p>", unsafe_allow_html=True)
            quantite = st.number_input(f"Qté {nom_produit}", min_value=0, max_value=max_stock, value=st.session_state.panier.get(nom_produit, {}).get('quantite', 0), key=f"prod_{index}", label_visibility="collapsed")
        
        # Enregistrement du Panier
        if quantite > 0:
            st.session_state.panier[nom_produit] = {"quantite": quantite, "prix": p_promo, "economie": (p_init - p_promo) * quantite if p_init > 0 else 0}
        elif nom_produit in st.session_state.panier:
            del st.session_state.panier[nom_produit]
            
        st.markdown('</div>', unsafe_allow_html=True)

# --- 3. Barre latérale : Gestion du Panier ---
if st.session_state.panier:
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🛒 Votre Panier Rose")
    total_facture = 0.0
    for prod_name, details in st.session_state.panier.items():
        st.sidebar.write(f"**{prod_name}** x{details['quantite']} : {details['prix'] * details['quantite']:.2f} €")
        total_facture += details['prix'] * details['quantite']
    st.sidebar.markdown(f"### Total : {total_facture:.2f} €")
