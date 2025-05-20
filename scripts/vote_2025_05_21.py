"""
Voting 21/05/2025

I. Post-pectra upgrade

1. Grant EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
2. Change exitedValidatorsPerDayLimit from 9000 to 3600 on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75`
3. Revoke EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
4. Grant APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
5. Change appearedValidatorsPerDayLimit from 43200 to 1800 on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` 
6. Revoke APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
7. Grant INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
8. Change initialSlashingAmountPWei from 1000 to 8 on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` 
9. Revoke INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`

II. Add Easy Track setup for Managing MEV-Boost Relay Allowed List 
10. Add `AddMEVBoostRelays` EVM script factory `0x00A3D6260f70b1660c8646Ef25D0820EFFd7bE60` to Easy Track
11. Add `RemoveMEVBoostRelays` EVM script factory `0x9721c0f77E3Ea40eD592B9DCf3032DaF269c0306` to Easy Track 
12. Add `EditMEVBoostRelays` EVM script factory `0x6b7863f2c7dEE99D3b744fDAEDbEB1aeCC025535` to Easy Track
13. Set Easy Track's EVM Script Executor `0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977` as manager on the MEV-Boost Relay Allowed List `0xF95f069F9AD107938F6ba802a3da87892298610E`

III. CSM: Reduce keyRemovalCharge
14. Grant MODULE_MANAGER_ROLE on CSModule `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
15. Reduce keyRemovalCharge from 0.05 to 0.02 ETH on CS Module `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F`
16. Revoke MODULE_MANAGER_ROLE on CSModule `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`

IV. Change Easy Track limits for Liquidity Observation Lab (LOL)
17. Increase the limit from 2,100 to 6,000 stETH and extend the duration from 3 to 6 months on LOL AllowedRecipientsRegistry `0x48c4929630099b217136b64089E8543dB0E5163a`
"""

import time
from typing import Dict
from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
    EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
    EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
)
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
)

from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role

# Oracle sanity checker params
NEW_INITIAL_SLASHING_AMOUNT_PWEI = 8
UNCHANGED_INACTIVITY_PENATIES_AMOUNT_PWEI = 101
NEW_EXITED_VALIDATORS_PER_DAY_LIMIT = 3600
NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT = 1800

NEW_KEY_REMOVAL_CHARGE = 0.02 * 1e18

NEW_LOL_LIMIT = 6000 * 1e18  # stETH
NEW_LOL_PERIOD = 6  # months

