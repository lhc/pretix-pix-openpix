import json
import logging
from http import HTTPStatus

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_scopes import scopes_disabled

from pretix.base.models import Order, OrderPayment

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request):
    event_body = request.body.decode("utf-8").strip()

    try:
        data = json.loads(event_body)
    except json.decoder.JSONDecodeError:
        logger.warning("pretix_pix_openpix.webhook.undecodable_content")
        return HttpResponse(status=HTTPStatus.OK)

    event = data.get("event") or ""

    if event == "OPENPIX:TRANSACTION_RECEIVED":
        pix = data.get("pix") or {}
        identifier = pix.get("transactionID")
        end_to_end_id = pix.get("endToEndId")
        value = pix.get("value", 0.0) / 100

        logger.info("%s received for order %s", event, identifier)
        with scopes_disabled():
            order_payment = OrderPayment.objects.filter(
                order__code=identifier,
                order__status=Order.STATUS_PENDING,
                amount=value,
                provider="pix_openpix",
                state__in=(
                    OrderPayment.PAYMENT_STATE_CREATED,
                    OrderPayment.PAYMENT_STATE_PENDING,
                ),
            ).last()
            if order_payment:
                order_payment.info_data = {
                    "end_to_end_id": end_to_end_id,
                }
                order_payment.confirm()

    return HttpResponse(status=HTTPStatus.OK)
