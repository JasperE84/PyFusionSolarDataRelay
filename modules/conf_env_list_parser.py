from pydantic.fields import FieldInfo
from pydantic_settings import EnvSettingsSource
import json
import os
from typing import Any


class ConfEnvListParser(EnvSettingsSource):
    def prepare_field_value(self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        if field_name in ["fusionsolar_kiosks", "kenter_metering_points", "fusionsolar_open_api_inverters", "fusionsolar_open_api_meters"]:
            prefix = f"{field_name.upper()}__"
            kiosks_map = {}
            for key, val in os.environ.items():
                key = key.upper()
                if key.startswith(prefix):
                    # Example: FUSIONSOLAR_KIOSKS__0__FUSIONSOLAR_KIOSK_API_URL
                    # Split out the index and field name
                    _, idx_str, field_found_name = key.split("__", 2)
                    try:
                        idx = int(idx_str)
                    except ValueError:
                        # If the middle portion is not an integer, ignore
                        continue
                    if idx not in kiosks_map:
                        kiosks_map[idx] = {}
                    # Put the raw string into the kiosk map under the correct field
                    kiosks_map[idx][field_found_name.lower()] = val

            # Sort keys numerically and build a list
            kiosks_list = []
            for idx in sorted(kiosks_map.keys()):
                kiosks_list.append(kiosks_map[idx])

            value = json.dumps(kiosks_list)

        ret = super(ConfEnvListParser, self).prepare_field_value(field_name, field, value, value_is_complex)
        return ret
