#!/usr/bin/python3

from typing import NamedTuple, Tuple

from brownie.network.event import EventDict
from .common import validate_events_chain

CREATE_VERSION_ROLE = "0x1f56cfecd3595a2e6cc1a7e6cb0b20df84cdbd92eff2fee554e70e4e45a9a7d8"


class RepoUpgrade(NamedTuple):
    version_id: int
    semantic_version: Tuple[int, int, int]


def validate_repo_upgrade_event(event: EventDict, ru: RepoUpgrade):
    _repo_upgrade_events_chain = ["LogScriptCall", "NewVersion"]

    validate_events_chain([e.name for e in event], _repo_upgrade_events_chain)

    assert event.count("NewVersion") == 1

    assert event["NewVersion"]["versionId"] == ru.version_id
    assert event["NewVersion"]["semanticVersion"] == ru.semantic_version


class NewRepoItem(NamedTuple):
    name: str
    app: str
    app_id: str
    repo_app_id: str
    semantic_version: Tuple[int, int, int]
    apm: str
    manager: str


def validate_new_repo_with_version_event(event: EventDict, new_repo_item: NewRepoItem):
    _repo_upgrade_events_chain = [
        "LogScriptCall",
        "NewAppProxy",
        "SetPermission",
        "ChangePermissionManager",
        "NewOwner",
        "NewName",
        "NewResolver",
        "AddressChanged",
        "AddrChanged",
        "NewRepo",
        "NewVersion",
        "SetPermission",
        "SetPermission",
        "ChangePermissionManager",
    ]

    validate_events_chain([e.name for e in event], _repo_upgrade_events_chain)

    assert event.count("NewAppProxy") == 1
    assert event.count("NewRepo") == 1
    assert event.count("NewVersion") == 1

    # expected ENS events
    assert event.count("NewOwner") == 1
    assert event.count("NewName") == 1
    assert event.count("NewResolver") == 1

    assert event["NewAppProxy"]["isUpgradeable"] == True
    assert event["NewAppProxy"]["appId"] == new_repo_item.repo_app_id

    repo = event["NewAppProxy"]["proxy"]

    assert event["NewRepo"]["id"] == new_repo_item.app_id
    assert event["NewRepo"]["name"] == new_repo_item.name
    assert event["NewRepo"]["repo"] == repo

    assert event["NewVersion"]["semanticVersion"] == new_repo_item.semantic_version, "Wrong version"

    assert event.count("SetPermission") == 3
    assert event.count("ChangePermissionManager") == 2

    assert event["SetPermission"][0]["entity"] == new_repo_item.apm
    assert event["SetPermission"][0]["app"] == repo
    assert event["SetPermission"][0]["role"] == CREATE_VERSION_ROLE
    assert event["SetPermission"][0]["allowed"] == True

    assert event["ChangePermissionManager"][0]["app"] == repo
    assert event["ChangePermissionManager"][0]["role"] == CREATE_VERSION_ROLE
    assert event["ChangePermissionManager"][0]["manager"] == new_repo_item.apm

    assert event["SetPermission"][1]["entity"] == new_repo_item.apm
    assert event["SetPermission"][1]["app"] == repo
    assert event["SetPermission"][1]["role"] == CREATE_VERSION_ROLE
    assert event["SetPermission"][1]["allowed"] == False

    assert event["SetPermission"][2]["entity"] == new_repo_item.manager
    assert event["SetPermission"][2]["app"] == repo
    assert event["SetPermission"][2]["role"] == CREATE_VERSION_ROLE
    assert event["SetPermission"][2]["allowed"] == True

    assert event["ChangePermissionManager"][1]["app"] == repo
    assert event["ChangePermissionManager"][1]["role"] == CREATE_VERSION_ROLE
    assert event["ChangePermissionManager"][1]["manager"] == new_repo_item.manager
