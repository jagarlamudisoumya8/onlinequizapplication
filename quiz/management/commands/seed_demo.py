from django.core.management.base import BaseCommand
from django.utils.text import slugify

from quiz.models import Choice, Course, Question, Quiz


COURSES = [
    ("Python Programming", "Master Python syntax, control flow, functions, collections, and problem solving.", "beginner"),
    ("Django Development", "Build secure full-stack web applications with Django models, views, forms, and templates.", "intermediate"),
    ("Java Programming", "Learn object-oriented Java, classes, interfaces, collections, and exception handling.", "beginner"),
    ("Web Development", "Understand HTML, CSS, JavaScript, responsive layouts, and browser fundamentals.", "beginner"),
    ("Data Structures", "Practice arrays, stacks, queues, linked lists, trees, graphs, and algorithmic thinking.", "intermediate"),
    ("Machine Learning", "Explore supervised learning, evaluation, features, models, and training workflows.", "advanced"),
    ("Artificial Intelligence", "Study AI fundamentals, search, reasoning, neural networks, and responsible AI.", "advanced"),
    ("SQL Database", "Learn relational tables, queries, joins, aggregation, indexes, and normalization.", "beginner"),
    ("React JS", "Build component-based interfaces with props, state, effects, and reusable UI patterns.", "intermediate"),
    ("Cyber Security", "Understand threats, authentication, encryption, web security, and secure practices.", "intermediate"),
]

