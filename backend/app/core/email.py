import httpx

from app.core.config import settings

BREVO_BASE_URL = "https://api.brevo.com/v3"


class EmailDeliveryError(Exception):
    """Levee quand l'envoi d'un e-mail transactionnel echoue (reseau ou refus de Brevo)."""


class BrevoEmailClient:
    def send_otp_email(self, to_email: str, to_name: str, code: str) -> None:
        payload = {
            "sender": {"email": settings.brevo_sender_email, "name": settings.brevo_sender_name},
            "to": [{"email": to_email, "name": to_name}],
            "subject": "Votre code de verification LuluSchools",
            "htmlContent": (
                f"<p>Bonjour {to_name},</p>"
                f"<p>Votre code de verification est : <strong>{code}</strong></p>"
                f"<p>Ce code est valable 10 minutes.</p>"
            ),
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

    def send_temporary_credentials_email(
        self, to_email: str, to_name: str, login_id: str, mot_de_passe: str
    ) -> None:
        payload = {
            "sender": {"email": settings.brevo_sender_email, "name": settings.brevo_sender_name},
            "to": [{"email": to_email, "name": to_name}],
            "subject": "Vos identifiants LuluSchools",
            "htmlContent": (
                f"<p>Bonjour {to_name},</p>"
                f"<p>Un compte a ete cree pour vous sur LuluSchools.</p>"
                f"<p>Identifiant : <strong>{login_id}</strong><br>"
                f"Mot de passe temporaire : <strong>{mot_de_passe}</strong></p>"
                f"<p>Vous devrez le changer des votre premiere connexion.</p>"
            ),
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


def get_email_client() -> BrevoEmailClient:
    return BrevoEmailClient()
