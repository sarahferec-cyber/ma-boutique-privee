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
# IMPORTANT :
# Ne mets pas le webhook Discord directement dans le code.
# Ajoute-le dans les Secrets Streamlit :
#
# DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
#
# Puis le code récupérera st.secrets["DISCORD_WEBHOOK"]
URL_MACRO_STOCK = (
    "https://script.google.com/macros/s/"
    "AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/"
    "exec"
)
# ============================================================
# 5. FONCTIONS UTILITAIRES
# ============================================================
def convertir_float(valeur, valeur_defaut=0.0):
    """
    Transforme proprement une valeur en nombre.
    Accepte :
    2.50
    2,50
    "2,50 €"
    """
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
    """
    Envoie un message sur Discord si le webhook est configuré.
    """
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
    """
    Charge le Google Sheets en CSV et nettoie les colonnes.
    """
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
        for col in data.select_dtypes(
            include=["object"]
        ).columns:
            data[col] = (
                data[col]
                .astype(str)
                .str.replace('"', '', regex=False)
                .str.strip()
            )
        return data
    except Exception as erreur:
        st.error(
            "❌ Impossible de charger les données Google Sheets."
        )
        st.caption(
            f"Détail technique : {erreur}"
        )
        return pd.DataFrame()
def trouver_colonne(dataframe, noms_possibles):
    """
    Retourne la première colonne trouvée dans la liste.
    """
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
    st.title(
        "🎀 Espace Privé : La Boutique des Bons Plans 🌸"
    )
    with st.form("formulaire_connexion"):
        identifiant = st.text_input(
            "👤 Votre Identifiant :"
        ).strip().lower()
        mot_de_passe = st.text_input(
            "🔑 Votre Mot de passe :",
            type="password"
        )
        connexion = st.form_submit_button(
            "✨ Entrer dans la boutique"
        )
        if connexion:
            if (
                identifiant in COMPTES_AUTORISES
                and COMPTES_AUTORISES[identifiant]
                == mot_de_passe
            ):
                st.session_state.connecte = True
                st.session_state.utilisateur = identifiant
                st.rerun()
            else:
                st.error(
                    "Identifiant ou mot de passe incorrect. ❌"
                )
    st.stop()
# ============================================================
# 8. EN-TÊTE
# ============================================================
st.title(
    "🌸 La Boutique des Bons Plans 🛍️"
)
st.write(
    f"Coucou **{st.session_state.utilisateur.capitalize()}** !"
)
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
    st.warning(
        "⚠️ Aucune donnée produit disponible."
    )
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
    st.error("❌ Les colonnes essentielles ('Produit' et 'Quantité') n'ont pas pu être détectées dans votre fichier.")
    st.stop()

# ============================================================
# 12. BARRE LATÉRALE : FILTRES & PANIER
# ============================================================
st.sidebar.header("🎯 Filtres de recherche")

# Filtre par catégorie (Définit correctement 'categorie_choisie' avant la suite)
categories_disponibles = ["Toutes"] + sorted(list(df[col_cat].dropna().unique())) if col_cat else ["Toutes"]
categorie_choisie = st.sidebar.selectbox("Filtrer par rayon :", categories_disponibles)

# Affichage du Panier dans la Sidebar
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
    
    # Bouton de validation finale du Panier
    if st.sidebar.button("✅ Valider ma commande", key="bouton_validation_panier"):
        with st.spinner("Prise en compte de votre commande en cours..."):
            succes_total = True
            details_commande_discord = []
            
            # Traitement de chaque article avec la macro Google Sheets
            for nom_art, details_art in st.session_state.panier.items():
                payload = {
                    "action": "retirer",
                    "produit": nom_art,
                    "quantite": int(details_art["quantite"]),
                    "utilisateur": st.session_state.utilisateur
                }
                try:
                    res = requests.post(URL_MACRO_STOCK, json=payload, timeout=10)
                    if res.status_code != 200:
                        succes_total = False
                    else:
                        details_commande_discord.append(f"- {details_art['quantite']}x {nom_art} ({details_art['prix']:.2f}€/u)")
                except Exception:
                    succes_total = False
            
            if succes_total:
                # Notification Discord
                msg_discord = f"🎉 **Nouvelle commande de {st.session_state.utilisateur.capitalize()} !**\n" + "\n".join(details_commande_discord) + f"\n\n💰 **Total : {total_panier:.2f} €**"
                envoyer_discord(msg_discord)
                
                st.session_state.panier = {}
                st.session_state.achat_reussi = True
                st.rerun()
            else:
                st.error("❌ Une erreur est survenue lors de la mise à jour des stocks. Veuillez réessayer.")

