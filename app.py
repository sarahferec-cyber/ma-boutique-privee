/****************************************************
 * MES BONS PLANS DE SARAH 🌸
 * Gestion du stock Google Sheets
 ****************************************************/

const SHEET_NAME = ""; 
// Laisser vide pour utiliser la première feuille.
// Si tu veux cibler une feuille précise, mets par exemple :
// const SHEET_NAME = "Feuille 1";


/****************************************************
 * GET
 ****************************************************/

function doGet(e) {

  try {

    return reponseJSON({
      success: true,
      message: "API Mes Bons Plans de Sarah 🌸 opérationnelle"
    });

  } catch (erreur) {

    return reponseJSON({
      success: false,
      message: erreur.message
    });
  }
}


/****************************************************
 * POST
 ****************************************************/

function doPost(e) {

  try {

    if (!e || !e.postData || !e.postData.contents) {

      return reponseJSON({
        success: false,
        message: "Aucune donnée reçue."
      });
    }

    const donnees = JSON.parse(
      e.postData.contents
    );

    if (!donnees.action) {

      return reponseJSON({
        success: false,
        message: "Action manquante."
      });
    }


    /************************************************
     * RETIRER UNE COMMANDE
     ************************************************/

    if (donnees.action === "retirer_commande") {

      return traiterCommande(donnees);
    }


    /************************************************
     * ACTION INCONNUE
     ************************************************/

    return reponseJSON({
      success: false,
      message: "Action inconnue : " + donnees.action
    });


  } catch (erreur) {

    return reponseJSON({
      success: false,
      message: "Erreur serveur : " + erreur.message
    });
  }
}


/****************************************************
 * TRAITEMENT DE LA COMMANDE
 ****************************************************/

function traiterCommande(donnees) {

  if (!donnees.produits) {

    return reponseJSON({
      success: false,
      message: "Aucun produit dans la commande."
    });
  }


  if (!Array.isArray(donnees.produits)) {

    return reponseJSON({
      success: false,
      message: "Format des produits incorrect."
    });
  }


  if (donnees.produits.length === 0) {

    return reponseJSON({
      success: false,
      message: "La commande est vide."
    });
  }


  const feuille = obtenirFeuille();

  const donneesFeuille = feuille.getDataRange().getValues();

  if (donneesFeuille.length < 2) {

    return reponseJSON({
      success: false,
      message: "Le Google Sheet ne contient aucun produit."
    });
  }


  /************************************************
   * LECTURE DES EN-TÊTES
   ************************************************/

  const entetes = donneesFeuille[0];

  const colonneProduit = trouverColonne(
    entetes,
    [
      "Denomination",
      "Dénomination",
      "Produit",
      "Nom",
      "Article"
    ]
  );


  const colonneStock = trouverColonne(
    entetes,
    [
      "Quantité",
      "Quantite",
      "Stock",
      "Stocks"
    ]
  );


  if (colonneProduit === -1) {

    return reponseJSON({
      success: false,
      message: "Colonne Denomination introuvable."
    });
  }


  if (colonneStock === -1) {

    return reponseJSON({
      success: false,
      message: "Colonne Quantité introuvable."
    });
  }


  /************************************************
   * PRÉPARATION DE LA COMMANDE
   ************************************************/

  const modifications = [];

  const erreurs = [];


  donnees.produits.forEach(function(produitCommande) {

    const nomProduit = String(
      produitCommande.produit || ""
    ).trim();


    const quantiteDemandee = Number(
      produitCommande.quantite
    );


    if (!nomProduit) {

      erreurs.push(
        "Un produit n'a pas de nom."
      );

      return;
    }


    if (
      !Number.isFinite(quantiteDemandee) ||
      quantiteDemandee <= 0
    ) {

      erreurs.push(
        "Quantité incorrecte pour : " +
        nomProduit
      );

      return;
    }


    /**********************************************
     * RECHERCHE DU PRODUIT
     **********************************************/

    let ligneTrouvee = -1;


    for (
      let ligne = 1;
      ligne < donneesFeuille.length;
      ligne++
    ) {

      const nomDansSheet = String(
        donneesFeuille[ligne][colonneProduit]
        || ""
      ).trim();


      if (
        normaliserTexte(nomDansSheet)
        === normaliserTexte(nomProduit)
      ) {

        ligneTrouvee = ligne;
        break;
      }
    }


    if (ligneTrouvee === -1) {

      erreurs.push(
        "Produit introuvable : " +
        nomProduit
      );

      return;
    }


    /**********************************************
     * STOCK ACTUEL
     **********************************************/

    const stockActuel = convertirNombre(
      donneesFeuille[ligneTrouvee][colonneStock]
    );


    if (stockActuel < quantiteDemandee) {

      erreurs.push(
        "Stock insuffisant pour " +
        nomProduit +
        " (stock : " +
        stockActuel +
        ", demandé : " +
        quantiteDemandee +
        ")"
      );

      return;
    }


    /**********************************************
     * NOUVEAU STOCK
     **********************************************/

    const nouveauStock =
      stockActuel - quantiteDemandee;


    modifications.push({

      ligne: ligneTrouvee + 1,

      nom: nomProduit,

      ancienStock: stockActuel,

      quantite: quantiteDemandee,

      nouveauStock: nouveauStock

    });

  });


  /************************************************
   * S'IL Y A UNE ERREUR :
   * ON NE MODIFIE RIEN
   ************************************************/

  if (erreurs.length > 0) {

    return reponseJSON({

      success: false,

      message: erreurs.join("\n"),

      erreurs: erreurs

    });
  }


  /************************************************
   * MISE À JOUR DU STOCK
   ************************************************/

  modifications.forEach(function(modification) {

    feuille
      .getRange(
        modification.ligne,
        colonneStock + 1
      )
      .setValue(
        modification.nouveauStock
      );

  });


  /************************************************
   * ENREGISTREMENT
   ************************************************/

  SpreadsheetApp.flush();


  /************************************************
   * RÉPONSE
   ************************************************/

  return reponseJSON({

    success: true,

    message: "Commande validée avec succès.",

    utilisateur:
      donnees.utilisateur || "",

    produits:
      modifications.map(function(modification) {

        return {

          produit: modification.nom,

          quantite:
            modification.quantite,

          ancien_stock:
            modification.ancienStock,

          nouveau_stock:
            modification.nouveauStock

        };

      })

  });
}


