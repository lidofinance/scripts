"""
I. Extend On-Chain Voting Duration
1. Grant UNSAFELY_MODIFY_VOTE_TIME_ROLE to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
2. Change Vote time from 259200 to 432000 on Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
3. Change Objection Phase time from 86400 to 172800 on Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
4. Revoke UNSAFELY_MODIFY_VOTE_TIME_ROLE from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
5. Grant CONFIG_MANAGER_ROLE on OracleDaemonConfig 0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09 to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
6. Update the FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT parameter in the OracleDaemonConfig contract  0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09 to 0x08CA (2250 epochs)
7. Revoke CONFIG_MANAGER_ROLE on OracleDaemonConfig 0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c

II. Change GateSeal on WithdrawalQueue and ValidatorsExitBusOracle
8. Grant PAUSE_ROLE on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 for the new GateSeal 0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178
9. Grant PAUSE_ROLE on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e for the new GateSeal 0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178
10. Revoke PAUSE_ROLE on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 from the old GateSeal 0x79243345eDbe01A7E42EDfF5900156700d22611c
11. Revoke PAUSE_ROLE on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e from the old GateSeal 0x79243345eDbe01A7E42EDfF5900156700d22611c

III. Change CSM GateSeal
12. Grant PAUSE_ROLE on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F for the new CSM GateSeal 0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0
13. Grant PAUSE_ROLE on CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da for the new CSM GateSeal 0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0
14. Grant PAUSE_ROLE on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB for the new CSM GateSeal 0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0
15. Revoke PAUSE_ROLE on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F from the old CSM GateSeal 0x5cFCa30450B1e5548F140C24A47E36c10CE306F0
16. Revoke PAUSE_ROLE on CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da from the old CSM GateSeal 0x5cFCa30450B1e5548F140C24A47E36c10CE306F0
17. Revoke PAUSE_ROLE on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB from the old CSM GateSeal 0x5cFCa30450B1e5548F140C24A47E36c10CE306F0

IV. Add Easy Track setups for funding Lido Ecosystem & Lido Labs BORGs’ Operational Expenses Multisigs
18. Add an Easy Track EVM script factory 0xf2476f967C826722F5505eDfc4b2561A34033477 for funding the Lido Ecosystem BORG’s operational multisig (AllowedRecipientsRegistry 0xDAdC4C36cD8F468A398C25d0D8aaf6A928B47Ab4)
19. Add an Easy Track EVM script factory 0xE1f6BaBb445F809B97e3505Ea91749461050F780 for funding the Lido Labs BORG’s operational multisig (AllowedRecipientsRegistry 0x68267f3D310E9f0FF53a37c141c90B738E1133c2)
"""

import time

try:
    from brownie import convert
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")

