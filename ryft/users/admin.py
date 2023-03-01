from django.contrib.auth import get_user_model

User = get_user_model()

#
# @admin.register(User)
# class UserAdmin(auth_admin.UserAdmin):
#     list_display = (
#         "email",
#         "is_staff",
#         "is_active",
#     )
#     list_filter = (
#         "email",
#         "is_staff",
#         "is_active",
#     )
#     fieldsets = (
#         (None, {"fields": ("email", "password")}),
#         ("Permissions", {"fields": ("is_staff", "is_active")}),
#     )
#     add_fieldsets = (
#         (
#             None,
#             {
#                 "classes": ("wide",),
#                 "fields": ("email", "password1", "password2", "is_staff", "is_active"),
#             },
#         ),
#     )
#     search_fields = ("email",)
#     ordering = ("email",)
