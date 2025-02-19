"""
Vote 19/02/2025 Holesky!!

I. Pre-pectra upgrade
1. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle 0x4E97A3972ce8511D87F334dA17a2C332542a5246 to Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d
2. Update Accounting Oracle0x4E97A3972ce8511D87F334dA17a2C332542a5246 consensus version to 3
3. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle0x4E97A3972ce8511D87F334dA17a2C332542a5246 from Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d
4. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb to Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d
5. Update Validator Exit Bus Oracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb consensus version to 3
6. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb from Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d
7. Grant MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee to Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d
8. Update CSFeeOracle  0xaF57326C7d513085051b50912D51809ECC5d98Ee consensus version to 2
9. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee from Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d
10. Revoke VERIFIER_ROLE role on CSModule 0x4562c3e63c2e586cD1651B958C22F88135aCAd4f from old CS Verifier 0x6FDAA094227CF8E1593f9fB9C1b867C1f846F916
11. Grant VERIFIER_ROLE role on CSModule 0x4562c3e63c2e586cD1651B958C22F88135aCAd4f to new CS Verifier 0xc099dfd61f6e5420e0ca7e84d820daad17fc1d44

II. Extend On-Chain Voting Duration
12. Grant UNSAFELY_MODIFY_VOTE_TIME_ROLE to Aragon Voting0xdA7d2573Df555002503F29aA4003e398d28cc00f.
13. Change Vote time from 900 to 1080 on Aragon Voting 0xdA7d2573Df555002503F29aA4003e398d28cc00f
14. Change Objection Phase time from 300 to 360 on Aragon Voting 0xdA7d2573Df555002503F29aA4003e398d28cc00f
15. Revoke UNSAFELY_MODIFY_VOTE_TIME_ROLE from Aragon Voting  0xdA7d2573Df555002503F29aA4003e398d28cc00f.
16. Grant CONFIG_MANAGER_ROLE on OracleDaemonConfig 0xC01fC1F2787687Bc656EAc0356ba9Db6e6b7afb7 to Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d
17. Update the FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT parameter in the OracleDaemonConfig contract  0xC01fC1F2787687Bc656EAc0356ba9Db6e6b7afb7 to 0x08CA (2250)
18. Revoke CONFIG_MANAGER_ROLE on OracleDaemonConfig 0xC01fC1F2787687Bc656EAc0356ba9Db6e6b7afb7 from Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d

III. Change GateSeal on WithdrawalQueue and ValidatorsExitBusOracle
19. Grant PAUSE_ROLE on WithdrawalQueue 0xc7cc160b58F8Bb0baC94b80847E2CF2800565C50 for the new GateSeal 0xAE6eCd77DCC656c5533c4209454Fd56fB46e1778
20. Grant PAUSE_ROLE on ValidatorsExitBusOracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb for the new GateSeal 0xAE6eCd77DCC656c5533c4209454Fd56fB46e1778
21. Revoke PAUSE_ROLE on WithdrawalQueue 0xc7cc160b58F8Bb0baC94b80847E2CF2800565C50 from the old GateSeal 0xA34d620EA9F3e86bf8B8a7699B4dE44CD9D3202d
22. Revoke PAUSE_ROLE on ValidatorsExitBusOracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb from the old GateSeal 0xA34d620EA9F3e86bf8B8a7699B4dE44CD9D3202d

IV. Change CSM GateSeal
23. Grant PAUSE_ROLE on CSModule 0x4562c3e63c2e586cD1651B958C22F88135aCAd4f for the new CSM GateSeal 0xf1C03536dbC77B1bD493a2D1C0b1831Ea78B540a
24. Grant PAUSE_ROLE on CSAccounting 0xc093e53e8F4b55A223c18A2Da6fA00e60DD5EFE1 for the new CSM GateSeal 0xf1C03536dbC77B1bD493a2D1C0b1831Ea78B540a
25. Grant PAUSE_ROLE on CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee for the new CSM GateSeal 0xf1C03536dbC77B1bD493a2D1C0b1831Ea78B540a
26. Revoke PAUSE_ROLE on CSModule 0x4562c3e63c2e586cD1651B958C22F88135aCAd4f from the old CSM GateSeal 0x41F2677fae0222cF1f08Cd1c0AAa607B469654Ce
27. Revoke PAUSE_ROLE on CSAccounting 0xc093e53e8F4b55A223c18A2Da6fA00e60DD5EFE1 from the old CSM GateSeal 0x41F2677fae0222cF1f08Cd1c0AAa607B469654Ce
28. Revoke PAUSE_ROLE on CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee from the old CSM GateSeal 0x41F2677fae0222cF1f08Cd1c0AAa607B469654Ce

V. Add Easy Track setups for funding Lido Ecosystem & Lido Labs BORG Foundations’ Operational Funds Multisigs
29. Add a top-up EVM script factory for stablecoins 0x167caEDde0F3230eB18763270B11c970409F389e to Easy Track to fund the Lido Ecosystem BORG's Ops multisig (AllowedRecipientsRegistry 0x0214CEBDEc06dc2729382860603d01113F068388)
30. Add a top-up EVM script factory for stETH 0x4F2dA002a7bD5F7C63B62d4C9e4b762c689Dd8Ac to Easy Track to fund the Lido Ecosystem BORG's Ops multisig (AllowedRecipientsRegistry 0x193d0bA65cf3a2726e12c5568c068D1B3ea51740)
31. Add a top-up EVM script factory for stablecoins 0xf7304738E9d4F572b909FaEd32504F558E234cdB to Easy Track to fund the Lido Labs BORG's Ops multisig (AllowedRecipientsRegistry 0x303F5b60e3cf6Ea11d8509A1546401e311A13B92)
32. Add a top-up EVM script factory for stETH 0xef0Df040B76252cC7fa31a5fc2f36e85c1C8c4f9 to Easy Track to fund the Lido Labs BORG's Ops multisig (AllowedRecipientsRegistry 0x02CD05c1cBa16113680648a8B3496A5aE312a935)
"""

