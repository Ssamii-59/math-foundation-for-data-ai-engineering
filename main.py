import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import markdown
import requests
from prompt_template import SYSTEM_PROMPT

def get_current_step():
    with open("state.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("current_step", 1)

def update_step(next_step):
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump({"current_step": next_step}, f, indent=2)

def generate_lesson(step):
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"   
    user_prompt = f"Génère la leçon correspondant à l'Étape {step} du programme. Reste strictement dans le format 60 minutes défini."
   
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }
   
    response = requests.post(url, json=payload, timeout=90)
    response.raise_for_status()
    res_json = response.json()
    return res_json["candidates"][0]["content"]["parts"][0]["text"]


def send_email(subject, markdown_content):
    sender = os.environ["SENDER_EMAIL"]
    password = os.environ["SENDER_PASSWORD"]
    raw_receivers = os.environ["RECEIVER_EMAIL"]
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    # Découpage en liste propre pour l'envoi technique
    receivers_list = [r.strip() for r in raw_receivers.split(",") if r.strip()]

    html_body = markdown.markdown(markdown_content, extensions=["extra", "sane_lists"])
   
    styled_html = f"""
    <html>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #24292e; max-width: 680px; margin: auto; padding: 25px;">
        <div style="background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
          <h2 style="color: #0969da; margin-top: 0;">Maths & IA — Entraînement 60 min</h2>
          <p style="margin: 0; color: #57606a;">Préparation concours & admissions sur titre (INSA / UT / Polytech)</p>
        </div>
        <div>
          {html_body}
        </div>
        <hr style="border: none; border-top: 1px solid #d0d7de; margin: 30px 0;" />
        <p style="font-size: 12px; color: #6e7781; text-align: center;">Session programmée en GitHub Actions — BUT SD 3</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(receivers_list)
    msg.attach(MIMEText(styled_html, "html", "utf-8"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        # On passe la liste Python directement à sendmail
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