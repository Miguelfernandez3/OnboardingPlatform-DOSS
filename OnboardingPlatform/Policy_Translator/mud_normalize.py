"""
MUD JSON shape normalization for translate pipeline.
Kept dependency-free (copy only) so tests can run without pyangbind/mspl.
"""
import copy

IETF_MUD_KEY = "ietf-mud:mud"
IETF_ACLS_KEY = "ietf-access-control-list:acls"


def normalize_mud_for_translate(mud):
    """
    Promote ietf-access-control-list:acls from inside ietf-mud:mud to root
    so translate() finds the same shape as RFC MUD (sibling of ietf-mud:mud).
    Deep-copies to avoid mutating caller's dict.
    """
    if not isinstance(mud, dict):
        return mud
    inner = mud.get(IETF_MUD_KEY)
    if not isinstance(inner, dict) or IETF_ACLS_KEY not in inner:
        return mud
    out = copy.deepcopy(mud)
    inner_out = out[IETF_MUD_KEY]
    out[IETF_ACLS_KEY] = inner_out.pop(IETF_ACLS_KEY)
    return out
