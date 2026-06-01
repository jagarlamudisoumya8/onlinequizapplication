from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Max, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .forms import ContactForm, EmailOrUsernameLoginForm, ProfileForm, StudentRegistrationForm, StyledPasswordChangeForm
from .models import AIConversation, Answer, Certificate, Choice, Course, Leaderboard, Question, Quiz, QuizAttempt, Result
from .services import certificate_pdf_bytes, educational_ai_response, recommendations_for_user, attempt_feedback


def home(request):
    stats = cache.get_or_set(
        "home_stats",
        lambda: {
            "students": QuizAttempt.objects.values("user").distinct().count(),
            "quizzes": Quiz.objects.filter(is_active=True).count(),
            "courses": Course.objects.filter(is_published=True).count(),
            "certificates": Certificate.objects.count(),
        },
        60,
    )
    courses = Course.objects.filter(is_published=True).annotate(quiz_count=Count("quizzes")).order_by("-created_at")[:3]
    return render(request, "quiz/home.html", {"stats": stats, "courses": courses})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = StudentRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your student account is ready.")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = EmailOrUsernameLoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        if not form.cleaned_data.get("remember_me"):
            request.session.set_expiry(0)
        return redirect(request.GET.get("next") or "dashboard")
    return render(request, "registration/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


def password_reset_view(request):
    form = PasswordResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save(request=request, use_https=request.is_secure(), email_template_name="registration/password_reset_email.html")
        messages.success(request, "If that email exists, a reset link has been sent.")
        return redirect("login")
    return render(request, "registration/password_reset.html", {"form": form})


def courses(request):
    course_qs = Course.objects.filter(is_published=True).annotate(quiz_count=Count("quizzes", filter=Q(quizzes__is_active=True))).order_by("title")
    paginator = Paginator(course_qs, 9)
    return render(request, "quiz/courses.html", {"page_obj": paginator.get_page(request.GET.get("page"))})


def course_detail(request, slug):
    course = get_object_or_404(
        Course.objects.prefetch_related("quizzes__questions__choices"),
        slug=slug,
        is_published=True,
    )
    return render(request, "quiz/course_detail.html", {"course": course})


@login_required
def dashboard(request):
    attempts = request.user.quiz_attempts.select_related("quiz__course").filter(submitted_at__isnull=False)
    avg = attempts.aggregate(value=Avg("percentage"))["value"] or 0
    rank = _user_rank(request.user)
    courses_qs = Course.objects.filter(is_published=True).annotate(quiz_count=Count("quizzes"))
    recommended = recommendations_for_user(request.user, courses_qs)
    chart = list(attempts.order_by("submitted_at").values("quiz__title", "percentage")[:10])
    completed_courses = attempts.values("quiz__course").distinct().count()
    latest_results = Result.objects.select_related("course", "quiz").filter(user=request.user)[:5]
    recent_notifications = [
        {"type": "success", "text": f"Certificate generated for {cert.attempt.quiz.course.title}"}
        for cert in Certificate.objects.select_related("attempt__quiz__course").filter(attempt__user=request.user)[:3]
    ]
    return render(
        request,
        "quiz/dashboard.html",
        {
            "total_attempts": attempts.count(),
            "total_courses": courses_qs.count(),
            "completed_courses": completed_courses,
            "certificates": Certificate.objects.filter(attempt__user=request.user).count(),
            "average_score": round(float(avg), 1),
            "rank": rank,
            "recent_attempts": attempts[:5],
            "latest_results": latest_results,
            "recent_notifications": recent_notifications,
            "recommended_courses": recommended,
            "chart_labels": [item["quiz__title"] for item in chart],
            "chart_values": [float(item["percentage"]) for item in chart],
        },
    )


@login_required
def my_quizzes(request):
    attempts = request.user.quiz_attempts.select_related("quiz__course").all()
    return render(request, "quiz/my_quizzes.html", {"attempts": attempts})


@login_required
def start_quiz(request, slug):
    quiz = get_object_or_404(Quiz.objects.select_related("course"), slug=slug, is_active=True)
    if quiz.questions.count() != 10:
        messages.error(request, "This quiz must have exactly 10 questions before students can attempt it.")
        return redirect(quiz.course.get_absolute_url())
    attempt = QuizAttempt.objects.create(user=request.user, quiz=quiz, total_questions=quiz.questions.count())
    return redirect("take_quiz", attempt_id=attempt.id)


@login_required
def take_quiz(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz__course").prefetch_related("quiz__questions__choices", "answers"),
        id=attempt_id,
        user=request.user,
    )
    if attempt.is_submitted:
        return redirect("result_detail", attempt_id=attempt.id)
    if timezone.now() >= attempt.ends_at:
        _submit_attempt(attempt)
        return redirect("result_detail", attempt_id=attempt.id)
    questions = list(attempt.quiz.questions.prefetch_related("choices").all())
    answers = {answer.question_id: answer.selected_choice_id for answer in attempt.answers.all()}
    remaining_seconds = max(0, int((attempt.ends_at - timezone.now()).total_seconds()))
    return render(
        request,
        "quiz/take_quiz.html",
        {
            "attempt": attempt,
            "questions": questions,
            "answers": answers,
            "remaining_seconds": remaining_seconds,
        },
    )


@login_required
@require_POST
def save_answer(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user, submitted_at__isnull=True)
    if timezone.now() >= attempt.ends_at:
        _submit_attempt(attempt)
        return JsonResponse({"ok": False, "submitted": True}, status=409)
    try:
        question_id = int(request.POST.get("question_id", ""))
        choice_id = int(request.POST.get("choice_id", ""))
    except ValueError:
        return JsonResponse({"ok": False, "error": "Invalid answer payload."}, status=400)
    question = get_object_or_404(Question, id=question_id, quiz=attempt.quiz)
    choice = get_object_or_404(Choice, id=choice_id, question=question)
    Answer.objects.update_or_create(attempt=attempt, question=question, defaults={"selected_choice": choice})
    return JsonResponse({"ok": True})




@login_required
@require_POST
def submit_quiz(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt.objects.select_related("quiz"), id=attempt_id, user=request.user)
    if not attempt.is_submitted:
        _save_posted_answers(attempt, request.POST)
    _submit_attempt(attempt)
    return redirect("result_detail", attempt_id=attempt.id)


@login_required
def results(request):
    attempts = request.user.quiz_attempts.select_related("quiz__course").filter(submitted_at__isnull=False)
    return render(request, "quiz/results.html", {"attempts": attempts})


@login_required
def result_detail(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz__course").prefetch_related("answers__question", "answers__selected_choice"),
        id=attempt_id,
        user=request.user,
        submitted_at__isnull=False,
    )
    certificate = getattr(attempt, "certificate", None)
    answered = attempt.correct_answers + attempt.wrong_answers
    return render(
        request,
        "quiz/result_detail.html",
        {
            "attempt": attempt,
            "certificate": certificate,
            "answered": answered,
            "pie_values": [attempt.correct_answers, attempt.wrong_answers, attempt.unanswered_questions],
        },
    )


@login_required
def certificate_detail(request, certificate_id):
    certificate = get_object_or_404(Certificate.objects.select_related("attempt__quiz__course", "attempt__user"), certificate_id=certificate_id)
    if certificate.attempt.user != request.user and not request.user.is_staff:
        raise Http404
    verify_url = request.build_absolute_uri(certificate.verification_url())
    return render(request, "quiz/certificate.html", {"certificate": certificate, "verify_url": verify_url})


def certificate_verify(request, certificate_id):
    certificate = get_object_or_404(Certificate.objects.select_related("attempt__quiz__course", "attempt__user"), certificate_id=certificate_id)
    return render(request, "quiz/certificate_verify.html", {"certificate": certificate})


@login_required
def certificate_pdf(request, certificate_id):
    certificate = get_object_or_404(Certificate.objects.select_related("attempt__quiz__course", "attempt__user"), certificate_id=certificate_id)
    if certificate.attempt.user != request.user and not request.user.is_staff:
        raise Http404
    data = certificate_pdf_bytes(certificate, request.build_absolute_uri(certificate.verification_url()))
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="certificate-{certificate.certificate_id}.pdf"'
    return response


def leaderboard(request):
    period = request.GET.get("period", "all")
    qs = Leaderboard.objects.select_related("user", "course", "result").all()
    now = timezone.now()
    if period == "weekly":
        qs = qs.filter(completed_at__gte=now - timezone.timedelta(days=7))
    elif period == "monthly":
        qs = qs.filter(completed_at__gte=now - timezone.timedelta(days=30))
    leaders = qs.order_by("-percentage", "completed_at")[:10]
    return render(request, "quiz/leaderboard.html", {"leaders": leaders, "period": period})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile, user=request.user)
    password_form = StyledPasswordChangeForm(request.user, request.POST if request.POST.get("form_type") == "password" else None)
    if request.method == "POST" and request.POST.get("form_type") == "profile" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    if request.method == "POST" and request.POST.get("form_type") == "password" and password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password changed.")
        return redirect("profile")
    certificates = Certificate.objects.select_related("attempt__quiz__course").filter(attempt__user=request.user)
    attempts = request.user.quiz_attempts.select_related("quiz__course").filter(submitted_at__isnull=False)[:10]
    return render(request, "quiz/profile.html", {"form": form, "password_form": password_form, "certificates": certificates, "attempts": attempts})


