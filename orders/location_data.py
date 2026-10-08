"""Bundled Nepal administrative choices; no network lookups at checkout.

The JSON files are a vendored static snapshot of:
https://github.com/bibekoli/local-levels-of-nepal-dataset
The hierarchy covers all 7 provinces, 77 districts, and 753 local levels.
"""

import json
from pathlib import Path


DATA_DIR = Path(__file__).parent
PROVINCE_LABELS = {
    1: 'Koshi Province',
    2: 'Madhesh Province',
    3: 'Bagmati Province',
    4: 'Gandaki Province',
    5: 'Lumbini Province',
    6: 'Karnali Province',
    7: 'Sudurpashchim Province',
}
LOCAL_LEVEL_TYPES = {
    1: 'Metropolitan City',
    2: 'Sub-Metropolitan City',
    3: 'Municipality',
    4: 'Rural Municipality',
}


def _read_dataset(filename):
    with (DATA_DIR / filename).open(encoding='utf-8') as dataset:
        return json.load(dataset)


def load_location_hierarchy():
    provinces = _read_dataset('nepal_provinces.json')
    districts = _read_dataset('nepal_districts.json')
    local_levels = _read_dataset('nepal_local_levels.json')

    province_by_id = {item['province_id']: PROVINCE_LABELS[item['province_id']] for item in provinces}
    district_by_id = {
        item['district_id']: {
            'name': item['name'],
            'province': province_by_id[item['province_id']],
        }
        for item in districts
    }

    hierarchy = {name: {} for name in PROVINCE_LABELS.values()}
    for district in districts:
        province = province_by_id[district['province_id']]
        hierarchy[province][district['name']] = []

    for local_level in local_levels:
        district = district_by_id[local_level['district_id']]
        local_level_type = LOCAL_LEVEL_TYPES[local_level['local_level_type_id']]
        hierarchy[district['province']][district['name']].append(
            f"{local_level['name']} {local_level_type}"
        )

    for province_districts in hierarchy.values():
        for municipalities in province_districts.values():
            municipalities.sort(key=str.casefold)

    return hierarchy


LOCATION_HIERARCHY = load_location_hierarchy()
PROVINCES = tuple(LOCATION_HIERARCHY)
MAX_WARD_NUMBER = 35
