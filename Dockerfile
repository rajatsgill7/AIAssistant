FROM python:3.12

RUN mkdir /src
WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy project dependencies
COPY ./requirements.txt src/requirements.txt

# Run project dependencies
RUN pip install --no-cache-dir -r src/requirements.txt

COPY . .

EXPOSE 8080
