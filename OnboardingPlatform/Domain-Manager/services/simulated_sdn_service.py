"""
Helpers for compiling Filtering_L4 MSPL policies into simulated iptables commands.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Iterable, List, Optional


class SimulatedSDNService:
    """Compiles MSPL filtering policies into human-readable iptables/ip6tables commands."""

    PLACEHOLDER_BY_HINT = {
        "mycontroller": "<MY_CONTROLLER>",
        "localnetworks": "<LOCAL_NETWORKS>",
        "samemanufacturer": "<SAME_MANUFACTURER>",
    }

    @staticmethod
    def _normalize_tag(tag: str) -> str:
        return str(tag or "").split("}", 1)[-1].replace("-", "").replace("_", "").lower()

    def _child_text(self, node: Optional[ET.Element], candidates: Iterable[str]) -> Optional[str]:
        if node is None:
            return None
        normalized = {candidate.replace("-", "").replace("_", "").lower() for candidate in candidates}
        for child in list(node):
            if self._normalize_tag(child.tag) in normalized:
                text = (child.text or "").strip()
                if text:
                    return text
        return None

    def _first_descendant(self, node: Optional[ET.Element], candidates: Iterable[str]) -> Optional[ET.Element]:
        if node is None:
            return None
        normalized = {candidate.replace("-", "").replace("_", "").lower() for candidate in candidates}
        for descendant in node.iter():
            if self._normalize_tag(descendant.tag) in normalized:
                return descendant
        return None

    @staticmethod
    def _xsi_type(element: Optional[ET.Element]) -> Optional[str]:
        if element is None:
            return None
        xsi_type = element.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type")
        if not xsi_type:
            xsi_type = element.attrib.get("xsi:type")
        if not xsi_type:
            return None
        return str(xsi_type).split(":")[-1].strip()

    def _iter_rule_nodes(self, rule_container: Optional[ET.Element]) -> Iterable[ET.Element]:
        if rule_container is None:
            return
        for child in list(rule_container):
            if self._looks_like_rule(child):
                yield child
                continue
            if list(child):
                for nested in self._iter_rule_nodes(child):
                    yield nested

    def _looks_like_rule(self, node: ET.Element) -> bool:
        child_tags = {self._normalize_tag(child.tag) for child in list(node)}
        return bool(
            child_tags.intersection(
                {
                    "name",
                    "configurationaction",
                    "configurationcondition",
                    "externaldata",
                }
            )
        )

    @staticmethod
    def _sanitize_chain_name(device_identifier: str, suffix: str) -> str:
        base = re.sub(r"[^A-Za-z0-9]+", "_", str(device_identifier or "device").upper()).strip("_")
        if not base:
            base = "DEVICE"
        return f"DOSS_{base[:18]}_{suffix}"

    @staticmethod
    def _normalize_port(port_value: Optional[str]) -> Optional[str]:
        if port_value is None:
            return None
        text = str(port_value).strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered.startswith("eq "):
            return text.split(None, 1)[1].strip()
        if lowered.startswith("range "):
            parts = text.split()
            if len(parts) >= 3:
                return f"{parts[1]}:{parts[2]}"
        return text

    @staticmethod
    def _normalize_action(action_value: Optional[str]) -> str:
        normalized = str(action_value or "ACCEPT").strip().upper()
        if normalized in {"ALLOW", "ACCEPT", "PERMIT"}:
            return "ACCEPT"
        if normalized in {"DENY", "DROP"}:
            return "DROP"
        if normalized == "REJECT":
            return "REJECT"
        return normalized

    @staticmethod
    def _normalize_protocol(protocol_value: Optional[str]) -> Optional[str]:
        normalized = str(protocol_value or "").strip().lower()
        if not normalized:
            return None
        if normalized in {"6", "tcp"}:
            return "tcp"
        if normalized in {"17", "udp"}:
            return "udp"
        return normalized

    def _infer_iptables_direction(self, direction_value: Optional[str], rule_name: str) -> List[str]:
        normalized_direction = str(direction_value or "").strip().upper()
        if normalized_direction == "INBOUND":
            return ["IN"]
        if normalized_direction == "OUTBOUND":
            return ["OUT"]
        if normalized_direction == "BOTH":
            return ["IN", "OUT"]

        normalized_name = rule_name.replace("-", "").replace("_", "").lower()
        if any(token in normalized_name for token in {"todev", "v1to", "toace"}):
            return ["IN"]
        if any(token in normalized_name for token in {"frdev", "fromdev", "v1fr", "frace"}):
            return ["OUT"]
        return ["IN", "OUT"]

    def _select_placeholder(self, rule_name: str) -> Optional[str]:
        normalized_name = rule_name.replace("-", "").replace("_", "").lower()
        for hint, placeholder in self.PLACEHOLDER_BY_HINT.items():
            if hint in normalized_name:
                return placeholder
        return None

    def _resolve_endpoint_value(
        self,
        *,
        explicit_value: Optional[str],
        dns_name: Optional[str],
        placeholder: Optional[str],
    ) -> Optional[str]:
        if explicit_value:
            return explicit_value
        if dns_name:
            return f"<RESOLVE:{dns_name}>"
        return placeholder

    def _resolve_default_action(self, rule_set: Optional[ET.Element]) -> str:
        """
        Resolves default action from plain text or nested FilteringAction XML.
        """
        if rule_set is None:
            return self._normalize_action(None)

        plain = self._child_text(
            rule_set,
            ["default_action", "default-action", "defaultAction"],
        )
        if plain:
            return self._normalize_action(plain)

        default_node = None
        for child in list(rule_set):
            if self._normalize_tag(child.tag) == "defaultaction":
                default_node = child
                break

        if default_node is None:
            return self._normalize_action(None)

        if (default_node.text or "").strip():
            return self._normalize_action(default_node.text)

        action_text = self._child_text(
            default_node,
            [
                "filtering-action-type",
                "filtering_action_type",
                "FilteringActionType",
            ],
        )
        if action_text:
            return self._normalize_action(action_text)

        filtering_action = self._first_descendant(
            default_node,
            ["filtering-action", "filteringaction", "filtering_action"],
        )
        if filtering_action is not None:
            nested = self._child_text(
                filtering_action,
                ["filtering-action-type", "filtering_action_type", "FilteringActionType"],
            )
            if nested:
                return self._normalize_action(nested)

        if self._xsi_type(default_node) == "FilteringAction":
            direct = self._child_text(
                default_node,
                ["filtering-action-type", "filtering_action_type", "FilteringActionType"],
            )
            if direct:
                return self._normalize_action(direct)

        return self._normalize_action(None)

    def compile_mspl(self, mspl_xml: str, device_identifier: str) -> List[str]:
        root = ET.fromstring(mspl_xml)

        policy_type = self._child_text(root, ["type"]) or ""
        command = "ip6tables" if "ipv6" in policy_type.lower() else "iptables"
        input_chain = self._sanitize_chain_name(device_identifier, "IN")
        output_chain = self._sanitize_chain_name(device_identifier, "OUT")

        configuration = self._first_descendant(root, ["configuration"])
        rule_set = self._first_descendant(configuration, ["rule-set-configuration", "rule_set_configuration"])
        if rule_set is None and self._xsi_type(configuration) == "RuleSetConfiguration":
            # Visual builder format may model RuleSetConfiguration as configuration xsi:type="RuleSetConfiguration".
            rule_set = configuration
        default_action = self._resolve_default_action(rule_set)

        commands = [
            f"{command} -N {input_chain}",
            f"{command} -F {input_chain}",
            f"{command} -N {output_chain}",
            f"{command} -F {output_chain}",
            f"{command} -A INPUT -j {input_chain}",
            f"{command} -A OUTPUT -j {output_chain}",
        ]

        for rule_node in self._iter_rule_nodes(rule_set):
            rule_name = self._child_text(rule_node, ["name"]) or self._normalize_tag(rule_node.tag)
            filtering_action = self._first_descendant(rule_node, ["filtering-action", "filteringaction"])
            packet_filter = self._first_descendant(rule_node, ["packet-filter-condition", "packet_filter_condition"])
            if packet_filter is None:
                continue

            action_text = self._child_text(filtering_action, ["filtering-action-type", "filtering_action_type"])
            if action_text is None:
                # Visual builder format stores action in configurationRuleAction xsi:type="FilteringAction"
                # with a direct FilteringActionType child.
                rule_action = self._first_descendant(
                    rule_node,
                    ["configuration-rule-action", "configurationruleaction", "configuration_action"],
                )
                if self._xsi_type(rule_action) == "FilteringAction":
                    action_text = self._child_text(
                        rule_action,
                        ["filtering-action-type", "filtering_action_type", "FilteringActionType"],
                    )
            action = self._normalize_action(action_text)
            protocol = self._normalize_protocol(
                self._child_text(packet_filter, ["protocol-type", "protocol_type", "protocol"])
            )
            source_port = self._normalize_port(self._child_text(packet_filter, ["source-port", "source_port"]))
            destination_port = self._normalize_port(
                self._child_text(packet_filter, ["destination-port", "destination_port"])
            )
            direction = self._child_text(packet_filter, ["direction"])
            placeholder = self._select_placeholder(rule_name)

            # TODO: replace placeholders with real network context once the
            # pilot exposes controller/local-network/manufacturer resolution.
            source_value = self._resolve_endpoint_value(
                explicit_value=self._child_text(packet_filter, ["source-address", "source_address"]),
                dns_name=self._child_text(packet_filter, ["source-dnsname", "source_dnsname"]),
                placeholder=placeholder if "IN" in self._infer_iptables_direction(direction, rule_name) else None,
            )
            destination_value = self._resolve_endpoint_value(
                explicit_value=self._child_text(packet_filter, ["destination-address", "destination_address"]),
                dns_name=self._child_text(packet_filter, ["destination-dnsname", "destination_dnsname"]),
                placeholder=placeholder if "OUT" in self._infer_iptables_direction(direction, rule_name) else None,
            )

            for chain_direction in self._infer_iptables_direction(direction, rule_name):
                chain_name = input_chain if chain_direction == "IN" else output_chain
                parts = [command, "-A", chain_name]
                if protocol:
                    parts.extend(["-p", protocol])

                if chain_direction == "IN":
                    if source_value:
                        parts.extend(["-s", source_value])
                    if source_port:
                        parts.extend(["--sport", source_port])
                    if destination_value:
                        parts.extend(["-d", destination_value])
                    if destination_port:
                        parts.extend(["--dport", destination_port])
                else:
                    if source_value:
                        parts.extend(["-s", source_value])
                    if source_port:
                        parts.extend(["--sport", source_port])
                    if destination_value:
                        parts.extend(["-d", destination_value])
                    if destination_port:
                        parts.extend(["--dport", destination_port])

                parts.extend(["-j", action])
                commands.append(" ".join(parts))

        if default_action and default_action not in {"ACCEPT", "ALLOW"}:
            commands.append(f"{command} -A {input_chain} -j {default_action}")
            commands.append(f"{command} -A {output_chain} -j {default_action}")

        return commands