if st.session_state.achat_reussi:
    st.success("🎉 Félicitations ! Votre commande a bien été enregistrée et votre stock a été mis à jour.")
    st.session_state.achat_reussi = False

# ============================================================
# 13. FILTRAGE ET AFFICHAGE DU CATALOGUE PRODUITS
# ============================================================
df_filtre = df.copy()
if col_cat and categorie_choisie != "Toutes":
    df_filtre = df_filtre[df_filtre[col_cat] == categorie_choisie]

# Grid layout : 3 colonnes de produits par ligne
colonnes_produits = st.columns(3)

for index, row in df_filtre.iterrows():
    nom_produit = row[col_nom]
    stock_actuel = int(convertir_float(row[col_stock]))
    
    # Si l'article n'a pas de nom ou est hors-stock, on passe au suivant
    if pd.isna(nom_produit) or str(nom_produit).strip() == "" or stock_actuel <= 0:
        continue
        
    px_base = convertir_float(row[col_prix_base]) if col_prix_base else 0.0
    px_promo = convertir_float(row[col_prix_promo]) if col_prix_promo else px_base
    
    # CALCUL DU POURCENTAGE DE PROMOTION
    pourcentage_remise = int(((px_base - px_promo) / px_base) * 100) if px_base > px_promo else 0
    
    # Répartition équitable dans la grille
    col_courante = colonnes_produits[index % 3]
    
    with col_courante:
        # Construction du texte de la promotion sous forme de badge HTML
        if pourcentage_remise > 0:
            texte_promo_html = f"""
            <div style='background-color: #FF69B4; color: white; padding: 5px; border-radius: 10px; font-weight: bold; margin: 10px auto; width: fit-content; font-size: 14px;'>
                🔥 ÉCONOMIE : -{pourcentage_remise}%
            </div>
            """
        else:
            texte_promo_html = "<div style='margin: 10px 0; color: #757575; font-size: 13px; font-style: italic;'>Prix bas garanti ✨</div>"

        st.markdown(f"""
        <div class="product-card">
            <h3>{nom_produit}</h3>
            <p style='color: gray; font-size: 14px;'>📦 Format : {row[col_format] if col_format and not pd.isna(row[col_format]) else 'N/A'}</p>
            
            <p style='margin-top: 10px; font-size: 18px;'>
                <del style='color: #FF4D4D; font-size: 15px;'>{f"{px_base:.2f} €" if px_base > px_promo else ""}</del> 
                <strong style='color: #2E8B57; font-size: 24px; margin-left: 8px;'>{px_promo:.2f} €</strong>
            </p>
            
            <!-- AFFICHAGE DU POURCENTAGE ICI -->
            {texte_promo_html}
            
            <p style='color: #C71585; font-weight: bold; margin-top: 10px;'>Disponibles : {stock_actuel} restant(s)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sélecteur de quantité basé sur le stock réel du fichier Excel
        quantite_selectionnee = st.number_input(
            f"Quantité pour {nom_produit}", 
            min_value=1, 
            max_value=stock_actuel, 
            value=1, 
            key=f"input_{index}"
        )
        
        if st.button(f"🛒 Ajouter au panier", key=f"btn_{index}"):
            if nom_produit in st.session_state.panier:
                nvelle_qte = st.session_state.panier[nom_produit]["quantite"] + quantite_selectionnee
                if nvelle_qte <= stock_actuel:
                    st.session_state.panier[nom_produit]["quantite"] = nvelle_qte
                    st.toast(f"✅ Quantité mise à jour pour {nom_produit} !", icon="🛒")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"Impossible d'ajouter plus que le stock disponible ({stock_actuel}).")
            else:
                st.session_state.panier[nom_produit] = {
                    "quantite": quantite_selectionnee,
                    "prix": px_promo
                }
                st.toast(f"🛒 {nom_produit} ajouté au panier !", icon="✨")
                time.sleep(0.5)
                st.rerun()

# ============================================================
# 14. PIED DE PAGE
# ============================================================
st.markdown("---")
st.caption("Application développée avec 🌸 pour Mes Bons Plans de Sarah. Tous droits réservés 2026.")
else:
                    st.error(f"Impossible d'ajouter plus que le stock disponible ({stock_actuel}).")
            else:
                st.session_state.panier[nom_produit] = {
                    "quantite": quantite_selectionnee,
                    "prix": px_promo
                }
                st.toast(f"🛒 {nom_produit} ajouté au panier !", icon="✨")
                time.sleep(0.5)
                st.rerun()

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )
# ============================================================
# 21. MESSAGE APRÈS COMMANDE
# ============================================================
if st.session_state.achat_reussi:
    st.sidebar.success(
        "Commande réalisée ! 🎉 "
        "Votre stock est à jour."
    )
    st.session_state.achat_reussi = False
# ============================================================
# 22. PANIER
# ============================================================
if st.session_state.panier:
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "## 🛒 Votre Panier Rose"
    )
    total_facture = 0.0
    total_economies = 0.0
    texte_message = (
        f"🌸 **Nouvelle commande de "
        f"{st.session_state.utilisateur.capitalize()}** :\n"
    )
    # --------------------------------------------------------
    # ARTICLES
    # --------------------------------------------------------
    for article, infos in st.session_state.panier.items():
        qte = int(
            infos.get(
                "quantite",
                1
            )
        )
        prix = convertir_float(
            infos.get(
                "prix",
                0
            )
        )
        economie_unitaire = convertir_float(
            infos.get(
                "economie_unitaire",
                0
            )
        )
        # Économie totale pour cet article
        economie_article = (
            economie_unitaire * qte
        )
        # Total article
        total_article = (
            prix * qte
        )
        total_facture += (
            total_article
        )
        total_economies += (
            economie_article
        )
        st.sidebar.write(
            f"• {article} "
            f"(x{qte}) — "
            f"{total_article:.2f} €"
        )
        texte_message += (
            f"- {article} "
            f"x{qte} "
            f"({prix:.2f}€/u)\n"
        )
    # ========================================================
    # LIVRAISON
    # ========================================================
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "### 📦 Mode de retrait"
    )
    option_livraison = st.sidebar.checkbox(
        "Demander la livraison à domicile 🏠"
    )
    frais_livraison = 0.0
    km_distance = 0
    if option_livraison:
        km_distance = st.sidebar.slider(
            "Distance de chez Sarah (en Km) :",
            min_value=1,
            max_value=50,
            value=5,
            help=(
                "Le tarif est de "
                "0,10 € par kilomètre."
            )
        )
        frais_livraison = (
            km_distance * 0.10
        )
        st.sidebar.caption(
            f"🚗 Frais de livraison : "
            f"+{frais_livraison:.2f} € "
            f"({km_distance} km)"
        )
    else:
        st.sidebar.caption(
            "🛒 Retrait gratuit en main propre chez Sarah"
        )
    # ========================================================
    # TOTAL
    # ========================================================
    total_final_avec_livraison = (
        total_facture
        + frais_livraison
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
        ### Total :
        **{total_final_avec_livraison:.2f} €**
        """
    )
    if total_economies > 0:
        st.sidebar.markdown(
            f"""
            💖 Vous économisez
            **{total_economies:.2f} €**
            sur cet achat !
            """
        )
    # ========================================================
    # VALIDATION
    # ========================================================
    if st.sidebar.button(
        "✨ Valider mon achat"
    ):
        # Copie du panier avant suppression
        panier_a_traiter = {
            article: infos.copy()
            for article, infos
            in st.session_state.panier.items()
        }
        # ----------------------------------------------------
        # MESSAGE DISCORD
        # ----------------------------------------------------
        msg_discord = (
            f"{texte_message}\n"
        )
        if option_livraison:
            msg_discord += (
                f"🚚 **Option Livraison activée :** "
                f"{km_distance} Km "
                f"(+{frais_livraison:.2f}€)\n"
            )
        else:
            msg_discord += (
                "🛒 **Retrait :** "
                "En main propre chez Sarah\n"
            )
        msg_discord += (
            f"💰 **Total Articles : "
            f"{total_facture:.2f}€**\n"
        )
        msg_discord += (
            f"⭐ **TOTAL À PAYER : "
            f"{total_final_avec_livraison:.2f}€**\n"
        )
        msg_discord += (
            f"🌸 **Économie réalisée : "
            f"{total_economies:.2f}€**"
        )
        # ----------------------------------------------------
        # ENVOI DISCORD
        # ----------------------------------------------------
        discord_ok = envoyer_discord(
            msg_discord
        )
        # ----------------------------------------------------
        # MISE À JOUR STOCK GOOGLE SHEETS
        # ----------------------------------------------------
        stock_ok = True
        for article, infos in panier_a_traiter.items():
            ligne_sheets = infos.get(
                "ligne_sheets"
            )
            quantite = infos.get(
                "quantite",
                1
            )
            # Si l'information manque,
            # on ne fait pas planter toute la commande.
            if ligne_sheets is None:
                stock_ok = False
                continue
            payload_stock = {
                "ligne": int(
                    ligne_sheets
                ),
                "quantite": int(
                    quantite
                )
            }
            try:
                response_stock = requests.post(
                    URL_MACRO_STOCK,
                    data=json.dumps(
                        payload_stock
                    ),
                    headers={
                        "Content-Type":
                            "application/json"
                    },
                    timeout=5
                )
                if response_stock.status_code not in [
                    200,
                    201,
                    204
                ]:
                    stock_ok = False
            except Exception:
                stock_ok = False
        # ----------------------------------------------------
        # FIN DE COMMANDE
        # ----------------------------------------------------
        st.session_state.panier = {}
        st.session_state.achat_reussi = True
        st.balloons()
        # Messages d'information
        if not discord_ok:
            st.sidebar.warning(
                "⚠️ La commande est enregistrée, "
                "mais la notification Discord "
                "n'a pas pu être envoyée."
            )
        if not stock_ok:
            st.sidebar.warning(
                "⚠️ La commande est enregistrée, "
                "mais une mise à jour du stock "
                "n'a pas pu être effectuée."
            )
        time.sleep(1)
        st.rerun()
