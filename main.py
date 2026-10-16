import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import markdown
import requests
from prompt_template import SYSTEM_PROMPT
import re

def get_current_step():
    with open("state.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("current_step", 1)

def update_step(next_step):
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump({"current_step": next_step}, f, indent=2)

def generate_lesson(step):
    api_key = os.environ["GROQ_API_KEY"].strip()
    model = os.environ.get("GROQ_MODEL", "").strip() or "openai/gpt-oss-20b"
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    user_prompt = f"Génère la leçon correspondant à l'Étape {step} du programme. Reste strictement dans le format 60 minutes défini."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.4
    }

    response = requests.post(url, headers=headers, json=payload, timeout=90)
    if not response.ok:
        raise RuntimeError(f"Erreur API Groq ({response.status_code}): {response.text}")
    res_json = response.json()
    return res_json["choices"][0]["message"]["content"]


def style_html_content(html: str) -> str:
    # 1. Titres H2 sobres avec barre latérale ambrée chaleureuse
    html = re.sub(
        r'<h2>(.*?)</h2>',
        r'<h2 style="font-size: 19px; font-weight: 700; color: #1e293b; border-left: 3px solid #d97706; background-color: #fffbeb; padding: 8px 14px; border-radius: 4px; margin: 28px 0 14px 0;">\1</h2>',
        html
    )

    # 2. Titres H3 discrets
    html = re.sub(
        r'<h3>(.*?)</h3>',
        r'<h3 style="font-size: 16px; font-weight: 700; color: #0f766e; margin: 20px 0 10px 0;">\1</h3>',
        html
    )

    # 3. Paragraphes bien aérés
    html = re.sub(
        r'<p>(.*?)</p>',
        r'<p style="font-size: 15.5px; line-height: 1.75; color: #334155; margin: 0 0 14px 0;">\1</p>',
        html,
        flags=re.DOTALL
    )

    # 4. Encarts de formules / citations (style Notion)
    html = re.sub(
        r'<blockquote>\s*<p>(.*?)</p>\s*</blockquote>',
        r'<blockquote style="background-color: #f8fafc; border-left: 3px solid #64748b; padding: 12px 18px; margin: 18px 0; border-radius: 4px; color: #0f172a; font-size: 15px; border: 1px solid #e2e8f0; border-left-width: 3px;"><p style="margin: 0; line-height: 1.6;">\1</p></blockquote>',
        html,
        flags=re.DOTALL
    )

    # 5. Liens cliquables bien visibles pour les ressources
    html = re.sub(
        r'<a (href="[^"]*")>(.*?)</a>',
        r'<a \1 style="color: #2563eb; text-decoration: underline; font-weight: 500;">\2 ↗</a>',
        html
    )

    # 6. Listes à puces et numérotées
    html = re.sub(
        r'<ol>(.*?)</ol>',
        r'<ol style="font-size: 15.5px; line-height: 1.75; color: #334155; margin: 0 0 16px 0; padding-left: 22px;">\1</ol>',
        html,
        flags=re.DOTALL
    )
    html = re.sub(
        r'<ul>(.*?)</ul>',
        r'<ul style="font-size: 15.5px; line-height: 1.75; color: #334155; margin: 0 0 16px 0; padding-left: 22px;">\1</ul>',
        html,
        flags=re.DOTALL
    )
    html = re.sub(
        r'<li>(.*?)</li>',
        r'<li style="margin-bottom: 6px;">\1</li>',
        html,
        flags=re.DOTALL
    )

    # 7. Séparateurs horizontaux
    html = re.sub(
        r'<hr\s*/?>',
        r'<div style="text-align: center; margin: 34px 0;"><hr style="border: none; border-top: 1px solid #e2e8f0; margin: 0;" /></div>',
        html
    )

    # 8. Mots en gras
    html = re.sub(
        r'<strong>(.*?)</strong>',
        r'<strong style="color: #0f172a; font-weight: 600;">\1</strong>',
        html,
        flags=re.DOTALL
    )

    return html


def send_email(subject, markdown_content):
    sender = os.environ["SENDER_EMAIL"]
    password = os.environ["SENDER_PASSWORD"]
    raw_receivers = os.environ["RECEIVER_EMAIL"]
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    receivers_list = [r.strip() for r in raw_receivers.split(",") if r.strip()]

    # Transformation Markdown vers HTML puis application du style sobre
    raw_html = markdown.markdown(markdown_content, extensions=["extra", "sane_lists"])
    styled_content = style_html_content(raw_html)

    styled_html = f"""<!DOCTYPE html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
  </head>
  <body style="margin: 0; padding: 24px 12px; background-color: #fafaf9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1c1917; -webkit-font-smoothing: antialiased;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #fafaf9; margin: 0; padding: 0;">
      <tr>
        <td align="center">
          <div style="max-width: 660px; width: 100%; margin: 0 auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #e7e5e4; padding: 32px 32px; text-align: left; box-sizing: border-box;">
            
            <!-- EN-TÊTE ÉPURÉ & CHALEUREUX -->
            <div style="border-bottom: 2px solid #f5f5f4; padding-bottom: 18px; margin-bottom: 26px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 8px;">
                <tr>
                  <td align="left">
                    <span style="font-size: 12px; font-weight: 700; color: #b45309; text-transform: uppercase; letter-spacing: 0.8px;">
                      Session d'entraînement • BUT SD 3
                    </span>
                  </td>
                  <td align="right">
                    <span style="font-size: 11px; background-color: #f3f4f6; color: #4b5563; font-weight: 600; padding: 3px 8px; border-radius: 4px;">
                      ⏱ 60 min
                    </span>
                  </td>
                </tr>
              </table>
              <h1 style="color: #0f172a; font-size: 21px; font-weight: 700; margin: 6px 0 4px 0; line-height: 1.35;">
                {subject}
              </h1>
              <p style="color: #78716c; font-size: 13.5px; margin: 0;">
                Objectif admissions sur titre : INSA • UT • Polytech
              </p>
            </div>

            <!-- CONTENU DE LA SÉANCE -->
            <div>
              {styled_content}
            </div>

            <!-- PIED DE PAGE DISCRET -->
            <div style="margin-top: 36px; padding-top: 18px; border-top: 1px solid #f5f5f4; text-align: center;">
              <p style="font-size: 12.5px; color: #a8a29e; margin: 0;">
                Math Foundations for AI Engineering — Routine de travail programmée
              </p>
            </div>

          </div>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(receivers_list)

    msg.attach(MIMEText(markdown_content, "plain", "utf-8"))
    msg.attach(MIMEText(styled_html, "html", "utf-8"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receivers_list, msg.as_string())


def main():
    step = get_current_step()
    if step > 21:
        print("Programme terminé (étape 21 atteinte). Aucun envoi.")
        return

    print(f"Génération de l'étape {step}/21...")
    content = generate_lesson(step)
    subject = f"Leçon Maths & IA #{step:02d} — Objectif Écoles d'Ingénieurs"
   
    print("Envoi de l'e-mail...")
    send_email(subject, content)
   
    update_step(step + 1)
    print(f"Succès. Prochaine étape : {step + 1}")

if __name__ == "__main__":
    main()