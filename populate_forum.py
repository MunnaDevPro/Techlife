from forum.models import Question, Answer
from django.contrib.auth import get_user_model
import random
from django.utils import timezone
from datetime import timedelta
from django.utils.text import slugify

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()

if not user:
    print("No users in the database to assign authors to.")
    exit()

questions_data = [
    "How to properly structure a React application?",
    "What are the best practices for REST API design?",
    "How does asyncio work in Python?",
    "Why use Docker for development?",
    "What is the difference between SQL and NoSQL?",
    "How to optimize PostgreSQL queries?",
    "Understanding the JavaScript event loop",
    "What is continuous integration and continuous deployment?",
    "How to manage state in a large Vue application?",
    "What are the pros and cons of microservices architecture?",
    "How to secure a web application from XSS attacks?",
    "What is the role of a reverse proxy like Nginx?",
    "How to implement authentication in Django?",
    "What are the differences between React and Angular?",
    "How to use Git effectively in a team?",
    "What is serverless computing?",
    "How to design a scalable database schema?",
    "What is the importance of writing unit tests?",
    "How to handle CORS in a RESTful API?",
    "What are the benefits of using TypeScript over JavaScript?",
    "How to monitor application performance in production?",
    "What is GraphQL and how does it compare to REST?",
    "How to deploy a Django app to AWS?",
    "What are some common design patterns in object-oriented programming?",
    "How to optimize front-end performance?"
]

answers_data = [
    "I usually start by organizing my components into logical folders.",
    "Using Docker has completely changed how I deploy applications. It makes things so much more consistent.",
    "Make sure to index your database columns that are frequently queried.",
    "The event loop handles asynchronous callbacks in JavaScript, allowing non-blocking I/O.",
    "State management libraries like Redux or Vuex are essential for large apps.",
    "Always sanitize user input to prevent XSS and SQL injection.",
    "Nginx acts as a great reverse proxy, handling SSL termination and static file serving.",
    "Django provides built-in authentication views and forms which are highly customizable.",
    "I prefer React for its simplicity and huge ecosystem, though Angular provides a more complete framework out of the box.",
    "Git branches and pull requests are crucial for code review and collaboration.",
    "Serverless can save money and reduce operational overhead, but watch out for cold starts.",
    "Unit tests give you confidence when refactoring and catch bugs early in the development cycle.",
    "CORS headers must be properly configured on your server to allow requests from different origins.",
    "TypeScript adds static typing, which helps catch errors at compile time rather than runtime.",
    "Use tools like New Relic or Datadog to monitor performance and set up alerts for anomalies.",
    "GraphQL allows clients to request exactly the data they need, reducing over-fetching.",
    "AWS Elastic Beanstalk or ECS are great options for deploying Django applications.",
    "Design patterns like Singleton, Factory, and Observer are incredibly useful in software architecture.",
    "Minify your CSS/JS, optimize images, and use a CDN for better front-end performance."
]

print(f"Adding 25 questions and answers for user {user.email}...")

created_questions = []

# Generate Questions
for i, title in enumerate(questions_data):
    q = Question.objects.create(
        title=title,
        slug=slugify(title) + f"-{random.randint(1000,9999)}",
        content=f"<p>I am looking for detailed information and best practices on: <strong>{title}</strong>. Any help or resources would be appreciated.</p>",
        author=user,
    )
    # randomly backdate between 1 and 30 days
    q.created_at = timezone.now() - timedelta(days=random.randint(1, 30), hours=random.randint(1, 24))
    q.save(update_fields=['created_at'])
    created_questions.append(q)

# Generate Answers
for i in range(40):
    q = random.choice(created_questions)
    ans = random.choice(answers_data)
    a = Answer.objects.create(
        question=q,
        content=ans + f" Here are some extra thoughts on {q.title}...",
        author=user,
    )
    # randomly backdate, but make sure it's after question creation
    a.created_at = q.created_at + timedelta(hours=random.randint(1, 48))
    a.save(update_fields=['created_at'])

print("Done generating dummy forum questions and answers.")
