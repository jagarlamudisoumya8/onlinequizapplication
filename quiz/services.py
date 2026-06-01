import json
import re
import urllib.error
import urllib.request

from django.conf import settings


def educational_ai_response(message, *, context="general", user=None, attempt=None, course=None, quiz=None):
    message = (message or "").strip()
    if not message:
        return "Ask me anything about quizzes, courses, certificates, or study planning."

    blocked = ["correct answer", "answer key", "reveal answers", "give me the answers"]
    if context in {"quiz", "active_quiz"} and any(term in message.lower() for term in blocked):
        return "I can help explain concepts and quiz rules, but I cannot reveal correct answers during an active quiz."

    if settings.OPENAI_API_KEY:
        remote = _openai_response(message, context=context, user=user, attempt=attempt, course=course, quiz=quiz)
        if remote:
            return remote

    return _fallback_response(message, context=context, attempt=attempt, course=course, quiz=quiz)


def attempt_feedback(attempt):
    quiz_title = attempt.quiz.title
    if attempt.percentage >= 85:
        headline = "Excellent Performance!"
    elif attempt.percentage >= attempt.quiz.pass_percentage:
        headline = "Great Job!"
    else:
        headline = "Needs Improvement"
    return (
        f"{headline}\n\n"
        f"You scored {attempt.percentage}% in {quiz_title}. "
        f"Correct answers: {attempt.correct_answers}; incorrect answers: {attempt.wrong_answers}; unanswered: {attempt.unanswered_questions}. "
        "Review explanations for missed questions, retake related practice, and focus on concepts that felt uncertain."
    )


def recommendations_for_user(user, courses):
    attempts = user.quiz_attempts.select_related("quiz__course").filter(submitted_at__isnull=False)[:20]
    weak_levels = {a.quiz.course.level for a in attempts if a.percentage < 70}
    completed_course_ids = {a.quiz.course_id for a in attempts}
    ranked = []
    for course in courses:
        score = 0
        if course.id not in completed_course_ids:
            score += 2
        if course.level in weak_levels:
            score += 2
        if user.profile.interests and course.title.lower() in user.profile.interests.lower():
            score += 3
        ranked.append((score, course))
    return [course for _, course in sorted(ranked, key=lambda item: item[0], reverse=True)[:3]]


def _openai_response(message, **kwargs):
    prompt = (
        "You are a safe educational assistant for an online quiz platform. "
        "Help with navigation, study guidance, quiz preparation, and result analysis. "
        "Never reveal active quiz answers, modify scores, or expose admin/private data.\n\n"
        f"Context: {kwargs.get('context')}\nStudent question: {message}"
    )
    body = json.dumps(
        {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "Be concise, friendly, accurate, and safe for students."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError):
        return ""


def _fallback_response(message, **kwargs):
    text = message.lower()
    course = kwargs.get("course")
    quiz = kwargs.get("quiz")
    attempt = kwargs.get("attempt")
    if "certificate" in text:
        return "Open Results, choose a passed quiz, then use Download PDF on the certificate page."
    if "reset" in text or "password" in text:
        return "Use Forgot Password on the login page. The reset email is sent to your registered email address."
    if "start" in text and "quiz" in text:
        return "Go to Courses, open a course, choose an active quiz, and press Start Quiz. The timer begins immediately."
    if "practice" in text or "important" in text:
        title = quiz.title if quiz else (course.title if course else "this course")
        return f"For {title}, review definitions, common examples, edge cases, and short practice problems. I can explain concepts, but I will not reveal live quiz answers."
    if attempt:
        return attempt_feedback(attempt)
    if re.search(r"django|python|oop|loop|inheritance", text):
        return "Here is a quick study path: learn the core definition, read one simple example, write a tiny program, then explain it back in your own words."
    return "I can help you find courses, start quizzes, understand results, download certificates, reset passwords, and prepare for topics."


def certificate_pdf_bytes(certificate, absolute_verify_url):
    attempt = certificate.attempt
    name = attempt.user.get_full_name() or attempt.user.username
    lines = [
        "Certificate of Achievement",
        "QuizLearn Professional Learning Platform",
        f"Student: {name}",
        f"Course: {attempt.quiz.course.title}",
        f"Percentage: {attempt.percentage}%",
        f"Date: {certificate.issued_at:%d %B %Y}",
        f"Certificate ID: {certificate.certificate_id}",
        "Authorized Signature: QuizLearn Academic Director",
        f"Verify: {absolute_verify_url}",
    ]
    stream = "BT /F1 20 Tf 72 730 Td " + " Tj 0 -42 Td ".join(f"({ _pdf_escape(line) })" for line in lines) + " Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream".encode("latin-1"),
    ]
    pdf = [b"%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in pdf))
        pdf.append(f"{index} 0 obj\n".encode("latin-1") + obj + b"\nendobj\n")
    xref_at = sum(len(part) for part in pdf)
    pdf.append(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode("latin-1"))
    for offset in offsets[1:]:
        pdf.append(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.append(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF".encode("latin-1"))
    return b"".join(pdf)


def _pdf_escape(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
