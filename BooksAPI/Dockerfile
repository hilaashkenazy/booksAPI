FROM python:3.12.3-slim
WORKDIR /app
COPY ./requirements.txt /app
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
ENV FLASK_APP=books.py
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "8000"]