DESCRIPTION = """Contains separate updates approved by Lido DAO via Snapshot voting:

1. **Post-Pectra update:** adjust Oracle Report Sanity Checker parameters to align with reduced slashing penalty and updated validator churn limits. Items 1-9.
[Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xb6559f0cdb1164ae5d63769827c4a275805bd944392a17b60cf51ddc54429dc6) | Audited by [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20Oracle%20v5%2004-25.pdf)
2. **Add Easy Track Factories** for managing MEV-Boost Relay Allowed List. Items 10-13. 
[Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xf1074ec134595ba8ba6f802c5e505fda32e6ab93e9763d1e43001f439241b7c9) | Audit and deploy verification by [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20RMC%20EasyTrack%20Security%20Audit%20Report%2005-2025.pdf) 
3. **Reduce `keyRemovalCharge`** for the Community Staking Module. Items 14-16. 
[Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xcd1c1a051888efd495d97458ae9fa4fe5198616eb3d92a71d3352d9f25e79c4e) 
4. **Increase Easy Track security limit** for [Liquidity Observation Lab](https://docs.lido.fi/multisigs/committees/#281-liquidity-observation-lab-committee-ethereum) from 2,100&nbsp;stETH per&nbsp;3&nbsp;months to 6,000&nbsp;stETH per&nbsp;6&nbsp;months. Item 17. 
[Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x3ecd09e4c0f22d25c711ca5777c49c22d144385b85dd7f696ca6cc66cc0ca157)
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting"""
    lol_registry = interface.AllowedRecipientRegistry("0x48c4929630099b217136b64089E8543dB0E5163a")

    vote_desc_items, call_script_items = zip(
        (
            "1) Grant EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.oracle_report_sanity_checker,
                        role_name="EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "2) Change exitedValidatorsPerDayLimit from 9000 to 3600 on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75`",
            agent_forward(
                [
                    (
                        contracts.oracle_report_sanity_checker.address,
                        contracts.oracle_report_sanity_checker.setExitedValidatorsPerDayLimit.encode_input(
                            NEW_EXITED_VALIDATORS_PER_DAY_LIMIT
                        ),
                    ),
                ]
            ),
        ),
        (
            "3) Revoke EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.oracle_report_sanity_checker,
                        role_name="EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "4) Grant APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.oracle_report_sanity_checker,
                        role_name="APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "5) Change appearedValidatorsPerDayLimit from 43200 to 1800 on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75`",
            agent_forward(
                [
                    (
                        contracts.oracle_report_sanity_checker.address,
                        contracts.oracle_report_sanity_checker.setAppearedValidatorsPerDayLimit.encode_input(
                            NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT
                        ),
                    ),
                ]
            ),
        ),
        (
            "6) Revoke APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.oracle_report_sanity_checker,
                        role_name="APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "7) Grant INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.oracle_report_sanity_checker,
                        role_name="INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "8) Change initialSlashingAmountPWei from 1000 to 8 on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75`",
            agent_forward(
                [
                    (
                        contracts.oracle_report_sanity_checker.address,
                        contracts.oracle_report_sanity_checker.setInitialSlashingAndPenaltiesAmount.encode_input(
                            NEW_INITIAL_SLASHING_AMOUNT_PWEI,
                            UNCHANGED_INACTIVITY_PENATIES_AMOUNT_PWEI,
                        ),
                    ),
                ]
            ),
        ),
        (
            "9) Revoke INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE on Oracle Report Sanity Checker `0x6232397ebac4f5772e53285b26c47914e9461e75` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.oracle_report_sanity_checker,
                        role_name="INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "10) Add `AddMEVBoostRelay` EVM script factory with address `0x00A3D6260f70b1660c8646Ef25D0820EFFd7bE60` to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
                permissions=create_permissions(contracts.relay_allowed_list, "add_relay"),
            ),
        ),
        (
            "11) Add `RemoveMEVBoostRelay` EVM script factory with address `0x9721c0f77E3Ea40eD592B9DCf3032DaF269c0306` to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
                permissions=create_permissions(contracts.relay_allowed_list, "remove_relay"),
            ),
        ),
        (
            "12) Add `EditMEVBoostRelay` EVM script factory with address `0x6b7863f2c7dEE99D3b744fDAEDbEB1aeCC025535` to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
                permissions=create_permissions(contracts.relay_allowed_list, "add_relay")
                + create_permissions(contracts.relay_allowed_list, "remove_relay")[2:],
            ),
        ),
        (
            "13) Set Easy Track's EVM Script Executor `0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977` as manager on the MEV-Boost Relay Allowed List `0xF95f069F9AD107938F6ba802a3da87892298610E`",
            agent_forward(
                [
                    (
                        contracts.relay_allowed_list.address,
                        contracts.relay_allowed_list.set_manager.encode_input(EASYTRACK_EVMSCRIPT_EXECUTOR),
                    )
                ]
            ),
        ),
        (
            "14) Grant MODULE_MANAGER_ROLE on CSModule `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
            agent_forward([encode_oz_grant_role(contracts.csm, "MODULE_MANAGER_ROLE", contracts.agent)]),
        ),
        (
            "15) Reduce keyRemovalCharge from 0.05 to 0.02 ETH on CS Module `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F`",
            agent_forward(
                [
                    (
                        contracts.csm.address,
                        contracts.csm.setKeyRemovalCharge.encode_input(NEW_KEY_REMOVAL_CHARGE),
                    ),
                ]
            ),
        ),
        (
            "16) Revoke MODULE_MANAGER_ROLE on CSModule `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
            agent_forward([encode_oz_revoke_role(contracts.csm, "MODULE_MANAGER_ROLE", contracts.agent)]),
        ),
        (
            "17) Increase the limit from 2,100 to 6,000 stETH and extend the duration from 3 to 6 months on LOL AllowedRecipientsRegistry `0x48c4929630099b217136b64089E8543dB0E5163a`",
            agent_forward(
                [
                    (
                        lol_registry.address,
                        lol_registry.setLimitParameters.encode_input(
                            NEW_LOL_LIMIT,  # stETH
                            NEW_LOL_PERIOD,  # months
                        ),
                    ),
                ]
            ),
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

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