def about(request):
    return render(request, "quiz/about.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thanks! Our support team has your message.")
        return redirect("contact")
    chat_history = request.session.get("ai_chat_history", [])
    return render(request, "quiz/contact.html", {"form": form, "chat_history": chat_history})


@api_view(["POST"])
@permission_classes([AllowAny])
def ai_chat(request):
    message = request.data.get("message", "")
    context = request.data.get("context", "general")
    response = educational_ai_response(message, context=context, user=request.user if request.user.is_authenticated else None)
    AIConversation.objects.create(user=request.user if request.user.is_authenticated else None, message=message, response=response, context=context)
    history = request.session.get("ai_chat_history", [])
    history.append({"message": message, "response": response})
    request.session["ai_chat_history"] = history[-20:]
    return Response({"response": response})


@login_required
@require_POST
def save_theme(request):
    theme = request.POST.get("theme", "system")
    if theme not in {"system", "light", "dark"}:
        return JsonResponse({"ok": False}, status=400)
    request.user.profile.theme_preference = theme
    request.user.profile.save(update_fields=["theme_preference"])
    return JsonResponse({"ok": True, "theme": theme})


def _submit_attempt(attempt):
    with transaction.atomic():
        attempt = QuizAttempt.objects.select_for_update().select_related("quiz__course", "user").get(pk=attempt.pk)
        if attempt.submitted_at:
            return attempt
        answers = attempt.answers.select_related("selected_choice").all()
        correct = sum(1 for answer in answers if answer.selected_choice and answer.selected_choice.is_correct)
        total = attempt.quiz.questions.count()
        answered = answers.filter(selected_choice__isnull=False).count()
        unanswered = max(0, total - answered)
        wrong = max(0, answered - correct)
        percentage = Decimal("0.00") if total == 0 else Decimal(correct * 100 / total).quantize(Decimal("0.01"))
        submitted_at = timezone.now()
        time_taken = min(attempt.quiz.duration_minutes * 60, max(0, int((submitted_at - attempt.started_at).total_seconds())))
        attempt.score = correct
        attempt.total_questions = total
        attempt.correct_answers = correct
        attempt.wrong_answers = wrong
        attempt.unanswered_questions = unanswered
        attempt.percentage = percentage
        attempt.time_taken = time_taken
        attempt.is_passed = percentage >= attempt.quiz.pass_percentage
        attempt.submitted_at = submitted_at
        attempt.ai_feedback = attempt_feedback(attempt)
        attempt.save(update_fields=["score", "total_questions", "correct_answers", "wrong_answers", "unanswered_questions", "percentage", "time_taken", "is_passed", "submitted_at", "ai_feedback"])
        result, _ = Result.objects.update_or_create(
            attempt=attempt,
            defaults={
                "user": attempt.user,
                "course": attempt.quiz.course,
                "quiz": attempt.quiz,
                "total_questions": total,
                "correct_answers": correct,
                "incorrect_answers": wrong,
                "unanswered_questions": unanswered,
                "percentage": percentage,
                "time_taken": time_taken,
                "is_passed": attempt.is_passed,
            },
        )
        Leaderboard.objects.update_or_create(
            result=result,
            defaults={"user": attempt.user, "course": attempt.quiz.course, "percentage": percentage, "completed_at": submitted_at},
        )
        if attempt.is_passed:
            Certificate.objects.get_or_create(attempt=attempt)
        cache.delete("home_stats")
        return attempt


def _save_posted_answers(attempt, post_data):
    question_ids = set(attempt.quiz.questions.values_list("id", flat=True))
    choices = Choice.objects.select_related("question").filter(question_id__in=question_ids)
    valid_choices = {choice.id: choice for choice in choices}
    pending_answers = []

    for key, value in post_data.items():
        if not key.startswith("question_") or not value:
            continue
        try:
            question_id = int(key.removeprefix("question_"))
            choice_id = int(value)
        except ValueError:
            continue
        choice = valid_choices.get(choice_id)
        if question_id in question_ids and choice and choice.question_id == question_id:
            pending_answers.append((question_id, choice))

    for question_id, choice in pending_answers:
        Answer.objects.update_or_create(
            attempt=attempt,
            question_id=question_id,
            defaults={"selected_choice": choice},
        )


def _user_rank(user):
    best_scores = (
        QuizAttempt.objects.filter(submitted_at__isnull=False)
        .values("user")
        .annotate(best=Max("percentage"))
        .order_by("-best")
    )
    for index, row in enumerate(best_scores, start=1):
        if row["user"] == user.id:
            return index
    return "-"
