from .logoverviewparams import LogOverviewParams


class FirmwareChartParams(LogOverviewParams):
    selected_codes: list[str]
    selected_firmwares: list[str]
