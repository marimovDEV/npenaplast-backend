from rest_framework import viewsets
from .models import User, ERPRole, ERPPermission, Department
from .serializers import UserSerializer, RoleSerializer, PermissionSerializer, DepartmentSerializer
from .permissions import IsAdmin, IsSuperAdmin, get_user_role_name

from rest_framework_simplejwt.views import TokenObtainPairView as SimpleJWTTokenView
from .serializers import TokenObtainPairSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    filterset_fields = ['department', 'role_obj', 'status']
    search_fields = ['full_name', 'username', 'phone']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or get_user_role_name(user) in ['Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN']:
            return User.objects.all()
        return User.objects.filter(is_active=True)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdmin]

class RoleViewSet(viewsets.ModelViewSet):
    queryset = ERPRole.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdmin]

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ERPPermission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAdmin]

class TokenObtainPairView(SimpleJWTTokenView):
    serializer_class = TokenObtainPairSerializer
