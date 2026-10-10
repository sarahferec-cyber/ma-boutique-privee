
0002  import streamlit as st
0003   
0004  import pandas as pd
0005   
0006  import requests
0007   
0008  import re
0009   
0010  import unicodedata
0011   
0012  import json
0013   
0014  import base64
0015  import sqlite3
0016  import hashlib
0017  import hmac
0018  import secrets
0019  import smtplib
0020  from email.message import EmailMessage
0021  from datetime import datetime, date, timedelta
0022   
0023   
0024   
0025  # ============================================================
0026   
0027  # CONFIGURATION ET CONSTANTES
0028   
0029  # ============================================================
0030   
0031  NOM_BOUTIQUE = "Mes Bons Plans de Sarah 🌸"
0032   
0033   
0034   
0035  GOOGLE_SHEET_URL = (
0036   
0037      "https://docs.google.com/spreadsheets/d/"
0038   
0039      "1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit?usp=sharing"
0040   
0041  )
0042   
0043   
0044   
0045  STOCK_API_URL = (
0046   
0047      "https://script.google.com/macros/s/"
0048   
0049      "AKfycbxTep4v3fevHxUE0Cv6f6SE1IRie_xCNctecO_7Ez_XXhNUQJlhc46l6mkDe-FQk7s5lA/exec"
0050   
0051  )
0052   
0053   
0054   
0055  # IMPORTANT :
0056   
0057  # Dans Streamlit > Settings > Secrets, ajouter :
0058   
0059  # DISCORD_WEBHOOK = " https://discord.com/api/webhooks/1549946850885238865/OItwwHS0spEUH0vzmBSJjAaCXwx2Yicaz2l30EolaALbmEufafnZI36M"
0060   
0061  DISCORD_WEBHOOK = st.secrets.get("DISCORD_WEBHOOK", "")
0062   
0063   
0064   
0065  # ATTENTION : pour Streamlit Community Cloud, un fichier SQLite local peut être perdu
0066  # lors d'un redémarrage. Utiliser un stockage persistant avant ouverture publique.
0067  DB_PATH = st.secrets.get("DB_PATH", "sarah_boutique.sqlite3")
0068  ADMIN_PASSWORD_HASH = st.secrets.get("ADMIN_PASSWORD_SHA256", "")
0069  
0070   
0071   
0072   
0073  # ============================================================
0074   
0075  # CONFIGURATION INTERFACE STREAMLIT
0076   
0077  # ============================================================
0078   
0079  st.set_page_config(
0080   
0081      page_title=NOM_BOUTIQUE,
0082   
0083      page_icon="🌸",
0084   
0085      layout="wide"
0086   
0087  )
0088   
0089   
0090   
0091  # ============================================================
0092   
0093  st.markdown("""
0094  <style>
0095  :root {--rose:#A56880;--prune:#66374D;--fond:#F7F0F1;--card:#FFFCFB;}
0096  .stApp,[data-testid="stAppViewContainer"] {background:#F7F0F1;color:#453840;}
0097  [data-testid="stSidebar"] {background:#F0E2E7;border-right:1px solid #E4CDD6;}
0098  [data-testid="stHeader"] {background:rgba(247,240,241,.96);}
0099  [data-testid="stMainBlockContainer"] {max-width:1350px;padding-top:2rem;}
0100  h1,h2,h3 {color:#66374D!important;}
0101  [data-testid="stMarkdownContainer"] p {line-height:1.5;}
0102  div[data-testid="stVerticalBlockBorderWrapper"] > div[style*="border"] {background:#FFFCFB;border:1px solid #EAD9DF!important;border-radius:17px!important;box-shadow:0 5px 18px rgba(102,55,77,.07);padding:10px;}
0103  div.stButton > button {border-radius:12px!important;border:1px solid #D8B9C5!important;background:#FFF9FB;color:#713C50;font-weight:600;min-height:40px;}
0104  div.stButton > button:hover {background:#EEDBE3;color:#66374D;border-color:#A56880!important;}
0105  div.stButton > button[kind="primary"] {background:#A56880!important;color:white!important;border-color:#A56880!important;}
0106  [data-testid="stTextInput"] input {background:#FFFCFB;border-radius:11px;}
0107  [data-testid="stSelectbox"] div[data-baseweb="select"] > div {background:#FFFCFB;border-radius:11px;}
0108  [data-testid="stImage"] img {object-fit:contain;max-height:230px;}
0109  @media(max-width:700px){[data-testid="stMainBlockContainer"]{padding:1rem .7rem;}h1{font-size:1.7rem!important;}}
0110  </style>
0111  """, unsafe_allow_html=True)# FONCTIONS DE PERSISTANCE DU PANIER
0112   
0113  # Le panier est encodé dans le paramètre ?panier= de l'URL.
0114   
0115  # Il reste donc présent après un rechargement de la page.
0116   
0117  # ============================================================
0118   
0119  def encoder_panier(panier):
0120   
0121      try:
0122   
0123          brut = json.dumps(
0124   
0125              panier,
0126   
0127              ensure_ascii=False,
0128   
0129              separators=(",", ":")
0130   
0131          ).encode("utf-8")
0132   
0133          return base64.urlsafe_b64encode(brut).decode("ascii")
0134   
0135      except Exception:
0136   
0137          return ""
0138   
0139   
0140   
0141   
0142   
0143  def decoder_panier(valeur):
0144   
0145      try:
0146   
0147          if not valeur:
0148   
0149              return []
0150   
0151          brut = base64.urlsafe_b64decode(valeur.encode("ascii"))
0152   
0153          panier = json.loads(brut.decode("utf-8"))
0154   
0155          if not isinstance(panier, list):
0156   
0157              return []
0158   
0159   
0160   
0161          panier_propre = []
0162   
0163          for produit in panier:
0164   
0165              if not isinstance(produit, dict):
0166   
0167                  continue
0168   
0169   
0170   
0171              nom = str(produit.get("produit", "")).strip()
0172   
0173              quantite = int(produit.get("quantite", 0))
0174   
0175              prix = float(produit.get("prix", 0))
0176   
0177   
0178   
0179              if nom and quantite > 0 and prix >= 0:
0180   
0181                  panier_propre.append({
0182   
0183                      "produit": nom,
0184   
0185                      "quantite": quantite,
0186   
0187                      "prix": prix
0188   
0189                  })
0190   
0191   
0192   
0193          return panier_propre
0194   
0195      except Exception:
0196   
0197          return []
0198   
0199   
0200   
0201   
0202   
0203  def sauvegarder_panier():
0204   
0205      if st.session_state.panier:
0206   
0207          st.query_params["panier"] = encoder_panier(st.session_state.panier)
0208   
0209      else:
0210   
0211          if "panier" in st.query_params:
0212   
0213              del st.query_params["panier"]
0214   
0215   
0216   
0217   
0218   
0219  def vider_panier():
0220   
0221      st.session_state.panier = []
0222   
0223      sauvegarder_panier()
0224   
0225   
0226   
0227   
0228   
0229  # ============================================================
0230   
0231  # INITIALISATION ET PERSISTANCE DE LA SESSION
0232   
0233  # ============================================================
0234   
0235  if "panier" not in st.session_state:
0236   
0237      panier_url = st.query_params.get("panier", "")
0238   
0239      st.session_state.panier = decoder_panier(panier_url)
0240   
0241   
0242   
0243  if "commande_envoyee" not in st.session_state:
0244      st.session_state.commande_envoyee = False
0245  if "confirmation_commande" not in st.session_state:
0246      st.session_state.confirmation_commande = None
0247  if "animation_confirmation" not in st.session_state:
0248      st.session_state.animation_confirmation = False
0249  if "commande_stock_en_erreur" not in st.session_state:
0250      st.session_state.commande_stock_en_erreur = False
0251   
0252   
0253   
0254  # ============================================================
0255   
0256  # FONCTIONS OUTILS ET NORMALISATION
0257   
0258  # ============================================================
0259   
0260  def normaliser_texte(texte):
0261   
0262      texte = str(texte)
0263   
0264      texte = unicodedata.normalize("NFD", texte)
0265   
0266      texte = "".join(
0267   
0268          caractere
0269   
0270          for caractere in texte
0271   
0272          if unicodedata.category(caractere) != "Mn"
0273   
0274      )
0275   
0276      texte = texte.lower()
0277   
0278      re_space = re.compile(r"\s+")
0279   
0280      texte = re_space.sub(" ", texte).strip()
0281   
0282      return texte
0283   
0284   
0285   
0286   
0287   
0288  def trouver_colonne(article, noms_possibles):
0289   
0290      if hasattr(article, "index"):
0291   
0292          colonnes = list(article.index)
0293   
0294      elif isinstance(article, dict):
0295   
0296          colonnes = list(article.keys())
0297   
0298      else:
0299   
0300          return None
0301   
0302   
0303   
0304      colonnes_normalisees = {
0305   
0306          normaliser_texte(colonne): colonne
0307   
0308          for colonne in colonnes
0309   
0310      }
0311   
0312   
0313   
0314      for nom in noms_possibles:
0315   
0316          cle = normaliser_texte(nom)
0317   
0318          if cle in colonnes_normalisees:
0319   
0320              return colonnes_normalisees[cle]
0321   
0322   
0323   
0324      return None
0325   
0326   
0327   
0328   
0329   
0330  def convertir_nombre(valeur, valeur_defaut=0.0):
0331   
0332      if valeur is None or pd.isna(valeur):
0333   
0334          return valeur_defaut
0335   
0336   
0337   
0338      if isinstance(valeur, (int, float)):
0339   
0340          return float(valeur)
0341   
0342   
0343   
0344      texte = str(valeur).strip()
0345   
0346   
0347   
0348      if not texte:
0349   
0350          return valeur_defaut
0351   
0352   
0353   
0354      texte = texte.replace("€", "").replace(" ", "")
0355   
0356   
0357   
0358      if "," in texte and "." in texte:
0359   
0360          if texte.rfind(",") > texte.rfind("."):
0361   
0362              texte = texte.replace(".", "").replace(",", ".")
0363   
0364          else:
0365   
0366              texte = texte.replace(",", "")
0367   
0368      else:
0369   
0370          texte = texte.replace(",", ".")
0371   
0372   
0373   
0374      try:
0375   
0376          return float(texte)
0377   
0378      except Exception:
0379   
0380          return valeur_defaut
0381   
0382   
0383   
0384   
0385   
0386  # ============================================================
0387   
0388  # LECTURE ET EXTRACTION DU GOOGLE SHEET
0389   
0390  # ============================================================
0391   
0392  def nom_produit(article):
0393   
0394      colonne = trouver_colonne(
0395   
0396          article,
0397   
0398          ["Denomination", "Dénomination", "Produit", "Nom", "Article"]
0399   
0400      )
0401   
0402      return (
0403   
0404          str(article.get(colonne, "Produit sans nom")).strip()
0405   
0406          if colonne
0407   
0408          else "Produit sans nom"
0409   
0410      )
0411   
0412   
0413   
0414   
0415   
0416  def categorie_produit(article):
0417   
0418      colonne = trouver_colonne(
0419   
0420          article,
0421   
0422          ["Categorie", "Catégorie", "Catégorie produit", "Famille"]
0423   
0424      )
0425   
0426      valeur = article.get(colonne, "Autre") if colonne else "Autre"
0427   
0428      return (
0429   
0430          "Autre"
0431   
0432          if pd.isna(valeur) or str(valeur).strip() == ""
0433   
0434          else str(valeur).strip()
0435   
0436      )
0437   
0438   
0439   
0440   
0441   
0442  def photo_produit(article):
0443   
0444      colonne = trouver_colonne(
0445   
0446          article,
0447   
0448          ["Photo produit", "Photo", "Image", "Photo produit URL"]
0449   
0450      )
0451   
0452      return (
0453   
0454          str(article.get(colonne, "")).strip()
0455   
0456          if colonne and not pd.isna(article.get(colonne))
0457   
0458          else ""
0459   
0460      )
0461   
0462   
0463   
0464   
0465   
0466  def obtenir_stock(article):
0467   
0468      colonne = trouver_colonne(
0469   
0470          article,
0471   
0472          ["Quantité", "Quantite", "Stock", "Stocks"]
0473   
0474      )
0475   
0476      return (
0477   
0478          int(convertir_nombre(article.get(colonne, 0), 0))
0479   
0480          if colonne
0481   
0482          else 0
0483   
0484      )
0485   
0486   
0487   
0488   
0489   
0490  def obtenir_prix(article):
0491   
0492      colonne = trouver_colonne(
0493   
0494          article,
0495   
0496          ["Prix initial", "Prix", "Prix normal", "Tarif"]
0497   
0498      )
0499   
0500      return (
0501   
0502          convertir_nombre(article.get(colonne, 0.0), 0.0)
0503   
0504          if colonne
0505   
0506          else 0.0
0507   
0508      )
0509   
0510   
0511   
0512   
0513   
0514  def obtenir_prix_promo(article):
0515   
0516      colonne = trouver_colonne(
0517   
0518          article,
0519   
0520          ["Prix promo", "Promo", "Prix promotion", "Prix promotionnel"]
0521   
0522      )
0523   
0524   
0525   
0526      if colonne is None:
0527   
0528          return None
0529   
0530   
0531   
0532      valeur = article.get(colonne, "")
0533   
0534   
0535   
0536      if pd.isna(valeur) or str(valeur).strip() == "":
0537   
0538          return None
0539   
0540   
0541   
0542      prix = convertir_nombre(valeur, 0.0)
0543   
0544      return prix if prix > 0 else None
0545   
0546   
0547   
0548   
0549   
0550  def format_produit(article):
0551   
0552      colonne = trouver_colonne(
0553   
0554          article,
0555   
0556          ["Litre / Gramme", "Litre/Gramme", "Format", "Poids", "Volume"]
0557   
0558      )
0559   
0560      return (
0561   
0562          str(article.get(colonne, "")).strip()
0563   
0564          if colonne and not pd.isna(article.get(colonne))
0565   
0566          else ""
0567   
0568      )
0569   
0570   
0571   
0572   
0573   
0574  def prix_kg_litre(article):
0575   
0576      colonne = trouver_colonne(
0577   
0578          article,
0579   
0580          [
0581   
0582              "Prix au Kg / Litre",
0583   
0584              "Prix au Kg/Litre",
0585   
0586              "Prix Kg",
0587   
0588              "Prix Litre",
0589   
0590              "Prix au kilo",
0591   
0592              "Prix au litre"
0593   
0594          ]
0595   
0596      )
0597   
0598      return (
0599   
0600          str(article.get(colonne, "")).strip()
0601   
0602          if colonne and not pd.isna(article.get(colonne))
0603   
0604          else ""
0605   
0606      )
0607   
0608   
0609   
0610   
0611   
0612  @st.cache_data(ttl=60)
0613   
0614  def charger_produits():
0615   
0616      match = re.search(
0617   
0618          r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
0619   
0620          GOOGLE_SHEET_URL
0621   
0622      )
0623   
0624   
0625   
0626      if not match:
0627   
0628          raise ValueError(
0629   
0630              "Impossible de trouver l'identifiant du Google Sheet."
0631   
0632          )
0633   
0634   
0635   
0636      spreadsheet_id = match.group(1)
0637   
0638      url_csv = (
0639   
0640          f"https://docs.google.com/spreadsheets/d/"
0641   
0642          f"{spreadsheet_id}/export?format=csv"
0643   
0644      )
0645   
0646   
0647   
0648      try:
0649   
0650          dataframe = pd.read_csv(url_csv)
0651   
0652      except Exception as erreur:
0653   
0654          raise RuntimeError(
0655   
0656              f"Impossible de charger le Google Sheet : {erreur}"
0657   
0658          )
0659   
0660   
0661   
0662      if dataframe.empty:
0663   
0664          return dataframe
0665   
0666   
0667   
0668      dataframe.columns = [
0669   
0670          str(colonne).strip()
0671   
0672          for colonne in dataframe.columns
0673   
0674      ]
0675   
0676   
0677   
0678      dataframe = dataframe.dropna(how="all").reset_index(drop=True)
0679   
0680      return dataframe
0681   
0682   
0683   
0684   
0685   
0686  # ============================================================
0687   
0688  # LOGIQUE ET INTERACTIONS DU PANIER
0689   
0690  # ============================================================
0691   
0692  def ajouter_au_panier(article):
0693   
0694      nom = nom_produit(article)
0695   
0696      prix_normal = obtenir_prix(article)
0697   
0698      prix_promo = obtenir_prix_promo(article)
0699   
0700      prix_final = (
0701   
0702          prix_promo
0703   
0704          if prix_promo is not None
0705   
0706          else prix_normal
0707   
0708      )
0709   
0710   
0711   
0712      stock = obtenir_stock(article)
0713   
0714   
0715   
0716      for produit in st.session_state.panier:
0717   
0718          if produit["produit"] == nom:
0719   
0720              if produit["quantite"] < stock:
0721   
0722                  produit["quantite"] += 1
0723   
0724                  sauvegarder_panier()
0725   
0726              return
0727   
0728   
0729   
0730      if stock > 0:
0731   
0732          st.session_state.panier.append({
0733   
0734              "produit": nom,
0735   
0736              "quantite": 1,
0737   
0738              "prix": prix_final
0739   
0740          })
0741   
0742          sauvegarder_panier()
0743   
0744   
0745   
0746   
0747   
0748  def diminuer_du_panier(index):
0749      """Diminue d'une unité, puis supprime si la quantité atteint zéro."""
0750      if 0 <= index < len(st.session_state.panier):
0751          article = st.session_state.panier[index]
0752          if article["quantite"] > 1:
0753              article["quantite"] -= 1
0754          else:
0755              st.session_state.panier.pop(index)
0756          sauvegarder_panier()
0757   
0758   
0759  def supprimer_du_panier(index):
0760   
0761      if 0 <= index < len(st.session_state.panier):
0762   
0763          st.session_state.panier.pop(index)
0764   
0765          sauvegarder_panier()
0766   
0767   
0768   
0769   
0770   
0771  # ============================================================
0772   
0773  # TRANSMISSION DISCORD
0774   
0775  # ============================================================
0776   
0777  def envoyer_commande_discord(
0778   
0779      nom_client,
0780   
0781      adresse_livraison,
0782   
0783      panier,
0784   
0785      total_articles,
0786   
0787      total_general,
0788      premiere_commande=False, telephone="", email="", creneau="", reference=""
0789   
0790  ):
0791   
0792      if not DISCORD_WEBHOOK:
0793   
0794          return False, (
0795   
0796              "Le webhook Discord n'est pas configuré dans "
0797   
0798              "les Secrets Streamlit."
0799   
0800          )
0801   
0802   
0803   
0804      lignes = []
0805   
0806   
0807   
0808      for produit in panier:
0809   
0810          sous_total = produit["quantite"] * produit["prix"]
0811   
0812          lignes.append(
0813   
0814              f"• {produit['produit']} × {produit['quantite']} "
0815   
0816              f"— {sous_total:.2f} €"
0817   
0818          )
0819   
0820   
0821   
0822      message = (
0823   
0824          "🌸 **NOUVELLE COMMANDE — Mes Bons Plans de Sarah**\n\n"
0825   
0826          f"👤 **Client :** {nom_client}\n"
0827   
0828          f"📍 **Adresse :** {adresse_livraison}\n"
0829           f"📞 **Téléphone :** {telephone}\n📧 **E-mail :** {email}\n"
0830           f"📅 **Livraison :** {creneau}\n🔖 **Référence :** {reference}\n\n"
0831   
0832          "🛒 **Produits :**\n"
0833   
0834          + "\n".join(lignes)
0835   
0836          + "\n\n"
0837   
0838          f"💰 TOTAL ARTICLES : **{total_general:.2f} €**\n"
0839          + ("🎁 **Livraison offerte demandée (première commande déclarée) — à vérifier manuellement**\n" if premiere_commande else "🚚 Livraison : modalités et frais à confirmer\n")
0840   
0841      )
0842   
0843   
0844   
0845      try:
0846   
0847          reponse = requests.post(
0848   
0849              DISCORD_WEBHOOK,
0850   
0851              json={"content": message},
0852   
0853              timeout=15
0854   
0855          )
0856   
0857   
0858   
0859          if reponse.status_code in (200, 204):
0860   
0861              return True, ""
0862   
0863   
0864   
0865          return False, (
0866   
0867              f"Discord a répondu avec le code "
0868   
0869              f"{reponse.status_code}."
0870   
0871          )
0872   
0873   
0874   
0875      except Exception as erreur:
0876   
0877          return False, f"Erreur Discord : {erreur}"
0878   
0879   
0880   
0881   
0882   
0883  # ============================================================
0884   
0885  # RETRAIT DES PRODUITS DU STOCK
0886   
0887  # ============================================================
0888   
0889  def envoyer_liste_courses(nom, contact, liste):
0890      if not DISCORD_WEBHOOK:
0891          return False, "Discord n'est pas configuré."
0892      message = (
0893          "📝 **NOUVELLE LISTE DE COURSES / RECHERCHE**\n"
0894          f"👤 Nom : {nom}\n📞 Contact : {contact}\n"
0895          f"🔎 Produits recherchés :\n{liste}\n\n"
0896          "ℹ️ Recherche uniquement : aucun achat ni retrait de stock."
0897      )
0898      try:
0899          reponse = requests.post(DISCORD_WEBHOOK, json={"content": message}, timeout=15)
0900          return reponse.status_code in (200, 204), ("" if reponse.status_code in (200, 204) else f"Discord : {reponse.status_code}")
0901      except requests.RequestException as erreur:
0902          return False, str(erreur)
0903   
0904   
0905  def retirer_stock_commande(panier):
0906      payload = {
0907          "action": "retirer_commande",
0908          "produits": [
0909              {
0910                  "produit": produit["produit"],
0911                  "quantite": produit["quantite"]
0912              }
0913              for produit in panier
0914          ]
0915      }
0916   
0917      try:
0918          reponse = requests.post(
0919              STOCK_API_URL,
0920              json=payload,
0921              timeout=15
0922          )
0923   
0924          resultat = reponse.json()
0925   
0926          if resultat.get("success") is True:
0927              return True, []
0928   
0929          return False, [
0930              resultat.get(
0931                  "message",
0932                  "Erreur inconnue lors du retrait du stock."
0933              )
0934          ]
0935   
0936      except Exception as erreur:
0937          return False, [str(erreur)]
0938  # ============================================================
0939   
0940  # ============================================================
0941  # LIVRAISONS, COMMANDES ET ADMINISTRATION
0942  # ============================================================
0943  def db_conn():
0944      connexion = sqlite3.connect(DB_PATH, timeout=20)
0945      connexion.row_factory = sqlite3.Row
0946      connexion.execute("PRAGMA busy_timeout=20000")
0947      return connexion
0948  
0949  
0950  def initialiser_db():
0951      with db_conn() as db:
0952          db.execute("CREATE TABLE IF NOT EXISTS creneaux (id INTEGER PRIMARY KEY AUTOINCREMENT, jour TEXT NOT NULL, debut TEXT NOT NULL, fin TEXT NOT NULL, capacite INTEGER NOT NULL DEFAULT 2, actif INTEGER NOT NULL DEFAULT 1, UNIQUE(jour,debut,fin))")
0953          db.execute("CREATE TABLE IF NOT EXISTS commandes (id TEXT PRIMARY KEY, cree_le TEXT NOT NULL, nom TEXT NOT NULL, telephone TEXT NOT NULL, email TEXT, adresse TEXT NOT NULL, creneau_id INTEGER NOT NULL, panier_json TEXT NOT NULL, total_prevu REAL NOT NULL, montant_encaisse REAL, statut TEXT NOT NULL DEFAULT 'réservée', premiere_commande INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(creneau_id) REFERENCES creneaux(id))")
0954          db.execute("CREATE TABLE IF NOT EXISTS lignes_livrees (commande_id TEXT, produit TEXT, quantite_gardee INTEGER, PRIMARY KEY(commande_id,produit))")
0955  
0956  
0957  def places_disponibles():
0958      with db_conn() as db:
0959          return db.execute("""SELECT c.id,c.jour,c.debut,c.fin,c.capacite, c.actif,
0960          (SELECT COUNT(*) FROM commandes o WHERE o.creneau_id=c.id AND o.statut NOT IN ('annulée','livrée')) AS reservees
0961          FROM creneaux c WHERE c.jour>=? AND c.actif=1 ORDER BY c.jour,c.debut""", (date.today().isoformat(),)).fetchall()
0962  
0963  
0964  def libelle_creneau(c):
0965      return f"{c['jour']} · {c['debut']}–{c['fin']} ({c['capacite']-c['reservees']} place(s))"
0966  
0967  
0968  def reserver_commande(commande):
0969      with db_conn() as db:
0970          db.execute("BEGIN IMMEDIATE")
0971          c = db.execute("""SELECT c.id,c.capacite,c.actif,c.jour,
0972            (SELECT COUNT(*) FROM commandes o WHERE o.creneau_id=c.id AND o.statut NOT IN ('annulée','livrée')) AS reservees
0973            FROM creneaux c WHERE c.id=?""", (commande['creneau_id'],)).fetchone()
0974          if not c or not c['actif'] or c['jour'] < date.today().isoformat() or c['reservees'] >= c['capacite']:
0975              return False, 'Ce créneau vient de devenir indisponible.'
0976          db.execute("""INSERT INTO commandes (id,cree_le,nom,telephone,email,adresse,creneau_id,panier_json,total_prevu,premiere_commande)
0977            VALUES (?,?,?,?,?,?,?,?,?,?)""", (commande['id'],datetime.now().isoformat(timespec='seconds'),commande['nom'],commande['telephone'],commande['email'],commande['adresse'],commande['creneau_id'],json.dumps(commande['panier'],ensure_ascii=False),commande['total'],int(commande['premiere_commande'])))
0978      return True, ''
0979  
0980  
0981  def annuler_reservation(identifiant):
0982      with db_conn() as db:
0983          db.execute("UPDATE commandes SET statut='annulée' WHERE id=? AND statut='réservée'", (identifiant,))
0984  
0985  
0986  def envoyer_email_confirmation(commande, texte_creneau):
0987      # Optionnel : secrets SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
0988      if not commande['email'] or not st.secrets.get('SMTP_HOST',''):
0989          return False
0990      try:
0991          msg = EmailMessage()
0992          msg['Subject'] = 'Votre commande Mes Bons Plans de Sarah — ' + commande['id']
0993          msg['From'] = st.secrets['SMTP_FROM']
0994          msg['To'] = commande['email']
0995          lignes = '\n'.join(f"{p['produit']} x{p['quantite']} : {p['prix']*p['quantite']:.2f} €" for p in commande['panier'])
0996          msg.set_content(f"Bonjour {commande['nom']},\n\nCommande {commande['id']}\nCréneau : {texte_creneau}\n\n{lignes}\n\nTotal prévisionnel : {commande['total']:.2f} €\nAucun paiement à l'avance. Vous pouvez vérifier et refuser des articles à la remise ; vous ne payez que ceux gardés.\nLa livraison et les éventuels frais restent à confirmer par Sarah.\nMerci !")
0997          with smtplib.SMTP(st.secrets['SMTP_HOST'],int(st.secrets.get('SMTP_PORT',587)),timeout=15) as smtp:
0998              smtp.starttls()
0999              smtp.login(st.secrets['SMTP_USER'],st.secrets['SMTP_PASSWORD'])
1000              smtp.send_message(msg)
1001          return True
1002      except Exception:
1003          return False
1004  
1005  
1006  def prix_comparaison(article):
1007      col = trouver_colonne(article, ['Prix comparé','Prix compare','Prix de comparaison','Prix constaté','Prix magasin'])
1008      return convertir_nombre(article.get(col),0) if col else 0
1009  
1010  
1011  def afficher_planning_public():
1012      st.markdown('### 🚚 Planning de livraison')
1013      st.caption('Consultez les disponibilités avant de faire vos achats. Choisissez votre créneau lors de la validation du panier.')
1014      creneaux = [c for c in places_disponibles() if c['reservees'] < c['capacite']]
1015      if not creneaux:
1016          st.info('Les prochains créneaux seront publiés ici prochainement. 🌸')
1017      else:
1018          for c in creneaux[:12]:
1019              st.write('🌸 ' + libelle_creneau(c))
1020  
1021  
1022  def afficher_admin():
1023      with st.expander('🔐 Administration de la boutique', expanded=False):
1024          if not ADMIN_PASSWORD_HASH:
1025              st.warning('Administration désactivée : configurez ADMIN_PASSWORD_SHA256 dans les Secrets Streamlit.')
1026              return
1027          if not st.session_state.get('admin_auth',False):
1028              with st.form('connexion_admin'):
1029                  pwd = st.text_input('Mot de passe administrateur',type='password')
1030                  ok = st.form_submit_button('Se connecter')
1031              if ok:
1032                  digest = hashlib.sha256(pwd.encode()).hexdigest()
1033                  if hmac.compare_digest(digest,ADMIN_PASSWORD_HASH):
1034                      st.session_state.admin_auth=True
1035                      st.rerun()
1036                  else:
1037                      st.error('Mot de passe incorrect.')
1038              return
1039          if st.button('Se déconnecter',key='admin_logout'):
1040              st.session_state.admin_auth=False
1041              st.rerun()
1042          tab1,tab2=st.tabs(['📅 Créneaux','📦 Commandes et clientes'])
1043          with tab1:
1044              with st.form('ajout_creneau'):
1045                  jour=st.date_input('Jour de livraison',min_value=date.today())
1046                  debut=st.time_input('Début',value=datetime.strptime('14:00','%H:%M').time())
1047                  fin=st.time_input('Fin',value=datetime.strptime('16:00','%H:%M').time())
1048                  capacite=st.number_input('Commandes maximum',min_value=1,max_value=100,value=3)
1049                  ajouter=st.form_submit_button('Ajouter ce créneau')
1050              if ajouter:
1051                  if debut>=fin:
1052                      st.error('La fin doit être après le début.')
1053                  else:
1054                      try:
1055                          with db_conn() as db:
1056                              db.execute('INSERT INTO creneaux (jour,debut,fin,capacite) VALUES (?,?,?,?)',(jour.isoformat(),debut.strftime('%H:%M'),fin.strftime('%H:%M'),int(capacite)))
1057                          st.success('Créneau créé.')
1058                          st.rerun()
1059                      except sqlite3.IntegrityError:
1060                          st.warning('Ce créneau existe déjà.')
1061              with db_conn() as db:
1062                  rows=db.execute('SELECT * FROM creneaux WHERE jour>=? ORDER BY jour,debut',(date.today().isoformat(),)).fetchall()
1063              for c in rows:
1064                  a,b,d=st.columns([4,2,2])
1065                  a.write(f"{c['jour']} {c['debut']}–{c['fin']} · max {c['capacite']} · {'ouvert' if c['actif'] else 'fermé'}")
1066                  if b.button('Fermer' if c['actif'] else 'Ouvrir',key=f"toggle_{c['id']}"):
1067                      with db_conn() as db:
1068                          db.execute('UPDATE creneaux SET actif=? WHERE id=?',(0 if c['actif'] else 1,c['id']))
1069                      st.rerun()
1070                  nouvelle_cap=d.number_input('Places',min_value=1,max_value=100,value=c['capacite'],key=f"cap_{c['id']}")
1071                  if nouvelle_cap != c['capacite']:
1072                      with db_conn() as db:
1073                          db.execute('UPDATE creneaux SET capacite=? WHERE id=?',(int(nouvelle_cap),c['id']))
1074                      st.rerun()
1075          with tab2:
1076              with db_conn() as db:
1077                  commandes=db.execute("SELECT o.*,c.jour,c.debut,c.fin FROM commandes o LEFT JOIN creneaux c ON c.id=o.creneau_id ORDER BY o.cree_le DESC LIMIT 200").fetchall()
1078              for c in commandes:
1079                  with st.expander(f"{c['id']} · {c['nom']} · {c['jour']} {c['debut']} · {c['statut']}"):
1080                      st.write(f"Téléphone : {c['telephone']} | E-mail : {c['email'] or 'non fourni'}")
1081                      st.write(f"Adresse : {c['adresse']}")
1082                      st.write(f"Total prévu : {c['total_prevu']:.2f} €")
1083                      lignes=json.loads(c['panier_json'])
1084                      if c['statut']=='réservée':
1085                          with st.form('fin_'+c['id']):
1086                              gardees={}
1087                              for i,p in enumerate(lignes):
1088                                  gardees[i]=st.number_input(p['produit']+' — quantité gardée',min_value=0,max_value=int(p['quantite']),value=int(p['quantite']),key=f"garde_{c['id']}_{i}")
1089                              montant=sum(gardees[i]*p['prix'] for i,p in enumerate(lignes))
1090                              st.write(f"Montant à encaisser pour les articles gardés : **{montant:.2f} €**")
1091                              confirmer=st.form_submit_button('✅ Livraison terminée et montant encaissé')
1092                          if confirmer:
1093                              with db_conn() as db:
1094                                  db.execute("UPDATE commandes SET statut='livrée',montant_encaisse=? WHERE id=? AND statut='réservée'",(montant,c['id']))
1095                                  for i,p in enumerate(lignes):
1096                                      db.execute('INSERT OR REPLACE INTO lignes_livrees VALUES (?,?,?)',(c['id'],p['produit'],gardees[i]))
1097                              st.success('Livraison enregistrée. Les articles refusés doivent être réintégrés manuellement au stock Google Sheets.')
1098                              st.rerun()
1099                          if st.button('Annuler la réservation',key='cancel_'+c['id']):
1100                              annuler_reservation(c['id'])
1101                              st.warning('Réservation annulée. Vérifiez manuellement le stock.')
1102                              st.rerun()
1103                      else:
1104                          st.write(f"Montant encaissé : {c['montant_encaisse'] if c['montant_encaisse'] is not None else '—'}")
1105  
1106  initialiser_db()
1107  
1108  # RENDU DU MENU LATÉRAL GAUCHE
1109   
1110  # ============================================================
1111   
1112  def afficher_sidebar_complete():
1113   
1114      st.sidebar.header(f"🌸 {NOM_BOUTIQUE}")
1115   
1116      st.sidebar.markdown("---")
1117   
1118   
1119   
1120      st.sidebar.subheader("🛒 Mon Espace Achat")
1121   
1122   
1123   
1124      nombre_articles = sum(
1125   
1126          produit["quantite"]
1127   
1128          for produit in st.session_state.panier
1129   
1130      )
1131   
1132   
1133   
1134      with st.sidebar.expander(
1135   
1136          f"💼 Votre Panier ({nombre_articles} articles)",
1137   
1138          expanded=True
1139   
1140      ):
1141   
1142          if not st.session_state.panier:
1143   
1144              st.info("Votre panier est vide 🌸")
1145   
1146   
1147   
1148          else:
1149   
1150              total_articles = 0.0
1151   
1152   
1153   
1154              for index, produit in enumerate(st.session_state.panier):
1155                  sous_total = produit["quantite"] * produit["prix"]
1156                  total_articles += sous_total
1157                  st.markdown(f"**{produit['produit']}**")
1158                  st.caption(f"{produit['prix']:.2f} € / unité · Sous-total : {sous_total:.2f} €")
1159                  col_moins, col_qte, col_plus, col_suppr = st.columns(4)
1160                  with col_moins:
1161                      if st.button("−", key=f"moins_{index}", help="Retirer une unité"):
1162                          diminuer_du_panier(index)
1163                          st.rerun()
1164                  with col_qte:
1165                      st.markdown(f"**{produit['quantite']}**")
1166                  with col_plus:
1167                      if st.button("+", key=f"plus_{index}", help="Ajouter une unité"):
1168                          try:
1169                              df_actuel = charger_produits()
1170                              correspondances = df_actuel[
1171                                  df_actuel.apply(nom_produit, axis=1) == produit["produit"]
1172                              ]
1173                              if not correspondances.empty:
1174                                  ajouter_au_panier(correspondances.iloc[0])
1175                                  st.rerun()
1176                              else:
1177                                  st.warning("Produit introuvable dans le catalogue.")
1178                          except Exception:
1179                              st.warning("Impossible de vérifier le stock actuellement.")
1180                  with col_suppr:
1181                      if st.button("🗑️", key=f"suppr_{index}", help="Supprimer la ligne"):
1182                          supprimer_du_panier(index)
1183                          st.rerun()
1184                  st.divider()
1185   
1186              st.markdown(
1187   
1188                  f"Sous-total articles : "
1189   
1190                  f"**{total_articles:.2f} €**"
1191   
1192              )
1193   
1194   
1195   
1196              total_general = total_articles
1197   
1198              st.markdown(
1199   
1200                  f"### Total : "
1201   
1202                  f"**{total_general:.2f} €**"
1203   
1204              )
1205   
1206   
1207   
1208              st.markdown(
1209   
1210                  "#### 📝 Informations de commande"
1211   
1212              )
1213   
1214   
1215   
1216              nom_client = st.text_input(
1217   
1218                  "Votre Nom et Prénom",
1219   
1220                  key="client_nom"
1221   
1222              )
1223   
1224   
1225   
1226              adresse_livraison = st.text_area(
1227   
1228                  "Adresse (Aigues-Vives ou environs)",
1229   
1230                  key="client_adresse"
1231   
1232              )
1233   
1234   
1235   
1236              telephone_client = st.text_input('Téléphone pour organiser la livraison *', key='client_tel')
1237              email_client = st.text_input('E-mail (pour recevoir votre confirmation)', key='client_email')
1238              disponibles = [c for c in places_disponibles() if c['reservees'] < c['capacite']]
1239              choix = {libelle_creneau(c): c for c in disponibles}
1240              creneau_choisi = st.selectbox('📅 Choisissez votre créneau de livraison *', list(choix), index=None, placeholder='Sélectionnez un créneau') if choix else None
1241              if not choix:
1242                  st.warning('Aucun créneau ouvert pour le moment. Revenez bientôt !')
1243              st.caption('Aucun paiement à l’avance. À la remise, vérifiez les articles et ne payez que ceux que vous gardez.')
1244              premiere_commande = st.checkbox(
1245                  "🎁 C'est ma première commande : je souhaite bénéficier de la livraison offerte",
1246                  key="premiere_commande",
1247                  help="Offre réservée à la première commande, sous réserve de vérification et de zone desservie."
1248              )
1249              st.caption("Les frais de livraison ne sont pas inclus dans le total des articles. Sarah confirmera l'éligibilité et les modalités avant la livraison.")
1250   
1251              if st.session_state.commande_stock_en_erreur:
1252                  st.error("Commande déjà transmise à la boutique, mais problème de stock. Contactez la boutique avant toute nouvelle tentative pour éviter un doublon.")
1253              if st.button(
1254                  "🚀 Valider ma commande",
1255                  use_container_width=True,
1256                  disabled=st.session_state.commande_stock_en_erreur
1257              ):
1258   
1259                  if (
1260   
1261                      nom_client.strip() == ""
1262   
1263                      or adresse_livraison.strip() == ""
1264                      or not telephone_client.strip()
1265                      or not creneau_choisi
1266   
1267                  ):
1268   
1269                      st.error(
1270   
1271                          "Veuillez remplir votre nom et "
1272   
1273                          "votre adresse, votre téléphone et un créneau pour valider."
1274   
1275                      )
1276   
1277   
1278   
1279                  else:
1280   
1281                      # Copie du panier avant toute opération.
1282   
1283                      panier_commande = [
1284   
1285                          produit.copy()
1286   
1287                          for produit
1288   
1289                          in st.session_state.panier
1290   
1291                      ]
1292   
1293   
1294   
1295                      # Revalider les prix depuis la feuille, pas depuis l'URL du panier.
1296                      try:
1297                          catalogue=charger_produits()
1298                          index_catalogue={nom_produit(r):r for _,r in catalogue.iterrows()}
1299                          for p in panier_commande:
1300                              if p['produit'] not in index_catalogue:
1301                                  raise ValueError('Article introuvable : '+p['produit'])
1302                              article=index_catalogue[p['produit']]
1303                              if obtenir_stock(article)<p['quantite']:
1304                                  raise ValueError('Stock insuffisant : '+p['produit'])
1305                              promo=obtenir_prix_promo(article)
1306                              p['prix']=promo if promo is not None else obtenir_prix(article)
1307                          total_general=sum(p['prix']*p['quantite'] for p in panier_commande)
1308                          ref=secrets.token_hex(6).upper()
1309                          commande={'id':ref,'nom':nom_client.strip(),'telephone':telephone_client.strip(),
1310                            'email':email_client.strip(),'adresse':adresse_livraison.strip(),
1311                            'creneau_id':choix[creneau_choisi]['id'],'panier':panier_commande,
1312                            'total':total_general,'premiere_commande':premiere_commande}
1313                          reserve,erreur=reserver_commande(commande)
1314                          if not reserve:
1315                              st.error(erreur)
1316                          else:
1317                              discord_ok,discord_erreur=envoyer_commande_discord(
1318                                commande['nom'],commande['adresse'],panier_commande,total_general,
1319                                total_general,premiere_commande,telephone_client,email_client,
1320                                creneau_choisi,ref)
1321                              if not discord_ok:
1322                                  annuler_reservation(ref)
1323                                  st.error('Réservation annulée : notification boutique impossible. '+discord_erreur)
1324                              else:
1325                                  stock_ok,erreurs_stock=retirer_stock_commande(panier_commande)
1326                                  if not stock_ok:
1327                                      st.session_state.commande_stock_en_erreur=True
1328                                      st.error('Commande '+ref+' transmise à Sarah, mais stock non mis à jour. Ne recommencez pas ; contactez la boutique.')
1329                                      for erreur_stock in erreurs_stock:
1330                                          st.caption(str(erreur_stock))
1331                                  else:
1332                                      email_ok=envoyer_email_confirmation(commande,creneau_choisi)
1333                                      st.session_state.confirmation_commande={
1334                                        'nombre':sum(p['quantite'] for p in panier_commande),
1335                                        'total':total_general,'livraison_demandee':premiere_commande,
1336                                        'reference':ref,'creneau':creneau_choisi,'email_ok':email_ok,
1337                                        'email_demande':bool(email_client.strip())}
1338                                      st.session_state.animation_confirmation=True
1339                                      vider_panier()
1340                                      st.cache_data.clear()
1341                                      st.rerun()
1342                      except Exception as erreur:
1343                          st.error('Impossible de valider la commande : '+str(erreur))
1344      st.sidebar.markdown("---")
1345   
1346   
1347   
1348  # AFFICHAGE DE LA BOUTIQUE ET DU CATALOGUE PRINCIPAL
1349   
1350  # ============================================================
1351   
1352  afficher_sidebar_complete()
1353   
1354  # Confirmation visible après le rechargement de la page.
1355  if st.session_state.confirmation_commande:
1356      recap = st.session_state.confirmation_commande
1357      st.markdown("""
1358      <div style="background:#F2E3E9;border:2px solid #C68CA3;border-radius:22px;
1359      padding:26px;text-align:center;margin:14px 0 24px 0;">
1360        <div style="font-size:42px">🎉 🌸 🎉</div>
1361        <div style="font-size:26px;color:#713C50;font-weight:750">Merci pour votre commande !</div>
1362        <div style="font-size:16px;color:#775365;margin-top:8px">
1363          Votre commande a bien été enregistrée et transmise à la boutique ♡
1364        </div>
1365      </div>
1366      """, unsafe_allow_html=True)
1367      st.success(f"✅ Confirmation : {recap['nombre']} article(s) — Total : {recap['total']:.2f} €")
1368      st.info(f"📅 Créneau réservé : {recap.get('creneau','—')} · Référence : {recap.get('reference','—')}")
1369      if recap.get('email_demande'):
1370          st.info('💌 E-mail de confirmation envoyé.' if recap.get('email_ok') else '💌 Envoi de l’e-mail indisponible. Conservez cette référence de commande.')
1371      if recap.get("livraison_demandee"):
1372          st.info("🎁 Votre demande de livraison offerte a été transmise. Sarah vérifiera votre éligibilité et vous confirmera les modalités.")
1373      st.info("La boutique a reçu votre demande. La disponibilité finale et les modalités de remise seront confirmées par la boutique.")
1374      if st.session_state.animation_confirmation:
1375          st.balloons()
1376          st.session_state.animation_confirmation = False
1377      if st.button("🌸 Fermer la confirmation", key="fermer_confirmation"):
1378          st.session_state.confirmation_commande = None
1379          st.rerun()
1380   
1381   
1382   
1383   
1384   
1385  st.markdown("""
1386  <div style="background:linear-gradient(115deg,#EFD9E1 0%,#FAF0F2 65%,#FFF9F7 100%);border:1px solid #E7CBD6;border-radius:25px;padding:35px 30px;margin-bottom:22px;box-shadow:0 8px 26px rgba(102,55,77,.06)">
1387    <div style="font-size:12px;letter-spacing:2.2px;color:#935D73;font-weight:700">✿ LA BOUTIQUE DES PETITS PRIX ✿</div>
1388    <div style="font-family:Georgia,serif;font-size:clamp(29px,3.5vw,49px);line-height:1.15;color:#66374D;margin:12px 0">Mes Bons Plans de Sarah 🌸</div>
1389    <div style="color:#805468;font-size:17px;margin-bottom:12px">Vos marques préférées à prix doux ♡</div>
1390    <div style="color:#6B5260;font-size:14px">Lessive · Entretien · Hygiène · Promotions</div>
1391  </div>
1392  """, unsafe_allow_html=True)
1393   
1394  st.markdown("""
1395  <div style="background:#EEDBE3;border:1px solid #DFC2CE;border-radius:22px;padding:24px;margin:16px 0;color:#713C50;text-align:center">
1396  <div style="font-size:28px">🎁 🌸</div>
1397  <div style="font-size:24px;font-weight:750">Livraison offerte pour votre première commande !</div>
1398  <div style="font-size:14px;margin-top:8px">Cochez « Première commande » dans votre panier pour demander votre avantage ♡</div>
1399  <div style="font-size:12px;margin-top:8px">Sous réserve de vérification et de zone de livraison desservie. Frais éventuels confirmés avant livraison.</div>
1400  </div>
1401  """, unsafe_allow_html=True)
1402  afficher_planning_public()
1403  afficher_admin()
1404  st.markdown('**🌸 Entreprise indépendante immatriculée en France.** Commandez sans payer à l’avance ; vérifiez les produits à la remise. Retrouvez les informations légales et les conditions de vente dans la rubrique dédiée à compléter avant publication.')
1405  with st.expander("📝 Ma liste de courses ♡ — demander la recherche de produits", expanded=False):
1406      st.write("Vous cherchez un article absent du catalogue ? Envoyez votre liste. Sarah recherchera les produits et vous répondra avec les prix et disponibilités, sans obligation d'achat.")
1407      with st.form("form_liste_courses", clear_on_submit=True):
1408          nom_recherche = st.text_input("Votre prénom et nom", max_chars=100)
1409          contact_recherche = st.text_input("Votre téléphone ou e-mail pour recevoir une réponse", max_chars=150)
1410          liste_recherche = st.text_area("Produits recherchés (marque, format, quantité si possible)", placeholder="Ex. Ariel 40 lavages, shampoing Garnier...", max_chars=1100)
1411          accord_contact = st.checkbox("J'accepte que mes coordonnées soient utilisées pour répondre à ma demande.")
1412          soumettre_recherche = st.form_submit_button("💌 Envoyer ma liste à Sarah", use_container_width=True)
1413      if soumettre_recherche:
1414          if not (nom_recherche.strip() and contact_recherche.strip() and liste_recherche.strip() and accord_contact):
1415              st.warning("Complétez votre nom, un moyen de contact, votre liste et l'autorisation de réponse.")
1416          else:
1417              ok, erreur = envoyer_liste_courses(nom_recherche.strip(), contact_recherche.strip(), liste_recherche.strip())
1418              if ok:
1419                  st.success("🌸 Votre liste a bien été envoyée à Sarah ! Ce n'est pas une commande.")
1420              else:
1421                  st.error("Votre demande n'a pas pu être envoyée : " + erreur)
1422   
1423  try:
1424   
1425      df_produits = charger_produits()
1426   
1427   
1428   
1429      if df_produits.empty:
1430   
1431          st.warning(
1432   
1433              "Aucun produit trouvé dans la base "
1434   
1435              "de données Google Sheets."
1436   
1437          )
1438   
1439   
1440   
1441      else:
1442   
1443          categories_disponibles = (
1444   
1445              ["Tous"]
1446   
1447              + sorted(
1448   
1449                  list(
1450   
1451                      df_produits.apply(
1452   
1453                          categorie_produit,
1454   
1455                          axis=1
1456   
1457                      ).unique()
1458   
1459                  )
1460   
1461              )
1462   
1463          )
1464   
1465   
1466   
1467          st.markdown("### ✨ Explorez nos rayons")
1468          categories_visibles = [c for c in categories_disponibles if c != "Tous"][:5]
1469          if "rayon_actif" not in st.session_state:
1470              st.session_state.rayon_actif = "Tous"
1471          if categories_visibles:
1472              colonnes_rayons = st.columns(len(categories_visibles))
1473              for col, categorie in zip(colonnes_rayons, categories_visibles):
1474                  with col:
1475                      if st.button("♡ " + str(categorie), key="rayon_" + str(categorie), use_container_width=True):
1476                          st.session_state.rayon_actif = categorie
1477                          st.rerun()
1478          st.markdown("### 🛍️ Notre sélection")
1479          # ========================================================
1480          # RECHERCHE PRODUITS
1481          # ========================================================
1482          recherche = st.text_input(
1483              "🔎 Rechercher un produit :",
1484              placeholder="Ex. lessive, Xtra, shampoing..."
1485          )
1486   
1487          categorie_selectionnee = st.selectbox(
1488   
1489              "📁 Filtrer par rayon / catégorie :",
1490   
1491              categories_disponibles,
1492              index=categories_disponibles.index(st.session_state.rayon_actif) if st.session_state.rayon_actif in categories_disponibles else 0
1493   
1494          )
1495          st.session_state.rayon_actif = categorie_selectionnee
1496   
1497   
1498   
1499          if categorie_selectionnee != "Tous":
1500   
1501              df_filtre = df_produits[
1502   
1503                  df_produits.apply(
1504   
1505                      categorie_produit,
1506   
1507                      axis=1
1508   
1509                  )
1510   
1511                  == categorie_selectionnee
1512   
1513              ]
1514   
1515          else:
1516   
1517              df_filtre = df_produits
1518   
1519   
1520   
1521          # Applique la recherche au catalogue déjà filtré par catégorie.
1522          # Recherche dans le nom, la catégorie et le format.
1523          if recherche.strip():
1524              recherche_normalisee = normaliser_texte(recherche)
1525   
1526              df_filtre = df_filtre[
1527                  df_filtre.apply(
1528                      lambda article: (
1529                          recherche_normalisee in normaliser_texte(nom_produit(article))
1530                          or recherche_normalisee in normaliser_texte(categorie_produit(article))
1531                          or recherche_normalisee in normaliser_texte(format_produit(article))
1532                      ),
1533                      axis=1
1534                  )
1535              ]
1536   
1537          if recherche.strip() and df_filtre.empty:
1538              st.info("🔎 Aucun produit ne correspond à votre recherche.")
1539   
1540          st.write(
1541   
1542              f"Catalogue synchronisé en direct : "
1543   
1544              f"{len(df_filtre)} articles disponibles."
1545   
1546          )
1547   
1548   
1549   
1550          st.markdown("---")
1551   
1552   
1553   
1554          colonnes_grille = st.columns(3)
1555   
1556   
1557   
1558          for index, row in (
1559   
1560              df_filtre.reset_index(drop=True).iterrows()
1561   
1562          ):
1563   
1564              colonne_cible = (
1565   
1566                  colonnes_grille[index % 3]
1567   
1568              )
1569   
1570   
1571   
1572              with colonne_cible:
1573                  lien_photo = photo_produit(row)
1574   
1575   
1576   
1577                  if lien_photo:
1578   
1579                      st.image(
1580   
1581                          lien_photo,
1582   
1583                          use_container_width=True
1584   
1585                      )
1586   
1587                  else:
1588   
1589                      st.image(
1590   
1591                          "https://via.placeholder.com/"
1592   
1593                          "150?text=Pas+de+photo",
1594   
1595                          use_container_width=True
1596   
1597                      )
1598   
1599   
1600   
1601                  st.markdown(
1602   
1603                      f"**{nom_produit(row)}**"
1604   
1605                  )
1606   
1607   
1608   
1609                  st.caption(
1610   
1611                      f"Format : {format_produit(row)} "
1612   
1613                      f"| {prix_kg_litre(row)}"
1614   
1615                  )
1616   
1617   
1618   
1619                  prix_init = obtenir_prix(row)
1620   
1621   
1622   
1623                  # Correction de l'erreur
1624   
1625                  # "prix_pr = Petersen = ..."
1626   
1627                  prix_pr = obtenir_prix_promo(row)
1628   
1629   
1630   
1631                  stock_dispo = obtenir_stock(row)
1632   
1633   
1634   
1635                  prix_comp=prix_comparaison(row)
1636                  prix_vente=prix_pr if prix_pr is not None else prix_init
1637                  if prix_comp > prix_vente > 0:
1638                      economie=prix_comp-prix_vente
1639                      pct=100*economie/prix_comp
1640                      st.caption(f"💚 Comparaison indicative : {economie:.2f} € de moins ({pct:.0f} %) qu'un prix constaté de {prix_comp:.2f} € — source et date à vérifier.")
1641                  if prix_pr is not None:
1642   
1643                      st.markdown(
1644   
1645                          f"~~{prix_init:.2f} €~~ "
1646   
1647                          f"🔴 **PROMO : {prix_pr:.2f} €**"
1648   
1649                      )
1650   
1651                  else:
1652   
1653                      st.markdown(
1654   
1655                          f"Prix : **{prix_init:.2f} €**"
1656   
1657                      )
1658   
1659   
1660   
1661                  if stock_dispo <= 0:
1662   
1663                      st.error("🚫 Rupture de stock")
1664   
1665   
1666   
1667                  else:
1668   
1669                      quantite_panier = 0
1670   
1671   
1672   
1673                      for produit_panier in (
1674   
1675                          st.session_state.panier
1676   
1677                      ):
1678   
1679                          if (
1680   
1681                              produit_panier["produit"]
1682   
1683                              == nom_produit(row)
1684   
1685                          ):
1686   
1687                              quantite_panier = (
1688   
1689                                  produit_panier["quantite"]
1690   
1691                              )
1692   
1693                              break
1694   
1695   
1696   
1697                      stock_restant_affichable = max(
1698   
1699                          0,
1700   
1701                          stock_dispo - quantite_panier
1702   
1703                      )
1704   
1705   
1706   
1707                      st.caption(
1708   
1709                          f"Stock disponible : "
1710   
1711                          f"{stock_restant_affichable}"
1712   
1713                      )
1714   
1715   
1716   
1717                      bouton_desactive = (
1718   
1719                          quantite_panier >= stock_dispo
1720   
1721                      )
1722   
1723   
1724   
1725                      if st.button(
1726   
1727                          "➕ Ajouter",
1728   
1729                          key=f"add_{row.name}_{index}",
1730   
1731                          use_container_width=True,
1732   
1733                          disabled=bouton_desactive
1734   
1735                      ):
1736   
1737                          ajouter_au_panier(row)
1738   
1739   
1740   
1741                          st.toast(
1742   
1743                              f"Ajouté : "
1744   
1745                              f"{nom_produit(row)}"
1746   
1747                          )
1748   
1749   
1750   
1751                          st.rerun()
1752   
1753   
1754   
1755                  st.markdown(
1756   
1757                      "<br>",
1758   
1759                      unsafe_allow_html=True
1760   
1761                  )
1762   
1763   
1764   
1765  except Exception as e:
1766   
1767      st.error(
1768   
1769          f"Erreur d'initialisation de la base produit : {e}"
1770   
1771      )
