import streamlit as st
import pandas as pd
import requests
import re
import unicodedata
import json
import base64
import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
 
st.set_page_config(page_title='Mes Bons Plans de Sarah 🌸', page_icon='🌸', layout='wide')
NOM_BOUTIQUE = 'Mes Bons Plans de Sarah 🌸'
GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit?usp=drivesdk'
STOCK_API_URL = st.secrets.get('STOCK_API_URL', 'https://script.google.com/macros/s/AKfycbytclcNfOboY3y9pAu9ViFkwPt_vVXHCwNI9PfCHnDycpOf6F0lNzmYAQ-51MuCeOCrlQ/exec').strip()
STOCK_API_KEY = st.secrets.get('STOCK_API_KEY', 'Sarah-Ferec11').strip()
DISCORD_WEBHOOK = st.secrets.get('DISCORD_WEBHOOK', 'https://discord.com/api/webhooks/1559204122308124672/ZNOHTnBzND7oJxXhqQjVhDVIz1VjwmBB13E12Q19ZiYOznCQl2Oezgd08OUbibz53o-n').strip()
ADMIN_PASSWORD_HASH = st.secrets.get('ADMIN_PASSWORD_SHA256', 'Chris2025').strip().lower()
DB_PATH = st.secrets.get('DB_PATH', 'sarah_boutique.sqlite3')
st.markdown('''<style>.stApp{background:#F7F0F1;color:#453840}[data-testid="stSidebar"]{background:#F0E2E7}h1,h2,h3{color:#66374D!important}div.stButton>button{border-radius:12px;background:#FFF9FB;color:#713C50;border:1px solid #D8B9C5}div.stButton>button:hover{background:#EEDBE3}</style>''', unsafe_allow_html=True)
 
def normaliser_texte(texte):
   texte = unicodedata.normalize('NFD', str(texte))
   return re.sub(r'\s+', ' ', ''.join(c for c in texte if unicodedata.category(c) != 'Mn').lower()).strip()
 
def trouver_colonne(article, candidats):
   colonnes = {normaliser_texte(k): k for k in article.index}
   for nom in candidats:
       if normaliser_texte(nom) in colonnes:
           return colonnes[normaliser_texte(nom)]
   return None
 
def champ(article, candidats, defaut=''):
   colonne = trouver_colonne(article, candidats)
   if colonne is None:
       return defaut
   valeur = article.get(colonne)
   return defaut if pd.isna(valeur) else valeur
 
def nombre(valeur, defaut=None):
   if valeur is None or pd.isna(valeur) or str(valeur).strip() == '':
       return defaut
   texte = str(valeur).replace('€', '').replace('\u202f', '').replace(' ', '').strip()
   if ',' in texte and '.' in texte:
       texte = texte.replace('.', '').replace(',', '.') if texte.rfind(',') > texte.rfind('.') else texte.replace(',', '')
   else:
       texte = texte.replace(',', '.')
   try:
       return float(texte)
   except ValueError:
       return defaut
 
def nom_produit(a):
   return str(champ(a, ['Dénomination', 'Denomination', 'Produit', 'Nom', 'Article'], 'Produit sans nom')).strip()
 
def categories_produit(a):
   brut = str(champ(a, ['Catégorie', 'Categorie', 'Catégorie produit', 'Famille'], 'Autre'))
   resultat = []
   for element in re.split(r'[,;]', brut):
       element = element.strip()
       if normaliser_texte(element) in ('alimentaire', 'alimentation'):
           element = 'Alimentation'
       if element and normaliser_texte(element) not in [normaliser_texte(x) for x in resultat]:
           resultat.append(element)
   return resultat or ['Autre']
 
def photo_produit(a):
   return str(champ(a, ['Photo produit', 'Photo', 'Image', 'Photo produit URL'], '')).strip()
 
def format_produit(a):
   return str(champ(a, ['Litre / Gramme', 'Litre/Gramme', 'Format', 'Poids', 'Volume'], '')).strip()
 
def obtenir_stock(a):
   return max(0, int(nombre(champ(a, ['Quantité', 'Quantite', 'Stock', 'Stocks'], 0), 0)))
 