import time

try:
    from brownie import interface, accounts, convert
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


from typing import Dict, Tuple, Optional
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
    CS_VERIFIER_ADDRESS_OLD,
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import (
    encode_oz_grant_role,
    encode_oz_revoke_role,
    encode_permission_grant,
    encode_permission_revoke,
    encode_permission_create,
)
from utils.easy_track import (
    add_evmscript_factory,
)
from utils.allowed_recipients_registry import (
    create_top_up_allowed_recipient_permission,
)
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.mainnet_fork import pass_and_exec_dao_vote


# Consensus version

AO_CONSENSUS_VERSION = 3
VEBO_CONSENSUS_VERSION = 3
CS_FEE_ORACLE_CONSENSUS_VERSION = 2

# Vote duration
NEW_VOTE_DURATION = 1080
NEW_OBJECTION_PHASE_DURATION = 360

#
FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE = 2250

# GateSeals
OLD_GATE_SEAL = "0xA34d620EA9F3e86bf8B8a7699B4dE44CD9D3202d"
NEW_GATE_SEAL = "0xAE6eCd77DCC656c5533c4209454Fd56fB46e1778"

# CSM GateSeals
OLD_CSM_GATE_SEAL = "0x41F2677fae0222cF1f08Cd1c0AAa607B469654Ce"
NEW_CSM_GATE_SEAL = "0xf1C03536dbC77B1bD493a2D1C0b1831Ea78B540a"

ECOSYSTEM_BORG_STABLE_FACTORY = "0x167caEDde0F3230eB18763270B11c970409F389e"
ECOSYSTEM_BORG_STABLE_REGISTRY = "0x0214CEBDEc06dc2729382860603d01113F068388"
ECOSYSTEM_BORG_STETH_FACTORY = "0x4F2dA002a7bD5F7C63B62d4C9e4b762c689Dd8Ac"
ECOSYSTEM_BORG_STETH_REGISTRY = "0x193d0bA65cf3a2726e12c5568c068D1B3ea51740"
LABS_BORG_STABLE_FACTORY = "0xf7304738E9d4F572b909FaEd32504F558E234cdB"
LABS_BORG_STABLE_REGISTRY = "0x303F5b60e3cf6Ea11d8509A1546401e311A13B92"
LABS_BORG_STETH_FACTORY = "0xef0Df040B76252cC7fa31a5fc2f36e85c1C8c4f9"
LABS_BORG_STETH_REGISTRY = "0x02CD05c1cBa16113680648a8B3496A5aE312a935"

