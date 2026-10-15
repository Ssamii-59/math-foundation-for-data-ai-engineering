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


import re

def clean_math_formatting(text: str) -> str:
    # 1. Déballer les commandes de style de police imbriquées
    for _ in range(4):
        text = re.sub(r'\\(?:mathbf|boldsymbol|vec|mathit|text|mathrm|bm|mathcal)\{([^{}]+)\}', r'\1', text)

    # 2. Fractions : \frac{a}{b} -> (a / b)
    for _ in range(4):
        text = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'(\1 / \2)', text)

    # 3. Racines carrées : \sqrt{...} -> √( ... )
    for _ in range(4):
        text = re.sub(r'\\sqrt\{([^{}]+)\}', r'√(\1)', text)
    text = re.sub(r'\\sqrt([a-zA-Z0-9])', r'√\1', text)

    # 4. Ensembles mathématiques usuels
    text = re.sub(r'\\mathbb\{R\}', 'ℝ', text)
    text = re.sub(r'\\mathbb\{N\}', 'ℕ', text)
    text = re.sub(r'\\mathbb\{Z\}', 'ℤ', text)
    text = re.sub(r'\\mathbb\{C\}', 'ℂ', text)

    # 5. Délimiteurs et crochets
    text = re.sub(r'\\langle\s*', '⟨', text)
    text = re.sub(r'\s*\\rangle', '⟩', text)
    text = re.sub(r'\\left\(', '(', text)
    text = re.sub(r'\\right\)', ')', text)
    text = re.sub(r'\\left\[', '[', text)
    text = re.sub(r'\\right\]', ']', text)
    text = re.sub(r'\\left\\\|', '‖', text)
    text = re.sub(r'\\right\\\|', '‖', text)
    text = re.sub(r'\\left\|', '|', text)
    text = re.sub(r'\\right\|', '|', text)
    text = re.sub(r'\\\|', '‖', text)

    # 6. Lettres grecques
    greek = {
        r'\\alpha\b': 'α', r'\\beta\b': 'β', r'\\gamma\b': 'γ', r'\\delta\b': 'δ',
        r'\\epsilon\b': 'ε', r'\\theta\b': 'θ', r'\\lambda\b': 'λ', r'\\mu\b': 'μ',
        r'\\sigma\b': 'σ', r'\\pi\b': 'π', r'\\omega\b': 'ω', r'\\phi\b': 'φ',
        r'\\eta\b': 'η', r'\\rho\b': 'ρ',
        r'\\Delta\b': 'Δ', r'\\Sigma\b': 'Σ', r'\\Omega\b': 'Ω'
    }
    for k, v in greek.items():
        text = re.sub(k, v, text)

    # 7. Opérateurs et relations
    ops = {
        r'\\times\b': '×', r'\\cdot\b': '·', r'\\nabla\b': '∇', r'\\partial\b': '∂',
        r'\\sum\b': '∑', r'\\prod\b': '∏', r'\\int\b': '∫', r'\\infty\b': '∞',
        r'\\in\b': '∈', r'\\notin\b': '∉', r'\\subset\b': '⊂', r'\\cup\b': '∪', r'\\cap\b': '∩',
        r'\\leq\b': '≤', r'\\le\b': '≤', r'\\geq\b': '≥', r'\\ge\b': '≥',
        r'\\neq\b': '≠', r'\\approx\b': '≈', r'\\to\b': '→', r'\\implies\b': '⇒', r'\\iff\b': '⇔',
        r'\\pm\b': '±', r'\\forall\b': '∀', r'\\exists\b': '∃'
    }
    for k, v in ops.items():
        text = re.sub(k, v, text)

    # 8. Exposants et transposée
    text = re.sub(r'\^\{\s*[tT]\s*\}|\^[tT]', 'ᵀ', text)
    text = re.sub(r'\^\{\s*2\s*\}|\^2', '²', text)
    text = re.sub(r'\^\{\s*3\s*\}|\^3', '³', text)
    text = re.sub(r'\^\{\s*n\s*\}|\^n', 'ⁿ', text)
    text = re.sub(r'\^\{\s*k\s*\}|\^k', 'ᵏ', text)
    text = re.sub(r'\^\{\s*(-?[0-9a-zA-Z]+)\s*\}', r'^\1', text)

    # 9. Indices
    sub_map = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉', 'i': 'ᵢ', 'j': 'ⱼ', 'k': 'ₖ', 'n': 'ₙ', 'm': 'ₘ', 'p': 'ₚ'}
    for num, sub in sub_map.items():
        text = re.sub(r'_\{' + num + r'\}|_' + num, sub, text)

    # 10. Nettoyage des délimiteurs LaTeX math ($$, $, \(, \))
    text = re.sub(r'\$\$', '', text)
    text = re.sub(r'\\\(|\\\)', '', text)
    text = re.sub(r'\$([^\$]+)\$', r'\1', text)

    # 11. Conversion des normes à doubles barres et simples barres d'égalité
    text = re.sub(r'\|{2}', '‖', text)
    text = re.sub(r'(^|[( \t])\|([a-zA-Z0-9_]+)\|\s*=\s*', r'\1‖\2‖ = ', text)

    # 12. Retrait des parenthèses superflues entourant une formule (ex: (‖x‖ = ...))
    text = re.sub(r'\(\s*(‖[^‖\n]+‖\s*=[^)\n]+)\)', r'\1', text)
    text = re.sub(r'‖\s*=\s*', r'‖ = ', text)

    # Espaces superflus et ponctuation
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'⟨ ', '⟨', text)
    text = re.sub(r' ⟩', '⟩', text)

    return text


