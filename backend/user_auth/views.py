from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from .serializers import CustomUserSerializer, UserProfileSerializer, UpdateProfileSerializer, ChangePasswordSerializer
from .models import CustomUser
from .permissions import IsEmailVerified, IsSameDepartment, IsManager
from django.contrib.auth.models import Group

# Create your views here.

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user"""
    serializer = CustomUserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Si l'utilisateur est du département IT, le rendre manager automatiquement
        if user.department == 'IT':
            manager_group, _ = Group.objects.get_or_create(name='Manager')
            user.groups.add(manager_group)
            user.email_verified = True  # Auto-vérifier l'email pour les IT
            user.save()
        
        # Générer le token de vérification
        token = user.generate_verification_token()
        verification_url = f"http://localhost:3000/verify-email/{token}"
        
        return Response({
            'message': 'User registered successfully. Please check your email to verify your account.',
            'user': CustomUserSerializer(user).data,
            'verification_url': verification_url,
            'debug_token': token
        })
    return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, token):
    """Verify user's email with the given token"""
    try:
        user = CustomUser.objects.get(email_verification_token=token)
        if user.verify_email(token):
            return Response({'message': 'Email verified successfully'})
        return Response({'error': 'Invalid verification token'}, status=400)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Invalid verification token'}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Authenticate a user and return tokens"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception:
        return Response({
            'error': 'Server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    user = authenticate(username=email, password=password)
    
    if user is not None:
        if user.department == 'IT':
            user.email_verified = True
            user.save()
            
            manager_group, _ = Group.objects.get_or_create(name='Manager')
            user.groups.add(manager_group)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': {
                'email': user.email,
                'department': user.department,
                'email_verified': user.email_verified,
                'is_manager': user.groups.filter(name='Manager').exists()
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })
    
    return Response({
        'error': 'Invalid credentials'
    }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Successfully logged out'},
                      status=status.HTTP_200_OK)
    except Exception:
        return Response({'error': 'Invalid token'},
                      status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = request.data.get('email')
    try:
        user = CustomUser.objects.get(email=email)
        # Générer le token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Construire le lien de réinitialisation
        reset_url = f"http://localhost:3000/reset-password/{uid}/{token}"
        
        # Envoyer l'email
        send_mail(
            'Réinitialisation de votre mot de passe',
            f'Cliquez sur ce lien pour réinitialiser votre mot de passe : {reset_url}',
            'noreply@example.com',
            [email],
            fail_silently=False,
        )
        
        return Response({'message': 'Password reset email has been sent.'}, 
                      status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User with this email does not exist.'}, 
                      status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_reset_token(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            return Response({'message': 'Token is valid'}, 
                          status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Token is invalid or expired'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return Response({'error': 'Invalid reset link'}, 
                      status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            new_password = request.data.get('new_password')
            if not new_password:
                return Response({'error': 'New password is required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
                
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password has been reset successfully'}, 
                          status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Token is invalid or expired'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return Response({'error': 'Invalid reset link'}, 
                      status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """
    Get the profile of the currently authenticated user
    """
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update the profile of the currently authenticated user
    """
    serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Profile updated successfully'})
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change password for the currently authenticated user
    """
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if user.check_password(serializer.data.get('old_password')):
            user.set_password(serializer.data.get('new_password'))
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response({'error': 'Incorrect old password'}, status=400)
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    """
    Renvoie l'email de vérification
    """
    email = request.data.get('email')
    try:
        user = CustomUser.objects.get(email=email)
        if user.email_verified:
            return Response({'message': 'Email déjà vérifié'})
            
        token = user.generate_verification_token()
        verification_url = f"http://localhost:3000/verify-email/{token}"
        
        # Pour le développement, affichons directement le token
        return Response({
            'message': 'Email de vérification renvoyé',
            'debug_token': token,  # Ne faire ceci qu'en développement !
            'verification_url': verification_url
        })
    except CustomUser.DoesNotExist:
        return Response({'error': 'Utilisateur non trouvé'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified, IsManager])
def list_department_users(request):
    """
    Liste tous les utilisateurs du même département que l'utilisateur connecté
    """
    users = CustomUser.objects.filter(department=request.user.department)
    serializer = UserProfileSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified, IsManager])
def assign_manager_role(request, user_id):
    """
    Assigne le rôle de manager à un utilisateur
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        if user.department != request.user.department:
            return Response(
                {'error': 'Vous ne pouvez pas modifier les utilisateurs d\'autres départements'},
                status=403
            )
        
        manager_group = Group.objects.get_or_create(name='Manager')[0]
        user.groups.add(manager_group)
        return Response({'message': f'Rôle de manager assigné à {user.email}'})
    except CustomUser.DoesNotExist:
        return Response({'error': 'Utilisateur non trouvé'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified, IsManager])
def department_stats(request):
    """
    Obtenir les statistiques du département
    """
    department = request.user.department
    total_users = CustomUser.objects.filter(department=department).count()
    verified_users = CustomUser.objects.filter(department=department, email_verified=True).count()
    managers = CustomUser.objects.filter(
        department=department,
        groups__name='Manager'
    ).count()

    return Response({
        'department': department,
        'total_users': total_users,
        'verified_users': verified_users,
        'managers': managers,
        'unverified_users': total_users - verified_users
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified, IsManager])
def remove_manager_role(request, user_id):
    """
    Retire le rôle de manager à un utilisateur
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        if user.department != request.user.department:
            return Response(
                {'error': 'Vous ne pouvez pas modifier les utilisateurs d\'autres départements'},
                status=403
            )
        
        manager_group = Group.objects.get(name='Manager')
        user.groups.remove(manager_group)
        return Response({'message': f'Rôle de manager retiré de {user.email}'})
    except CustomUser.DoesNotExist:
        return Response({'error': 'Utilisateur non trouvé'}, status=404)
    except Group.DoesNotExist:
        return Response({'error': 'Groupe Manager non trouvé'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_token(request):
    """
    Vérifie si le token JWT est valide et renvoie les informations de l'utilisateur
    """
    user = request.user
    return Response({
        'user': UserProfileSerializer(user).data,
        'is_manager': user.groups.filter(name='Manager').exists(),
        'token_valid': True
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager])
def list_all_users(request):
    """
    Liste tous les utilisateurs (accessible uniquement aux managers)
    """
    users = CustomUser.objects.all().order_by('department', 'email')
    user_list = []
    
    for user in users:
        user_data = {
            'email': user.email,
            'department': user.department,
            'role': 'Manager' if user.groups.filter(name='Manager').exists() else 'Employee',
            'verified': 'Oui' if user.email_verified else 'Non'
        }
        user_list.append(user_data)
    
    return Response({
        'total_users': len(user_list),
        'users': user_list
    })
