# QuizLearn - Django Online Quiz Platform

Production-shaped Django quiz platform with student registration, course browsing, timed quizzes, result analytics, certificates, leaderboards, profiles, contact support, and an AI study assistant.

## Run Locally

```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/

## Optional Environment Variables

```powershell
$env:DJANGO_SECRET_KEY="replace-in-production"
$env:DJANGO_DEBUG="0"
$env:DJANGO_ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
$env:OPENAI_API_KEY="your-openai-key"
$env:OPENAI_MODEL="gpt-4o-mini"
$env:TAWK_TO_PROPERTY_ID="your-tawk-property-id"
```

## Main Modules

- Student authentication with direct registration, username/email login, remember me, password reset, profile editing, and password change.
- Course, quiz, question, choice, attempt, answer, certificate, contact, and AI conversation models.
- Timed quiz runner with refresh-safe timer, progress bar, previous/next navigation, autosave, and automatic submit.
- Result dashboard with score, percentage, pass/fail, time taken, AI feedback, and certificate generation after passing.
- Certificate page with verification URL, share action, and PDF download.
- Leaderboard with weekly, monthly, and all-time filters.
- Floating AI assistant with OpenAI integration when configured and safe local fallbacks otherwise.
