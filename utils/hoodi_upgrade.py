import json
import os
from pathlib import Path
from typing import Any, Dict

from brownie import Contract

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:
    import toml as tomllib  # type: ignore[no-redef]


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIDO_CORE_ROOT = PROJECT_ROOT / "lido-core"

DEFAULT_DEPLOYED_LOCAL_FILE = "deployed-local.json"
DEFAULT_UPGRADE_PARAMS_FILE = "scripts/upgrade/upgrade-params-hoodi.toml"
DEFAULT_CURATED_MODULE_ARTIFACT = "artifacts/contracts/upgrade/UpgradeTypes.sol/ICuratedModule.json"


def _resolve_lido_core_path(env_name: str, default_relative_path: str) -> Path:
    value = os.getenv(env_name, default_relative_path)
    path = Path(value)
    if not path.is_absolute():
        path = LIDO_CORE_ROOT / path
    return path


def get_deployed_local_path() -> Path:
    return _resolve_lido_core_path("LIDO_CORE_DEPLOYED_FILE", DEFAULT_DEPLOYED_LOCAL_FILE)


def get_upgrade_params_path() -> Path:
    return _resolve_lido_core_path("LIDO_CORE_UPGRADE_PARAMS_FILE", DEFAULT_UPGRADE_PARAMS_FILE)


def get_curated_module_artifact_path() -> Path:
    return _resolve_lido_core_path("LIDO_CORE_CURATED_MODULE_ARTIFACT", DEFAULT_CURATED_MODULE_ARTIFACT)


def load_deployed_local_state() -> Dict[str, Any]:
    state_path = get_deployed_local_path()
    if not state_path.exists():
        raise FileNotFoundError(f"local deployment state file not found: {state_path}")
    return json.loads(state_path.read_text())


def _loads_toml(text: str) -> Dict[str, Any]:
    return tomllib.loads(text)


def load_upgrade_params() -> Dict[str, Any]:
    params_path = get_upgrade_params_path()
    if not params_path.exists():
        raise FileNotFoundError(f"upgrade params file not found: {params_path}")
    return _loads_toml(params_path.read_text())


def get_state_address(key: str) -> str:
    state = load_deployed_local_state()
    item = state.get(key)
    if item is None:
        raise KeyError(f"deployment state key is missing: {key}")

    if isinstance(item, dict):
        address = item.get("address")
        if isinstance(address, str):
            return address

        proxy = item.get("proxy")
        if isinstance(proxy, dict) and isinstance(proxy.get("address"), str):
            return proxy["address"]

    raise KeyError(f"could not extract address from deployment state key: {key}")


def get_optional_state_address(key: str, default: str = ZERO_ADDRESS) -> str:
    try:
        return get_state_address(key)
    except Exception:
        return default


def get_upgrade_vote_script_address() -> str:
    return get_state_address("upgradeVoteScript")


def get_optional_upgrade_vote_script_address(default: str = ZERO_ADDRESS) -> str:
    return get_optional_state_address("upgradeVoteScript", default)


def get_consolidation_migrator_address() -> str:
    return get_state_address("consolidationMigrator")


def get_optional_consolidation_migrator_address(default: str = ZERO_ADDRESS) -> str:
    return get_optional_state_address("consolidationMigrator", default)


def get_easy_track_new_factories() -> Dict[str, str]:
    params = load_upgrade_params()
    return dict(params["easyTrack"]["newFactories"])


def get_optional_easy_track_new_factories() -> Dict[str, str]:
    try:
        return get_easy_track_new_factories()
    except Exception:
        return {
            "UpdateStakingModuleShareLimits": ZERO_ADDRESS,
            "AllowConsolidationPair": ZERO_ADDRESS,
            "CreateOrUpdateOperatorGroup": ZERO_ADDRESS,
        }


def get_curated_module_address() -> str:
    params = load_upgrade_params()
    return params["curatedModule"]["module"]


def get_meta_registry_address() -> str:
    artifact_path = get_curated_module_artifact_path()
    if not artifact_path.exists():
        raise FileNotFoundError(f"curated module artifact not found: {artifact_path}")

    artifact = json.loads(artifact_path.read_text())
    abi = artifact["abi"]
    curated_module = Contract.from_abi("ICuratedModule", get_curated_module_address(), abi)
    return curated_module.META_REGISTRY()


def get_optional_meta_registry_address(default: str = ZERO_ADDRESS) -> str:
    try:
        return get_meta_registry_address()
    except Exception:
        return default
