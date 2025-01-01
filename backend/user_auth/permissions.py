from rest_framework import permissions

class IsEmailVerified(permissions.BasePermission):
    """
    Permission qui vérifie si l'email de l'utilisateur est vérifié
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.email_verified

class IsSameDepartment(permissions.BasePermission):
    """
    Permission qui vérifie si l'utilisateur appartient au même département
    """
    def has_object_permission(self, request, view, obj):
        return obj.department == request.user.department

class IsManager(permissions.BasePermission):
    """
    Permission qui vérifie si l'utilisateur est un manager
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='Manager').exists()
