import urllib
from unittest.mock import patch

import responses
from django.conf import settings
from django.urls import reverse

from pretix_pix_openpix.openpix import API_URL_MAP, OpenPix


@responses.activate
@patch(
    "pretix_pix_openpix.openpix.WEBHOOK_EVENTS",
    {"OPENPIX:WEBHOOK_EVENT_1", "OPENPIX:WEBHOOK_EVENT_2"},
)
def test_register_webhooks__call_openpix_api_for_events(mocker):
    base_url = API_URL_MAP.get("production")
    webhook_full_url = urllib.parse.urljoin(
        settings.SITE_URL, reverse("plugins:pretix_pix_openpix:webhook")
    )

    responses.add(
        responses.GET,
        url=f"{base_url}/api/v1/webhook",
        json={
            "pageInfo": {
                "skip": 0,
                "limit": 100,
                "hasPreviousPage": False,
                "hasNextPage": False,
            },
            "webhooks": [],
        },
    )
    responses.add(
        responses.POST,
        url=f"{base_url}/api/v1/webhook",
    )

    openpix = OpenPix("APP_ID", "production")

    openpix.register_webhooks()

    assert len(responses.calls) == 3
    query_params = {"url": webhook_full_url}
    assert responses.calls[0].request.method == "GET"
    assert (
        responses.calls[0].request.url
        == f"{base_url}/api/v1/webhook?{urllib.parse.urlencode(query_params)}"
    )

    assert responses.calls[1].request.url == f"{base_url}/api/v1/webhook"
    assert responses.calls[2].request.url == f"{base_url}/api/v1/webhook"

    post_request_bodies = {
        responses.calls[1].request.body.decode(),
        responses.calls[2].request.body.decode(),
    }
    assert post_request_bodies == {
        '{"webhook": {"name": "OPENPIX:WEBHOOK_EVENT_1", "event": "OPENPIX:WEBHOOK_EVENT_1", "url": "http://example.com/_pretix_pix_openpix/webhook/", "authorization": "openpix", "isActive": true}}',
        '{"webhook": {"name": "OPENPIX:WEBHOOK_EVENT_2", "event": "OPENPIX:WEBHOOK_EVENT_2", "url": "http://example.com/_pretix_pix_openpix/webhook/", "authorization": "openpix", "isActive": true}}',
    }


@responses.activate
@patch(
    "pretix_pix_openpix.openpix.WEBHOOK_EVENTS",
    {
        "OPENPIX:WEBHOOK_EVENT_1",
    },
)
def test_register_webhooks__do_not_try_register_existing_active_webhook_again(mocker):
    base_url = API_URL_MAP.get("production")
    webhook_full_url = urllib.parse.urljoin(
        settings.SITE_URL, reverse("plugins:pretix_pix_openpix:webhook")
    )

    responses.add(
        responses.GET,
        url=f"{base_url}/api/v1/webhook",
        json={
            "pageInfo": {
                "skip": 0,
                "limit": 100,
                "hasPreviousPage": False,
                "hasNextPage": False,
            },
            "webhooks": [
                {
                    "id": "V2ViaG9vazo2OGIwZjUzZGJlYzgwMjhkZThjZTM0NTM=",
                    "name": "OPENPIX:WEBHOOK_EVENT_1",
                    "url": webhook_full_url,
                    "isActive": True,
                    "createdAt": "2025-08-29T00:33:04.295Z",
                    "updatedAt": "2025-08-29T00:33:04.295Z",
                    "hmacSecretKey": "openpix_O6DGbFP8TApBYlSoCvEXgghhoo5KirxM25C4hwvJ6a0=",
                    "actionPayload": {"url": webhook_full_url},
                    "event": "OPENPIX:WEBHOOK_EVENT_1",
                },
            ],
        },
    )

    openpix = OpenPix("APP_ID", "production")

    openpix.register_webhooks()

    assert len(responses.calls) == 1
    query_params = {"url": webhook_full_url}
    assert responses.calls[0].request.method == "GET"
    assert (
        responses.calls[0].request.url
        == f"{base_url}/api/v1/webhook?{urllib.parse.urlencode(query_params)}"
    )