def style_html_content(html: str) -> str:
    # 1. Protéger les blocs de code <pre> avant d'appliquer les styles sur le texte et le code inline
    pre_blocks = []
    def save_pre(m):
        pre_blocks.append(m.group(0))
        return f"<!--PRE_BLOCK_{len(pre_blocks)-1}-->"

    html = re.sub(r'<pre>.*?</pre>', save_pre, html, flags=re.DOTALL)

    # 2. Style pour le code inline <code>
    html = re.sub(
        r'<code(?:\s+class="[^"]*")?>(.*?)</code>',
        r'<code style="background-color: #f1f5f9; color: #0f172a; padding: 2px 7px; border-radius: 4px; font-family: \'SFMono-Regular\', Consolas, \'Liberation Mono\', Menlo, monospace; font-size: 15.5px; border: 1px solid #e2e8f0;">\1</code>',
        html,
        flags=re.DOTALL
    )

    # 3. Réinsérer et styliser les blocs <pre>
    for i, block in enumerate(pre_blocks):
        styled_pre = re.sub(
            r'<pre><code(?:\s+class="[^"]*")?>(.*?)</code></pre>',
            r'<pre style="background-color: #0f172a; color: #f8fafc; padding: 16px 20px; border-radius: 8px; font-family: \'SFMono-Regular\', Consolas, \'Liberation Mono\', Menlo, monospace; font-size: 15px; line-height: 1.6; overflow-x: auto; margin: 20px 0;"><code style="color: #f8fafc; font-family: inherit;">\1</code></pre>',
            block,
            flags=re.DOTALL
        )
        html = html.replace(f"<!--PRE_BLOCK_{i}-->", styled_pre)

    # 4. Titres h2 et h3
    html = re.sub(
        r'<h2>(.*?)</h2>',
        r'<h2 style="font-size: 21px; font-weight: 700; color: #1e3a8a; border-left: 4px solid #3b82f6; background-color: #eff6ff; padding: 10px 16px; border-radius: 0 8px 8px 0; margin: 32px 0 14px 0;">\1</h2>',
        html
    )
    html = re.sub(
        r'<h3>(.*?)</h3>',
        r'<h3 style="font-size: 18px; font-weight: 700; color: #0f766e; margin: 24px 0 12px 0; padding-bottom: 5px; border-bottom: 1px solid #e2e8f0;">\1</h3>',
        html
    )
    html = re.sub(
        r'<h4>(.*?)</h4>',
        r'<h4 style="font-size: 16px; font-weight: 700; color: #334155; margin: 18px 0 8px 0;">\1</h4>',
        html
    )

    # 5. Paragraphes
    html = re.sub(
        r'<p>(.*?)</p>',
        r'<p style="font-size: 17px; line-height: 1.75; color: #334155; margin: 0 0 16px 0;">\1</p>',
        html,
        flags=re.DOTALL
    )

    # 6. Blocs de citations / Encarts de formules importantes
    html = re.sub(
        r'<blockquote>\s*<p style="[^"]*">(.*?)</p>\s*</blockquote>',
        r'<blockquote style="background-color: #f8fafc; border-left: 4px solid #6366f1; padding: 14px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; color: #1e293b; font-size: 17px; box-shadow: inset 0 0 0 1px #e2e8f0;"><p style="font-size: 17px; line-height: 1.75; color: #1e293b; margin: 0;">\1</p></blockquote>',
        html,
        flags=re.DOTALL
    )

    # 7. Listes
    html = re.sub(
        r'<ol>(.*?)</ol>',
        r'<ol style="font-size: 17px; line-height: 1.75; color: #334155; margin: 0 0 18px 0; padding-left: 24px;">\1</ol>',
        html,
        flags=re.DOTALL
    )
    html = re.sub(
        r'<ul>(.*?)</ul>',
        r'<ul style="font-size: 17px; line-height: 1.75; color: #334155; margin: 0 0 18px 0; padding-left: 24px;">\1</ul>',
        html,
        flags=re.DOTALL
    )
    html = re.sub(
        r'<li>(.*?)</li>',
        r'<li style="margin-bottom: 8px;">\1</li>',
        html,
        flags=re.DOTALL
    )

    # 8. Séparateurs horizontaux
    html = re.sub(
        r'<hr\s*/?>',
        r'<div style="text-align: center; margin: 38px 0;"><hr style="border: none; border-top: 2px dashed #cbd5e1; margin: 0;" /></div>',
        html
    )

    # 9. Gras
    html = re.sub(
        r'<strong>(.*?)</strong>',
        r'<strong style="color: #0f172a; font-weight: 700;">\1</strong>',
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

    # Nettoyage des notations mathématiques brutes
    cleaned_markdown = clean_math_formatting(markdown_content)

    # Conversion Markdown vers HTML puis injection des styles inline
    raw_html = markdown.markdown(cleaned_markdown, extensions=["extra", "sane_lists"])
    styled_content = style_html_content(raw_html)

    styled_html = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
      body {{
        margin: 0;
        padding: 0;
        background-color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
      }}
      @media only screen and (max-width: 620px) {{
        .email-container {{
          width: 100% !important;
          padding: 20px 16px !important;
        }}
      }}
    </style>
  </head>
  <body style="margin: 0; padding: 25px 12px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; -webkit-font-smoothing: antialiased;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f1f5f9; margin: 0; padding: 0;">
      <tr>
        <td align="center">
          <div class="email-container" style="max-width: 700px; width: 100%; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); padding: 32px 36px; text-align: left; box-sizing: border-box;">
            
            <!-- EN-TÊTE DU MAIL -->
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); border-radius: 10px; padding: 24px 26px; margin-bottom: 30px; color: #ffffff;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 12px;">
                <tr>
                  <td align="left">
                    <span style="background-color: rgba(255, 255, 255, 0.2); color: #ffffff; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px; padding: 5px 12px; border-radius: 20px; display: inline-block;">
                      MATHS &amp; IA — ADMISSION INGÉNIEUR
                    </span>
                  </td>
                  <td align="right">
                    <span style="background-color: #f59e0b; color: #ffffff; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 6px; display: inline-block;">
                      60 MIN CHRONO
                    </span>
                  </td>
                </tr>
              </table>
              <h1 style="color: #ffffff; font-size: 22px; font-weight: 800; margin: 0 0 8px 0; line-height: 1.35;">
                {subject}
              </h1>
              <p style="color: #bfdbfe; font-size: 14px; margin: 0; font-weight: 500;">
                Préparation : INSA (Lyon, Toulouse, Rennes) • UT (UTC, UTT, UTBM) • Polytech
              </p>
            </div>

            <!-- CONTENU DE LA LEÇON -->
            <div style="font-size: 17px; line-height: 1.75; color: #334155;">
              {styled_content}
            </div>

            <!-- PIED DE PAGE -->
            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; text-align: center;">
              <p style="font-size: 13px; color: #94a3b8; margin: 0 0 6px 0;">
                Entraînement programmé — BUT Science des Données (BUT SD 3)
              </p>
              <p style="font-size: 12px; color: #cbd5e1; margin: 0;">
                Généré automatiquement via GitHub Actions
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

    # Version texte brut de secours et version HTML soignée
    msg.attach(MIMEText(cleaned_markdown, "plain", "utf-8"))
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