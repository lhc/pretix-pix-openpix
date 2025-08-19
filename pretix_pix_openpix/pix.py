class Pix:
    def __init__(self):
        """
        Define objects of type Pix.
        https://www.bcb.gov.br/content/estabilidadefinanceira/spb_docs/ManualBRCode.pdf
        """
        self._ID_PAYLOAD_FORMAT_INDICATOR = "00"
        # Removido _ID_POINT_OF_INITIATION_METHOD para compatibilidade com Bradesco
        self._ID_MERCHANT_ACCOUNT_INFORMATION = "26"
        self._ID_MERCHANT_ACCOUNT_INFORMATION_GUI = "00"
        self._ID_MERCHANT_ACCOUNT_INFORMATION_KEY = "01"
        self._ID_MERCHANT_ACCOUNT_INFORMATION_DESCRIPTION = "02"
        self._ID_MERCHANT_CATEGORY_CODE = "52"
        self._ID_TRANSACTION_CURRENCY = "53"
        self._ID_TRANSACTION_AMOUNT = "54"
        self._ID_COUNTRY_CODE = "58"
        self._ID_MERCHANT_NAME = "59"
        self._ID_MERCHANT_CITY = "60"
        self._ID_ADDITIONAL_DATA_FIELD_TEMPLATE = "62"
        self._ID_ADDITIONAL_DATA_FIELD_TEMPLATE_TXID = "05"
        self._ID_CRC16 = "63"

        self.pixkey = None
        self.description = None
        self.merchant_name = None
        self.merchant_city = None
        self.country_code = "BR"
        self.txid = None
        self.amount = None

    def __str__(self):
        # Validar campos obrigatórios antes de gerar o código
        self.validate()

        # Formato compatível com o Bradesco (sem o campo Point of Initiation Method)
        payload = "{}{}{}{}{}{}{}{}{}".format(
            self.get_value(self._ID_PAYLOAD_FORMAT_INDICATOR, "01"),
            self.get_merchant_account_information(),
            self.get_value(self._ID_MERCHANT_CATEGORY_CODE, "0000"),
            self.get_value(self._ID_TRANSACTION_CURRENCY, "986"),
            (
                self.get_value(self._ID_TRANSACTION_AMOUNT, self.amount)
                if self.amount
                else ""
            ),
            self.get_value(self._ID_COUNTRY_CODE, self.country_code),
            self.get_value(
                self._ID_MERCHANT_NAME, self.sanitize_text(self.merchant_name)
            ),
            self.get_value(
                self._ID_MERCHANT_CITY, self.sanitize_text(self.merchant_city)
            ),
            self.get_additional_data_field_template(),
        )

        return "{}{}".format(payload, self.get_crc16(payload))

    def set_pixkey(self, pixkey: str):
        self.pixkey = pixkey[:77]

    def set_description(self, description: str):
        self.description = description[:72]

    def set_merchant_name(self, merchant_name: str):
        self.merchant_name = merchant_name[:25]

    def set_merchant_city(self, merchant_city: str):
        self.merchant_city = merchant_city[:15]

    def set_country_code(self, country: str):
        self.country_code = country

    def set_txid(self, txid: str):
        self.txid = txid[:25]

    def set_amount(self, amount: float):
        """Defines the transaction amount with proper formatting"""
        # Formato com exatamente duas casas decimais, sem zeros à esquerda
        # Usar Decimal para garantir o arredondamento correto
        from decimal import ROUND_HALF_UP, Decimal

        # Converter para Decimal e arredondar para duas casas decimais
        decimal_amount = Decimal(str(amount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        self.amount = str(decimal_amount)

    def get_value(self, identify: str, value: str):
        """Concatenates the identifier and the value"""
        return "{}{}{}".format(identify, str(len(value)).zfill(2), value)

    def get_merchant_account_information(self):
        # Usar letras maiúsculas para o domínio do Banco Central, conforme padrão do Bradesco
        gui = self.get_value(
            self._ID_MERCHANT_ACCOUNT_INFORMATION_GUI, "BR.GOV.BCB.PIX"
        )
        key = self.get_value(self._ID_MERCHANT_ACCOUNT_INFORMATION_KEY, self.pixkey)
        description = (
            self.get_value(
                self._ID_MERCHANT_ACCOUNT_INFORMATION_DESCRIPTION, self.description
            )
            if self.description
            else ""
        )

        return self.get_value(
            self._ID_MERCHANT_ACCOUNT_INFORMATION,
            "{}{}{}".format(gui, key, description),
        )

    def get_additional_data_field_template(self):
        if self.txid:
            txid = self.get_value(
                self._ID_ADDITIONAL_DATA_FIELD_TEMPLATE_TXID, self.txid
            )
            return self.get_value(self._ID_ADDITIONAL_DATA_FIELD_TEMPLATE, txid)
        return ""

    def toHex(self, dec: float):
        digits = "0123456789ABCDEF"
        x = dec % 16
        rest = dec // 16
        if rest == 0:
            return digits[x]
        return self.toHex(rest) + digits[x]

    def validate(self):
        """Validates if all required fields are filled"""
        if not self.pixkey:
            raise ValueError("Pix key is required")
        if not self.merchant_name:
            raise ValueError("Merchant name is required")
        if not self.merchant_city:
            raise ValueError("Merchant city is required")
        # O valor é opcional para QR codes estáticos

    def sanitize_text(self, text: str):
        """Remove special characters and accents"""
        import unicodedata

        # Normaliza e remove acentos
        normalized = unicodedata.normalize("NFD", text)
        result = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
        # Remove caracteres não alfanuméricos exceto espaços
        result = "".join(c for c in result if c.isalnum() or c.isspace())
        return result

    def get_crc16(self, payload: str):
        payload = "{}{}{}".format(payload, self._ID_CRC16, "04")
        crc = 0xFFFF
        for i in range(len(payload)):
            crc ^= ord(payload[i]) << 8
            for j in range(8):
                if (crc & 0x8000) > 0:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
        return "{}{}{}".format(self._ID_CRC16, "04", self.toHex(crc & 0xFFFF).upper())