description = """
1. **Pectra Hardfork Compatibility** (Items 1-11)
Changes include adjustments to oracle algorithms, Oracle Report Sanity Checker limits, and the CS Verifier.
Approved on [Snapshot](https://snapshot.box/#/s:lido-snapshot.eth).


2. **On-Chain Voting Duration Extension** (Items 12-28)
As approved on [Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xa58da73cc4257837ae981d8ad861252f4cbbda7a173a577702f8f93561f57825), the voting periods will be extended:
- **Main phase**: 48h → 72h
- **Objection phase**: 24h → 48h

To align with these changes, **GateSeal** (used for pausing the **WithdrawalQueue** and **ValidatorExitBusOracle** contracts) and **CSM GateSeal** will be updated while maintaining the same configuration. The new versions will expire on **March 1, 2026**.
**Statemind.io** audited the [initial Factory and Blueprint](https://github.com/lidofinance/audits/?tab=readme-ov-file#04-2023-statemind-gateseals-audit) and [verified](https://research.lido.fi/) that the updated GateSeal matches the Blueprint and has the correct parameters.

3. Easy Track Setups for Lido Ecosystem & Lido Labs BORG Foundations (Items 29-32)
Deploy new **Easy Track factories** for BORGs ([Ecosystem BORG](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x7f72f12d72643c20cd0455c603d344050248e75ed1074c8391fae4c30f09ca15), [Labs BORG](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xdf648307e68415e7b5cf96c6afbabd696c1731839f4b4a7cf5cb7efbc44ee9d6)) to streamline operations. Factories [details here](https://research.lido.fi/).
"""


def encode_ao_set_consensus_version() -> Tuple[str, str]:
    proxy = contracts.accounting_oracle
    return proxy.address, proxy.setConsensusVersion.encode_input(AO_CONSENSUS_VERSION)


def encode_vebo_set_consensus_version() -> Tuple[str, str]:
    proxy = contracts.validators_exit_bus_oracle
    return proxy.address, proxy.setConsensusVersion.encode_input(VEBO_CONSENSUS_VERSION)


