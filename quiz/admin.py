from django.contrib import admin

from .models import (
    AIConversation,
    Answer,
    Certificate,
    Choice,
    ContactMessage,
    Course,
    Leaderboard,
    Profile,
    Question,
    Quiz,
    QuizAttempt,
    Result,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor_name", "level", "is_published", "created_at")
    list_filter = ("level", "is_published")
    search_fields = ("title", "description", "instructor_name")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "duration_minutes", "pass_percentage", "is_active")
    list_filter = ("is_active", "course")
    search_fields = ("title", "course__title")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "text")
    list_filter = ("quiz__course", "quiz")
    search_fields = ("text",)
    inlines = [ChoiceInline]


admin.site.register(Profile)
admin.site.register(Choice)
admin.site.register(QuizAttempt)
admin.site.register(Answer)
admin.site.register(Certificate)
admin.site.register(ContactMessage)
admin.site.register(AIConversation)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "quiz", "percentage", "is_passed", "created_at")
    list_filter = ("is_passed", "course", "quiz")
    search_fields = ("user__username", "user__first_name", "user__last_name", "course__title")
    readonly_fields = ("attempt", "user", "course", "quiz", "created_at")


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "percentage", "completed_at")
    list_filter = ("course",)
    search_fields = ("user__username", "course__title")
