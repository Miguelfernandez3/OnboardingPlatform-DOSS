# utils/app_context.py
"""
Application context management.
Manages global DeviceDomainManager instance.
"""
_dadm_instance = None

def set_dadm_instance(dadm):
    """Sets the global DeviceDomainManager instance"""
    global _dadm_instance
    _dadm_instance = dadm

def get_dadm_instance():
    """Gets the global DeviceDomainManager instance"""
    return _dadm_instance

