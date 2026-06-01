from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset_view, name="password_reset"),
    path("password-reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html"), name="password_reset_confirm"),
    path("password-reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("courses/", views.courses, name="courses"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("my-quizzes/", views.my_quizzes, name="my_quizzes"),
    path("quiz/<slug:slug>/start/", views.start_quiz, name="start_quiz"),
    path("attempt/<int:attempt_id>/", views.take_quiz, name="take_quiz"),
    path("attempt/<int:attempt_id>/save/", views.save_answer, name="save_answer"),
    path("attempt/<int:attempt_id>/submit/", views.submit_quiz, name="submit_quiz"),
    path("results/", views.results, name="results"),
    path("results/<int:attempt_id>/", views.result_detail, name="result_detail"),
    path("certificate/<uuid:certificate_id>/", views.certificate_detail, name="certificate_detail"),
    path("certificate/<uuid:certificate_id>/download/", views.certificate_pdf, name="certificate_pdf"),
    path("verify/<uuid:certificate_id>/", views.certificate_verify, name="certificate_verify"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("profile/", views.profile, name="profile"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("api/ai/chat/", views.ai_chat, name="ai_chat"),
    path("api/theme/", views.save_theme, name="save_theme"),
]