QUESTION_BANK = {
    "Python Programming": [
        ("Which keyword defines a function in Python?", ["func", "def", "function", "define"], 1),
        ("Which collection is ordered and mutable?", ["tuple", "list", "set", "frozenset"], 1),
        ("What does len([1, 2, 3]) return?", ["2", "3", "4", "Error"], 1),
        ("Which symbol starts a comment?", ["//", "#", "--", "/*"], 1),
        ("Which loop iterates over items?", ["for", "switch", "case", "try"], 0),
        ("What is the output type of input()?", ["int", "str", "bool", "list"], 1),
        ("Which block handles exceptions?", ["catch", "except", "rescue", "handle"], 1),
        ("Which operator checks equality?", ["=", "==", "===", "!="], 1),
        ("What creates a dictionary?", ["[]", "()", "{}", "<>"], 2),
        ("Which keyword returns a value?", ["send", "return", "yieldonly", "break"], 1),
    ],
    "Django Development": [
        ("Which file commonly stores project settings?", ["views.py", "settings.py", "forms.py", "admin.py"], 1),
        ("What maps URLs to view functions?", ["urls.py", "models.py", "apps.py", "wsgi.py"], 0),
        ("What does ORM stand for?", ["Object Relational Mapper", "Open Route Manager", "Online Render Mode", "Object Request Method"], 0),
        ("Which template tag protects forms?", ["csrf_token", "safe", "url", "static"], 0),
        ("Which command applies migrations?", ["runserver", "migrate", "collectstatic", "shell"], 1),
        ("Which class creates database tables?", ["View", "Model", "Form", "Template"], 1),
        ("Which decorator restricts pages to authenticated users?", ["staff_only", "login_required", "csrf_exempt", "cache_page"], 1),
        ("What stores uploaded user files locally by default?", ["MEDIA_ROOT", "STATIC_ROOT", "BASE_DIR", "ROOT_URLCONF"], 0),
        ("Which method is used for form submissions?", ["POST", "TRACE", "HEAD", "OPTIONS"], 0),
        ("What does select_related optimize?", ["Foreign key queries", "CSS loading", "Password hashing", "Email templates"], 0),
    ],
    "Java Programming": [
        ("Which method starts a Java application?", ["start()", "main()", "run()", "init()"], 1),
        ("Which keyword creates a subclass?", ["extends", "inherits", "parent", "superclass"], 0),
        ("Which type stores true or false?", ["boolean", "bit", "truth", "flag"], 0),
        ("Which keyword creates an object?", ["make", "new", "object", "build"], 1),
        ("Which construct handles exceptions?", ["try-catch", "if-else", "for-each", "switch-only"], 0),
        ("Which collection stores unique values?", ["ArrayList", "HashSet", "Stack", "Queue"], 1),
        ("Which access modifier is most restrictive?", ["public", "protected", "private", "default"], 2),
        ("Which keyword prevents inheritance?", ["static", "final", "const", "sealedonly"], 1),
        ("Which file extension is Java source?", [".class", ".java", ".jar", ".javac"], 1),
        ("Which keyword refers to current object?", ["this", "self", "current", "me"], 0),
    ],
    "Web Development": [
        ("What does HTML define?", ["Structure", "Database", "Server CPU", "Encryption"], 0),
        ("Which language styles web pages?", ["SQL", "CSS", "Python", "Java"], 1),
        ("Which tag creates a link?", ["a", "linkonly", "href", "url"], 0),
        ("Which CSS property changes text color?", ["font-size", "color", "display", "margin"], 1),
        ("Which JavaScript method selects an element by id?", ["getElementById", "selectId", "queryId", "findId"], 0),
        ("What does responsive design support?", ["Different screen sizes", "Only desktops", "Only printers", "Only servers"], 0),
        ("Which HTTP method reads data?", ["GET", "POST", "PATCH", "DELETE"], 0),
        ("Which tag loads JavaScript?", ["script", "style", "meta", "section"], 0),
        ("Which CSS layout is one-dimensional?", ["Flexbox", "SQL", "DOM", "JSON"], 0),
        ("What does DOM represent?", ["Document Object Model", "Data Order Map", "Design Object Mode", "Direct Output Method"], 0),
    ],
    "Data Structures": [
        ("Which structure uses LIFO?", ["Queue", "Stack", "Tree", "Graph"], 1),
        ("Which structure uses FIFO?", ["Queue", "Stack", "Heap", "Set"], 0),
        ("Which structure has nodes and edges?", ["Graph", "Array", "String", "Tuple"], 0),
        ("Which tree node has no children?", ["Root", "Leaf", "Parent", "Sibling"], 1),
        ("Which operation adds to a stack?", ["push", "enqueue", "visit", "hash"], 0),
        ("Which search works on sorted arrays?", ["Binary search", "Random search", "Linear only", "Hash walk"], 0),
        ("Which structure maps keys to values?", ["Hash table", "Stack", "Queue", "Tree only"], 0),
        ("What is an array index usually based on?", ["Zero", "Ten", "Infinity", "Null only"], 0),
        ("Which traversal visits tree levels?", ["BFS", "DFS only", "Sort", "Hash"], 0),
        ("Which structure can model hierarchy?", ["Tree", "Queue only", "Array only", "Set only"], 0),
    ],
    "Machine Learning": [
        ("What is supervised learning trained with?", ["Labeled data", "No data", "Only images", "Only rules"], 0),
        ("What is overfitting?", ["Memorizing training data", "Fast loading", "Data cleaning only", "Encryption"], 0),
        ("Which metric is common for classification?", ["Accuracy", "Latency only", "Padding", "Uptime"], 0),
        ("What is a feature?", ["Input variable", "Server", "Password", "Template"], 0),
        ("Which split evaluates generalization?", ["Test set", "CSS file", "Admin page", "Cache"], 0),
        ("Which model is used for regression?", ["Linear regression", "Bubble sort", "Hash map", "DNS"], 0),
        ("What does training adjust?", ["Model parameters", "Monitor brightness", "HTML tags", "Port number"], 0),
        ("Which problem predicts categories?", ["Classification", "Compression", "Rendering", "Routing"], 0),
        ("What is normalization used for?", ["Scaling data", "Deleting users", "Styling buttons", "Creating URLs"], 0),
        ("Which library is common in Python ML?", ["scikit-learn", "Bootstrap", "Django templates", "SQLite shell"], 0),
    ],
    "Artificial Intelligence": [
        ("What is AI broadly about?", ["Intelligent behavior in machines", "Only databases", "Only CSS", "Only cables"], 0),
        ("Which search explores neighbor states?", ["Graph search", "Color search", "File search only", "DNS search"], 0),
        ("What is NLP focused on?", ["Human language", "Image cables", "Disk partitions", "Button color"], 0),
        ("Which model is inspired by neurons?", ["Neural network", "Hash table", "Queue", "Router"], 0),
        ("What is a heuristic?", ["Useful estimate", "Final password", "Exact database", "CSS selector"], 0),
        ("Which AI concern matters in production?", ["Bias", "Font weight only", "Navbar height", "Image size only"], 0),
        ("What is reinforcement learning based on?", ["Rewards", "HTML tags", "SQL joins", "Static files"], 0),
        ("Which system recommends courses?", ["Recommendation system", "Compiler", "Firewall only", "Template tag"], 0),
        ("What is computer vision about?", ["Understanding images", "Writing emails", "Making tables", "Running migrations"], 0),
        ("What should AI avoid during quizzes?", ["Revealing answers", "Giving guidance", "Explaining rules", "Study tips"], 0),
    ],
    "SQL Database": [
        ("Which command reads rows?", ["SELECT", "INSERT", "UPDATE", "DELETE"], 0),
        ("Which clause filters rows?", ["WHERE", "ORDER", "GROUP", "LIMIT"], 0),
        ("Which operation combines tables?", ["JOIN", "MERGE CSS", "ROUTE", "CACHE"], 0),
        ("What uniquely identifies a row?", ["Primary key", "Paragraph", "Class name", "Port"], 0),
        ("Which function counts rows?", ["COUNT", "TOTALCSS", "LENHTML", "SIZEURL"], 0),
        ("Which clause sorts results?", ["ORDER BY", "SORT CSS", "RANK HTML", "VIEW BY"], 0),
        ("Which command adds rows?", ["INSERT", "SELECT", "DROP", "ALTER only"], 0),
        ("What is normalization?", ["Reducing data duplication", "Increasing font size", "Adding buttons", "Opening ports"], 0),
        ("Which constraint prevents duplicate values?", ["UNIQUE", "STYLE", "ROUTE", "CACHE"], 0),
        ("Which index benefit is common?", ["Faster lookups", "Larger images", "Darker theme", "Email reset"], 0),
    ],
    "React JS": [
        ("What is React mainly used for?", ["User interfaces", "Databases", "Operating systems", "Networking only"], 0),
        ("What are props?", ["Component inputs", "SQL tables", "Server logs", "CSS resets"], 0),
        ("Which hook manages state?", ["useState", "useRoute", "useSQL", "useAdmin"], 0),
        ("Which hook handles side effects?", ["useEffect", "useStyleOnly", "useServer", "useTable"], 0),
        ("What is JSX?", ["JavaScript XML syntax", "Database file", "Image format", "Server engine"], 0),
        ("What should list items have?", ["key", "password", "port", "query"], 0),
        ("What triggers re-render?", ["State change", "Only page refresh", "File rename", "DNS"], 0),
        ("What composes UI in React?", ["Components", "Rows only", "Certificates", "Migrations"], 0),
        ("Which command often starts Vite apps?", ["npm run dev", "python migrate", "sql select", "git status"], 0),
        ("What does controlled input use?", ["State value", "Only CSS", "Only URL", "Only image"], 0),
    ],
    "Cyber Security": [
        ("What does authentication verify?", ["Identity", "Screen size", "Font", "Image color"], 0),
        ("What does authorization control?", ["Access permissions", "Button radius", "Page title", "Cache color"], 0),
        ("Which attack does CSRF protection reduce?", ["Forged requests", "Slow typing", "Dark mode", "Image blur"], 0),
        ("What should passwords be?", ["Strong and hashed", "Plain text", "Public", "Short only"], 0),
        ("What does HTTPS protect?", ["Data in transit", "CSS layout", "Image cropping", "Table sorting"], 0),
        ("Which vulnerability injects scripts?", ["XSS", "DNS", "SMTP", "FTP"], 0),
        ("Which principle limits damage?", ["Least privilege", "Largest access", "No logging", "Shared passwords"], 0),
        ("What is phishing?", ["Deceptive credential theft", "Database join", "Code formatter", "Chart type"], 0),
        ("What should sensitive keys use?", ["Environment variables", "Templates", "Public repos", "CSS comments"], 0),
        ("What should AI not expose?", ["Private/admin data", "Study guidance", "Quiz rules", "Course overview"], 0),
    ],
}

