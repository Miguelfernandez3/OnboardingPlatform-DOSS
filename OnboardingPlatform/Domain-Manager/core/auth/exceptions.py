# core/auth/exceptions.py
"""
Custom exceptions for authentication and authorization.
"""

class AuthenticationError(Exception):
    """Excepción para errores de autenticación (token inválido/faltante)"""
    def __init__(self, message, original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
    
    def __str__(self):
        if self.original_error:
            return f"{self.message}: {self.original_error}"
        return self.message

class AuthorizationError(Exception):
    """Excepción para errores de autorización (permisos insuficientes)"""
    def __init__(self, message, original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
    
    def __str__(self):
        if self.original_error:
            return f"{self.message}: {self.original_error}"
        return self.message

class TokenExpiredError(Exception):
    """Excepción para tokens expirados"""
    def __init__(self, message="Token has expired", original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
    
    def __str__(self):
        if self.original_error:
            return f"{self.message}: {self.original_error}"
        return self.message

class InvalidCredentialsError(Exception):
    """Excepción para credenciales inválidas (email/password incorrectos)"""
    def __init__(self, message="Invalid email or password", original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
    
    def __str__(self):
        if self.original_error:
            return f"{self.message}: {self.original_error}"
        return self.message
