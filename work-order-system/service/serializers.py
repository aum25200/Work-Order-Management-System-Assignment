from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Attachment, Comment, Profile, WorkOrder, WorkOrderEvent
from .permissions import can_see_internal_notes

User = get_user_model()


class Brief(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class CommentSerializer(serializers.ModelSerializer):
    author = Brief(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "body", "is_internal", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class EventSerializer(serializers.ModelSerializer):
    actor = Brief(read_only=True)

    class Meta:
        model = WorkOrderEvent
        fields = ["id", "actor", "event_type", "from_value", "to_value", "note", "created_at"]


class AttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "original_name", "uploaded_at", "download_url"]

    def get_download_url(self, obj):
        req = self.context.get("request")
        return req.build_absolute_uri(f"/api/attachments/{obj.pk}/download/") if req else None


class WorkOrderSerializer(serializers.ModelSerializer):
    customer = Brief(read_only=True)
    technician = Brief(read_only=True)
    technician_id = serializers.PrimaryKeyRelatedField(
        source="technician",
        queryset=User.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    comments = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    history = EventSerializer(many=True, read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "title",
            "description",
            "customer",
            "technician",
            "technician_id",
            "priority",
            "status",
            "location",
            "created_at",
            "updated_at",
            "completed_at",
            "closed_at",
            "comments",
            "attachments",
            "history",
        ]
        read_only_fields = [
            "id",
            "customer",
            "technician",
            "status",
            "created_at",
            "updated_at",
            "completed_at",
            "closed_at",
            "comments",
            "attachments",
            "history",
        ]

    def get_comments(self, obj):
        comments = obj.comments.select_related("author")
        request = self.context.get("request")
        if request and not can_see_internal_notes(request.user):
            comments = comments.filter(is_internal=False)
        return CommentSerializer(comments, many=True).data

    def validate_technician_id(self, user):
        if not hasattr(user, "profile") or user.profile.role != Profile.Role.TECHNICIAN:
            raise serializers.ValidationError("Assigned user must have the Technician role.")
        return user


class CreateWorkOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ["id", "title", "description", "priority", "location"]
        read_only_fields = ["id"]


class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=WorkOrder.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class AssignmentSerializer(serializers.Serializer):
    technician_id = serializers.PrimaryKeyRelatedField(
        source="technician",
        queryset=User.objects.all(),
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_technician_id(self, user):
        if not hasattr(user, "profile") or user.profile.role != Profile.Role.TECHNICIAN:
            raise serializers.ValidationError("Assigned user must have the Technician role.")
        return user


class UploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["file"]

    def validate_file(self, f):
        if f.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File must be 10 MB or smaller.")
        return f


class CustomerSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        source="profile.phone",
        required=False,
        allow_blank=True,
        max_length=32,
    )
    company = serializers.CharField(
        source="profile.company",
        required=False,
        allow_blank=True,
        max_length=120,
    )
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "phone",
            "company",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {"email": {"required": True, "allow_blank": False}}

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required."})
        return attrs

    def create(self, validated):
        extra = validated.pop("profile", {})
        password = validated.pop("password")
        user = User.objects.create_user(password=password, **validated)
        for k, v in extra.items():
            setattr(user.profile, k, v)
        user.profile.save()
        return user

    def update(self, instance, validated):
        extra = validated.pop("profile", {})
        password = validated.pop("password", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        for k, v in extra.items():
            setattr(instance.profile, k, v)
        instance.profile.save()
        return instance
