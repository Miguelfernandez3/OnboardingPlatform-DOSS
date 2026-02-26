# scripts/setup_env.py
"""
Script de ayuda para configurar el archivo .env
Genera un archivo .env con valores seguros si no existe.
"""
import os
import secrets
import sys

def generate_secret_key():
    """Genera una clave secreta segura para JWT"""
    return secrets.token_urlsafe(32)

def setup_env_file():
    """Crea o actualiza el archivo .env"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    env_path = os.path.join(parent_dir, '.env')
    
    # Verificar si el archivo ya existe
    if os.path.exists(env_path):
        print(f"El archivo .env ya existe en: {env_path}")
        response = input("¿Deseas sobrescribirlo? (s/N): ")
        if response.lower() != 's':
            print("Operación cancelada.")
            return False
    
    # Generar valores
    jwt_secret = generate_secret_key()
    
    print("\n=== Configuración de Variables de Entorno ===")
    print("\nPor favor, proporciona los siguientes valores:")
    
    admin_email = input("Email del administrador [admin@doss.local]: ").strip()
    if not admin_email:
        admin_email = "admin@doss.local"
    
    admin_password = input("Password del administrador (mínimo 8 caracteres): ").strip()
    if not admin_password:
        print("ERROR: El password es requerido")
        return False
    
    if len(admin_password) < 8:
        print("ADVERTENCIA: El password debe tener al menos 8 caracteres")
        response = input("¿Continuar de todos modos? (s/N): ")
        if response.lower() != 's':
            return False
    
    # Crear contenido del archivo .env
    env_content = f"""# Variables de Entorno para Domain-Manager
# IMPORTANTE: Configura estos valores antes de ejecutar la aplicación

# JWT Secret Key - REQUERIDO
# Clave generada automáticamente (32 caracteres aleatorios)
JWT_SECRET_KEY={jwt_secret}

# Credenciales del Administrador Inicial - REQUERIDO
# El usuario admin se creará automáticamente al iniciar la aplicación si no existe
ADMIN_EMAIL={admin_email}
ADMIN_PASSWORD={admin_password}
"""
    
    # Escribir archivo
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        print(f"\n✓ Archivo .env creado exitosamente en: {env_path}")
        print("\nIMPORTANTE:")
        print("- Guarda este archivo de forma segura")
        print("- NO lo commitees al repositorio")
        print("- Usa la misma JWT_SECRET_KEY en todos los proyectos")
        return True
    except Exception as e:
        print(f"\nERROR: No se pudo crear el archivo .env: {e}")
        return False

if __name__ == '__main__':
    setup_env_file()