from typing import Dict, Tuple, Optional
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)
from utils.permissions import (
    encode_oz_grant_role,
    encode_oz_revoke_role,
    encode_permission_grant,
    encode_permission_revoke,
)
from utils.easy_track import (
    add_evmscript_factory,
)
from utils.allowed_recipients_registry import (
    create_top_up_allowed_recipient_permission,
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.mainnet_fork import pass_and_exec_dao_vote


description = """1. **Extend On-Chain Voting Duration** (Items 1-17)  
As approved on [Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xa58da73cc4257837ae981d8ad861252f4cbbda7a173a577702f8f93561f57825):
- **Main phase**: 48h → 72h
- **Objection phase**: 24h → 48h

To align with these changes, **GateSeal** (pausing the [WithdrawalQueue](https://etherscan.io/address/0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1) and [ValidatorExitBusOracle](https://etherscan.io/address/0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e)) and **CSM GateSeal** (pausing the [CSModule](https://etherscan.io/address/0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F), [CSAccounting](https://etherscan.io/address/0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da), and [CSFeeOracle](https://etherscan.io/address/0x4D4074628678Bd302921c20573EEa1ed38DdF7FB)) will be updated with the same configuration, except for extending the duration from 6 to 11 days. The new versions will expire on **March 1, 2026**.
**Statemind.io** audited the [initial Factory and Blueprint](https://github.com/lidofinance/audits/?tab=readme-ov-file#04-2023-statemind-gateseals-audit) and [verified](https://github.com/lidofinance/audits/blob/main/Statemind%20GateSeal%20Deployment%20Validation%2003-2025.pdf) that the updated GateSeal contracts match the Blueprint and have the correct parameters.

2. **Deploy Easy Track Factories for Lido Ecosystem & Lido Labs BORG Foundations to streamline operational funding** (Items 18, 19)

Snapshot proposals & contract details:
- [Lido Ecosystem Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x7f72f12d72643c20cd0455c603d344050248e75ed1074c8391fae4c30f09ca15) | [Configuration](https://research.lido.fi/t/establishment-of-lido-ecosystem-borg-foundation-as-a-lido-dao-adjacent-foundation/9345/15) | security limit $5M per quarter
- [Lido Labs Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xdf648307e68415e7b5cf96c6afbabd696c1731839f4b4a7cf5cb7efbc44ee9d6) | [Configuration](https://research.lido.fi/t/establishment-of-lido-labs-borg-foundation-as-a-lido-dao-adjacent-foundation/9344/18) | security limit $18M per quarter"""

# Vote duration
NEW_VOTE_DURATION = 432000
NEW_OBJECTION_PHASE_DURATION = 172800

# Oracle daemon config
FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE = 2250

# GateSeals
OLD_GATE_SEAL = "0x79243345eDbe01A7E42EDfF5900156700d22611c"
NEW_GATE_SEAL = "0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178"

# CSM GateSeals
OLD_CSM_GATE_SEAL = "0x5cFCa30450B1e5548F140C24A47E36c10CE306F0"
NEW_CSM_GATE_SEAL = "0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0"

# EasyTrack factories
ECOSYSTEM_BORG_STABLE_FACTORY = "0xf2476f967C826722F5505eDfc4b2561A34033477"
ECOSYSTEM_BORG_STABLE_REGISTRY = "0xDAdC4C36cD8F468A398C25d0D8aaf6A928B47Ab4"
LABS_BORG_STABLE_FACTORY = "0xE1f6BaBb445F809B97e3505Ea91749461050F780"
LABS_BORG_STABLE_REGISTRY = "0x68267f3D310E9f0FF53a37c141c90B738E1133c2"


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        # Extend On-Chain Voting Duration
        (
            "1. Grant UNSAFELY_MODIFY_VOTE_TIME_ROLE to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            encode_permission_grant(
                target_app=contracts.voting,
                permission_name="UNSAFELY_MODIFY_VOTE_TIME_ROLE",
                grant_to=contracts.voting,
            ),
        ),
        (
            "2. Change Vote time from 259200 to 432000 on Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            (
                contracts.voting.address,
                contracts.voting.unsafelyChangeVoteTime.encode_input(NEW_VOTE_DURATION),
            ),
        ),
        (
            "3. Change Objection Phase time from 86400 to 172800 on Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            (
                contracts.voting.address,
                contracts.voting.unsafelyChangeObjectionPhaseTime.encode_input(NEW_OBJECTION_PHASE_DURATION),
            ),
        ),
        (
            "4. Revoke UNSAFELY_MODIFY_VOTE_TIME_ROLE from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            encode_permission_revoke(
                target_app=contracts.voting,
                permission_name="UNSAFELY_MODIFY_VOTE_TIME_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "5. Grant CONFIG_MANAGER_ROLE on OracleDaemonConfig 0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09 to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
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
            "6. Update the FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT parameter in the OracleDaemonConfig contract 0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09 to 0x08CA (2250 epochs)",
            agent_forward(
                [
                    (
                        contracts.oracle_daemon_config.address,
                        contracts.oracle_daemon_config.update.encode_input(
                            "FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT",
                            convert.to_bytes(FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE, 'bytes'),
                        ),
                    )
                ]
            ),
        ),
        (
            "7. Revoke CONFIG_MANAGER_ROLE on OracleDaemonConfig 0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
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
        (
            "8. Grant PAUSE_ROLE on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 for the new GateSeal 0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178",
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
            "9. Grant PAUSE_ROLE on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e for the new GateSeal 0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178",
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
            "10. Revoke PAUSE_ROLE on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 from the old GateSeal 0x79243345eDbe01A7E42EDfF5900156700d22611c",
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
            "11. Revoke PAUSE_ROLE on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e from the old GateSeal 0x79243345eDbe01A7E42EDfF5900156700d22611c",
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
            "12. Grant PAUSE_ROLE on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F for the new CSM GateSeal 0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0",
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
            "13. Grant PAUSE_ROLE on CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da for the new CSM GateSeal 0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0",
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
            "14. Grant PAUSE_ROLE on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB for the new CSM GateSeal 0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0",
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
            "15. Revoke PAUSE_ROLE on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F from the old CSM GateSeal 0x5cFCa30450B1e5548F140C24A47E36c10CE306F0",
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
            "16. Revoke PAUSE_ROLE on CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da from the old CSM GateSeal 0x5cFCa30450B1e5548F140C24A47E36c10CE306F0",
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
            "17. Revoke PAUSE_ROLE on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB from the old CSM GateSeal 0x5cFCa30450B1e5548F140C24A47E36c10CE306F0",
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
            "18. Add an Easy Track EVM script factory 0xf2476f967C826722F5505eDfc4b2561A34033477 for funding the Lido Ecosystem BORG Foundation’s operational multisig (AllowedRecipientsRegistry 0xDAdC4C36cD8F468A398C25d0D8aaf6A928B47Ab4)",
            add_evmscript_factory(
                factory=ECOSYSTEM_BORG_STABLE_FACTORY,
                permissions=create_top_up_allowed_recipient_permission(registry_address=ECOSYSTEM_BORG_STABLE_REGISTRY),
            ),
        ),
        (
            "19. Add an Easy Track EVM script factory 0xE1f6BaBb445F809B97e3505Ea91749461050F780 for funding the Lido Labs BORG Foundation’s operational multisig (AllowedRecipientsRegistry 0x68267f3D310E9f0FF53a37c141c90B738E1133c2)",
            add_evmscript_factory(
                factory=LABS_BORG_STABLE_FACTORY,
                permissions=create_top_up_allowed_recipient_permission(registry_address=LABS_BORG_STABLE_REGISTRY),
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