IMAGES = {
    "Python Programming": "https://images.unsplash.com/photo-1526379095098-d400fd0bf935?auto=format&fit=crop&w=900&q=80",
    "Django Development": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=900&q=80",
    "Java Programming": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=900&q=80",
    "Web Development": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=900&q=80",
    "Data Structures": "https://images.unsplash.com/photo-1509228627152-72ae9ae6848d?auto=format&fit=crop&w=900&q=80",
    "Machine Learning": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?auto=format&fit=crop&w=900&q=80",
    "Artificial Intelligence": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=900&q=80",
    "SQL Database": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=900&q=80",
    "React JS": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=900&q=80",
    "Cyber Security": "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=900&q=80",
}


class Command(BaseCommand):
    help = "Create 10 professional demo courses with exactly 10 questions each."

    def handle(self, *args, **options):
        required_titles = {title for title, _, _ in COURSES}
        Course.objects.exclude(title__in=required_titles).update(is_published=False)
        Quiz.objects.exclude(course__title__in=required_titles).update(is_active=False)
        for title, description, level in COURSES:
            course, _ = Course.objects.update_or_create(
                slug=slugify(title),
                defaults={
                    "title": title,
                    "description": description,
                    "duration": "5 minutes",
                    "instructor_name": "QuizLearn Faculty",
                    "level": level,
                    "thumbnail": IMAGES[title],
                    "is_published": True,
                },
            )
            quiz, _ = Quiz.objects.update_or_create(
                slug=slugify(f"{title} Quiz"),
                defaults={
                    "course": course,
                    "title": f"{title} Quiz",
                    "description": "A focused 10-question assessment with a 5-minute timer.",
                    "duration_minutes": 5,
                    "pass_percentage": 40,
                    "is_active": True,
                },
            )
            existing_orders = set(Question.objects.filter(quiz=quiz).values_list("order", flat=True))
            for order, (text, choices, correct) in enumerate(QUESTION_BANK[title], start=1):
                question, _ = Question.objects.update_or_create(
                    quiz=quiz,
                    order=order,
                    defaults={"text": text, "points": 1},
                )
                question.choices.all().delete()
                for index, choice_text in enumerate(choices):
                    Choice.objects.create(question=question, text=choice_text, is_correct=index == correct)
            Question.objects.filter(quiz=quiz).exclude(order__in=range(1, 11)).delete()
        self.stdout.write(self.style.SUCCESS("10 courses with exactly 10 questions each are ready."))
