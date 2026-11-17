"""
Helpers for normalizing ACL/MUD actions into MSPL filtering actions.
"""


def normalize_filtering_action(action_value):
    """
    Maps ACL forwarding actions to the MSPL enumeration accepted by pyangbind.

    MSPL only accepts: allow, deny, reject.
    MUD/ACL forwarding commonly uses: accept, drop, reject.
    """
    normalized = str(action_value or "accept").strip().lower()
    if normalized in {"accept", "allow", "permit"}:
        return "allow"
    if normalized in {"drop", "deny", "block"}:
        return "deny"
    if normalized == "reject":
        return "reject"
    return normalized
