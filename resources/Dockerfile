# Use an official Python runtime as a parent image
FROM python:3.12

# Set the working directory in the container
WORKDIR /src

# Copy requirements first (for caching optimization)
COPY requirements.txt /src/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . /src/

# Expose FastAPI default port
EXPOSE 5000

# Run the application with Uvicorn
CMD ["uvicorn", "src.TwilioElevenLabs:app", "--host", "0.0.0.0", "--port", "5000"]
