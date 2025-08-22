import base64
from collections import OrderedDict
from http import HTTPStatus
from io import BytesIO

import qrcode
import requests
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _

from pretix.base.payment import BasePaymentProvider

OPENPIX_API_PRODUCTION = "https://api.openpix.com.br"
OPENPIX_API_SANDBOX = "https://api.woovi-sandbox.com"

SUPPORTED_CURRENCIES = [
    "BRL",
]


def valid_api_credentials(app_id, endpoint):
    base_api_url = (
        OPENPIX_API_PRODUCTION if endpoint == "production" else OPENPIX_API_SANDBOX
    )
    response = requests.get(
        f"{base_api_url}/api/v1/account/",
        headers={"Authorization": app_id},
        timeout=10,
    )
    return response.status_code == HTTPStatus.OK


class PixCodeGenerationException(Exception):
    pass


class PixOpenPix(BasePaymentProvider):
    identifier = "pix_openpix"
    verbose_name = _("Brazilian Pix - OpenPix integration")

    @property
    def settings_form_fields(self):
        default_form_fields = list(super().settings_form_fields.items())
        custom_keys = [
            (
                "app_id",
                forms.CharField(
                    label=_("OpenPix AppID"),
                    help_text=_(
                        '<a target="_blank" rel="noopener" href="{docs_url}">{text}</a>'
                    ).format(
                        text=_("Click here for a tutorial on how to obtain the AppID"),
                        docs_url="https://developers.openpix.com.br/docs/apis/api-getting-started",
                    ),
                    required=True,
                ),
            ),
            (
                "endpoint",
                forms.ChoiceField(
                    label=_("Endpoint"),
                    initial="production",
                    choices=(
                        ("production", _("Production")),
                        ("sandbox", _("Sandbox")),
                    ),
                ),
            ),
        ]
        return OrderedDict(custom_keys + default_form_fields)

    def settings_form_clean(self, cleaned_data):
        app_id = cleaned_data.get("payment_pix_openpix_app_id")
        endpoint = cleaned_data.get("payment_pix_openpix_endpoint")
        if not valid_api_credentials(app_id, endpoint):
            raise ValidationError(
                {
                    "payment_pix_openpix_app_id": _(
                        "Please provide a valid API key. Ensure the selected endpoint is correct for the key provided."
                    )
                }
            )
        return cleaned_data

    def settings_content_render(self, request):
        settings_content = _(
            "This payment method will generate a Pix code with order information "
            "that your customer can use to make the payment. You need to have a valid "
            'account in <a href="https://openpix.com.br/">OpenPix</a> to use this method.'
        )

        if self.event.currency not in SUPPORTED_CURRENCIES:
            settings_content += _(
                '<br><br><div class="alert alert-warning">Pix payments are only allowed when the event currency is BRL.</div>'
            )

        return settings_content

    @property
    def test_mode_message(self):
        if self.settings.endpoint == "sandbox":
            return _(
                "OpenPix sandbox settings are being used, you can test without actually sending money but you will need a "
                "sandbox account configured to use it."
            )

        if self.settings.endpoint == "production":
            return _(
                "OpenPix production settings are being used, the generated "
                "Pix Code will be real and you will actually send money to the configured account if you make the payment."
            )

        return None

    def is_allowed(self, request, total):
        return (
            super().is_allowed(request, total)
            and self.event.currency in SUPPORTED_CURRENCIES
        )

    def payment_is_valid_session(self, request):
        return True

    def checkout_confirm_render(self, request, order=None, info_data=None):
        template = get_template("pretix_pix_openpix/checkout_confirm.html")
        return template.render({})

    def _generate_pix_code(self, *, amount, identifier):
        app_id = self.settings.get("app_id")
        endpoint = self.settings.get("endpoint")
        api_url = (
            OPENPIX_API_PRODUCTION if endpoint == "production" else OPENPIX_API_SANDBOX
        )
        amount = str(amount * 100)
        name = identifier

        payload = {
            "name": name,
            "correlationID": identifier,
            "value": amount,
            "identifier": identifier,
            "comment": "good",
        }
        headers = {
            "Authorization": app_id,
        }
        response = requests.post(
            f"{api_url}/api/v1/qrcode-static",
            json=payload,
            headers=headers,
            timeout=10,
        )

        data = response.json()

        if response.status_code == 400:
            if (
                data["error"]
                == "Já existe um QRCode com este identificador. O identificador deve ser único"
            ):
                response = requests.get(
                    f"{api_url}/api/v1/qrcode-static/{identifier}",
                    headers=headers,
                    timeout=10,
                )
                data = response.json()

        pix_code = data["pixQrCode"]["brCode"]

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=4,
        )
        qr.add_data(pix_code)
        qr.make(fit=True)
        qr_code_img = qr.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()
        qr_code_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue())
        base64_qr_code = f"data:image/png;base64,{img_str.decode()}"

        return pix_code, base64_qr_code

    def order_pending_mail_render(self, order, payment):
        try:
            pix_code, base64_qr_code = self._generate_pix_code(
                amount=payment.amount, identifier=payment.order.code
            )
        except PixCodeGenerationException:
            return _(
                "An error occurred while generating the Pix Code. Please try again. If the problem persists, contact the event organizers or select another payment method, if available."
            )

        return _(
            f"""To make the payment, copy and paste the following Pix code into your banking app.

{pix_code}

"""
        )

    def payment_pending_render(self, request, payment):
        try:
            pix_code, base64_qr_code = self._generate_pix_code(
                amount=payment.amount, identifier=payment.order.code
            )
        except PixCodeGenerationException:
            messages.error(
                request,
                _(
                    "An error occurred while generating the Pix Code. Please try again. If the problem persists, contact the event organizers or select another payment method, if available."
                ),
            )
            return ""

        template = get_template("pretix_pix_openpix/payment_pending.html")
        ctx = {
            "pix_code": pix_code,
            "base64_qr_code": base64_qr_code,
        }
        return template.render(ctx, request=request)
