"""AWS Elastic Beanstalk entry point.

Exposes the WSGI application callable as `application:application`.
"""
import os
from app import app as application

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    application.run(host="0.0.0.0", port=port, debug=False)