def obtenir_prix(a):
   valeur = nombre(champ(a, ['Prix initial', 'Prix', 'Prix normal', 'Tarif', 'Prix de vente', 'Prix vente', 'Prix unitaire', 'Prix TTC'], None))
   return valeur if valeur is not None and valeur > 0 else None
 
def obtenir_prix_promo(a):
   valeur = nombre(champ(a, ['Prix promo', 'Promo', 'Prix promotion', 'Prix promotionnel', 'Prix promotionnel TTC'], None))
   return valeur if valeur is not None and valeur > 0 else None
 
def prix_vente(a):
   return obtenir_prix_promo(a) or obtenir_prix(a)
 
def prix_kg_litre(a):
   prix = prix_vente(a)
   if prix is None:
       return ''
   texte = normaliser_texte(format_produit(a)).replace(',', '.')
   m = re.search(r'(\d+(?:\.\d+)?)\s*(kg|kilogrammes?|gr|grammes?|g|litres?|l|ml|cl)\b', texte)
   if m:
       q, unite = float(m.group(1)), m.group(2)
       multiple = re.search(r'(\d+)\s*[x×]\s*$', texte[:m.start()])
       if multiple:
           q *= int(multiple.group(1))
       if unite in ('g', 'gr', 'gramme', 'grammes', 'ml'):
           q /= 1000
       elif unite == 'cl':
           q /= 100
       if q > 0:
           unit = 'kg' if unite in ('kg', 'g', 'gr', 'gramme', 'grammes') or unite.startswith('kilogramme') else 'L'
           return f'{prix/q:.2f} €/{unit}'.replace('.', ',')
   return str(champ(a, ['Prix au Kg / Litre', 'Prix au Kg/Litre', 'Prix Kg', 'Prix Litre', 'Prix au kilo', 'Prix au litre'], '')).strip()
 
@st.cache_data(ttl=60)
def charger_produits():
   m = re.search(r'/spreadsheets/d/([\w-]+)', GOOGLE_SHEET_URL)
   if not m:
       raise ValueError('Identifiant Google Sheets introuvable.')
   url = f'https://docs.google.com/spreadsheets/d/{m.group(1)}/gviz/tq?tqx=out:csv&sheet=CampoStore'
   try:
       response = requests.get(url, timeout=20)
       response.raise_for_status()
       from io import StringIO
       df = pd.read_csv(StringIO(response.content.decode('utf-8-sig')))
   except Exception as e:
       raise RuntimeError(f'Impossible de lire CampoStore : {e}. Vérifiez les autorisations de partage de la feuille.')
   df.columns = [str(c).strip() for c in df.columns]
   return df.dropna(how='all').reset_index(drop=True)
 
def panier_encode(panier):
   return base64.urlsafe_b64encode(json.dumps(panier, ensure_ascii=False).encode()).decode()
 
def panier_decode(texte):
   try:
       objets = json.loads(base64.urlsafe_b64decode(texte.encode()).decode()) if texte else []
       return [{'produit': str(p['produit']), 'quantite': int(p['quantite']), 'prix': float(p['prix'])} for p in objets if isinstance(p, dict) and int(p['quantite']) > 0 and float(p['prix']) > 0]
   except Exception:
       return []
 
if 'panier' not in st.session_state:
   st.session_state.panier = panier_decode(st.query_params.get('panier', ''))
if 'confirmation' not in st.session_state:
   st.session_state.confirmation = None
if 'stock_erreur' not in st.session_state:
   st.session_state.stock_erreur = False
 
def sauvegarder_panier():
   if st.session_state.panier:
       st.query_params['panier'] = panier_encode(st.session_state.panier)
   elif 'panier' in st.query_params:
       del st.query_params['panier']
 
def ajouter_au_panier(a):
   prix, stock, nom = prix_vente(a), obtenir_stock(a), nom_produit(a)
   if prix is None:
       st.error('Prix manquant : article non commandable.')
       return
   for p in st.session_state.panier:
       if p['produit'] == nom:
           if p['quantite'] < stock:
               p['quantite'] += 1
               p['prix'] = prix
               sauvegarder_panier()
           return
   if stock > 0:
       st.session_state.panier.append({'produit': nom, 'quantite': 1, 'prix': prix})
       sauvegarder_panier()
 
