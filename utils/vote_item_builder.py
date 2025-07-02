from typing import List, Optional, Sequence, Tuple, Dict
from utils.config import contracts, AGENT
from utils.evm_script import encode_call_script

# ──────────────────────────────────────────────────────────────────────────
#  Type Definitions
# ──────────────────────────────────────────────────────────────────────────

# Raw vote action structure
VoteActionDict = Dict[str, str]  # {"type": str, "address": str, "data": str}

# Vote item with description and action
VoteItem = Tuple[str, VoteActionDict]  # (description, action)

# Executable call ready for blockchain execution
ExecutableCall = Tuple[str, str]  # (target_address, encoded_data)

# Final vote structure for execution
ExecutableVoteItems = Dict[str, ExecutableCall]  # {description: (address, data)}

# Proposal action for dual governance
ProposalAction = Tuple[str, int, str]  # (target, value, data)

# ──────────────────────────────────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────────────────────────────────

class ActionType:
    """Vote action types."""
    AGENT = "agent"
    DUAL_GOVERNANCE_ADMIN = "dg_admin"
    DIRECT_VOTING = "voting"

# ──────────────────────────────────────────────────────────────────────────
#  Vote Action Builders
# ──────────────────────────────────────────────────────────────────────────

class VoteAction:
    """Factory for creating different types of vote actions."""

    @staticmethod
    def agent(target_address: str, encoded_data: str) -> VoteActionDict:
        """Create vote action that will be executed through the Agent."""
        return {"type": ActionType.AGENT, "address": target_address, "data": encoded_data}

    @staticmethod
    def admin(target_address: str, encoded_data: str) -> VoteActionDict:
        """Create vote action that will be executed through Dual Governance."""
        return {"type": ActionType.DUAL_GOVERNANCE_ADMIN, "address": target_address, "data": encoded_data}

    @staticmethod
    def voting(target_address: str, encoded_data: str) -> VoteActionDict:
        """Create vote action that will be executed directly by the Voting contract."""
        return {"type": ActionType.DIRECT_VOTING, "address": target_address, "data": encoded_data}

# ──────────────────────────────────────────────────────────────────────────
#  Call Script Encoders
# ──────────────────────────────────────────────────────────────────────────

def encode_agent_forward_call(call_script: Sequence[Tuple[str, str]]) -> ExecutableCall:
    """Encode a call script for Agent forwarding."""
    agent = contracts.agent
    print(f"Encoding agent forward call for script: {call_script}")
    return (AGENT, agent.forward.encode_input(encode_call_script(call_script)))

# ──────────────────────────────────────────────────────────────────────────
#  Vote Items Validation and Aggregation
# ──────────────────────────────────────────────────────────────────────────

def validate_and_aggregate_vote_items(
    vote_items: List[VoteItem]
) -> Tuple[List[str], List[VoteActionDict]]:
    """
    Validates vote items ordering and separates descriptions from actions.

    Validation rule: Direct voting actions must appear either before all other
    actions or after all other actions (not interleaved).
    """
    descriptions: List[str] = []
    actions: List[VoteActionDict] = []
    action_types: List[str] = []

    for description, action in vote_items:
        descriptions.append(description)
        actions.append(action)
        action_types.append(action["type"])

    # Find the boundaries of non-voting actions
    first_non_voting_index = next(
        (i for i, action_type in enumerate(action_types) if action_type != ActionType.DIRECT_VOTING),
        len(action_types)
    )
    last_non_voting_index = (
        len(action_types) - 1 - next(
            (i for i, action_type in enumerate(reversed(action_types)) if action_type != ActionType.DIRECT_VOTING),
            len(action_types)
        )
    )

    # Check if voting actions are interleaved with non-voting actions
    interleaved_voting_actions = action_types[first_non_voting_index:last_non_voting_index + 1]
    if any(action_type == ActionType.DIRECT_VOTING for action_type in interleaved_voting_actions):
        raise ValueError(
            "Direct voting actions can only appear before all other actions or after them, not interleaved"
        )

    return descriptions, actions

# ──────────────────────────────────────────────────────────────────────────
#  Vote Items Categorization
# ──────────────────────────────────────────────────────────────────────────

def categorize_vote_actions(
    descriptions: List[str],
    actions: List[VoteActionDict]
) -> Tuple[List[VoteItem], List[VoteItem]]:
    """
    Categorizes vote actions into two groups:

    1. Actions for Agent/Dual Governance execution
    2. Actions for direct voting execution
    """
    agent_dg_actions: List[VoteItem] = []
    direct_voting_actions: List[VoteItem] = []

    for description, action in zip(descriptions, actions):
        if action["type"] == ActionType.DIRECT_VOTING:
            direct_voting_actions.append((description, action))
        else:
            agent_dg_actions.append((description, action))

    return agent_dg_actions, direct_voting_actions

# ──────────────────────────────────────────────────────────────────────────
#  Main Vote Processing Pipeline
# ──────────────────────────────────────────────────────────────────────────

def build_executable_vote_items(
    vote_items: List[VoteItem]
) -> ExecutableVoteItems:
    """
    Main pipeline that processes vote items and builds executable vote structure.

    Returns a dictionary where keys are descriptions and values are (address, data) tuples
    ready for execution.
    """
    descriptions, actions = validate_and_aggregate_vote_items(vote_items)

    agent_dg_actions, direct_voting_actions = categorize_vote_actions(descriptions, actions)

    # Build the final vote structure
    executable_vote_items: ExecutableVoteItems = {}

    # Process direct voting actions
    for description, action in direct_voting_actions:
        executable_vote_items[description] = (action["address"], action["data"])

    # Process agent/dual governance actions if any exist
    if agent_dg_actions:
        combined_description = "\n".join(desc for desc, _ in agent_dg_actions)
        combined_actions = [action for _, action in agent_dg_actions]

        dual_governance_call = encode_dual_governance_proposal(
            combined_actions,
            combined_description
        )
        executable_vote_items[combined_description] = dual_governance_call

    return executable_vote_items

def encode_dual_governance_proposal(
    actions: Sequence[VoteActionDict],
    description: Optional[str] = "",
) -> ExecutableCall:
    """
    Encodes a sequence of actions into a dual governance proposal.
    """
    dual_governance = contracts.dual_governance
    proposal_actions: List[ProposalAction] = []

    for action in actions:
        print(f"Processing action for dual governance: {action}")

        if action["type"] == ActionType.DUAL_GOVERNANCE_ADMIN:
            # Direct dual governance admin action
            target_address, encoded_data = action["address"], action["data"]
            proposal_actions.append((target_address, 0, encoded_data))
        elif action["type"] == ActionType.AGENT:
            # Agent forwarded action
            agent_call = [(action["address"], action["data"])]
            agent_address, agent_data = encode_agent_forward_call(agent_call)
            proposal_actions.append((agent_address, 0, agent_data))

    print(f"Submitting proposal to dual governance with actions: {proposal_actions}")
    return (
        contracts.dual_governance.address,
        dual_governance.submitProposal.encode_input(proposal_actions, description),
    )
