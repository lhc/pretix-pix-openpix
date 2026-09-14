import qrcode
import base64
import requests
from pretix.base.models.orders import OrderPayment, OrderRefund
from io import BytesIO

from http import HTTPStatus


class PixCodeGenerationException(Exception):
    pass


class OpenPix:
    API_URL_MAP = {
        "production": "https://api.openpix.com.br",
        "sandbox": "https://api.woovi-sandbox.com",
    }

    def __init__(self, app_id: str, environment: str, timeout: int = 10):
        self.base_api_url = OpenPix.API_URL_MAP.get(environment)
        if not self.base_api_url:
            raise ValueError("Invalid environment")
        self.headers = {"Authorization": app_id}
        self.timeout = timeout

    def valid_credentials(self) -> bool:
        response = requests.get(
            f"{self.base_api_url}/api/v1/account/",
            headers=self.headers,
            timeout=self.timeout,
        )
        return response.status_code == HTTPStatus.OK

    def refund(self, refund: OrderRefund) -> bool:
        refund_value = str(int(refund.amount * 100))
        payload = {
            "transactionEndToEndId": refund.payment.info_data.get("end_to_end_id")
            or "",
            "correlationID": refund.order.code,
            "value": refund_value,
            "comment": refund.comment,
        }
        response = requests.post(
            f"{self.base_api_url}/api/v1/refund",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        return response.status_code == HTTPStatus.OK

    def qrcode_static(self, payment: OrderPayment):
        payload = {
            "name": payment.order.code,
            "correlationID": payment.order.code,
            "value": str(int(payment.amount * 100)),
            "identifier": payment.order.code,
            "comment": str(_(f"Payment of order {payment.order.code}")),
        }
        response = requests.post(
            f"{self.base_api_url}/api/v1/qrcode-static",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        data = response.json()

        if response.status_code == HTTPStatus.BAD_REQUEST:
            if (
                data["error"]
                == "Já existe um QRCode com este identificador. O identificador deve ser único"
            ):
                response = requests.get(
                    f"{self.base_api_url}/api/v1/qrcode-static/{payment.order.code}",
                    headers=self.headers,
                    timeout=self.timeout,
                )
                data = response.json()

        pix_qr_code = data.get("pixQrCode") or {}
        br_code = pix_qr_code.get("brCode")
        if not br_code:
            raise PixCodeGenerationException

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=4,
        )
        qr.add_data(br_code)
        qr.make(fit=True)
        qr_code_img = qr.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()
        qr_code_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue())
        base64_qr_code = f"data:image/png;base64,{img_str.decode()}"

        return br_code, base64_qr_code
