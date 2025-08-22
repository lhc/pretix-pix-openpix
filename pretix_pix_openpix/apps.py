from django.utils.translation import gettext_lazy as _

from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_pix_openpix"
    verbose_name = _("Brazilian Pix - OpenPix integration")

    class PretixPluginMeta:
        name = _("Brazilian Pix - OpenPix integration")
        author = "Renne Rocha"
        description = _("Accept Pix payments with your OpenPix account.")
        visible = True
        version = __version__
        category = "PAYMENT"
        compatibility = "pretix>=2.7.0"
        settings_links = [
            (
                (_("Payment"), _("OpenPix")),
                "control:event.settings.payment.provider",
                {"provider": "pix_openpix"},
            ),
        ]
        navigation_links = []

    def ready(self):
        from . import signals  # NOQA
