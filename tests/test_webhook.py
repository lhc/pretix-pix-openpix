from http import HTTPStatus

import pytest
from django.urls import reverse

from pretix.base.models import Order


def test_webhook_url(client, db):
    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")

    response = client.post(webhook_url)

    assert response.status_code == HTTPStatus.OK


def test_webhook_url_valid_payload(client, db, create_payload):
    payload = create_payload()

    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")

    response = client.post(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == HTTPStatus.OK


def test_mark_order_as_paid(client, db, order, create_payload):
    assert order.status == Order.STATUS_PENDING

    payload = create_payload(order_code=order.code, order_total=order.total)

    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")

    response = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
    )

    order.refresh_from_db()
    assert order.status == Order.STATUS_PAID
    assert response.status_code == HTTPStatus.OK


def test_do_not_change_order_if_webhook_event_not_valid(
    client, db, order, create_payload
):
    assert order.status == Order.STATUS_PENDING

    payload = create_payload(order_code=order.code, order_total=order.total)
    payload["event"] = "OPENPIX:TRANSACTION_REFUND_RECEIVED"

    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")

    response = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
    )

    order.refresh_from_db()
    assert order.status == Order.STATUS_PENDING
    assert response.status_code == HTTPStatus.OK


def test_invalid_json_payload_do_nothing(client, db, order):
    assert order.status == Order.STATUS_PENDING

    payload = {"content": "not the expected JSON payload"}

    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")

    response = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
    )

    order.refresh_from_db()
    assert order.status == Order.STATUS_PENDING
    assert response.status_code == HTTPStatus.OK


def test_missing_transaction_id_in_payload_do_nothing(client, db, order):
    assert order.status == Order.STATUS_PENDING

    payload = {
        "event": "OPENPIX:TRANSACTION_RECEIVED",
        "pix": {
            "value": 10000,
        },
    }

    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")
    response = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
    )

    order.refresh_from_db()
    assert order.status == Order.STATUS_PENDING
    assert response.status_code == HTTPStatus.OK


def test_missing_value_in_payload_do_nothing(client, db, order):
    assert order.status == Order.STATUS_PENDING

    payload = {
        "event": "OPENPIX:TRANSACTION_RECEIVED",
        "pix": {
            "transactionID": order.code,
        },
    }

    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")

    response = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
    )

    order.refresh_from_db()
    assert order.status == Order.STATUS_PENDING
    assert response.status_code == HTTPStatus.OK


def test_identifier_does_not_refer_to_existing_order(client, db, create_payload):
    payload = create_payload(order_code="NOT-VALID-ORDER")

    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")

    response = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "order_status", [Order.STATUS_PAID, Order.STATUS_EXPIRED, Order.STATUS_CANCELED]
)
def test_when_order_is_not_pending_do_nothing(
    order_status, client, db, order, create_payload
):
    order.status = order_status
    order.save()

    payload = create_payload(order_code=order.code, order_total=order.total)

    webhook_url = reverse("plugins:pretix_pix_openpix:webhook")

    response = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
    )

    order.refresh_from_db()
    assert order.status == order_status
    assert response.status_code == HTTPStatus.OK
