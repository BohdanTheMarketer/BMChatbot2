from setuptools import setup, find_packages

setup(
    name="business-match-bot",
    version="1.0.0",
    description="Telegram bot for business networking and professional matching",
    author="Business Match",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot==20.8",
        "pandas==2.1.4",
        "openai==1.3.7",
        "python-dotenv==1.0.0",
        "openpyxl==3.1.2",
        "flask==3.0.0",
        "requests==2.31.0",
    ],
    python_requires=">=3.8",
)

