#  Gispo Ltd., hereby disclaims all copyright interest in the program FMI2QGIS
#  Copyright (C) 2020-2021 Gispo Ltd (https://www.gispo.fi/).
#
#
#  This file is part of FMI2QGIS.
#
#  FMI2QGIS is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  FMI2QGIS is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with FMI2QGIS.  If not, see <https://www.gnu.org/licenses/>.

import logging
import re
from typing import List, Optional

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDockWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from qgis.gui import (
    QgisInterface,
    QgsCollapsibleGroupBox,
    QgsDateTimeEdit,
    QgsFilterLineEdit,
)

from ..core.wms import WMSLayer, WMSLayerHandler
from ..definitions.configurable_settings import Settings
from ..qgis_plugin_tools.tools.custom_logging import bar_msg
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.resources import load_ui, plugin_name

TEMPORAL_CONTROLLER = "Temporal Controller"

FORM_CLASS = load_ui("wms_dialog.ui")
LOGGER = logging.getLogger(plugin_name())


class WMSDialog(QDialog, FORM_CLASS):  # type: ignore
    # TODO: merge this class and dialog with main_dialog

    def __init__(self, iface: QgisInterface, parent: QWidget = None) -> None:
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.iface = iface

        self.btn_select_wms.clicked.connect(self.__wms_layer_selected)
        self.btn_add_wms.clicked.connect(self.__add_wms_to_map)
        self.btn_clear_wms_search.clicked.connect(self.__clear_wms_search)

        self.ln_ed_wms_search: QgsFilterLineEdit
        self.ln_ed_wms_search.valueChanged.connect(self.__search_wms_layers)

        self.group_box_wms_params: QgsCollapsibleGroupBox
        self.group_box_wms_params.setCollapsed(True)
        self.group_box_wms_params.setEnabled(False)

        self.wms_layer_handler = WMSLayerHandler(Settings.FMI_WMS_URL.get())
        self.wms_layers: List[WMSLayer] = []
        self.selected_wms_layer: Optional[WMSLayer] = None

        self.tbl_wms_layers: QTableWidget

        self.__refresh_wms_layers()

    def __refresh_wms_layers(self) -> None:
        self.wms_layers = self.wms_layer_handler.list_wms_layers()
        self.tbl_wms_layers.setColumnCount(3)
        self.tbl_wms_layers.setRowCount(len(self.wms_layers))

        for idx, wms_layer in enumerate(self.wms_layers):
            self.tbl_wms_layers.setItem(idx, 0, QTableWidgetItem(wms_layer.name))
            self.tbl_wms_layers.setItem(idx, 1, QTableWidgetItem(wms_layer.title))
            abstract_item = QTableWidgetItem(wms_layer.abstract)
            abstract_item.setToolTip(wms_layer.abstract)
            self.tbl_wms_layers.setItem(idx, 2, abstract_item)

    def __search_wms_layers(self) -> None:

        self.wms_layers = self.wms_layer_handler.list_wms_layers()
        self.tbl_wms_layers.setColumnCount(3)
        self.tbl_wms_layers.setRowCount(len(self.wms_layers))
        self.search_string = self.ln_ed_wms_search.value()
        search_string = self.search_string.lower()

        for idx, wms_layer in enumerate(self.wms_layers):
            wms_layer_fields = [wms_layer.name, wms_layer.title, wms_layer.abstract]
            used_fields = [field for field in wms_layer_fields if field is not None]
            found_match = []
            for item in used_fields:
                if re.search(search_string, item.lower()):
                    found_match.append(item)
            if found_match:
                self.tbl_wms_layers.showRow(idx)
            else:
                self.tbl_wms_layers.hideRow(idx)

    def __clear_wms_search(self) -> None:
        self.ln_ed_wms_search.clearValue()
        for idx, _ in enumerate(self.wms_layers):
            self.tbl_wms_layers.showRow(idx)

    def __wms_layer_selected(self) -> None:
        self.tbl_wms_layers: QTableWidget  # type: ignore
        indexes = self.tbl_wms_layers.selectedIndexes()
        if not indexes:
            LOGGER.warning(
                tr("Could not execute select"),
                extra=bar_msg(tr("Data source must be selected!")),
            )
            return
        else:
            wms_layer = self.wms_layers[indexes[0].row()]
            self.group_box_wms_params.setEnabled(
                any((wms_layer.is_temporal, wms_layer.has_elevation))
            )
            self.group_box_wms_params.setCollapsed(
                not any((wms_layer.is_temporal, wms_layer.has_elevation))
            )

            self.date_time_start: QgsDateTimeEdit
            self.date_time_end: QgsDateTimeEdit
            self.date_time_start.setEnabled(wms_layer.is_temporal)
            self.date_time_end.setEnabled(wms_layer.is_temporal)
            if wms_layer.is_temporal:
                time_step_text = tr(
                    "With time steps {}{}", wms_layer.t_step, wms_layer.time_step_uom
                )
                self.date_time_start.setDateTimeRange(
                    wms_layer.start_time, wms_layer.end_time
                )
                self.date_time_start.setDateTime(wms_layer.start_time)
                self.date_time_start.setToolTip(time_step_text)
                self.date_time_end.setDateTimeRange(
                    wms_layer.start_time, wms_layer.end_time
                )
                self.date_time_end.setDateTime(wms_layer.end_time)
                self.date_time_end.setToolTip(time_step_text)

            self.combo_box_elevation: QComboBox
            self.combo_box_elevation.clear()
            self.combo_box_elevation.setEnabled(wms_layer.has_elevation)
            self.label_elevation_units.setText("")
            if wms_layer.has_elevation:
                self.combo_box_elevation.addItems(list(map(str, wms_layer.elevations)))
                self.combo_box_elevation.setCurrentText(
                    str(wms_layer.default_elevation)
                )
                self.combo_box_elevation.setToolTip(wms_layer.elevation_unit)
                self.label_elevation_units: QLabel
                self.label_elevation_units.setToolTip(wms_layer.elevation_unit)
                self.label_elevation_units.setText(wms_layer.elevation_unit_symbol)

            self.selected_wms_layer = wms_layer

    def __add_wms_to_map(self) -> None:
        if self.selected_wms_layer:
            self.date_time_start: QgsDateTimeEdit  # type: ignore
            start_time = (
                self.date_time_start.dateTime().toPyDateTime()
                if self.date_time_start.isEnabled()
                else None
            )
            end_time = (
                self.date_time_end.dateTime().toPyDateTime()
                if self.date_time_end.isEnabled()
                else None
            )
            elevation = (
                float(self.combo_box_elevation.currentText())
                if self.combo_box_elevation.isEnabled()
                else None
            )

            if self.selected_wms_layer.is_temporal:
                self.__show_temporal_controller()

            self.wms_layer_handler.add_to_map(
                self.selected_wms_layer, start_time, end_time, elevation
            )
        else:
            LOGGER.warning(
                tr("Could not add to map"),
                extra=bar_msg(tr("Data source must be selected!")),
            )

    def __show_temporal_controller(self) -> None:
        """Sets Temporal Controller dock widget visible if it exists"""
        dock_widget: QDockWidget
        for dock_widget in self.iface.mainWindow().findChildren(QDockWidget):
            if dock_widget.objectName() == TEMPORAL_CONTROLLER:
                dock_widget.setVisible(True)
