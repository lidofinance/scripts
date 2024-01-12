from typing import Tuple
from brownie import interface

from utils.config import contracts
from .easy_track import create_permissions


def set_limit_parameters(registry_address: str, limit: int, period_duration_months: int) -> Tuple[str, str]:
    registry = interface.AllowedRecipientRegistry(registry_address)
    return (registry.address, registry.setLimitParameters.encode_input(limit, period_duration_months))


def update_spent_amount(registry_address: str, spent_amount: int) -> Tuple[str, str]:
    registry = interface.AllowedRecipientRegistry(registry_address)
    return (registry.address, registry.updateSpentAmount.encode_input(spent_amount))


def create_top_up_allowed_recipient_permission(registry_address: str) -> str:
    return (
        create_permissions(contracts.finance, "newImmediatePayment")
        + create_permissions(interface.AllowedRecipientRegistry(registry_address), "updateSpentAmount")[2:]
    )
