// Déclenchée automatiquement par Netlify à chaque inscription reçue par le formulaire « inscriptions ».
// 1. Ajoute ou met à jour le contact dans Brevo (liste des inscrits, et liste du point marché s'il a accepté).
// 2. Envoie le mail de bienvenue.
// Variables à définir dans Netlify (Site configuration > Environment variables) :
//   BREVO_API_KEY, BREVO_LIST_INSCRITS, BREVO_LIST_POINT_MARCHE, SENDER_EMAIL, SENDER_NAME
//   GROUPE_WHATSAPP (facultatif), SITE_URL (facultatif)

const API = "https://api.brevo.com/v3";

async function brevo(path, body, key) {
  const r = await fetch(API + path, {
    method: "POST",
    headers: { "api-key": key, "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  return { ok: r.ok, status: r.status, text };
}

function esc(s) {
  return String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function welcome(d, env) {
  const prenom = esc((d.prenom || (d.nom || "").split(" ")[0] || "").trim()) || "et bienvenue";
  const site = env.SITE_URL || "";
  const groupe = env.GROUPE_WHATSAPP || "";
  let sujet, corps;
  if (d.type === "masterclass") {
    const diaspora = (d.groupe || "").toLowerCase().includes("diaspora");
    const date = diaspora ? "dimanche 6 décembre 2026 à 20 h GMT, en ligne sur Zoom" : "dimanche 29 novembre 2026 à 20 h GMT";
    sujet = "Ta place à la masterclass gratuite est réservée";
    corps = `
      <p>Merci pour ton inscription à la <b>masterclass gratuite « Investir à la BRVM avec méthode »</b>.</p>
      <p><b>Ta session :</b> ${date}.</p>
      <p>Le lien de connexion et les derniers détails te seront envoyés sur WhatsApp et par e-mail avant la session.</p>
      ${groupe ? `<p><a href="${groupe}" style="display:inline-block;background:#BE581C;color:#fff;padding:12px 20px;border-radius:24px;text-decoration:none;font-weight:bold">Rejoindre le groupe WhatsApp</a></p>` : ""}
      <p>D'ici là, une seule question à garder en tête : <i>combien suis-je prêt à perdre ?</i> C'est par là que commence un investissement réfléchi.</p>`;
  } else {
    sujet = "Ton inscription à la formation BRVM du 12 décembre";
    corps = `
      <p>Merci pour ton inscription à la <b>formation complète BRVM du samedi 12 décembre 2026</b>.</p>
      ${d.reference ? `<p><b>Ta référence :</b> ${esc(d.reference)}</p>` : ""}
      <p>Ta place est confirmée dès la vérification de ton paiement. Si ce n'est pas déjà fait, envoie la capture de ton dépôt sur WhatsApp au +226 65 57 62 13.</p>
      <p>Les horaires, le lieu pour le présentiel et le lien de connexion te seront envoyés avant la formation.</p>`;
  }
  const pointMarche = d.newsletter === "oui"
    ? `<p>Tu recevras aussi <b>le point marché d'AFROCK Investment</b> : l'essentiel de la BRVM et les titres à surveiller, décryptés simplement.</p>`
    : "";
  const html = `<!doctype html><html><body style="margin:0;background:#F3F5F8;font-family:Georgia,'Times New Roman',serif;color:#0B1730">
  <table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px">
  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-radius:12px;overflow:hidden">
    <tr><td style="background:#0B142E;padding:28px 32px;color:#fff">
      <div style="font-size:13px;letter-spacing:2px;color:#E0782F">GLS FINANCE × AFROCK INVESTMENT</div>
      <div style="font-size:26px;font-weight:bold;margin-top:8px">Bonjour ${prenom},</div>
    </td></tr>
    <tr><td style="padding:28px 32px;font-size:16px;line-height:1.6">
      ${corps}
      ${pointMarche}
      <p>À très vite,<br><b>Géraud Ludovic SANDWIDI</b><br>Analyste quantitatif · Investment Officer, AFROCK Investment</p>
      ${site ? `<p><a href="${site}" style="color:#BE581C">${site}</a></p>` : ""}
    </td></tr>
    <tr><td style="background:#F3F5F8;padding:16px 32px;font-size:12px;color:#5A6680;line-height:1.5">
      Contenu éducatif. Investir comporte un risque de perte en capital ; les performances passées ne préjugent pas des performances futures.
      Tu reçois ce message parce que tu t'es inscrit sur le site GLS.
    </td></tr>
  </table></td></tr></table></body></html>`;
  return { sujet, html };
}

exports.handler = async (event) => {
  const env = process.env;
  let data = {};
  try { data = JSON.parse(event.body).payload.data || {}; } catch (e) { return { statusCode: 200, body: "ignoré" }; }
  if (!data.email || !env.BREVO_API_KEY) return { statusCode: 200, body: "pas d'e-mail ou pas de clé Brevo" };

  const listIds = [parseInt(env.BREVO_LIST_INSCRITS, 10)];
  if (data.newsletter === "oui" && env.BREVO_LIST_POINT_MARCHE) listIds.push(parseInt(env.BREVO_LIST_POINT_MARCHE, 10));
  const nomComplet = (data.nom || "").trim();
  const contact = {
    email: data.email.trim(),
    updateEnabled: true,
    listIds: listIds.filter((n) => !isNaN(n)),
    attributes: {
      FIRSTNAME: data.prenom || nomComplet.split(" ")[0] || "",
      LASTNAME: data.prenom ? nomComplet : nomComplet.split(" ").slice(1).join(" "),
      WHATSAPP: (data.whatsapp || "").replace(/[^\d+]/g, "").replace(/^00/, "+"),
      EVENEMENTS: data.type === "masterclass" ? `Masterclass ${data.groupe || ""}`.trim() : "Formation 12 décembre",
      PAYS: data.pays || data.residence || "",
    },
  };
  let r = await brevo("/contacts", contact, env.BREVO_API_KEY);
  if (!r.ok && r.status === 400) {             // numéro refusé par le champ WHATSAPP de Brevo : on réessaie sans lui
    const { WHATSAPP, ...rest } = contact.attributes; contact.attributes = rest;
    r = await brevo("/contacts", contact, env.BREVO_API_KEY);
  }
  if (!r.ok && r.status === 400) {             // attributs personnalisés absents : attributs de base seulement
    contact.attributes = { FIRSTNAME: contact.attributes.FIRSTNAME, LASTNAME: contact.attributes.LASTNAME };
    r = await brevo("/contacts", contact, env.BREVO_API_KEY);
  }
  console.log("contact", r.status, r.text.slice(0, 200));

  const { sujet, html } = welcome(data, env);
  const m = await brevo("/smtp/email", {
    sender: { email: env.SENDER_EMAIL, name: env.SENDER_NAME || "GLS Finance" },
    to: [{ email: contact.email, name: nomComplet || contact.email }],
    subject: sujet,
    htmlContent: html,
  }, env.BREVO_API_KEY);
  console.log("bienvenue", m.status, m.text.slice(0, 200));
  return { statusCode: 200, body: "ok" };
};
