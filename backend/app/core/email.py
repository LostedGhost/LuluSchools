import httpx

from app.core.config import settings

BREVO_BASE_URL = "https://api.brevo.com/v3"

_BRAND_GREEN = "#16a34a"
_INK = "#1a2420"
_INK_SOFT = "#5b6b62"
_BORDER = "#e3e8e5"
_SURFACE_2 = "#f3f6f4"


class EmailDeliveryError(Exception):
    """Levee quand l'envoi d'un e-mail transactionnel echoue (reseau ou refus de Brevo)."""


def _wrap_email_html(preheader: str, title: str, body_html: str) -> str:
    """Enveloppe un contenu dans un document HTML complet (DOCTYPE/html/head/body),
    avec CSS inline pour rester compatible avec la majorite des clients mail."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0; padding:0; background-color:{_SURFACE_2}; font-family:'Segoe UI', Helvetica, Arial, sans-serif;">
  <span style="display:none; font-size:1px; color:{_SURFACE_2}; line-height:1px; max-height:0; max-width:0; opacity:0; overflow:hidden;">{preheader}</span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{_SURFACE_2}; padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px; width:100%; background-color:#ffffff; border:1px solid {_BORDER}; border-radius:12px; overflow:hidden;">
          <tr>
            <td style="padding:28px 32px 20px 32px; border-bottom:1px solid {_BORDER};">
              <span style="font-size:20px; font-weight:700; color:{_INK};">Lulu<span style="color:{_BRAND_GREEN};">·</span>Schools</span>
              <div style="font-size:12px; color:{_INK_SOFT}; margin-top:2px;">Plateforme educative nationale &middot; Republique du Benin</div>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              {body_html}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px; background-color:{_SURFACE_2}; border-top:1px solid {_BORDER};">
              <p style="margin:0; font-size:12px; color:{_INK_SOFT};">
                Cet e-mail est envoye automatiquement, merci de ne pas y repondre.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


class BrevoEmailClient:
    def _send(self, to_email: str, to_name: str, subject: str, html_content: str, text_content: str) -> None:
        payload = {
            "sender": {"email": settings.brevo_sender_email, "name": settings.brevo_sender_name},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content,
        }
        try:
            response = httpx.post(
                f"{BREVO_BASE_URL}/smtp/email",
                headers={"api-key": settings.brevo_api_key, "content-type": "application/json"},
                json=payload,
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise EmailDeliveryError("Impossible de contacter le service d'e-mail.") from exc

        if response.status_code not in (201, 202):
            raise EmailDeliveryError(f"Brevo a refuse l'envoi (statut {response.status_code}).")

    def send_otp_email(self, to_email: str, to_name: str, code: str) -> None:
        body_html = f"""
              <h1 style="margin:0 0 16px 0; font-size:18px; color:{_INK};">Bonjour {to_name},</h1>
              <p style="margin:0 0 20px 0; font-size:14px; line-height:1.6; color:{_INK_SOFT};">
                Voici votre code de verification pour confirmer votre adresse e-mail sur LuluSchools.
              </p>
              <div style="text-align:center; margin:0 0 20px 0;">
                <span style="display:inline-block; padding:14px 28px; background-color:{_SURFACE_2}; border:1px solid {_BORDER}; border-radius:8px; font-size:28px; font-weight:700; letter-spacing:0.3em; color:{_BRAND_GREEN};">{code}</span>
              </div>
              <p style="margin:0; font-size:13px; color:{_INK_SOFT};">
                Ce code est valable 10 minutes. Si vous n'etes pas a l'origine de cette demande, ignorez cet e-mail.
              </p>"""
        html_content = _wrap_email_html(
            preheader=f"Votre code de verification : {code}",
            title="Code de verification LuluSchools",
            body_html=body_html,
        )
        text_content = (
            f"Bonjour {to_name},\n\n"
            f"Votre code de verification LuluSchools est : {code}\n"
            "Ce code est valable 10 minutes.\n"
        )
        self._send(to_email, to_name, "Votre code de verification LuluSchools", html_content, text_content)

    def send_temporary_credentials_email(
        self, to_email: str, to_name: str, login_id: str, mot_de_passe: str
    ) -> None:
        body_html = f"""
              <h1 style="margin:0 0 16px 0; font-size:18px; color:{_INK};">Bonjour {to_name},</h1>
              <p style="margin:0 0 20px 0; font-size:14px; line-height:1.6; color:{_INK_SOFT};">
                Un compte vient d'etre cree pour vous sur LuluSchools. Voici vos identifiants de premiere connexion :
              </p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px 0; border:1px solid {_BORDER}; border-radius:8px; overflow:hidden;">
                <tr>
                  <td style="padding:12px 16px; background-color:{_SURFACE_2}; font-size:13px; color:{_INK_SOFT}; border-bottom:1px solid {_BORDER};">Identifiant</td>
                  <td style="padding:12px 16px; font-size:14px; font-weight:700; color:{_INK}; border-bottom:1px solid {_BORDER};">{login_id}</td>
                </tr>
                <tr>
                  <td style="padding:12px 16px; background-color:{_SURFACE_2}; font-size:13px; color:{_INK_SOFT};">Mot de passe temporaire</td>
                  <td style="padding:12px 16px; font-size:14px; font-weight:700; color:{_INK};">{mot_de_passe}</td>
                </tr>
              </table>
              <p style="margin:0; font-size:13px; color:{_INK_SOFT};">
                Pour votre securite, vous devrez le changer des votre premiere connexion.
              </p>"""
        html_content = _wrap_email_html(
            preheader="Vos identifiants de connexion LuluSchools",
            title="Vos identifiants LuluSchools",
            body_html=body_html,
        )
        text_content = (
            f"Bonjour {to_name},\n\n"
            "Un compte a ete cree pour vous sur LuluSchools.\n"
            f"Identifiant : {login_id}\n"
            f"Mot de passe temporaire : {mot_de_passe}\n\n"
            "Vous devrez le changer des votre premiere connexion.\n"
        )
        self._send(to_email, to_name, "Vos identifiants LuluSchools", html_content, text_content)


def get_email_client() -> BrevoEmailClient:
    return BrevoEmailClient()
