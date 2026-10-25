from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.services import audit

from .models import User
from .serializers import ChangePasswordSerializer, RegisterSerializer, UserSerializer


def _auth_payload(user):
    token, _ = Token.objects.get_or_create(user=user)
    return {"token": token.key, "user": UserSerializer(user).data}


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        link = f"{settings.FRONTEND_URL}/verify-email?token={user.verification_token}"
        try:
            send_mail("Verify your RecoverIQ account",
                      f"Hello {user.first_name},\n\nOpen this link to verify your college email:\n{link}\n",
                      settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception:  # never fail registration because mail is not configured
            pass
        audit(user, "user.registered", user, request=request)
        body = {"message": "Account created. Verify your email to sign in.", "email_verified": False}
        if settings.DEV_EXPOSE_VERIFICATION_LINK:
            body["dev_verification_link"] = link
            body["dev_notice"] = "Development mode: no email was sent. Use this link to verify."
        return Response(body, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        user = User.objects.filter(verification_token=token).first() if token else None
        if not user:
            return Response({"detail": "This verification link is invalid or already used."}, status=400)
        user.email_verified = True
        user.verification_token = ""
        user.save(update_fields=["email_verified", "verification_token"])
        audit(user, "user.email_verified", user, request=request)
        return Response({"detail": "Email verified. You can now sign in."})


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        user = User.objects.filter(email__iexact=email).first()
        if not user or not user.check_password(password):
            return Response({"detail": "Invalid email or password."}, status=400)
        if not user.is_active:
            return Response({"detail": "This account has been deactivated. Contact campus support."}, status=403)
        if not user.email_verified:
            return Response({"detail": "Please verify your email before signing in.", "code": "email_unverified"},
                            status=403)
        audit(user, "user.login", user, request=request)
        return Response(_auth_payload(user))


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class ChangePasswordView(APIView):
    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        request.user.set_password(ser.validated_data["new_password"])
        request.user.save()
        Token.objects.filter(user=request.user).delete()
        audit(request.user, "user.password_changed", request.user, request=request)
        return Response(_auth_payload(request.user))
