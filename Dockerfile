# Use official Python image
FROM python:3.10

# Set working directory
WORKDIR /app

# Update package list (if needed for future dependencies)
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn
RUN pip install gunicorn

# Copy the Django project files
COPY . .

# Expose port 8000
EXPOSE 8000

# Run the Django application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "RideShare.wsgi:application"]
