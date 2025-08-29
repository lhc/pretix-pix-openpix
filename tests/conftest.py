from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from pretix.base.models import Event, Order, OrderPayment, Organizer, SalesChannel


@pytest.fixture
def organizer(db):
    return Organizer.objects.create(name="Test Organizer", slug="test-organizer")


@pytest.fixture
def event(db, organizer):
    return Event.objects.create(
        organizer=organizer,
        name="Test Event",
        slug="test_event",
        date_from=datetime(2025, 8, 20, 10, 0, 0, tzinfo=timezone.utc),
        plugins="pretix.plugins.pix_openpix",
    )


@pytest.fixture
def order(db, event):
    sales_channel = SalesChannel.objects.create(
        organizer=event.organizer,
        label="Test Sales Channel",
        identifier="SALES-CHANNEL",
        type="SALES-CHANNEL",
    )

    _order = Order.objects.create(
        code="FOOBAR",
        event=event,
        email="dummy@dummy.test",
        status=Order.STATUS_PENDING,
        expires=datetime.now() + timedelta(days=10),
        total=Decimal("100.0"),
        sales_channel=sales_channel,
    )
    OrderPayment.objects.create(
        local_id=1,
        state=OrderPayment.PAYMENT_STATE_CREATED,
        amount=_order.total,
        order=_order,
        provider="pix_openpix",
        process_initiated=True,
    )

    return _order


@pytest.fixture
def create_payload():
    def _create_payload(
        *,
        order_code="CODE",
        payload_event="OPENPIX:TRANSACTION_RECEIVED",
        order_total=Decimal("100.0")
    ):
        value = 10000

        return {
            "event": "OPENPIX:TRANSACTION_RECEIVED",
            "pixQrCode": {
                "name": order_code,
                "value": value,
                "comment": "good",
                "identifier": order_code,
                "correlationID": order_code,
                "paymentLinkID": "d6e6864a-d7f1-4f1f-b487-ba833b207248",
                "createdAt": "2025-08-29T00:43:58.047Z",
                "updatedAt": "2025-08-29T00:43:58.047Z",
                "brCode": "00020126660014br.gov.bcb.pix01367fc202c1-40a2-49cc-912f-5d2c1c3919c70204good520value00530398654044.005802BR5925Laboratorio_Hacker_de_Cam6009Sao_Paulo62090505P0HXH6304C3CE",
                "paymentLinkUrl": "https://woovi-sandbox.com/pay/d6e6864a-d7f1-4f1f-b487-ba833b207248",
                "qrCodeImage": "https://api.woovi-sandbox.com/openpix/charge/brcode/image/d6e6864a-d7f1-4f1f-b487-ba833b207248.png",
                "pixKey": "7fc202c1-40a2-49cc-912f-5d2c1c3919c7",
            },
            "pix": {
                "payer": {
                    "name": "Cliente Teste",
                    "taxID": {"taxID": "44720743000101", "type": "BR:CNPJ"},
                    "correlationID": "02c308a7-9dc9-4df7-8346-035463066094",
                },
                "value": value,
                "time": "2025-08-29T00:44:11.881Z",
                "endToEndId": "Ef6223604800442e9852227415e7b6141",
                "transactionID": order_code,
                "infoPagador": "OpenPix PixQrCode testing",
                "status": "CONFIRMED",
                "type": "PAYMENT",
                "pixQrCode": {
                    "name": order_code,
                    "value": value,
                    "comment": "good",
                    "identifier": order_code,
                    "correlationID": order_code,
                    "paymentLinkID": "d6e6864a-d7f1-4f1f-b487-ba833b207248",
                    "createdAt": "2025-08-29T00:43:58.047Z",
                    "updatedAt": "2025-08-29T00:43:58.047Z",
                    "brCode": "00020126660014br.gov.bcb.pix01367fc202c1-40a2-49cc-912f-5d2c1c3919c70204good520value00530398654044.005802BR5925Laboratorio_Hacker_de_Cam6009Sao_Paulo62090505P0HXH6304C3CE",
                    "paymentLinkUrl": "https://woovi-sandbox.com/pay/d6e6864a-d7f1-4f1f-b487-ba833b207248",
                    "qrCodeImage": "https://api.woovi-sandbox.com/openpix/charge/brcode/image/d6e6864a-d7f1-4f1f-b487-ba833b207248.png",
                    "pixKey": "7fc202c1-40a2-49cc-912f-5d2c1c3919c7",
                },
                "createdAt": "2025-08-29T00:44:11.883Z",
                "globalID": "UGl4VHJhbnNhY3Rpb246NjhiMGY3ZGJiZWM4MDI4ZGU4Y2UzODNl",
            },
            "company": {
                "id": "689a6d3abc44a20d2b4d3e6d",
                "name": "Laboratório Hacker de Campinas",
                "taxID": "35215073000185",
            },
            "account": {
                "accountId": "689a6d3abc44a20d2b4d3e86",
                "branch": "0001",
                "account": "0240",
            },
            "refunds": [],
        }

    return _create_payload