def db_conn():
   db = sqlite3.connect(DB_PATH, timeout=20)
   db.row_factory = sqlite3.Row
   db.execute('PRAGMA busy_timeout=20000')
   return db
 
def initialiser_db():
   with db_conn() as db:
       db.execute('''CREATE TABLE IF NOT EXISTS commandes (id TEXT PRIMARY KEY, cree_le TEXT, nom TEXT, telephone TEXT, adresse TEXT, mode_remise TEXT, precision_lieu TEXT, panier_json TEXT, total_prevu REAL, montant_encaisse REAL, statut TEXT DEFAULT 'réservée', premiere_commande INTEGER DEFAULT 0)''')
       db.execute('''CREATE TABLE IF NOT EXISTS lignes_livrees (commande_id TEXT, produit TEXT, quantite_gardee INTEGER, PRIMARY KEY(commande_id, produit))''')
       cols = {r[1] for r in db.execute('PRAGMA table_info(commandes)')}
       for nom, definition in [('mode_remise', "TEXT DEFAULT 'Livraison à domicile'"), ('precision_lieu', "TEXT DEFAULT ''"), ('montant_encaisse', 'REAL'), ('statut', "TEXT DEFAULT 'réservée'")]:
           if nom not in cols:
               db.execute(f'ALTER TABLE commandes ADD COLUMN {nom} {definition}')
 
initialiser_db()
 
def envoyer_discord(message):
   if not DISCORD_WEBHOOK:
       return False, 'Webhook Discord non configuré dans les Secrets Streamlit.'
   try:
       rep = requests.post(DISCORD_WEBHOOK, json={'content': message[:1900]}, timeout=15)
       return rep.status_code in (200, 204), '' if rep.status_code in (200, 204) else f'Code Discord : {rep.status_code}'
   except requests.RequestException as e:
       return False, str(e)
 
def retirer_stock_commande(panier, reference):
   if not STOCK_API_URL or not STOCK_API_KEY:
       return False, 'STOCK_API_URL ou STOCK_API_KEY manquant dans Secrets.'
   payload = {'action': 'retirer_commande', 'reference': reference, 'secret': STOCK_API_KEY, 'produits': [{'produit': p['produit'], 'quantite': p['quantite']} for p in panier]}
   try:
       rep = requests.post(STOCK_API_URL, json=payload, timeout=20)
       rep.raise_for_status()
       data = rep.json()
       return data.get('success') is True, str(data.get('message', 'Réponse de stock sans confirmation.'))
   except (requests.RequestException, ValueError) as e:
       return False, str(e)
 
def creer_pdf(c, lignes):
   buf = BytesIO()
   doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=35, rightMargin=35)
   styles = getSampleStyleSheet()
   els = [Paragraph('Mes Bons Plans de Sarah - Récapitulatif non acquitté', styles['Heading1'])]
   for titre, valeur in [('Référence', c['id']), ('Client', c['nom']), ('Téléphone', c['telephone']), ('Lieu', c['adresse']), ('Remise', c['mode_remise']), ('Statut', c['statut'])]:
       els.append(Paragraph(f'<b>{escape(titre)} :</b> {escape(str(valeur or ""))}', styles['Normal']))
       els.append(Spacer(1, 6))
   data = [['Article', 'Qté', 'Prix', 'Total']]
   for p in lignes:
       data.append([Paragraph(escape(p['produit']), styles['Normal']), str(p['quantite']), f"{p['prix']:.2f} €", f"{p['prix']*p['quantite']:.2f} €"])
   data.append(['TOTAL PRÉVU', '', '', f"{c['total_prevu']:.2f} €"])
   tab = Table(data, colWidths=[240, 45, 80, 100], repeatRows=1)
   tab.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEDBE3')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
   els.extend([Spacer(1, 12), tab, Spacer(1, 15), Paragraph('Document non acquitté. Paiement uniquement à la remise des articles conservés. Frais de livraison éventuels à confirmer.', styles['Normal'])])
   doc.build(els)
   return buf.getvalue()
 
