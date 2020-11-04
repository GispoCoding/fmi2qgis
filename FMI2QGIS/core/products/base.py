from pathlib import Path

from qgis.core import QgsProcessingFeedback

from ..exceptions.loader_exceptions import BadRequestException
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools import network


class BaseProduct:
    producer = ''
    time_format = '%Y-%m-%dT%H:%M:%SZ'  # 2020-11-02T15:00:00Z

    def __init__(self, download_dir: Path, fmi_download_url: str, feedback: QgsProcessingFeedback):
        """
        :param download_dir:Download directory of the output file(s)
        :param fmi_download_url: FMI download url
        :param feedback:
        """
        self.download_dir = download_dir
        if not self.download_dir.exists():
            self.download_dir.mkdir()
        self.url = fmi_download_url
        self.feedback = feedback

    def download(self, **kwargs) -> Path:
        """
        Downloads files to the disk (self.download_dir)
        :param kwargs: keyword arguments depending on the product
        :return: Path to the downloaded file
        """
        try:
            self.feedback.setProgress(0)
            uri = self._construct_uri(**kwargs)
            self.feedback.setProgress(0.10)
            self.feedback.pushDebugInfo(uri)

            try:
                data, default_name = network.fetch_raw(uri)
                self.feedback.setProgress(0.7)
                if not self.feedback.isCanceled():
                    output = Path(self.download_dir, default_name)
                    with open(output, 'wb') as f:
                        f.write(data)
                    return output
            except QgsPluginNetworkException as e:
                error_message = e.bar_msg['details']
                if 'Bad Request' in error_message:
                    raise BadRequestException(tr('Bad request'),
                                              bar_msg=bar_msg(tr('Try with different start and end times')))
        except Exception as e:
            self.feedback.reportError(tr('Error occurred: {}', e), True)
            self.feedback.cancel()

        self.feedback.setProgress(1.0)

    def _construct_uri(self, **kwargs) -> str:
        url = self.url + f'?producer={self.producer}'
        return url