# ============================================================
# 23. CONDITIONS GÉNÉRALES DE VENTE
# ============================================================
st.sidebar.markdown("---")
with st.sidebar.popover(
    "📄 Conditions Générales de Vente (CGV)"
):
    st.markdown(
        """
        ### ⚖️ Conditions Générales de Vente
        En utilisant la boutique
        **"Mes Bons Plans de Sarah 🌸"**,
        vous acceptez les conditions suivantes :
        #### 1. 🛍️ Commandes & Réservations
        * Ce site est un espace privé de
          réservation de produits.
        * Toute validation de panier entraîne
          l'envoi d'une notification via notre
          système de messagerie Discord.
        #### 2. 📦 Stocks & Disponibilités
        * Les stocks affichés sont synchronisés
          avec l'inventaire.
        * En cas de rupture de stock simultanée,
          la priorité est accordée à la première
          commande validée chronologiquement.
        #### 3. 💳 Modalités de Paiement & Retrait
        * Aucun paiement direct n'est effectué
          sur cette application.
        * Le règlement et la remise des articles
          s'effectuent selon les modalités
          convenues directement avec Sarah.
        #### 4. 🔒 Protection des Données (RGPD)
        * Les identifiants de connexion servent
          uniquement à personnaliser votre
          expérience et sécuriser l'accès
          à la boutique.
        * Aucune donnée personnelle n'est vendue
          ou partagée avec des tiers.
        """
    )
    st.caption(
        "Mise à jour : Septembre 2026"
    )
