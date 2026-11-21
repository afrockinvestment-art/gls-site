/**
 * GLS : enregistrer les inscriptions du site dans une Google Sheet.
 *
 * 1. Crée une Google Sheet avec deux onglets : "Masterclass" et "Formation".
 * 2. Menu Extensions > Apps Script, colle ce code, enregistre.
 * 3. Déployer > Nouveau déploiement > Type : Application Web
 *    Exécuter en tant que : moi ; Accès : Tout le monde.
 * 4. Copie l'URL obtenue dans CONFIG.formEndpoint, en haut du script de index.html.
 */
function doPost(e) {
  const data = JSON.parse(e.postData.contents);
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (data.type === 'formation') {
    const sh = ss.getSheetByName('Formation');
    if (sh.getLastRow() === 0) sh.appendRow(['Date', 'Nom', 'WhatsApp', 'E-mail', 'Pays', 'Formule', 'Montant', 'Référence', 'Payé ?']);
    sh.appendRow([data.date, data.nom, data.whatsapp, data.email, data.pays, data.formule, data.montant, data.reference, '']);
  } else {
    const sh = ss.getSheetByName('Masterclass');
    if (sh.getLastRow() === 0) sh.appendRow(['Date', 'Nom', 'WhatsApp', 'E-mail', 'Résidence', 'Niveau', 'Groupe']);
    sh.appendRow([data.date, data.nom, data.whatsapp, data.email, data.residence, data.niveau, data.groupe]);
  }
  return ContentService.createTextOutput('ok');
}
