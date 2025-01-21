from scripts.after_pectra_upgrade_holesky import start_vote
from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS
from brownie import interface
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.common import validate_events_chain

# Contracts
AGENT = "0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d"
VOTING = "0xdA7d2573Df555002503F29aA4003e398d28cc00f"
ORACLE_SANITY_CHECKER = "0x80D1B1fF6E84134404abA18A628347960c38ccA7"

# Roles
EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE = "0x60b9982471bc0620c7b74959f48a86c55c92c11876fddc5b0b54d1ec47153e5d"
APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE = "0x14ca7b84baa11a976283347b0159b8ddf2dcf5fd5cf613cc567a3423cf510119"
INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE = "0xebfa317a5d279811b024586b17a50f48924bce86f6293b233927322d7209b507"

# Old values

OLD_INITIAL_SLASHING_AMOUNT_PWEI = 1000
OLD_EXITED_VALIDATORS_PER_DAY_LIMIT = 9016
OLD_APPEARED_VALIDATORS_PER_DAY_LIMIT = 43200

# New values
NEW_INITIAL_SLASHING_AMOUNT_PWEI = 8
NEW_EXITED_VALIDATORS_PER_DAY_LIMIT = 3600
NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT = 1800


def get_voting():
    return interface.Voting(VOTING)


def get_sanity_checker():
    return interface.OracleReportSanityChecker(ORACLE_SANITY_CHECKER)


def test_vote(helpers, accounts, vote_ids_from_env, bypass_events_decoding):
    sanityChecker = get_sanity_checker()
    sanity_checker_limits = sanityChecker.getOracleReportLimits()

    # Before voting tests
    # 1) Aragon Agent doesn't have `EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanityChecker.hasRole(EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 2) Check `exitedValidatorsPerDayLimit` sanity checker old value
    assert sanity_checker_limits["exitedValidatorsPerDayLimit"] == OLD_EXITED_VALIDATORS_PER_DAY_LIMIT
    # 3) Aragon Agent doesn't have `APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanityChecker.hasRole(APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 4) Check `appearedValidatorsPerDayLimit` sanity checker old value
    assert sanity_checker_limits["appearedValidatorsPerDayLimit"] == OLD_APPEARED_VALIDATORS_PER_DAY_LIMIT
    # 5) Aragon Agent doesn't have `INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanityChecker.hasRole(INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 6) Check `initialSlashingAmountPWei` sanity checker old value
    assert sanity_checker_limits["initialSlashingAmountPWei"] == OLD_INITIAL_SLASHING_AMOUNT_PWEI

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    voting = get_voting()

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    sanity_checker_limits = sanityChecker.getOracleReportLimits()

    # After voting tests
    # 1) Aragon Agent doesn't have `EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanityChecker.hasRole(EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 2) Check `exitedValidatorsPerDayLimit` sanity checker value after voting equal to 3600
    assert sanity_checker_limits["exitedValidatorsPerDayLimit"] == NEW_EXITED_VALIDATORS_PER_DAY_LIMIT
    # 3) Aragon Agent doesn't have `APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanityChecker.hasRole(APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 4) Check `appearedValidatorsPerDayLimit` sanity checker value after voting equal to 1800
    assert sanity_checker_limits["appearedValidatorsPerDayLimit"] == NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT
    # 5) Aragon Agent doesn't have `INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanityChecker.hasRole(INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 6) Check `initialSlashingAmountPWei` sanity checker value to 8
    assert sanity_checker_limits["initialSlashingAmountPWei"] == NEW_INITIAL_SLASHING_AMOUNT_PWEI

    # Events check
    display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    assert len(events) == 9

    # Validate exitedValidatorsPerDayLimit sanity checker value set to `NEW_EXITED_VALIDATORS_PER_DAY_LIMIT`
    validate_sc_exited_validators_limit_update(events[:3], NEW_EXITED_VALIDATORS_PER_DAY_LIMIT)
    # Validate appearedValidatorsPerDayLimit sanity checker value set to `NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT`
    validate_appeared_validators_limit_update(events[3:6], NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT)
    # Validate initialSlashingAmountPWei sanity checker value set to `NEW_INITIAL_SLASHING_AMOUNT_PWEI`
    validate_initial_slashing_and_penalties_update(events[6:9], NEW_INITIAL_SLASHING_AMOUNT_PWEI)


# Events check


def validate_sc_exited_validators_limit_update(events: list[EventDict], exitedValidatorsPerDayLimit):
    validate_grant_role_event(
        events[0],
        EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_exited_validators_per_day_limit_event(events[1], exitedValidatorsPerDayLimit)
    validate_revoke_role_event(
        events[2],
        EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )


def validate_appeared_validators_limit_update(events: list[EventDict], appearedValidatorsPerDayLimit):
    validate_grant_role_event(
        events[0],
        APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_appeared_validators_limit_event(events[1], appearedValidatorsPerDayLimit)
    validate_revoke_role_event(
        events[2],
        APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )


def validate_initial_slashing_and_penalties_update(events: list[EventDict], initialSlashingAmountPWei):
    validate_grant_role_event(
        events[0],
        INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_initial_slashing_and_penalties_event(events[1], initialSlashingAmountPWei)
    validate_revoke_role_event(
        events[2],
        INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE,
        AGENT,
        AGENT,
    )


def validate_exited_validators_per_day_limit_event(event: EventDict, value: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "ExitedValidatorsPerDayLimitSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ExitedValidatorsPerDayLimitSet") == 1

    assert event["ExitedValidatorsPerDayLimitSet"]["exitedValidatorsPerDayLimit"] == value


def validate_appeared_validators_limit_event(event: EventDict, value: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "AppearedValidatorsPerDayLimitSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("AppearedValidatorsPerDayLimitSet") == 1

    assert event["AppearedValidatorsPerDayLimitSet"]["appearedValidatorsPerDayLimit"] == value


def validate_initial_slashing_and_penalties_event(event: EventDict, value: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "InitialSlashingAmountSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("InitialSlashingAmountSet") == 1

    assert event["InitialSlashingAmountSet"]["initialSlashingAmountPWei"] == value
