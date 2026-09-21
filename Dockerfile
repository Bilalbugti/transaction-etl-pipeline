# Start from a lightweight, official Python environment
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy just the requirements file first (Docker caching optimization)
COPY requirements.txt .

# Install the Python libraries this pipeline needs
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the project files into the container
COPY . .

# The command that runs when the container starts
CMD ["python", "src/main.py"]