# ============================================================
# 24. AVIS CLIENTS
# ============================================================
st.sidebar.markdown("---")
st.sidebar.markdown(
    "### 🌸 Votre Avis compte !"
)
with st.sidebar.form(
    "formulaire_avis_complet",
    clear_on_submit=True
):
    note_etoiles = st.slider(
        "Notez votre expérience sur la boutique :",
        min_value=1,
        max_value=5,
        value=5,
        help=(
            "1 = À améliorer, "
            "5 = Parfait !"
        )
    )
    avis_texte = st.text_area(
        "Laissez-moi un commentaire ou une idée de produit : 📝",
        placeholder=(
            "Dites-moi ce que vous aimez "
            "ou ce que je devrais améliorer "
            "(points négatifs, produits manquants...)"
        )
    )
    bouton_avis = st.form_submit_button(
        "🚀 Envoyer mon avis"
    )
    if bouton_avis:
        etoiles_visuelles = (
            "⭐" * note_etoiles
        )
        if note_etoiles <= 2:
            statut_avis = (
                "⚠️ **AVIS REÇU "
                "(À AMÉLIORER / POINT NÉGATIF)**"
            )
        else:
            statut_avis = (
                "✨ **Nouvel avis client reçu**"
            )
        commentaire = (
            avis_texte.strip()
            if avis_texte.strip()
            else "Aucun commentaire écrit."
        )
        msg_discord_avis = (
            f"{statut_avis}\n"
            f"👤 **Par :** "
            f"{st.session_state.utilisateur.capitalize()}\n"
            f"📊 **Note :** "
            f"{etoiles_visuelles} "
            f"({note_etoiles}/5)\n"
            f"💬 **Commentaire :** "
            f"{commentaire}"
        )
        if envoyer_discord(
            msg_discord_avis
        ):
            if note_etoiles <= 2:
                st.sidebar.success(
                    "Merci pour ce retour honnête ! "
                    "Sarah va faire le nécessaire "
                    "pour s'améliorer. 💖"
                )
            else:
                st.sidebar.success(
                    "Merci beaucoup pour votre "
                    "superbe note ! 🌸"
                )
        else:
            st.sidebar.error(
                "Petit problème lors de l'envoi. "
                "Vérifiez la configuration Discord."
            )