/****************************************************
 * OBTENIR LA FEUILLE
 ****************************************************/

function obtenirFeuille() {

  const classeur =
    SpreadsheetApp.getActiveSpreadsheet();


  if (SHEET_NAME) {

    const feuille =
      classeur.getSheetByName(SHEET_NAME);


    if (!feuille) {

      throw new Error(
        "La feuille '" +
        SHEET_NAME +
        "' est introuvable."
      );
    }


    return feuille;
  }


  return classeur.getSheets()[0];
}


/****************************************************
 * TROUVER UNE COLONNE
 ****************************************************/

function trouverColonne(
  entetes,
  nomsPossibles
) {

  const entetesNormalises =
    entetes.map(function(entete) {

      return normaliserTexte(entete);

    });


  for (
    let i = 0;
    i < nomsPossibles.length;
    i++
  ) {

    const recherche =
      normaliserTexte(
        nomsPossibles[i]
      );


    const index =
      entetesNormalises.indexOf(
        recherche
      );


    if (index !== -1) {

      return index;
    }
  }


  return -1;
}


/****************************************************
 * NORMALISER UN TEXTE
 ****************************************************/

function normaliserTexte(texte) {

  return String(texte || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}


/****************************************************
 * CONVERTIR EN NOMBRE
 ****************************************************/

function convertirNombre(valeur) {

  if (
    valeur === null ||
    valeur === undefined ||
    valeur === ""
  ) {

    return 0;
  }


  if (typeof valeur === "number") {

    return valeur;
  }


  let texte =
    String(valeur)
      .trim()
      .replace("€", "")
      .replace(/\s/g, "");


  /*
   * Gestion des nombres français :
   *
   * 10,50
   * 1 250,50
   * 1250.50
   */

  if (
    texte.indexOf(",") !== -1 &&
    texte.indexOf(".") !== -1
  ) {

    if (
      texte.lastIndexOf(",") >
      texte.lastIndexOf(".")
    ) {

      texte = texte
        .replace(/\./g, "")
        .replace(",", ".");

    } else {

      texte = texte
        .replace(/,/g, "");
    }

  } else {

    texte = texte.replace(",", ".");
  }


  const nombre =
    Number(texte);


  if (
    !Number.isFinite(nombre)
  ) {

    return 0;
  }


  return nombre;
}


/****************************************************
 * RÉPONSE JSON
 ****************************************************/

function reponseJSON(objet) {

  return ContentService
    .createTextOutput(
      JSON.stringify(objet)
    )
    .setMimeType(
      ContentService.MimeType.JSON
    );
}