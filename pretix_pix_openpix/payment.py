from collections import OrderedDict

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _

from pretix.base.models.orders import OrderPayment, OrderRefund
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix_pix_openpix import OpenPix, PixCodeGenerationException

SUPPORTED_CURRENCIES = [
    "BRL",
]


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
                "environment",
                forms.ChoiceField(
                    label=_("Environment"),
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
        openpix = OpenPix(
            cleaned_data.get("payment_pix_openpix_app_id"),
            cleaned_data.get("payment_pix_openpix_environment"),
        )
        if not openpix.valid_credentials():
            raise ValidationError(
                {
                    "payment_pix_openpix_app_id": _(
                        "Please provide a valid OpenPix AppID. Ensure the selected endpoint is correct for the key provided."
                    )
                }
            )

        # OpenPix webhooks are registered during the plugin configuration form
        # validation because pretix plugin code structure doesn't provide an easy
        # way to override the save() method of the general SettingsForm form (shared by
        # all other plugins) that would be the proper location to perform that action.
        openpix.register_webhooks()

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
        test_mode_messages = {
            "production": _(
                "OpenPix production settings are being used, the generated "
                "Pix Code will be real and you will actually send money to the configured account if you make the payment."
            ),
            "sandbox": _(
                "OpenPix sandbox settings are being used, you can test without actually sending money but you will need a "
                "sandbox account configured to use it."
            ),
        }
        return test_mode_messages.get(self.settings.environment)

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

    def order_pending_mail_render(self, order, payment):
        openpix = OpenPix(self.settings.app_id, self.settings.environment)
        try:
            pix_code, base64_qr_code = openpix.qrcode_static(payment)
        except PixCodeGenerationException:
            return _(
                "An error occurred while generating the Pix Code. Please try again. If the problem persists, contact the event organizers or select another payment method, if available."
            )

        return _(
            f"""To make the payment, copy and paste the following Pix code into your banking app.

{pix_code}

"""
        )

    def payment_refund_supported(self, payment: OrderPayment) -> bool:
        end_to_end_id = payment.info_data.get("end_to_end_id") or None
        correlation_id = payment.order.code
        return all([end_to_end_id, correlation_id])

    def payment_partial_refund_supported(self, payment: OrderPayment) -> bool:
        end_to_end_id = payment.info_data.get("end_to_end_id") or None
        correlation_id = payment.order.code
        return all([end_to_end_id, correlation_id])

    def execute_refund(self, refund: OrderRefund) -> None:
        openpix = OpenPix(self.settings.app_id, self.settings.environment)
        if not openpix.refund(refund):
            raise PaymentException
        refund.done()

    def payment_pending_render(self, request, payment):
        openpix = OpenPix(self.settings.app_id, self.settings.environment)
        try:
            pix_code, base64_qr_code = openpix.qrcode_static(payment)
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
