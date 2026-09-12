import streamlit as st
import pandas as pd
import re

# Configurer la page pour un rendu propre
st.set_page_config(page_title="Les Bons Plans de Sarah", page_icon="🛍️", layout="centered")

# --- Initialisation du panier en session_state ---
if "panier" not in st.session_state:
    st.session_state.panier = {}

st.title("Les Bons Plans de Sarah 🛍️")

# --- 1. Chargement et Découpage Ultra-Robuste des Données ---
@st.cache_data(ttl=10)  # Le cache expire après 10 secondes pour forcer la mise à jour
def charger_donnees():
    try:
        # Lecture brute ligne par ligne pour éviter les conflits de guillemets
        with open("donnees.csv", "r", encoding="utf-8") as f:
            lignes = f.readlines()
        
        if not lignes:
            return pd.DataFrame()
            
        # Découpage strict par les tabulations (\t)
        donnees_nettoyees = []
        for ligne in lignes:
            # Enlève le saut de ligne à la fin et découpe
            elements = ligne.replace('\n', '').split('\t')
            # Nettoie les guillemets superflus et les espaces autour de chaque élément
            elements_propres = [el.strip().strip('"').strip("'") for el in elements]
            donnees_nettoyees.append(elements_propres)
            
        titres = donnees_nettoyees[0]
        lignes_produits = donnees_nettoyees[1:]
        
        # Ajustement de la taille des lignes au cas où certaines soient incomplètes
        nb_colonnes = len(titres)
        lignes_ajustees = [l + [""] * (nb_colonnes - len(l)) for l in lignes_produits]
        
        # Création du DataFrame propre
        df_produits = pd.DataFrame(lignes_ajustees, columns=titres)
        df_produits.columns = df_produits.columns.str.strip()
        return df_produits
    except Exception as e:
        st.error(f"Erreur lors de la lecture des données : {e}")
        return pd.DataFrame()

df = charger_donnees()

# --- 2. Boucle d'affichage dynamique des produits ---
if not df.empty:
    for index, row in df.iterrows():
        # Identification intelligente des colonnes (évite les bugs d'accents ou majuscules)
        col_photo = next((c for c in df.columns if "photo" in c.lower()), None)
        col_nom = next((c for c in df.columns if "denom" in c.lower() or "nom" in c.lower()), None)
        col_fmt = next((c for c in df.columns if "litr" in c.lower() or "gram" in c.lower() or "format" in c.lower()), None)
        col_stock = next((c for c in df.columns if "quant" in c.lower() or "stock" in c.lower()), None)
        col_pinit = next((c for c in df.columns if "initial" in c.lower() or "avant" in c.lower()), None)
        col_ppromo = next((c for c in df.columns if "promo" in c.lower() or "apres" in c.lower()), None)
        
        # Extraction sécurisée des valeurs
        lien_photo = str(row[col_photo]).strip() if col_photo else ""
        nom_produit = str(row[col_nom]).strip() if col_nom else "Produit sans nom"
        fmt = str(row[col_fmt]).strip() if col_fmt else "N/A"
        
        # Ignorer les lignes vides ou les entêtes accidentels
        if nom_produit.lower() in ["nan", "", "denomination", "produit sans nom"]:
            continue
            
        st.markdown('<div class="product-card" style="border:1px solid #ddd; padding:15px; border-radius:10px; margin-bottom:15px;">', unsafe_allow_html=True)
        
        # Affichage de l'image
        if lien_photo and lien_photo.startswith('http') and lien_photo != 'nan':
            st.image(lien_photo, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; font-size: 50px; margin:0;'>🛍️</h1>", unsafe_allow_html=True)
            
        # Nom du produit
        st.markdown(f"### {nom_produit}")
        
        # Gestion du stock
        try:
            val_stock = str(row[col_stock]) if col_stock else "0"
            max_stock = int(float(val_stock.replace(' ', '')))
        except:
            max_stock = 0
            
        if max_stock <= 0:
            st.markdown("<p style='color: red; font-size: 14px; margin-top:0;'>❌ <b>Rupture de stock !</b></p>", unsafe_allow_html=True)
            quantite = 0
        else:
            st.markdown(f"<p style='color: #8B5A6F; font-size: 14px; margin-top:0;'>Format : {fmt} | Stock : <b>{max_stock}</b></p>", unsafe_allow_html=True)
            
            # Gestion et calcul des prix
            try:
                val_init = str(row[col_pinit]) if col_pinit else "0"
                val_promo = str(row[col_ppromo]) if col_ppromo else "0"
                
                # Nettoyage des caractères monétaires
                p_init = float(val_init.replace('€', '').replace(',', '.').replace(' ', '').strip())
                p_promo = float(val_promo.replace('€', '').replace(',', '.').replace(' ', '').strip())
                
                remise = int((1 - (p_promo / p_init)) * 100) if p_init > 0 else 0
                st.markdown(f"<span style='background-color:#D2143A; color:white; padding:2px 6px; border-radius:5px; font-size:14px; margin-right:5px;'>-{remise}%</span> <b style='font-size: 22px; color: #D2143A;'>{p_promo:.2f} €</b> <span style='text-decoration: line-through; color: #C0A9B0;'>{p_init:.2f} €</span>", unsafe_allow_html=True)
            except:
                val_promo = str(row[col_ppromo]) if col_ppromo else "0"
                st.markdown(f"<h3 style='color: #D2143A; margin:0;'>{val_promo}</h3>", unsafe_allow_html=True)
                p_promo, p_init = 0, 0
                
            # Sélecteur de quantité numérique
            st.markdown("<p style='font-size: 12px; color: gray; margin-bottom:5px; margin-top:10px;'>Quantité désirée :</p>", unsafe_allow_html=True)
            quantite = st.number_input(
                f"Qté {nom_produit}", 
                min_value=0, 
                max_value=max_stock, 
                value=st.session_state.panier.get(nom_produit, {}).get('quantite', 0), 
                key=f"prod_{index}", 
                label_visibility="collapsed"
            )
        
        # Enregistrement dans la session du panier
        if quantite > 0:
            st.session_state.panier[nom_produit] = {
                "quantite": quantite, 
                "prix": p_promo, 
                "economie": (p_init - p_promo) * quantite if p_init > 0 else 0
            }
        elif nom_produit in st.session_state.panier:
            del st.session_state.panier[nom_produit]
            
        st.markdown('</div>', unsafe_allow_html=True)

# --- 3. Barre latérale : Affichage du Panier ---
if st.session_state.panier:
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🛒 Votre Panier Rose")
    total_facture = 0.0
    for prod_name, details in st.session_state.panier.items():
        st.sidebar.write(f"**{prod_name}** x{details['quantite']} : {details['prix'] * details['quantite']:.2f} €")
        total_facture += details['prix'] * details['quantite']
    st.sidebar.markdown(f"### Total : {total_facture:.2f} €")
