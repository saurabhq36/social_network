# # Use the official Python image from the Docker Hub
# FROM python:3.11-slim

# # Set the working directory in the container
# WORKDIR /app

# # Copy the requirements file into the container
# COPY requirements.txt .

# # Install the required packages
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the rest of the application code into the container
# COPY . .

# # Expose the port the app runs on
# EXPOSE 8000

# # Define environment variable
# ENV PYTHONUNBUFFERED=1

# # Run the application using gunicorn
# # CMD ["gunicorn", "--bind", "0.0.0.0:8000", "social_network.wsgi:application"]
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
















# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Define environment variable
ENV PYTHONUNBUFFERED=1

# Run the application using Django's development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
