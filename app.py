# --- 1. Chargement sécurisé avec le bon séparateur ---
df = pd.read_csv("donnees.csv", sep="\t")

# Nettoyage automatique des espaces invisibles dans les titres
df.columns = df.columns.str.strip()

# --- 2. Boucle d'affichage sur tes produits ---
for index, row in df.iterrows():
    # Création d'une boîte pour chaque produit (Adapter selon ton style CSS si besoin)
    st.markdown('<div class="product-card">', unsafe_allow_html=True)
    
    # Correction : On cherche 'Photo produit' avec le nom exact de ton CSV
    lien_photo = str(row['Photo produit']).strip() if 'Photo produit' in row else ""
    
    # Affichage de la photo si le lien commence par http
    if lien_photo and lien_photo.startswith('http') and lien_photo != 'nan':
        st.image(lien_photo, use_container_width=True)
    else:
        # Icône par défaut si pas d'image
        st.markdown(f"<h1 style='text-align: center; font-size: 50px;'>🛍️</h1>", unsafe_allow_html=True)
        
    st.markdown(f"### {row['Denomination']}")
    
    # Gestion du format
    fmt = row['Litre / Gramme'] if 'Litre / Gramme' in row else "N/A"
    
    # Correction : Prise en compte du 'é' accentué pour 'Quantité'
    try: 
        max_stock = int(float(str(row['Quantité']).replace(' ', '')))
    except: 
        max_stock = 0
        
    if max_stock <= 0:
        st.markdown("<p style='color: red; font-size: 14px;'>❌ <b>Rupture de stock !</b></p>", unsafe_allow_html=True)
        quantite = 0
    else:
        st.markdown(f"<p style='color: #8B5A6F; font-size: 14px;'>Format : {fmt} | Stock : <b>{max_stock}</b></p>", unsafe_allow_html=True)
        
        # Gestion et calcul des prix
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
    
    # Enregistrement dans le panier
    if quantite > 0:
        st.session_state.panier[row['Denomination']] = {"quantite": quantite, "prix": p_promo, "economie": (p_init - p_promo) * quantite if p_init > 0 else 0}
    elif row['Denomination'] in st.session_state.panier:
        del st.session_state.panier[row['Denomination']]
        
    st.markdown('</div>', unsafe_allow_html=True)
