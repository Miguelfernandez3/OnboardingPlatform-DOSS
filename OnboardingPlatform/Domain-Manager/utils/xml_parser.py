# utils/xml_parser.py
"""
Centralized functions for parsing XML mitigation files.
Consolidates parseMitigationsTMUD, parseMitigationsMUD and parse_mitigation_xml
"""
from lxml import etree
import logging

def parse_mitigation_xml(mitigation_xml):
    """
    Parses mitigation XML and extracts structured information.
    This is the main function that replaces parse_mitigation_xml from the original code.
    
    Args:
        mitigation_xml: XML string or list with XML string
        
    Returns:
        dict with 'actions', 'conditions', 'models_affected' or None if error
    """
    try:
        # Handle list (compatibility with parseMitigationsTMUD)
        if isinstance(mitigation_xml, list):
            mitigation_xml = mitigation_xml[0] if mitigation_xml else ''
        
        if not mitigation_xml:
            return None
            
        root = etree.XML(str(mitigation_xml).encode("utf-8"))
        
        # Extract models-affected
        models_affected = root.xpath('//models-affected/text()')
        
        # Extract configuration-actions
        config_actions = []
        for action in root.xpath('//configuration-action'):
            action_dict = {}
            for child in action:
                if child.tag not in action_dict:
                    action_dict[child.tag] = {}
                for grandchild in child:
                    if grandchild.tag in action_dict[child.tag]:
                        if isinstance(action_dict[child.tag][grandchild.tag], list):
                            action_dict[child.tag][grandchild.tag].append(grandchild.text)
                        else:
                            action_dict[child.tag][grandchild.tag] = [
                                action_dict[child.tag][grandchild.tag],
                                grandchild.text
                            ]
                    else:
                        action_dict[child.tag][grandchild.tag] = grandchild.text
            config_actions.append(action_dict)
        
        # Extract configuration-conditions
        config_conditions = []
        for condition in root.xpath('//configuration-condition'):
            condition_dict = {}
            for child in condition:
                if child.tag not in condition_dict:
                    condition_dict[child.tag] = {}
                for grandchild in child:
                    if grandchild.tag not in condition_dict[child.tag]:
                        condition_dict[child.tag][grandchild.tag] = {}
                    for greatgrandchild in grandchild:
                        condition_dict[child.tag][grandchild.tag][greatgrandchild.tag] = greatgrandchild.text
            config_conditions.append(condition_dict)
        
        return {
            'actions': config_actions,
            'conditions': config_conditions,
            'models_affected': models_affected
        }
    except Exception as e:
        logging.error(f"Error parsing mitigation XML: {e}")
        return None

def parse_mitigations_tmud(mitigation_actions):
    """
    Parses TMUD mitigations (compatibility with original code).
    Maintains exact behavior of parseMitigationsTMUD.
    
    Args:
        mitigation_actions: List with XML strings
        
    Returns:
        dict with 'action', 'condition', 'models'
    """
    if not mitigation_actions or len(mitigation_actions) < 1:
        logging.warning("parse_mitigations_tmud: mitigation_actions is empty")
        return None
    
    logging.debug(f"parse_mitigations_tmud: ma0={mitigation_actions[0]}")
    if len(mitigation_actions) > 1:
        logging.debug(f"parse_mitigations_tmud: ma1={mitigation_actions[1]}")
    
    root = etree.XML(mitigation_actions[0].encode("utf-8"))
    
    # Extract models-affected
    models_affected = root.xpath('//models-affected/text()')
    
    # Initialize an empty list to store the dictionaries
    config_actions = []
    
    # Iterate through each configuration-action element
    for action in root.xpath('//configuration-action'):
        action_dict = {}
        
        # Iterate through each child of the action element
        for child in action:
            if child.tag not in action_dict:
                action_dict[child.tag] = {}
            for grandchild in child:
                # Handle multiple elements with the same tag (e.g., software-fix-url)
                if grandchild.tag in action_dict[child.tag]:
                    if isinstance(action_dict[child.tag][grandchild.tag], list):
                        action_dict[child.tag][grandchild.tag].append(grandchild.text)
                    else:
                        action_dict[child.tag][grandchild.tag] = [
                            action_dict[child.tag][grandchild.tag],
                            grandchild.text
                        ]
                else:
                    action_dict[child.tag][grandchild.tag] = grandchild.text
        
        # Add the action dictionary to the list
        config_actions.append(action_dict)
    
    config_conditions = []
    
    # Iterate through each configuration-condition element
    for condition in root.xpath('//configuration-condition'):
        condition_dict = {}
        
        # Iterate through each child of the condition element
        for child in condition:
            if child.tag not in condition_dict:
                condition_dict[child.tag] = {}
            for grandchild in child:
                if grandchild.tag not in condition_dict[child.tag]:
                    condition_dict[child.tag][grandchild.tag] = {}
                for greatgrandchild in grandchild:
                    condition_dict[child.tag][grandchild.tag][greatgrandchild.tag] = greatgrandchild.text
        
        # Add the condition dictionary to the list
        config_conditions.append(condition_dict)
    
    mitigation_data = {
        "action": config_actions,
        "condition": config_conditions,
        "models": models_affected
    }
    
    logging.debug(f"parse_mitigations_tmud result: {mitigation_data}")
    return mitigation_data

def parse_mitigations_mud(mitigation_actions):
    """
    Parses MUD mitigations (compatibility with original code).
    Maintains exact behavior of parseMitigationsMUD.
    
    Args:
        mitigation_actions: XML string
        
    Returns:
        list of config_actions
    """
    logging.debug(f"parse_mitigations_mud: {mitigation_actions}")
    logging.debug(f"parse_mitigations_mud type: {type(mitigation_actions)}")
    
    tree = etree.fromstring(mitigation_actions.encode("utf-8"))
    
    config_actions = []
    for action in tree.findall('.//configuration-action'):
        action_dict = {}
        
        # Iterate through each child of the action element
        for child in action:
            action_dict[child.tag] = {grandchild.tag: grandchild.text for grandchild in child}
        
        # Add the action dictionary to the list
        config_actions.append(action_dict)
    
    logging.debug(f"parse_mitigations_mud result: {config_actions}")
    return config_actions

