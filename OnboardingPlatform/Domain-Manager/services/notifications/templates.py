"""Multi-language templates for prerequisite / Telegram notifications."""

TELEGRAM_TEMPLATES = {
    'es': {
        'missing_mitigation_fields': (
            '⚠️ <b>Mitigación pendiente</b>\n\n'
            'En el dispositivo <b>{device_name}</b> faltan los datos: '
            '<b>{missing_fields}</b> para poder aplicar la mitigación '
            '<b>{mitigation_name}</b>.\n\n'
            'Por favor ingrese esos campos de forma manual para aplicar la mitigación.'
        ),
        'missing_policy_context': (
            '⚠️ <b>Política pendiente</b>\n\n'
            'En el dispositivo <b>{device_name}</b> faltan datos de contexto: '
            '<b>{missing_fields}</b> para aplicar la política <b>{policy_name}</b> '
            '(id <b>{policy_id}</b>).\n\n'
            'Complete el contexto de enforcement en el dispositivo o en el perfil y vuelva a intentar.'
        ),
        'feam_unavailable': (
            '⚠️ <b>FEAM no disponible</b>\n\n'
            'El servicio FEAM no responde correctamente.\n\n'
            'Endpoint: <b>{endpoint}</b>\n'
            'HTTP: <b>{status_code}</b>\n'
            'Error: <b>{error_message}</b>\n\n'
            'Las operaciones se reintentarán automáticamente. '
            'Si el problema persiste, revise la conectividad con FEAM.'
        ),
    },
    'en': {
        'missing_mitigation_fields': (
            '⚠️ <b>Pending mitigation</b>\n\n'
            'Device <b>{device_name}</b> is missing the following data: '
            '<b>{missing_fields}</b> to apply mitigation '
            '<b>{mitigation_name}</b>.\n\n'
            'Please enter those fields manually to apply the mitigation.'
        ),
        'missing_policy_context': (
            '⚠️ <b>Pending policy</b>\n\n'
            'Device <b>{device_name}</b> is missing enforcement context: '
            '<b>{missing_fields}</b> to apply policy <b>{policy_name}</b> '
            '(id <b>{policy_id}</b>).\n\n'
            'Complete the device or profile enforcement context and try again.'
        ),
        'feam_unavailable': (
            '⚠️ <b>FEAM unavailable</b>\n\n'
            'FEAM service is not responding correctly.\n\n'
            'Endpoint: <b>{endpoint}</b>\n'
            'HTTP: <b>{status_code}</b>\n'
            'Error: <b>{error_message}</b>\n\n'
            'Operations will retry automatically. '
            'If the problem persists, check FEAM connectivity.'
        ),
    },
}


def render_template(language: str, template_key: str, context: dict) -> str:
    lang = (language or 'en').lower().split('-')[0]
    templates = TELEGRAM_TEMPLATES.get(lang, TELEGRAM_TEMPLATES['en'])
    if template_key not in templates:
        templates = TELEGRAM_TEMPLATES['en']
    template = templates.get(template_key) or TELEGRAM_TEMPLATES['en'][template_key]
    return template.format(**context)
