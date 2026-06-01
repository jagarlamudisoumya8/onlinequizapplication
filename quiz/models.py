import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Profile(models.Model):
    THEME_CHOICES = [("system", "System"), ("light", "Light"), ("dark", "Dark")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.FileField(upload_to="profiles/", blank=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    interests = models.CharField(max_length=255, blank=True)
    theme_preference = models.CharField(max_length=12, choices=THEME_CHOICES, default="system")

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Course(models.Model):
    title = models.CharField(max_length=180, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    thumbnail = models.URLField(blank=True)
    thumbnail_file = models.FileField(upload_to="courses/", blank=True)
    duration = models.CharField(max_length=80, blank=True)
    instructor_name = models.CharField(max_length=120)
    level = models.CharField(
        max_length=20,
        choices=[("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")],
        default="beginner",
    )
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("course_detail", kwargs={"slug": self.slug})

    @property
    def image_url(self):
        if self.thumbnail_file:
            return self.thumbnail_file.url
        return self.thumbnail or "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=900&q=80"


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=5, validators=[MinValueValidator(1)])
    pass_percentage = models.PositiveIntegerField(default=40, validators=[MinValueValidator(1), MaxValueValidator(100)])
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course__title", "title"]
        indexes = [models.Index(fields=["course", "is_active"])]

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    points = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:80]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    unanswered_questions = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_taken = models.PositiveIntegerField(default=0, help_text="Stored in seconds after submission.")
    is_passed = models.BooleanField(default=False, db_index=True)
    ai_feedback = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["user", "-started_at"]), models.Index(fields=["quiz", "-percentage"])]

    def __str__(self):
        return f"{self.user} - {self.quiz}"

    @property
    def is_submitted(self):
        return self.submitted_at is not None

    @property
    def time_taken_seconds(self):
        end = self.submitted_at or timezone.now()
        return max(0, int((end - self.started_at).total_seconds()))

    @property
    def ends_at(self):
        return self.started_at + timezone.timedelta(minutes=self.quiz.duration_minutes)


class Answer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="one_answer_per_question")]


class Certificate(models.Model):
    attempt = models.OneToOneField(QuizAttempt, on_delete=models.CASCADE, related_name="certificate")
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.certificate_id)

    def verification_url(self):
        return reverse("certificate_verify", kwargs={"certificate_id": self.certificate_id})


class Result(models.Model):
    attempt = models.OneToOneField(QuizAttempt, on_delete=models.CASCADE, related_name="result")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="results")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="results")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="results")
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    incorrect_answers = models.PositiveIntegerField()
    unanswered_questions = models.PositiveIntegerField()
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    time_taken = models.PositiveIntegerField(help_text="Seconds")
    is_passed = models.BooleanField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["course", "-percentage"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.course} - {self.percentage}%"


class Leaderboard(models.Model):
    result = models.OneToOneField(Result, on_delete=models.CASCADE, related_name="leaderboard_entry")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leaderboard_entries")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="leaderboard_entries")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, db_index=True)
    completed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-percentage", "completed_at"]
        indexes = [models.Index(fields=["-percentage", "completed_at"])]

    def __str__(self):
        return f"{self.user} - {self.course} - {self.percentage}%"


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class AIConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_conversations", null=True, blank=True)
    message = models.TextField()
    response = models.TextField()
    context = models.CharField(max_length=40, default="general")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
