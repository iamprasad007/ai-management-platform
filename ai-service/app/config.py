import os

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8080")
TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8081")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")