def afficher_admin():
   if not ADMIN_PASSWORD_HASH:
       st.warning('Définissez ADMIN_PASSWORD_SHA256 dans Secrets pour activer cette page.')
       return
   if not st.session_state.get('admin_auth', False):
       with st.form('connexion_admin'):
           pwd = st.text_input('Mot de passe', type='password')
           entrer = st.form_submit_button('Connexion')
       if entrer:
           if hmac.compare_digest(hashlib.sha256(pwd.encode()).hexdigest(), ADMIN_PASSWORD_HASH):
               st.session_state.admin_auth = True
               st.rerun()
           else:
               st.error('Mot de passe incorrect.')
       return
   if st.button('Déconnexion'):
       st.session_state.admin_auth = False
       st.rerun()
   with db_conn() as db:
       commandes = db.execute('SELECT * FROM commandes ORDER BY cree_le DESC LIMIT 200').fetchall()
   for c in commandes:
       with st.expander(f"{c['id']} · {c['nom']} · {c['statut']}"):
           st.write(f"Téléphone : {c['telephone']} | {c['mode_remise']} : {c['adresse']}")
           st.write(f"Total : {c['total_prevu']:.2f} €")
           lignes = json.loads(c['panier_json'])
           st.download_button('📄 Récapitulatif PDF', creer_pdf(c, lignes), file_name=f"commande_{c['id']}.pdf", mime='application/pdf', key='pdf'+c['id'])
           if c['statut'] == 'réservée':
               with st.form('livraison'+c['id']):
                   gardees = [st.number_input(p['produit'], min_value=0, max_value=int(p['quantite']), value=int(p['quantite']), key=f"garde_{c['id']}_{i}") for i, p in enumerate(lignes)]
                   montant = sum(q*p['prix'] for q, p in zip(gardees, lignes))
                   st.write(f'Montant encaissé : {montant:.2f} €')
                   valider = st.form_submit_button('Livraison terminée')
               if valider:
                   with db_conn() as db:
                       db.execute("UPDATE commandes SET statut='livrée', montant_encaisse=? WHERE id=?", (montant, c['id']))
                       for q, p in zip(gardees, lignes):
                           db.execute('INSERT OR REPLACE INTO lignes_livrees VALUES (?,?,?)', (c['id'], p['produit'], q))
                   st.warning('Réintégrez manuellement au stock les produits refusés.')
                   st.rerun()
               if st.button('Annuler la commande', key='annuler'+c['id']):
                   with db_conn() as db:
                       db.execute("UPDATE commandes SET statut='annulée' WHERE id=?", (c['id'],))
                   st.warning('Vérifiez et réintégrez manuellement le stock.')
                   st.rerun()
 
