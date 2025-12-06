from rest_framework import serializers
from .models import CustomUser

class CustomerSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["full_name", "phone_number"]

    def create(self, validated_data):
        return CustomUser.objects.create_user(
            phone_number=validated_data["phone_number"],
            full_name=validated_data["full_name"],
            user_type="Customer"
        )
