from typing import KeysView, Generator

SERVICES_FOR_GROUP = {
    "all": "cryptodogelight_harvester cryptodogelight_timelord_launcher cryptodogelight_timelord cryptodogelight_farmer cryptodogelight_full_node cryptodogelight_wallet".split(),
    "node": "cryptodogelight_full_node".split(),
    "harvester": "cryptodogelight_harvester".split(),
    "farmer": "cryptodogelight_harvester cryptodogelight_farmer cryptodogelight_full_node cryptodogelight_wallet".split(),
    "farmer-no-wallet": "cryptodogelight_harvester cryptodogelight_farmer cryptodogelight_full_node".split(),
    "farmer-only": "cryptodogelight_farmer".split(),
    "timelord": "cryptodogelight_timelord_launcher cryptodogelight_timelord cryptodogelight_full_node".split(),
    "timelord-only": "cryptodogelight_timelord".split(),
    "timelord-launcher-only": "cryptodogelight_timelord_launcher".split(),
    "wallet": "cryptodogelight_wallet cryptodogelight_full_node".split(),
    "wallet-only": "cryptodogelight_wallet".split(),
    "introducer": "cryptodogelight_introducer".split(),
    "simulator": "cryptodogelight_full_node_simulator".split(),
}


def all_groups() -> KeysView[str]:
    return SERVICES_FOR_GROUP.keys()


def services_for_groups(groups) -> Generator[str, None, None]:
    for group in groups:
        for service in SERVICES_FOR_GROUP[group]:
            yield service


def validate_service(service: str) -> bool:
    return any(service in _ for _ in SERVICES_FOR_GROUP.values())