def encode_cs_fee_oracle_set_consensus_version() -> Tuple[str, str]:
    proxy = contracts.cs_fee_oracle
    return proxy.address, proxy.setConsensusVersion.encode_input(CS_FEE_ORACLE_CONSENSUS_VERSION)


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        # Pre-pectra upgrade
        (
            "1. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle 0x4E97A3972ce8511D87F334dA17a2C332542a5246 to Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.accounting_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "2. Update Accounting Oracle 0x4E97A3972ce8511D87F334dA17a2C332542a5246 consensus version to 3",
            agent_forward([encode_ao_set_consensus_version()]),
        ),
        (
            "3. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle 0x4E97A3972ce8511D87F334dA17a2C332542a5246 from Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.accounting_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "4. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb to Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "5. Update Validator Exit Bus Oracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb consensus version to 3",
            agent_forward([encode_vebo_set_consensus_version()]),
        ),
        (
            "6. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb from Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "7. Grant MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee to Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.cs_fee_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "8. Update CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee consensus version to 2",
            agent_forward([encode_cs_fee_oracle_set_consensus_version()]),
        ),
        (
            "9. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee from Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.cs_fee_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "10. Revoke VERIFIER_ROLE role on CSModule 0x4562c3e63c2e586cD1651B958C22F88135aCAd4f from old CS Verifier 0x6FDAA094227CF8E1593f9fB9C1b867C1f846F916",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.csm,
                        role_name="VERIFIER_ROLE",
                        revoke_from=CS_VERIFIER_ADDRESS_OLD,
                    )
                ]
            ),
        ),
        (
            "11. Grant VERIFIER_ROLE role on CSModule 0x4562c3e63c2e586cD1651B958C22F88135aCAd4f to new CS Verifier 0xc099dfd61f6e5420e0ca7e84d820daad17fc1d44",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.csm,
                        role_name="VERIFIER_ROLE",
                        grant_to=contracts.cs_verifier,
                    )
                ]
            ),
        ),
        # Extend On-Chain Voting Duration
        (
            "12. Grant UNSAFELY_MODIFY_VOTE_TIME_ROLE to Aragon Voting 0xdA7d2573Df555002503F29aA4003e398d28cc00f",
            encode_permission_grant(
                target_app=contracts.voting,
                permission_name="UNSAFELY_MODIFY_VOTE_TIME_ROLE",
                grant_to=contracts.voting,
            ),
        ),
        (
            "13. Change Vote time from 900 to 1080 on Aragon Voting 0xdA7d2573Df555002503F29aA4003e398d28cc00f",
            (
                contracts.voting.address,
                contracts.voting.unsafelyChangeVoteTime.encode_input(NEW_VOTE_DURATION),
            ),
        ),
        (
            "14. Change Objection Phase time from 300 to 360 on Aragon Voting 0xdA7d2573Df555002503F29aA4003e398d28cc00f",
            (
                contracts.voting.address,
                contracts.voting.unsafelyChangeObjectionPhaseTime.encode_input(NEW_OBJECTION_PHASE_DURATION),
            ),
        ),
        (
            "15. Revoke UNSAFELY_MODIFY_VOTE_TIME_ROLE from Aragon Voting 0xdA7d2573Df555002503F29aA4003e398d28cc00f",
            encode_permission_revoke(
                target_app=contracts.voting,
                permission_name="UNSAFELY_MODIFY_VOTE_TIME_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "16. Grant CONFIG_MANAGER_ROLE on OracleDaemonConfig 0xC01fC1F2787687Bc656EAc0356ba9Db6e6b7afb7 to Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.oracle_daemon_config,
                        role_name="CONFIG_MANAGER_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "17. Update the FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT parameter in the OracleDaemonConfig contract 0xC01fC1F2787687Bc656EAc0356ba9Db6e6b7afb7 to 0x08CA (2250)",
            agent_forward(
                [
                    (
                        contracts.oracle_daemon_config.address,
                        contracts.oracle_daemon_config.update.encode_input(
                            "FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT",
                            convert.to_bytes(FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE),
                        ),
                    )
                ]
            ),
        ),
        (
            "18. Revoke CONFIG_MANAGER_ROLE on OracleDaemonConfig 0xC01fC1F2787687Bc656EAc0356ba9Db6e6b7afb7 from Aragon Agent 0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.oracle_daemon_config,
                        role_name="CONFIG_MANAGER_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        # Change GateSeal on WithdrawalQueue and ValidatorsExitBusOracle
        (
            "19. Grant PAUSE_ROLE on WithdrawalQueue 0xc7cc160b58F8Bb0baC94b80847E2CF2800565C50 to the new GateSeal 0xAE6eCd77DCC656c5533c4209454Fd56fB46e1778",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.withdrawal_queue,
                        role_name="PAUSE_ROLE",
                        grant_to=NEW_GATE_SEAL,
                    )
                ]
            ),
        ),
        (
            "20. Grant PAUSE_ROLE on ValidatorsExitBusOracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb to the new GateSeal 0xAE6eCd77DCC656c5533c4209454Fd56fB46e1778",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="PAUSE_ROLE",
                        grant_to=NEW_GATE_SEAL,
                    )
                ]
            ),
        ),
        (
            "21. Revoke PAUSE_ROLE on WithdrawalQueue 0xc7cc160b58F8Bb0baC94b80847E2CF2800565C50 from the old GateSeal 0xA34d620EA9F3e86bf8B8a7699B4dE44CD9D3202d",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.withdrawal_queue,
                        role_name="PAUSE_ROLE",
                        revoke_from=OLD_GATE_SEAL,
                    )
                ]
            ),
        ),
        (
            "22. Revoke PAUSE_ROLE on ValidatorsExitBusOracle 0xffDDF7025410412deaa05E3E1cE68FE53208afcb from the old GateSeal 0xA34d620EA9F3e86bf8B8a7699B4dE44CD9D3202d",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="PAUSE_ROLE",
                        revoke_from=OLD_GATE_SEAL,
                    )
                ]
            ),
        ),
        # Change CSM GateSeals
        (
            "23. Grant PAUSE_ROLE on CSModule 0x4562c3e63c2e586cD1651B958C22F88135aCAd4f to the new CSM GateSeal 0xf1C03536dbC77B1bD493a2D1C0b1831Ea78B540a",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.csm,
                        role_name="PAUSE_ROLE",
                        grant_to=NEW_CSM_GATE_SEAL,
                    )
                ]
            ),
        ),
        (
            "24. Grant PAUSE_ROLE on CSAccounting 0xc093e53e8F4b55A223c18A2Da6fA00e60DD5EFE1 to the new CSM GateSeal 0xf1C03536dbC77B1bD493a2D1C0b1831Ea78B540a",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.cs_accounting,
                        role_name="PAUSE_ROLE",
                        grant_to=NEW_CSM_GATE_SEAL,
                    )
                ]
            ),
        ),
        (
            "25. Grant PAUSE_ROLE on CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee to the new CSM GateSeal 0xf1C03536dbC77B1bD493a2D1C0b1831Ea78B540a",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.cs_fee_oracle,
                        role_name="PAUSE_ROLE",
                        grant_to=NEW_CSM_GATE_SEAL,
                    )
                ]
            ),
        ),
        (
            "26. Revoke PAUSE_ROLE on CSModule 0x4562c3e63c2e586cD1651B958C22F88135aCAd4f from the old CSM GateSeal 0x41F2677fae0222cF1f08Cd1c0AAa607B469654Ce",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.csm,
                        role_name="PAUSE_ROLE",
                        revoke_from=OLD_CSM_GATE_SEAL,
                    )
                ]
            ),
        ),
        (
            "27. Revoke PAUSE_ROLE on CSAccounting 0xc093e53e8F4b55A223c18A2Da6fA00e60DD5EFE1 from the old CSM GateSeal 0x41F2677fae0222cF1f08Cd1c0AAa607B469654Ce",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.cs_accounting,
                        role_name="PAUSE_ROLE",
                        revoke_from=OLD_CSM_GATE_SEAL,
                    )
                ]
            ),
        ),
        (
            "28. Revoke PAUSE_ROLE on CSFeeOracle 0xaF57326C7d513085051b50912D51809ECC5d98Ee from the old CSM GateSeal 0x41F2677fae0222cF1f08Cd1c0AAa607B469654Ce",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.cs_fee_oracle,
                        role_name="PAUSE_ROLE",
                        revoke_from=OLD_CSM_GATE_SEAL,
                    )
                ]
            ),
        ),
        # EasyTrack factories
        (
            "29. Add a top-up EVM script factory for stablecoins 0x167caEDde0F3230eB18763270B11c970409F389e to Easy Track to fund the Lido Ecosystem BORG's Ops multisig (AllowedRecipientsRegistry 0x0214CEBDEc06dc2729382860603d01113F068388)",
            add_evmscript_factory(
                factory=ECOSYSTEM_BORG_STABLE_FACTORY,
                permissions=create_top_up_allowed_recipient_permission(registry_address=ECOSYSTEM_BORG_STABLE_REGISTRY),
            ),
        ),
        (
            "30. Add a top-up EVM script factory for stETH 0x4F2dA002a7bD5F7C63B62d4C9e4b762c689Dd8Ac to Easy Track to fund the Lido Ecosystem BORG's Ops multisig (AllowedRecipientsRegistry 0x193d0bA65cf3a2726e12c5568c068D1B3ea51740)",
            add_evmscript_factory(
                factory=ECOSYSTEM_BORG_STETH_FACTORY,
                permissions=create_top_up_allowed_recipient_permission(registry_address=ECOSYSTEM_BORG_STETH_REGISTRY),
            ),
        ),
        (
            "31. Add a top-up EVM script factory for stablecoins 0xf7304738E9d4F572b909FaEd32504F558E234cdB to Easy Track to fund the Lido Labs BORG's Ops multisig (AllowedRecipientsRegistry 0x303F5b60e3cf6Ea11d8509A1546401e311A13B92)",
            add_evmscript_factory(
                factory=LABS_BORG_STABLE_FACTORY,
                permissions=create_top_up_allowed_recipient_permission(registry_address=LABS_BORG_STABLE_REGISTRY),
            ),
        ),
        (
            "32. Add a top-up EVM script factory for stETH 0xef0Df040B76252cC7fa31a5fc2f36e85c1C8c4f9 to Easy Track to fund the Lido Labs BORG's Ops multisig (AllowedRecipientsRegistry 0x02CD05c1cBa16113680648a8B3496A5aE312a935)",
            add_evmscript_factory(
                factory=LABS_BORG_STETH_FACTORY,
                permissions=create_top_up_allowed_recipient_permission(registry_address=LABS_BORG_STETH_REGISTRY),
            ),
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.


def start_and_execute_vote_on_fork():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id))