def afficher_panier():
   st.sidebar.header('🌸 Mes Bons Plans de Sarah')
   panier = st.session_state.panier
   with st.sidebar.expander(f"🛒 Panier ({sum(p['quantite'] for p in panier)} articles)", expanded=True):
       if not panier:
           st.info('Votre panier est vide 🌸')
           return
       for i, p in enumerate(list(panier)):
           st.markdown(f"**{p['produit']}** — {p['prix']:.2f} € × {p['quantite']}")
           moins, plus, retirer = st.columns(3)
           if moins.button('−', key=f'moins{i}'):
               p['quantite'] -= 1
               if p['quantite'] == 0:
                   panier.pop(i)
               sauvegarder_panier()
               st.rerun()
           if plus.button('+', key=f'plus{i}'):
               try:
                   df = charger_produits()
                   lignes = df[df.apply(nom_produit, axis=1) == p['produit']]
                   if not lignes.empty:
                       ajouter_au_panier(lignes.iloc[0])
                       st.rerun()
               except Exception as e:
                   st.error(str(e))
           if retirer.button('🗑️', key=f'suppr{i}'):
               panier.pop(i)
               sauvegarder_panier()
               st.rerun()
       st.markdown(f"### Total : {sum(p['quantite']*p['prix'] for p in panier):.2f} €")
       nom = st.text_input('Nom et prénom', key='client_nom')
       telephone = st.text_input('Téléphone', key='client_tel')
       mode = st.radio('Mode de remise', ['Point de rendez-vous', 'Livraison à domicile'], key='client_mode')
       adresse = st.text_area('Adresse de livraison ou lieu de rendez-vous', key='client_adresse')
       precision = st.text_input('Précisions (facultatif)', key='client_precision')
       premiere = st.checkbox('🎁 Première commande : livraison offerte demandée', key='client_premiere')
       st.caption('Sarah vous contactera pour convenir du lieu et de l’horaire. Aucun paiement à l’avance. Frais éventuels à confirmer.')
       if st.session_state.stock_erreur:
           st.error('Commande déjà transmise, mais stock non confirmé. Contactez Sarah : ne recommencez pas.')
       if st.button('🚀 Valider ma commande', disabled=st.session_state.stock_erreur):
           if not all([nom.strip(), telephone.strip(), adresse.strip()]):
               st.error('Renseignez le nom, le téléphone et le lieu.')
               return
           try:
               df = charger_produits()
               catalogue = {nom_produit(a): a for _, a in df.iterrows()}
               commande_panier = []
               for p in panier:
                   a = catalogue.get(p['produit'])
                   if a is None or obtenir_stock(a) < p['quantite']:
                       raise ValueError('Article introuvable ou stock insuffisant : '+p['produit'])
                   prix = prix_vente(a)
                   if prix is None:
                       raise ValueError('Prix manquant pour : '+p['produit'])
                   commande_panier.append({'produit': p['produit'], 'quantite': p['quantite'], 'prix': prix})
               total = sum(p['quantite']*p['prix'] for p in commande_panier)
               ref = secrets.token_hex(6).upper()
               with db_conn() as db:
                   db.execute('INSERT INTO commandes (id,cree_le,nom,telephone,adresse,mode_remise,precision_lieu,panier_json,total_prevu,premiere_commande) VALUES (?,?,?,?,?,?,?,?,?,?)', (ref, datetime.now().isoformat(timespec='seconds'), nom.strip(), telephone.strip(), adresse.strip(), mode, precision.strip(), json.dumps(commande_panier, ensure_ascii=False), total, int(premiere)))
               lignes = '\n'.join(f"• {p['produit']} × {p['quantite']} — {p['quantite']*p['prix']:.2f} €" for p in commande_panier)
               message = f'🌸 NOUVELLE COMMANDE {ref}\nClient : {nom}\nTéléphone : {telephone}\n{mode} : {adresse}\nPrécisions : {precision}\n{lignes}\nTOTAL : {total:.2f} €\nPremière livraison offerte demandée : {"oui" if premiere else "non"}'
               ok, err = envoyer_discord(message)
               if not ok:
                   with db_conn() as db:
                       db.execute("UPDATE commandes SET statut='annulée' WHERE id=?", (ref,))
                   st.error('Notification impossible : '+err)
                   return
               ok_stock, err_stock = retirer_stock_commande(commande_panier, ref)
               if not ok_stock:
                   st.session_state.stock_erreur = True
                   st.error(f'Commande {ref} transmise, mais stock non confirmé. Ne recommencez pas. {err_stock}')
                   return
               st.session_state.confirmation = {'reference': ref, 'total': total, 'nombre': sum(p['quantite'] for p in commande_panier)}
               st.session_state.panier = []
               sauvegarder_panier()
               st.cache_data.clear()
               st.rerun()
           except Exception as e:
               st.error('Impossible de valider : '+str(e))
 
afficher_panier()
if st.session_state.confirmation:
   c = st.session_state.confirmation
   st.success(f"🎉 Merci ! Commande {c['reference']} reçue — {c['nombre']} articles — {c['total']:.2f} €")
   st.info('Sarah vous contactera pour organiser la remise. Aucun paiement à l’avance.')
   if st.button('Fermer la confirmation'):
       st.session_state.confirmation = None
       st.rerun()
 
