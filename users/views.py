"""
User authentication and management views
"""
from rest_framework import status, permissions, generics, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db.models import Q
from .models import User, Company
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, 
    UserSerializer, UserUpdateSerializer, CompanySerializer
)


class UserRegistrationView(APIView):
    """User registration with company creation for admins"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'message': 'User created successfully'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """User login with JWT token generation"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'message': 'Login successful'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """Get current user profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserUpdateSerializer(
            request.user, 
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(viewsets.ModelViewSet):
    """List and create users (Admin only)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    
    def get_queryset(self):
        if not self.request.user.is_admin():
            return User.objects.none()
        return User.objects.filter(company=self.request.user.company)
    
    def perform_create(self, serializer):
        # Ensure new users are added to the same company
        serializer.save(company=self.request.user.company)


class UserDetailView(viewsets.ModelViewSet):
    """User detail view (Admin only)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    
    def get_queryset(self):
        if not self.request.user.is_admin():
            return User.objects.none()
        return User.objects.filter(company=self.request.user.company)


class CompanyUsersView(APIView):
    """Get users by role for the current company"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_admin():
            return Response(
                {'error': 'Only admins can view company users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        role = request.GET.get('role')
        users = User.objects.filter(company=request.user.company)
        
        if role:
            users = users.filter(role=role)
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class ManagerEmployeesView(APIView):
    """Get employees under a manager"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not (request.user.is_manager() or request.user.is_admin()):
            return Response(
                {'error': 'Only managers and admins can view team members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.user.is_admin():
            # Admin can see all employees
            employees = User.objects.filter(
                company=request.user.company,
                role='employee'
            )
        else:
            # Manager can see their direct reports
            employees = User.objects.filter(
                manager=request.user,
                company=request.user.company
            )
        
        serializer = UserSerializer(employees, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_manager(request):
    """Assign manager to employee (Admin only)"""
    if not request.user.is_admin():
        return Response(
            {'error': 'Only admins can assign managers'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    employee_id = request.data.get('employee_id')
    manager_id = request.data.get('manager_id')
    
    try:
        employee = User.objects.get(id=employee_id, company=request.user.company)
        manager = User.objects.get(id=manager_id, company=request.user.company)
        
        if not manager.is_manager():
            return Response(
                {'error': 'Assigned user must be a manager'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        employee.manager = manager
        employee.save()
        
        return Response({
            'message': f'{employee.full_name} assigned to {manager.full_name}'
        })
    
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_user_role(request):
    """Change user role (Admin only)"""
    if not request.user.is_admin():
        return Response(
            {'error': 'Only admins can change user roles'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user_id = request.data.get('user_id')
    new_role = request.data.get('role')
    
    if new_role not in ['admin', 'manager', 'employee']:
        return Response(
            {'error': 'Invalid role'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(id=user_id, company=request.user.company)
        user.role = new_role
        user.save()
        
        return Response({
            'message': f'{user.full_name} role changed to {new_role}'
        })
    
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
