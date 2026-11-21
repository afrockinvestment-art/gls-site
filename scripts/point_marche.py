"""Envoie « Le point marché AFROCK Investment » aux abonnés Brevo (liste du point marché).

Contenu : indices BRVM, plus fortes hausses et baisses connues, la lecture d'AFROCK (champ « commentaire » de
data/marche.json) et, si AFROCK Investment l'a rempli, la rubrique « Titres à surveiller » de data/opportunites.json.
Rien n'est inventé : une rubrique sans données n'est pas affichée.

Variables d'environnement : BREVO_API_KEY, BREVO_LIST_POINT_MARCHE, SENDER_EMAIL, SENDER_NAME, SITE_URL (facultatif)
Option : --test adresse@exemple.com  envoie seulement un e-mail de test à cette adresse.
"""
import json, os, sys, html, datetime, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.brevo.com/v3"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"api-key": os.environ["BREVO_API_KEY"], "content-type": "application/json", "accept": "application/json"})
    with urllib.request.urlopen(req) as r:
        t = r.read().decode(); return json.loads(t) if t else {}


def fr(v, d=2): return f"{v:,.{d}f}".replace(",", " ").replace(".", ",")


def build():
    m = json.load(open(os.path.join(ROOT, "data", "marche.json"), encoding="utf-8"))
    o = json.load(open(os.path.join(ROOT, "data", "opportunites.json"), encoding="utf-8"))
    e = html.escape
    def col(v): return "#1E9E5A" if (v or 0) > 0 else "#D64545" if (v or 0) < 0 else "#5A6680"
    rows = "".join(f"<tr><td style='padding:8px 0;border-bottom:1px solid #E3E7EE'>{e(i['n'])}</td>"
                   f"<td align='right' style='padding:8px 0;border-bottom:1px solid #E3E7EE'><b>{fr(i['c'])}</b></td>"
                   f"<td align='right' style='padding:8px 0 8px 12px;border-bottom:1px solid #E3E7EE;color:{col(i.get('v'))}'>"
                   f"{(fr(i['v']) + ' %') if i.get('v') is not None else ''}</td></tr>" for i in m["indices"])
    known = [a for a in m["actions"] if a.get("v") is not None]
    up = sorted([a for a in known if a["v"] > 0], key=lambda a: -a["v"])[:3]
    dn = sorted([a for a in known if a["v"] < 0], key=lambda a: a["v"])[:3]
    def lst(items):
        return "".join(f"<li><b>{e(a['s'])}</b> {e(a['n'])} : {fr(a['c'], 0)} F ({fr(a['v'])} %)</li>" for a in items)
    movers = ""
    if up or dn:
        movers = "<h3 style='margin:24px 0 8px'>Les mouvements de la séance</h3>"
        if up: movers += f"<p style='margin:4px 0;color:#1E9E5A'><b>En hausse</b></p><ul style='margin:0 0 8px 18px;padding:0'>{lst(up)}</ul>"
        if dn: movers += f"<p style='margin:4px 0;color:#D64545'><b>En baisse</b></p><ul style='margin:0 0 8px 18px;padding:0'>{lst(dn)}</ul>"
    lecture = f"<h3 style='margin:24px 0 8px'>La lecture d'AFROCK Investment</h3><p>{e(m['commentaire'])}</p>" if m.get("commentaire") else ""
    opp = ""
    if o.get("a_surveiller"):
        items = "".join(f"<li style='margin-bottom:8px'><b>{e(x.get('titre', ''))}</b> : {e(x.get('texte', ''))}</li>" for x in o["a_surveiller"])
        opp = (f"<h3 style='margin:24px 0 8px'>{e(o.get('titre_semaine') or 'Titres à surveiller')}</h3><ul style='margin:0 0 8px 18px;padding:0'>{items}</ul>"
               "<p style='font-size:13px;color:#5A6680'>Ces titres sont présentés à titre pédagogique. Ce n'est pas une recommandation d'achat ou de vente.</p>")
    site = os.environ.get("SITE_URL", "")
    seance = m.get("seance", "")
    try: seance = datetime.date.fromisoformat(seance[:10]).strftime("%d/%m/%Y")
    except ValueError: pass
    body = f"""<!doctype html><html><body style="margin:0;background:#F3F5F8;font-family:Georgia,'Times New Roman',serif;color:#0B1730">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#0B142E;padding:28px 32px;color:#fff">
<div style="font-size:13px;letter-spacing:2px;color:#E0782F">AFROCK INVESTMENT × GLS FINANCE</div>
<div style="font-size:28px;font-weight:bold;margin-top:8px">Le point marché</div>
<div style="font-size:15px;color:#C9D2E3;margin-top:4px">BRVM · séance du {e(seance)}</div></td></tr>
<tr><td style="padding:24px 32px;font-size:16px;line-height:1.6">
<h3 style="margin:0 0 8px">Les indices</h3><table width="100%" cellpadding="0" cellspacing="0" style="font-size:15px">{rows}</table>
{movers}{lecture}{opp}
{f'<p style="margin-top:24px"><a href="{site}" style="display:inline-block;background:#BE581C;color:#fff;padding:12px 20px;border-radius:24px;text-decoration:none;font-weight:bold">Voir la cote complète</a></p>' if site else ''}
</td></tr>
<tr><td style="background:#F3F5F8;padding:16px 32px;font-size:12px;color:#5A6680;line-height:1.5">
Source des cours : {e(m.get('source', 'BRVM'))}. Contenu éducatif, sans conseil en investissement personnalisé. Investir comporte un risque de perte en capital.
<br><a href="{{{{ unsubscribe }}}}" style="color:#5A6680">Se désinscrire</a></td></tr></table></td></tr></table></body></html>"""
    return f"Le point marché BRVM · {seance}", body


def main():
    sujet, body = build()
    if "--test" in sys.argv:
        to = sys.argv[sys.argv.index("--test") + 1]
        call("POST", "/smtp/email", {"sender": {"email": os.environ["SENDER_EMAIL"], "name": os.environ.get("SENDER_NAME", "AFROCK Investment")},
                                     "to": [{"email": to}], "subject": "[TEST] " + sujet, "htmlContent": body.replace("{{ unsubscribe }}", "#")})
        print("test envoyé à", to); return
    c = call("POST", "/emailCampaigns", {"name": f"Point marché {datetime.date.today().isoformat()}", "subject": sujet,
                                         "sender": {"email": os.environ["SENDER_EMAIL"], "name": os.environ.get("SENDER_NAME", "AFROCK Investment")},
                                         "htmlContent": body, "recipients": {"listIds": [int(os.environ["BREVO_LIST_POINT_MARCHE"])]}})
    call("POST", f"/emailCampaigns/{c['id']}/sendNow")
    print("campagne envoyée", c["id"])


if __name__ == "__main__":
    main()