page = st.radio('Navigation', ['🏠 Accueil', '🛍️ Boutique', '💝 Liste de souhaits', '🚚 Livraisons', '🔐 Administration'], horizontal=True, label_visibility='collapsed')
if page == '🏠 Accueil':
   st.title('🌸 Mes Bons Plans de Sarah')
   st.subheader('Vos marques préférées à prix doux ♡')
   st.write('Lessive · Entretien · Hygiène · Alimentation · Promotions')
   st.info('🎁 Première livraison offerte sous réserve de vérification et de zone desservie.')
elif page == '💝 Liste de souhaits':
   st.title('💝 Liste de souhaits')
   with st.form('souhaits', clear_on_submit=True):
       nom = st.text_input('Nom et prénom')
       contact = st.text_input('Téléphone')
       liste = st.text_area('Produits recherchés (marque, format, quantité)')
       accord = st.checkbox("J'accepte d'être contacté pour cette demande")
       envoyer = st.form_submit_button('💌 Envoyer ma liste')
   if envoyer:
       if not (nom.strip() and contact.strip() and liste.strip() and accord):
           st.warning('Complétez tous les champs et votre accord.')
       else:
           ok, err = envoyer_discord(f'📝 LISTE DE SOUHAITS\nNom : {nom}\nTéléphone : {contact}\nProduits : {liste}\nAucune commande ni retrait de stock.')
           st.success('Liste transmise à Sarah !') if ok else st.error(err)
elif page == '🚚 Livraisons':
   st.title('🚚 Livraisons et points de rendez-vous')
   st.info('Sarah vous contactera par téléphone pour fixer le lieu et l’horaire.')
elif page == '🔐 Administration':
   st.title('🔐 Administration')
   afficher_admin()
else:
   st.title('🛍️ La boutique')
   try:
       df = charger_produits()
       if df.empty:
           st.warning('Aucun produit dans CampoStore.')
       else:
           categories = sorted({c for _, a in df.iterrows() for c in categories_produit(a)}, key=normaliser_texte)
           categories = ['Tous'] + categories
           recherche = st.text_input('🔎 Rechercher un produit')
           categorie = st.selectbox('📁 Rayon', categories)
           filtre = df
           if categorie != 'Tous':
               filtre = filtre[filtre.apply(lambda a: categorie in categories_produit(a), axis=1)]
           if recherche.strip():
               mot = normaliser_texte(recherche)
               filtre = filtre[filtre.apply(lambda a: mot in normaliser_texte(nom_produit(a)+' '+format_produit(a)+' '+' '.join(categories_produit(a))), axis=1)]
           st.caption(f'{len(filtre)} produit(s) affiché(s)')
           colonnes = st.columns(3)
           for i, (_, a) in enumerate(filtre.iterrows()):
               with colonnes[i % 3]:
                   with st.container(border=True):
                       photo = photo_produit(a)
                       if photo.startswith(('http://', 'https://')):
                           try:
                               st.image(photo, use_container_width=True)
                           except Exception:
                               st.caption('Photo indisponible')
                       st.markdown(f'**{nom_produit(a)}**')
                       if format_produit(a):
                           st.caption('📦 '+format_produit(a))
                       normal, promo, stock = obtenir_prix(a), obtenir_prix_promo(a), obtenir_stock(a)
                       if promo is not None:
                           if normal is not None and normal > promo:
                               st.markdown(f'~~{normal:.2f} €~~ 🔴 **PROMO : {promo:.2f} €**')
                           else:
                               st.markdown(f'🔴 **PROMO : {promo:.2f} €**')
                       elif normal is not None:
                           st.markdown(f'**Prix : {normal:.2f} €**')
                       else:
                           st.warning('Prix à renseigner dans CampoStore')
                       unitaire = prix_kg_litre(a)
                       if unitaire:
                           st.caption('⚖️ '+unitaire)
                       q_panier = sum(p['quantite'] for p in st.session_state.panier if p['produit'] == nom_produit(a))
                       st.caption(f'Stock disponible : {max(0, stock-q_panier)}')
                       if stock <= 0:
                           st.error('🚫 Rupture de stock')
                       elif st.button('➕ Ajouter', key=f'ajouter_{i}', disabled=prix_vente(a) is None or q_panier >= stock):
                           ajouter_au_panier(a)
                           st.rerun()
   except Exception as e:
       st.error('Erreur de chargement du catalogue : '+str(e))